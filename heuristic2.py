from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import itertools
import math

EPS = 1e-9


# =========================================================
# MODEL 2 COMPATIBLE HEURISTIC
# =========================================================

@dataclass(frozen=True)
class Pattern:
    seq: Tuple[int, ...]
    piece_type: int
    used_length: float

    @property
    def regular_seq(self):
        return self.seq[:-1]

    @property
    def last_demand(self):
        return self.seq[-1]

    def paper_waste(self, L):
        return max(0.0, L - self.used_length)

    def has_waste(self, L):
        return self.paper_waste(L) > EPS

    def blade_count(self, L):
        # Model 2: Bj = number of regular cuts + V
        if self.has_waste(L):
            return len(self.regular_seq) + 1
        return len(self.regular_seq)

    def p_positions(self, LD, B):
        # Model 2 P[1..B]
        vals = []
        pos = 0.0

        for d in self.regular_seq:
            pos += LD[d]
            vals.append(pos)

        if len(vals) == 0:
            vals.append(0.0)

        while len(vals) < B:
            vals.append(vals[-1])

        return tuple(round(x, 6) for x in vals[:B])

    def final_distance_F(self, LD, L):
        regular_sum = sum(LD[d] for d in self.regular_seq)

        if self.has_waste(L):
            return round(self.used_length, 6)

        # Model 2: if no waste, V=0 and F = P[B]
        return round(regular_sum, 6)

    def config(self, LD, L, B):
        return (
            self.blade_count(L),
            self.p_positions(LD, B),
            self.final_distance_F(LD, L)
        )

    def display_blade_distances(self, LD, L):
        vals = []
        pos = 0.0

        for d in self.regular_seq:
            pos += LD[d]
            vals.append(round(pos, 4))

        if self.has_waste(L):
            vals.append(round(self.used_length, 4))

        return tuple(vals)

    def demand_count(self):
        c = defaultdict(int)
        for d in self.seq:
            c[d] += 1
        return dict(c)


@dataclass
class ReelPlan:
    reel_id: int
    reel_type: Optional[int]
    used: bool
    pattern: Optional[Pattern]


# =========================================================
# BASIC HELPERS
# =========================================================

def can_apply_pattern(p, remaining):
    need = p.demand_count()
    return all(remaining.get(d, 0) >= c for d, c in need.items())


def apply_pattern(p, remaining):
    new_remaining = dict(remaining)

    for d, c in p.demand_count().items():
        new_remaining[d] -= c

    return new_remaining


def remaining_key(D, remaining):
    return tuple(remaining[d] for d in D)


def is_finished(D, remaining):
    return all(remaining[d] == 0 for d in D)


def reel_transition_tw(prev, curr, LD, L, B):
    if not curr.used or curr.pattern is None:
        return 0

    if prev is None:
        return 1

    if not prev.used or prev.pattern is None:
        return 1

    if prev.pattern.config(LD, L, B) == curr.pattern.config(LD, L, B):
        return 0

    return 1


def normalized_objective(pw, tw, n, L, lam):
    return lam * (pw / (n * L)) + (1.0 - lam) * (tw / n)


# =========================================================
# PATTERN GENERATION
# =========================================================

def generate_patterns_for_type(D, TD, LD, ND, B, L, t):
    type_demands = [d for d in D if TD[d] == t and ND[d] > 0]

    patterns = {}
    max_pieces = B + 1

    def backtrack(seq, used, counts):
        if seq:
            p = Pattern(tuple(seq), t, used)

            if p.used_length <= L + EPS and p.blade_count(L) <= B:
                patterns[p.seq] = p

        if len(seq) >= max_pieces:
            return

        for d in type_demands:
            if counts.get(d, 0) >= ND[d]:
                continue

            new_used = used + LD[d]

            if new_used <= L + EPS:
                counts[d] = counts.get(d, 0) + 1
                seq.append(d)

                backtrack(seq, new_used, counts)

                seq.pop()
                counts[d] -= 1

    backtrack([], 0.0, {})

    result = list(patterns.values())

    result.sort(
        key=lambda p: (
            p.paper_waste(L),
            p.blade_count(L),
            -len(p.seq),
            p.seq
        )
    )

    return result


def generate_all_patterns(data):
    D = data["D"]
    T = data["T"]
    TD = data["TD"]
    LD = data["LD"]
    ND = data["ND"]
    B = int(data["B"])
    L = float(data["L"])

    patterns_by_type = {}

    for t in T:
        patterns_by_type[t] = generate_patterns_for_type(
            D, TD, LD, ND, B, L, t
        )

    return patterns_by_type


# =========================================================
# LOOK-AHEAD ESTIMATION
# =========================================================

def lower_bound_remaining_pw(D, TD, LD, remaining, L):
    total_by_type = defaultdict(float)

    for d in D:
        total_by_type[TD[d]] += remaining[d] * LD[d]

    lb = 0.0

    for total in total_by_type.values():
        if total <= EPS:
            continue

        reels_needed = math.ceil(total / L)
        lb += reels_needed * L - total

    return lb


def candidate_patterns(patterns_by_type, remaining, prev, LD, L, B, max_candidates_per_type):
    candidates = []

    # First try same pattern again, because TW becomes 0
    if prev and prev.used and prev.pattern:
        if can_apply_pattern(prev.pattern, remaining):
            candidates.append(prev.pattern)

    for t, patterns in patterns_by_type.items():
        feasible = []

        for p in patterns:
            if can_apply_pattern(p, remaining):
                feasible.append(p)

        feasible.sort(
            key=lambda p: (
                0 if prev and prev.used and prev.pattern and
                p.config(LD, L, B) == prev.pattern.config(LD, L, B) else 1,
                p.paper_waste(L),
                p.blade_count(L),
                -len(p.seq)
            )
        )

        candidates.extend(feasible[:max_candidates_per_type])

    unique = {}

    for p in candidates:
        unique[p.seq] = p

    return list(unique.values())


# =========================================================
# BEAM SEARCH CONSTRUCTION
# =========================================================

@dataclass
class State:
    pw: float
    tw: int
    remaining: Dict[int, int]
    plans: List[ReelPlan]
    prev: Optional[ReelPlan]


def construct_model2_heuristic(data, beam_width=500, max_candidates_per_type=120):
    S = list(data["S"])
    D = list(data["D"])
    LD = data["LD"]
    TD = data["TD"]
    ND = data["ND"]
    L = float(data["L"])
    B = int(data["B"])
    lam = float(data["lambda"])
    n = len(S)

    total_demand_length = sum(ND[d] * LD[d] for d in D)

    if total_demand_length > n * L + EPS:
        print("WARNING: Total demand length exceeds total jumbo reel capacity.")

    patterns_by_type = generate_all_patterns(data)

    states = [
        State(
            pw=0.0,
            tw=0,
            remaining=dict(ND),
            plans=[],
            prev=None
        )
    ]

    for j in S:
        next_states = []

        for st in states:

            if is_finished(D, st.remaining):
                curr = ReelPlan(j, None, False, None)

                next_states.append(
                    State(
                        pw=st.pw,
                        tw=st.tw,
                        remaining=dict(st.remaining),
                        plans=st.plans + [curr],
                        prev=curr
                    )
                )
                continue

            cand = candidate_patterns(
                patterns_by_type,
                st.remaining,
                st.prev,
                LD,
                L,
                B,
                max_candidates_per_type
            )

            for p in cand:
                curr = ReelPlan(j, p.piece_type, True, p)

                add_pw = p.paper_waste(L)
                add_tw = reel_transition_tw(st.prev, curr, LD, L, B)

                new_remaining = apply_pattern(p, st.remaining)

                next_states.append(
                    State(
                        pw=st.pw + add_pw,
                        tw=st.tw + add_tw,
                        remaining=new_remaining,
                        plans=st.plans + [curr],
                        prev=curr
                    )
                )

        compressed = {}

        for st in next_states:
            prev_config = None

            if st.prev and st.prev.used and st.prev.pattern:
                prev_config = st.prev.pattern.config(LD, L, B)

            key = (
                remaining_key(D, st.remaining),
                prev_config,
                len(st.plans)
            )

            current_score = normalized_objective(st.pw, st.tw, n, L, lam)

            if key not in compressed:
                compressed[key] = st
            else:
                old = compressed[key]
                old_score = normalized_objective(old.pw, old.tw, n, L, lam)

                if current_score < old_score:
                    compressed[key] = st

        states = sorted(
            compressed.values(),
            key=lambda st: (
                normalized_objective(st.pw, st.tw, n, L, lam)
                + 0.20 * lam * lower_bound_remaining_pw(D, TD, LD, st.remaining, L) / (n * L),
                sum(st.remaining[d] for d in D),
                st.tw,
                st.pw
            )
        )[:beam_width]

    feasible = [st for st in states if is_finished(D, st.remaining)]

    if feasible:
        best = min(
            feasible,
            key=lambda st: normalized_objective(st.pw, st.tw, n, L, lam)
        )
    else:
        best = min(
            states,
            key=lambda st: (
                sum(st.remaining[d] for d in D),
                normalized_objective(st.pw, st.tw, n, L, lam)
            )
        )

        print("WARNING: Heuristic could not satisfy all demands with given jumbo reels.")
        print("Remaining demands:")
        for d in D:
            if best.remaining[d] > 0:
                print(f"d = {d}, remaining = {best.remaining[d]}")

    return best.plans


# =========================================================
# OBJECTIVE
# =========================================================

def total_objective(plans, data):
    L = float(data["L"])
    B = int(data["B"])
    LD = data["LD"]

    pw = 0.0
    tw = 0
    prev = None

    for r in plans:
        if r.used and r.pattern:
            pw += r.pattern.paper_waste(L)

        tw += reel_transition_tw(prev, r, LD, L, B)
        prev = r

    return pw, tw


# =========================================================
# SOLVER OUTPUT SAME AS MODEL 2
# =========================================================

def solve_model2_heuristic(data, beam_width=500, max_candidates_per_type=120):
    plans = construct_model2_heuristic(
        data,
        beam_width=beam_width,
        max_candidates_per_type=max_candidates_per_type
    )

    pw, tw = total_objective(plans, data)

    S = list(data["S"])
    D = list(data["D"])
    LD = data["LD"]
    TD = data["TD"]

    L = float(data["L"])
    B = int(data["B"])
    lam = float(data["lambda"])
    lam1 = 1.0 - lam

    n = len(S)
    PW_max = n * L

    print("\n==============================")
    print("OBJECTIVE FUNCTION DETAILS")
    print("==============================")

    print("\nZ = λ·(PW/(nL)) + (1-λ)·(TW/n)")

    print("\nVALUES:")
    print(f"Total PW = {round(pw, 4)}")
    print(f"Total TW = {int(round(tw))}")

    print("\nNORMALIZED:")
    print(f"PW_norm = {round(pw, 4)} / {PW_max} = {round(pw / PW_max, 6)}")
    print(f"TW_norm = {int(round(tw))} / {n} = {round(tw / n, 6)}")

    Z_norm = normalized_objective(pw, tw, n, L, lam)

    print("\nFINAL OBJECTIVE:")
    print(
        f"Z = {lam}×{round(pw / PW_max, 6)} + "
        f"{round(lam1, 4)}×{round(tw / n, 6)} = {round(Z_norm, 6)}"
    )

    for r in plans:
        print()

        title = f"Jumbo Reel {r.reel_id} (Type {r.reel_type})"
        print(title)
        print("-" * len(title))

        if not r.used or r.pattern is None:
            print("Used blades: 0")
            print("Not used")
            print("Paper waste:", 0.0)
            print("Time waste:", 0)
            print("Blade distances: ()")
            continue

        p = r.pattern

        print(f"Used blades: {p.blade_count(L)}")

        for d in p.regular_seq:
            print(f"d = {d} (Type {TD[d]} ) length {LD[d]}")

        if p.paper_waste(L) > EPS:
            print(
                f"Last assigned length: d = {p.last_demand} "
                f"(Type {TD[p.last_demand]} ) length {LD[p.last_demand]}"
            )
        else:
            print(
                f"Last assigned length (no paper waste): d = {p.last_demand} "
                f"(Type {TD[p.last_demand]} ) length {LD[p.last_demand]}"
            )

        print("Paper waste:", round(p.paper_waste(L), 6))

        prev_index = plans.index(r) - 1
        prev = plans[prev_index] if prev_index >= 0 else None

        print("Time waste:", reel_transition_tw(prev, r, LD, L, B))
        print("Blade distances:", p.display_blade_distances(LD, L))

    return plans


def run_model2(data):
    return solve_model2_heuristic(data)


# =========================================================
# EXAMPLE TEST DATA
# =========================================================

if __name__ == "__main__":
    data_model2_test = {

        "S": list(range(1, 9)),  # 8 reel
        "D": list(range(1, 13)),
        "T": [1, 2, 3],

        "B": 5,
        "L": 320.0,
        "lambda": 0.5,

        # =========================
        # DEMAND TYPES
        # =========================
        "TD": {
            1: 1, 2: 1, 3: 1, 4: 1,
            5: 2, 6: 2, 7: 2, 8: 2,
            9: 3, 10: 3, 11: 3, 12: 3
        },

        # =========================
        # LENGTHS
        # =========================
        "LD": {
            1: 140, 2: 120, 3: 100, 4: 80,
            5: 150, 6: 110, 7: 90, 8: 70,
            9: 160, 10: 130, 11: 95, 12: 60
        },

        # =========================
        # DEMANDS
        # =========================
        "ND": {
            1: 2, 2: 1, 3: 2, 4: 1,
            5: 1, 6: 2, 7: 2, 8: 1,
            9: 1, 10: 2, 11: 1, 12: 2
        }
    }
    solve_model2_heuristic(data_model2_test)
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import random

EPS = 1e-9


# =========================================================
# DATA STRUCTURES
# =========================================================

@dataclass
class Pattern:
    assignments: Dict[int, int]          # regular cuts
    last_demand: int                     # final demand
    used_length: float                   # regular + final
    blade_positions: List[float]         # regular blade positions
    piece_type: int

    def paper_waste(self, L: float) -> float:
        return max(0.0, L - self.used_length)

    @property
    def paper_waste_value(self) -> float:
        return getattr(self, "_paper_waste_value", 0.0)

    @paper_waste_value.setter
    def paper_waste_value(self, value: float) -> None:
        self._paper_waste_value = value

    def V(self) -> int:
        return 1 if self.paper_waste_value > EPS else 0

    def regular_blade_count(self) -> int:
        return len(self.blade_positions)

    def blade_count(self) -> int:
        return self.regular_blade_count() + self.V()

    def final_position(self) -> float:
        if self.V() == 1:
            return self.used_length
        if self.blade_positions:
            return self.blade_positions[-1]
        return 0.0

    def display_blade_distances(self, LD) -> Tuple[float, ...]:
        vals = []
        pos = 0.0

        for d, cnt in sorted(self.assignments.items()):
            for _ in range(cnt):
                pos += LD[d]
                vals.append(round(pos, 4))

        if self.V() == 1:
            pos += LD[self.last_demand]
            vals.append(round(pos, 4))

        return tuple(vals)

    def config(self) -> Tuple[int, Tuple[float, ...], float]:
        return (
            self.blade_count(),
            tuple(round(x, 4) for x in self.blade_positions),
            round(self.final_position(), 4),
        )


@dataclass
class ReelPlan:
    reel_id: int
    reel_type: int
    used: bool
    pattern: Optional[Pattern] = None


# =========================================================
# CORE HELPERS
# =========================================================

def compute_pattern_from_sequence(
    seq: List[int],
    LD: Dict[int, float],
    TD: Dict[int, int],
    reel_type: int,
    L: float,
    B: int
) -> Optional[Pattern]:
    """
    seq = [d1, d2, ..., dk]
    son eleman final demand, öncekiler regular cuts
    """
    if not seq:
        return None

    if any(TD[d] != reel_type for d in seq):
        return None

    total = sum(LD[d] for d in seq)
    if total > L + EPS:
        return None

    regular = seq[:-1]
    last_demand = seq[-1]

    waste = L - total
    V = 1 if waste > EPS else 0

    # Exact model mantığı: Bj = regular cuts + V
    if len(regular) + V > B:
        return None

    pos = 0.0
    blade_positions = []
    for d in regular:
        pos += LD[d]
        blade_positions.append(round(pos, 9))

    assignments: Dict[int, int] = {}
    for d in regular:
        assignments[d] = assignments.get(d, 0) + 1

    p = Pattern(
        assignments=assignments,
        last_demand=last_demand,
        used_length=total,
        blade_positions=blade_positions,
        piece_type=reel_type,
    )
    p.paper_waste_value = max(0.0, waste)
    return p


def can_apply_once(pattern: Pattern, remaining: Dict[int, int]) -> bool:
    need = dict(pattern.assignments)
    need[pattern.last_demand] = need.get(pattern.last_demand, 0) + 1
    return all(remaining.get(d, 0) >= cnt for d, cnt in need.items())


def apply_pattern_once(pattern: Pattern, remaining: Dict[int, int]) -> None:
    for d, cnt in pattern.assignments.items():
        remaining[d] -= cnt
    remaining[pattern.last_demand] -= 1


def max_multiplicity(pattern: Pattern, remaining: Dict[int, int]) -> int:
    need = dict(pattern.assignments)
    need[pattern.last_demand] = need.get(pattern.last_demand, 0) + 1
    vals = [remaining.get(d, 0) // cnt for d, cnt in need.items()]
    return min(vals) if vals else 0


def reel_transition_tw(prev_plan: Optional[ReelPlan], curr_plan: ReelPlan) -> int:
    """
    Model 1'e daha uygun TW mantığı:
    - current reel unused => TW = 0
    - first used reel => TW = 1
    - previous reel unused, current used => TW = 1
    - two consecutive used reels arasında config farklıysa => TW = 1
    - aynıysa => TW = 0
    """
    if not curr_plan.used or curr_plan.pattern is None:
        return 0

    if prev_plan is None:
        return 1

    if (not prev_plan.used) or (prev_plan.pattern is None):
        return 1

    prev_pattern = prev_plan.pattern
    curr_pattern = curr_plan.pattern

    if prev_pattern.blade_count() != curr_pattern.blade_count():
        return 1

    if len(prev_pattern.blade_positions) != len(curr_pattern.blade_positions):
        return 1

    for a, b in zip(prev_pattern.blade_positions, curr_pattern.blade_positions):
        if abs(a - b) > EPS:
            return 1

    if abs(prev_pattern.final_position() - curr_pattern.final_position()) > EPS:
        return 1

    return 0


# =========================================================
# CANDIDATE GENERATION
# =========================================================

def greedy_sequence(
    items: List[Tuple[float, int, int]],
    L: float,
    B: int
) -> List[int]:
    seq: List[int] = []
    used = 0.0

    for length, did, max_cnt in sorted(items, reverse=True):
        taken = 0
        while taken < max_cnt:
            new_used = used + length
            if new_used > L + EPS:
                break

            temp_seq = seq + [did]
            regular_count = max(0, len(temp_seq) - 1)
            temp_waste = L - new_used
            V = 1 if temp_waste > EPS else 0

            if regular_count + V > B:
                break

            seq.append(did)
            used = new_used
            taken += 1

    return seq


def randomized_greedy_sequence(
    items: List[Tuple[float, int, int]],
    L: float,
    B: int,
    alpha: float = 0.25
) -> List[int]:
    seq: List[int] = []
    used = 0.0

    rem = {did: cnt for length, did, cnt in items}
    length_map = {did: length for length, did, cnt in items}

    while True:
        feasible = []
        for did, cnt in rem.items():
            if cnt <= 0:
                continue

            length = length_map[did]
            new_used = used + length
            if new_used > L + EPS:
                continue

            temp_seq = seq + [did]
            regular_count = max(0, len(temp_seq) - 1)
            temp_waste = L - new_used
            V = 1 if temp_waste > EPS else 0

            if regular_count + V <= B:
                feasible.append((length, did))

        if not feasible:
            break

        max_len = max(x[0] for x in feasible)
        min_len = min(x[0] for x in feasible)
        threshold = max_len - alpha * (max_len - min_len)

        rcl = [x for x in feasible if x[0] >= threshold]
        length, did = random.choice(rcl)

        seq.append(did)
        used += length
        rem[did] -= 1

    return seq


def enumerate_count_combinations(
    eligible: List[int],
    LD: Dict[int, float],
    remaining: Dict[int, int],
    L: float,
    B: int
) -> List[Dict[int, int]]:
    """
    Feasible count combinations üretir.
    """
    results: List[Dict[int, int]] = []

    def dfs(idx: int, current: Dict[int, int], total_len: float, total_items: int):
        if idx == len(eligible):
            if total_items >= 1:
                waste = L - total_len
                V = 1 if waste > EPS else 0
                if total_items - 1 + V <= B:
                    results.append(dict(current))
            return

        d = eligible[idx]
        max_take = min(remaining[d], B + 1 - total_items)
        max_take = min(max_take, int((L - total_len) // LD[d]))

        # 0 case
        dfs(idx + 1, current, total_len, total_items)

        for c in range(1, max_take + 1):
            new_len = total_len + c * LD[d]
            if new_len > L + EPS:
                break
            current[d] = c
            dfs(idx + 1, current, new_len, total_items + c)
            del current[d]

    dfs(0, {}, 0.0, 0)
    return results


def counts_to_sequence_orders(
    counts: Dict[int, int],
    LD: Dict[int, float],
    prev_pattern: Optional[Pattern]
) -> List[List[int]]:
    """
    Aynı count yapısından birkaç farklı sıra üret.
    """
    if not counts:
        return []

    seqs = []

    used_demands = [d for d, c in counts.items() if c > 0]

    # her demand bir kez final demand olabilir
    for last_demand in used_demands:
        reg_counts = dict(counts)
        reg_counts[last_demand] -= 1
        if reg_counts[last_demand] == 0:
            del reg_counts[last_demand]

        regular_desc = []
        for d in sorted(reg_counts.keys(), key=lambda x: (-LD[x], x)):
            regular_desc.extend([d] * reg_counts[d])

        regular_asc = []
        for d in sorted(reg_counts.keys(), key=lambda x: (LD[x], x)):
            regular_asc.extend([d] * reg_counts[d])

        seqs.append(regular_desc + [last_demand])
        seqs.append(regular_asc + [last_demand])

        # prev-guided order
        if prev_pattern is not None and prev_pattern.piece_type == counts_to_type(counts):
            prev_like = []
            prev_regular_lengths = []

            for d, cnt in sorted(prev_pattern.assignments.items()):
                prev_regular_lengths.extend([d] * cnt)

            temp_reg = []
            reg_copy = dict(reg_counts)

            # önce previous pattern'da görünenleri sırayla koy
            for d in prev_regular_lengths:
                if reg_copy.get(d, 0) > 0:
                    temp_reg.append(d)
                    reg_copy[d] -= 1
                    if reg_copy[d] == 0:
                        del reg_copy[d]

            # kalanları büyükten küçüğe ekle
            for d in sorted(reg_copy.keys(), key=lambda x: (-LD[x], x)):
                temp_reg.extend([d] * reg_copy[d])

            prev_like = temp_reg + [last_demand]
            seqs.append(prev_like)

    # duplicate kaldır
    uniq = []
    seen = set()
    for s in seqs:
        key = tuple(s)
        if key not in seen:
            seen.add(key)
            uniq.append(s)

    return uniq


def counts_to_type(counts: Dict[int, int]) -> int:
    # sadece helper; dışarıdan tip zaten sabit geliyor ama prev-guided için lazım oldu
    return -1


def build_candidate_pool(
    D: List[int],
    TD: Dict[int, int],
    LD: Dict[int, float],
    remaining: Dict[int, int],
    reel_type: int,
    L: float,
    B: int,
    prev_pattern: Optional[Pattern] = None
) -> List[Pattern]:
    eligible = [d for d in D if TD[d] == reel_type and remaining[d] > 0]
    if not eligible:
        return []

    pool: List[Pattern] = []
    seen = set()

    def add_from_seq(seq: List[int]) -> None:
        if not seq:
            return
        p = compute_pattern_from_sequence(seq, LD, TD, reel_type, L, B)
        if p is None:
            return
        key = (
            tuple(sorted(p.assignments.items())),
            p.last_demand,
            tuple(round(x, 6) for x in p.blade_positions),
            round(p.used_length, 6),
        )
        if key not in seen:
            seen.add(key)
            pool.append(p)

    # deterministic greedy
    full_items = [(LD[d], d, remaining[d]) for d in eligible]
    one_items = [(LD[d], d, 1) for d in eligible]
    two_items = [(LD[d], d, min(2, remaining[d])) for d in eligible]

    add_from_seq(greedy_sequence(full_items, L, B))
    add_from_seq(greedy_sequence(one_items, L, B))
    add_from_seq(greedy_sequence(two_items, L, B))

    # GRASP
    for _ in range(18):
        add_from_seq(randomized_greedy_sequence(full_items, L, B, alpha=0.20))
        add_from_seq(randomized_greedy_sequence(full_items, L, B, alpha=0.35))
        add_from_seq(randomized_greedy_sequence(two_items, L, B, alpha=0.25))

    # count-combination based candidates
    combos = enumerate_count_combinations(eligible, LD, remaining, L, B)
    # used_length'e göre büyükten küçüğe sırala, en iyi dolanları önce dene
    combos.sort(key=lambda cnts: -sum(LD[d] * c for d, c in cnts.items()))
    combos = combos[:120]

    for cnts in combos:
        orders = counts_to_sequence_orders(cnts, LD, prev_pattern)
        for seq in orders[:3]:
            add_from_seq(seq)

    return pool


# =========================================================
# GLOBAL-AWARE SCORING
# =========================================================

def estimate_next_type_break(
    next_reel_type: Optional[int],
    curr_pattern: Pattern,
    D: List[int],
    TD: Dict[int, int],
    LD: Dict[int, float],
    remaining_after_curr: Dict[int, int],
    L: float,
    B: int
) -> int:
    """
    Sonraki reel için 0/1 bir kırılma tahmini.
    """
    if next_reel_type is None:
        return 0

    candidates = build_candidate_pool(
        D, TD, LD, remaining_after_curr, next_reel_type, L, B, curr_pattern
    )

    if not candidates:
        return 0

    fake_prev = ReelPlan(-1, curr_pattern.piece_type, True, curr_pattern)
    best = 1
    for p in candidates:
        curr = ReelPlan(-2, next_reel_type, True, p)
        best = min(best, reel_transition_tw(fake_prev, curr))
        if best == 0:
            break
    return best


def pattern_score(
    pattern: Pattern,
    prev_plan: Optional[ReelPlan],
    remaining: Dict[int, int],
    current_total_pw: float,
    current_total_tw: int,
    n: int,
    L: float,
    lam: float,
    D: List[int],
    TD: Dict[int, int],
    LD: Dict[int, float],
    B: int,
    next_reel_type: Optional[int]
) -> Tuple[float, int, float, int]:

    candidate_plan = ReelPlan(-999, pattern.piece_type, True, pattern)

    # --- incremental values ---
    tw_add = reel_transition_tw(prev_plan, candidate_plan)
    pw_add = pattern.paper_waste(L)
    mult = max_multiplicity(pattern, remaining)

    # --- GLOBAL objective (model 1 ile aynı mantık) ---
    est_total_pw = current_total_pw + pw_add
    est_total_tw = current_total_tw + tw_add

    pw_norm = est_total_pw / (n * L)
    tw_norm = est_total_tw / n

    base = lam * pw_norm + (1.0 - lam) * tw_norm

    # =========================================================
    # 🔥 IMPROVEMENTS (PW FIX)
    # =========================================================

    # 1️⃣ FULLNESS (EN KRİTİK)
    fullness_bonus = 0.05 * (pattern.used_length / L)

    # 2️⃣ PERFECT FIT BONUS
    perfect_bonus = 0.0
    if abs(pw_add) < 1e-6:
        perfect_bonus = 0.05

    # 3️⃣ SAME PATTERN BONUS (TW kontrol)
    same_bonus = 0.0
    if prev_plan is not None and prev_plan.used and prev_plan.pattern is not None:
        if prev_plan.pattern.config() == pattern.config():
            same_bonus = 0.03

    # 4️⃣ MULTIPLICITY BONUS
    mult_bonus = 0.004 * min(mult, 6)

    # 5️⃣ LOW MULT PENALTY (AZALTILDI)
    low_mult_penalty = 0.0
    if mult <= 1:
        low_mult_penalty = 0.005
    elif mult == 2:
        low_mult_penalty = 0.002

    # 6️⃣ LOOK-AHEAD (YUMUŞATILDI)
    remaining_after = dict(remaining)
    apply_pattern_once(pattern, remaining_after)

    next_break = estimate_next_type_break(
        next_reel_type, pattern, D, TD, LD, remaining_after, L, B
    )

    next_break_penalty = 0.01 * next_break

    # =========================================================
    # FINAL SCORE
    # =========================================================

    score = (
        base
        + low_mult_penalty
        + next_break_penalty
        - same_bonus
        - mult_bonus
        - fullness_bonus
        - perfect_bonus
    )

    return score, tw_add, pw_add, mult


# =========================================================
# CONSTRUCTION + IMPROVEMENT
# =========================================================

def construct_solution(
    S: List[int],
    D: List[int],
    TJ: Dict[int, int],
    TD: Dict[int, int],
    LD: Dict[int, float],
    ND: Dict[int, int],
    L: float,
    B: int,
    lam: float,
    guide_patterns: Optional[List[Optional[Pattern]]] = None,
    seed: int = 42
) -> List[ReelPlan]:
    random.seed(seed)

    remaining = {d: int(ND[d]) for d in D}
    reel_plans: List[ReelPlan] = []

    total_pw = 0.0
    total_tw = 0
    prev_plan: Optional[ReelPlan] = None

    block_pattern: Optional[Pattern] = None
    block_left = 0

    n = len(S)

    for idx, reel_id in enumerate(S):
        reel_type = TJ[reel_id]
        next_reel_type = TJ[S[idx + 1]] if idx + 1 < len(S) else None

        type_available = any(remaining[d] > 0 and TD[d] == reel_type for d in D)
        if not type_available:
            curr_plan = ReelPlan(reel_id, reel_type, False, None)
            total_tw += reel_transition_tw(prev_plan, curr_plan)
            reel_plans.append(curr_plan)
            prev_plan = curr_plan
            block_pattern = None
            block_left = 0
            continue

        # 1) block continuation
        if block_pattern is not None and block_left > 0:
            if block_pattern.piece_type == reel_type and can_apply_once(block_pattern, remaining):
                curr_plan = ReelPlan(reel_id, reel_type, True, block_pattern)
                total_pw += block_pattern.paper_waste(L)
                total_tw += reel_transition_tw(prev_plan, curr_plan)
                apply_pattern_once(block_pattern, remaining)
                reel_plans.append(curr_plan)
                prev_plan = curr_plan
                block_left -= 1
                continue
            else:
                block_pattern = None
                block_left = 0

        # 2) build candidate pool
        prev_pattern = prev_plan.pattern if (prev_plan is not None and prev_plan.used and prev_plan.pattern is not None) else None
        pool = build_candidate_pool(D, TD, LD, remaining, reel_type, L, B, prev_pattern)

        # guide pattern ekle
        if guide_patterns is not None and idx < len(guide_patterns):
            gpatt = guide_patterns[idx]
            if gpatt is not None and gpatt.piece_type == reel_type and can_apply_once(gpatt, remaining):
                pool = [gpatt] + pool

        best_pattern: Optional[Pattern] = None
        best_score = float("inf")
        best_mult = -1
        best_pw = float("inf")

        for p in pool:
            mult = max_multiplicity(p, remaining)
            if mult <= 0:
                continue

            score, tw_add, pw_add, mult = pattern_score(
                p, prev_plan, remaining, total_pw, total_tw, n, L, lam,
                D, TD, LD, B, next_reel_type
            )

            if score + EPS < best_score:
                best_score = score
                best_pattern = p
                best_mult = mult
                best_pw = pw_add
            elif abs(score - best_score) <= EPS:
                if pw_add + EPS < best_pw:
                    best_pattern = p
                    best_mult = mult
                    best_pw = pw_add
                elif abs(pw_add - best_pw) <= EPS and mult > best_mult:
                    best_pattern = p
                    best_mult = mult
                    best_pw = pw_add

        if best_pattern is None:
            curr_plan = ReelPlan(reel_id, reel_type, False, None)
            total_tw += reel_transition_tw(prev_plan, curr_plan)
            reel_plans.append(curr_plan)
            prev_plan = curr_plan
            block_pattern = None
            block_left = 0
            continue

        curr_plan = ReelPlan(reel_id, reel_type, True, best_pattern)
        total_pw += best_pattern.paper_waste(L)
        total_tw += reel_transition_tw(prev_plan, curr_plan)
        apply_pattern_once(best_pattern, remaining)
        reel_plans.append(curr_plan)
        prev_plan = curr_plan

        # block continuation
        future_mult = max_multiplicity(best_pattern, remaining)
        if future_mult >= 1:
            block_pattern = best_pattern
            block_left = min(future_mult, 2)
        else:
            block_pattern = None
            block_left = 0

    return reel_plans


def local_improvement(
    reel_plans: List[ReelPlan],
    S: List[int],
    D: List[int],
    TJ: Dict[int, int],
    TD: Dict[int, int],
    LD: Dict[int, float],
    ND: Dict[int, int],
    L: float,
    B: int,
    lam: float
) -> List[ReelPlan]:
    """
    Reel sırası sabit.
    2 kez guided reconstruction yapıyoruz.
    """
    guide_patterns = [rp.pattern if (rp.used and rp.pattern is not None) else None for rp in reel_plans]

    best = reel_plans
    best_z, _, _, _, _ = total_objective(best, L, lam)

    for seed in [7, 21]:
        cand = construct_solution(
            S, D, TJ, TD, LD, ND, L, B, lam,
            guide_patterns=guide_patterns,
            seed=seed
        )
        z, _, _, _, _ = total_objective(cand, L, lam)
        if z + EPS < best_z:
            best = cand
            best_z = z

    return best


# =========================================================
# OBJECTIVE EVALUATION
# =========================================================

def total_objective(
    reel_plans: List[ReelPlan],
    L: float,
    lam: float
) -> Tuple[float, float, float, float, int]:
    n = len(reel_plans)
    total_pw = 0.0
    total_tw = 0

    prev_plan: Optional[ReelPlan] = None
    for r in reel_plans:
        if r.used and r.pattern is not None:
            total_pw += r.pattern.paper_waste(L)
        total_tw += reel_transition_tw(prev_plan, r)
        prev_plan = r

    pw_norm = total_pw / (n * L)
    tw_norm = total_tw / n
    z = lam * pw_norm + (1 - lam) * tw_norm
    return z, pw_norm, tw_norm, total_pw, total_tw


# =========================================================
# MAIN SOLVER
# =========================================================

def solve_model1_heuristic(data: Dict, verbose: bool = True) -> List[ReelPlan]:
    S = list(data["S"])
    D = list(data["D"])
    L = float(data["L"])
    B = int(data["B"])
    TJ = data["TJ"]
    TD = data["TD"]
    LD = data["LD"]
    ND = data["ND"]
    lam = float(data["lambda"])

    if verbose:
        print("=" * 70)
        print("MODEL 1 HEURISTIC SOLVER")
        print("=" * 70)
        print(f"ns={len(S)} | nd={len(D)} | L={L} | B={B} | lambda={lam}")
        print("=" * 70)

    # 1) first construction
    reel_plans = construct_solution(
        S, D, TJ, TD, LD, ND, L, B, lam,
        guide_patterns=None,
        seed=42
    )

    # 2) guided improvement
    reel_plans = local_improvement(
        reel_plans, S, D, TJ, TD, LD, ND, L, B, lam
    )

    # feasibility check
    remaining_check = {d: int(ND[d]) for d in D}
    for r in reel_plans:
        if r.used and r.pattern is not None:
            apply_pattern_once(r.pattern, remaining_check)

    unsatisfied = [d for d in D if remaining_check[d] != 0]
    if unsatisfied:
        print("\n" + "=" * 50)
        print("MODEL STATUS: INFEASIBLE")
        print("=" * 50)
        print("\nUnsatisfied Demands:")
        for d in unsatisfied:
            print(f"Demand {d} -> remaining = {remaining_check[d]}")
        return reel_plans

    # ==============================
    # OBJECTIVE FUNCTION DETAILS
    # ==============================
    Z, pw_norm, tw_norm, total_pw, total_tw = total_objective(reel_plans, L, lam)
    n = len(S)
    PW_max = n * L

    print("\n==============================")
    print("OBJECTIVE FUNCTION DETAILS")
    print("==============================")

    print("\nZ = λ·(PW/(nL)) + (1-λ)·(TW/n)")

    print("\nVALUES:")
    print(f"Total PW = {round(total_pw, 1)}")
    print(f"Total TW = {int(total_tw)}")

    print("\nNORMALIZED:")
    print(f"PW_norm = {round(total_pw, 1)} / {PW_max} = {round(pw_norm, 6)}")
    print(f"TW_norm = {int(total_tw)} / {n} = {round(tw_norm, 6)}")

    print("\nFINAL OBJECTIVE:")
    print(
        f"Z = {lam}×{round(pw_norm, 6)} + "
        f"{round(1 - lam, 1)}×{round(tw_norm, 6)} = {round(Z, 6)}"
    )

    # ==============================
    # JUMBO REEL DETAILS
    # ==============================
    print("\n==============================")
    print("JUMBO REEL DETAILS")
    print("==============================")

    prev_plan: Optional[ReelPlan] = None

    for r in reel_plans:
        print(f"\nJumbo Reel {r.reel_id} (Type {r.reel_type})")

        if not r.used or r.pattern is None:
            print("  Not used | blades: 0 | PW: 0.0 | TW: 0")
            print("  Blade distances: ()")
            prev_plan = r
            continue

        p = r.pattern
        reel_pw = p.paper_waste(L)
        reel_tw = reel_transition_tw(prev_plan, r)

        print(f"  Used blades: {p.blade_count()}")

        for d, cnt in sorted(p.assignments.items()):
            for _ in range(cnt):
                print(f"  Regular cut -> d={d} | Type={TD[d]} | Length={LD[d]}")

        print(f"  Last assigned length -> d={p.last_demand} | Type={TD[p.last_demand]} | Length={LD[p.last_demand]}")

        print(f"  Paper waste: {round(reel_pw, 4)}")
        print(f"  Time waste:  {reel_tw}")
        print(f"  Blade distances: {p.display_blade_distances(LD)}")

        prev_plan = r

    return reel_plans


if __name__ == "__main__":
    data_model1_test = {

        "S": list(range(1, 9)),  # 8 reel
        "D": list(range(1, 13)),

        "B": 5,
        "L": 320.0,
        "lambda": 0.5,

        # 🔥 REEL TYPE SABİT
        "TJ": {
            1: 1, 2: 2, 3: 3, 4: 1,
            5: 2, 6: 3, 7: 1, 8: 2
        },

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
    solve_model1_heuristic(data_model1_test)
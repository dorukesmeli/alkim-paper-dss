from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

EPS = 1e-9


# =========================================================
# DATA STRUCTURES
# =========================================================

@dataclass
class Pattern:
    assignments: Dict[int, int]          # regular cuts assigned to demands
    last_demand: int                     # Z_dj = 1 olan demand
    used_length: float                   # total used = regular + last
    blade_positions: List[float]         # regular blade positions P_bj
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
        """
        Exact modeldeki Vj:
        waste varsa 1, yoksa 0
        """
        return 1 if self.paper_waste_value > EPS else 0

    def regular_blade_count(self) -> int:
        """
        sum_b Y[b,j]
        """
        return len(self.blade_positions)

    def blade_count(self) -> int:
        """
        Exact modeldeki Bj = regular blades + V
        """
        return self.regular_blade_count() + self.V()

    def final_position(self) -> float:
        """
        Exact modeldeki Fj:
        - waste varsa Fj = used_length
        - waste yoksa Fj = son regular position
        - regular blade de yoksa Fj = 0
        """
        if self.V() == 1:
            return self.used_length
        if self.blade_positions:
            return self.blade_positions[-1]
        return 0.0

    def display_blade_distances(self, LD) -> Tuple[float, ...]:
        """
        Blade distances:
        - Demand sırasına göre (printteki sırayla)
        - Model mantığına uygun:
            V=1 → Fj eklenir
            V=0 → eklenmez
        """

        vals = []
        pos = 0.0

        # Regular cuts (aynı sırayla)
        for d, cnt in sorted(self.assignments.items()):
            for _ in range(cnt):
                pos += LD[d]
                vals.append(round(pos, 4))

        # 🔥 KRİTİK FIX
        if self.V() == 1:
            # waste varsa last eklenir
            pos += LD[self.last_demand]
            vals.append(round(pos, 4))

        return tuple(vals)

    def config(self) -> Tuple[int, Tuple[float, ...], float]:
        return (
            self.blade_count(),
            tuple(round(x, 6) for x in self.blade_positions),
            round(self.final_position(), 6),
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
    seq = [d1, d2, d3, ...] sıralı kesimler
    Son eleman last_demand olarak yorumlanır.
    Ondan öncekiler regular blade cuts.
    """

    if not seq:
        return None

    if any(TD[d] != reel_type for d in seq):
        return None

    total = sum(LD[d] for d in seq)
    if total > L + EPS:
        return None

    # last_demand = seq[-1]
    regular = seq[:-1]
    last_demand = seq[-1]

    # Exact model: Bj = regular cuts + V
    waste = L - total
    V = 1 if waste > EPS else 0
    expected_blades = len(regular) + V

    if expected_blades > B:
        return None

    blade_positions = []
    pos = 0.0
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


def max_multiplicity(pattern: Pattern, remaining: Dict[int, int]) -> int:
    """
    Pattern kaç kez tekrar uygulanabilir?
    regular cuts + last demand dahil bakılır.
    """
    need: Dict[int, int] = dict(pattern.assignments)
    need[pattern.last_demand] = need.get(pattern.last_demand, 0) + 1

    vals = []
    for d, cnt in need.items():
        vals.append(remaining.get(d, 0) // cnt)

    return min(vals) if vals else 0


def apply_pattern_once(pattern: Pattern, remaining: Dict[int, int]) -> None:
    for d, cnt in pattern.assignments.items():
        remaining[d] -= cnt
    remaining[pattern.last_demand] -= 1


def can_apply_once(pattern: Pattern, remaining: Dict[int, int]) -> bool:
    need: Dict[int, int] = dict(pattern.assignments)
    need[pattern.last_demand] = need.get(pattern.last_demand, 0) + 1
    return all(remaining.get(d, 0) >= cnt for d, cnt in need.items())


def compute_TW(prev_pattern: Optional[Pattern], curr_pattern: Pattern) -> int:
    """
    Model 1 time waste mantığı:
    - ilk kullanılan reelde TW=1
    - blade count değişirse TW=1
    - blade positions değişirse TW=1
    - final blade distance / Fj değişirse TW=1
    """
    if prev_pattern is None:
        return 1

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
    """
    items: (length, demand_id, max_count)
    Greedy olarak seq döndürür.
    En az 1 item varsa sonuncu last_demand olur.
    """
    seq: List[int] = []
    used = 0.0

    for length, did, max_cnt in sorted(items, reverse=True):
        for _ in range(max_cnt):
            new_used = used + length
            if new_used > L + EPS:
                break

            # geçici seq ile blade feasibility kontrolü
            temp_seq = seq + [did]
            regular_count = max(0, len(temp_seq) - 1)
            temp_total = new_used
            temp_waste = L - temp_total
            V = 1 if temp_waste > EPS else 0
            expected_blades = regular_count + V

            if expected_blades > B:
                break

            seq.append(did)
            used = new_used

    return seq


def build_candidate_pool(
    D: List[int],
    TD: Dict[int, int],
    LD: Dict[int, float],
    remaining: Dict[int, int],
    reel_type: int,
    L: float,
    B: int
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

    # C1: Full greedy
    full_items = [(LD[d], d, remaining[d]) for d in eligible]
    add_from_seq(greedy_sequence(full_items, L, B))

    # C2: One-each greedy
    one_items = [(LD[d], d, 1) for d in eligible]
    add_from_seq(greedy_sequence(one_items, L, B))

    # C3: Two-each greedy
    two_items = [(LD[d], d, min(2, remaining[d])) for d in eligible]
    add_from_seq(greedy_sequence(two_items, L, B))

    # Single-demand patterns
    for d in eligible:
        cnt = min(int(L // LD[d]), remaining[d])
        cnt = min(cnt, B + 1)  # güvenlik
        if cnt >= 1:
            add_from_seq([d] * cnt)

    # Pair patterns
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            d1, d2 = eligible[i], eligible[j]
            seq = greedy_sequence(
                [(LD[d1], d1, min(remaining[d1], 2)),
                 (LD[d2], d2, min(remaining[d2], 2))],
                L, B
            )
            add_from_seq(seq)

    # Triple patterns
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            for k in range(j + 1, len(eligible)):
                d1, d2, d3 = eligible[i], eligible[j], eligible[k]
                seq = greedy_sequence(
                    [(LD[d1], d1, 1), (LD[d2], d2, 1), (LD[d3], d3, 1)],
                    L, B
                )
                add_from_seq(seq)

    return pool


# =========================================================
# OBJECTIVE / SCORING
# =========================================================

def pattern_score(
    pattern: Pattern,
    prev_pattern: Optional[Pattern],
    remaining: Dict[int, int],
    L: float,
    ns: int,
    lam: float,
    mult_bonus: float = 0.001
) -> Tuple[float, int, float, int]:
    pw = pattern.paper_waste(L)
    tw = compute_TW(prev_pattern, pattern)
    mult = max_multiplicity(pattern, remaining)

    pw_norm = pw / L
    tw_norm = tw  # 0 or 1, reel bazlı karşılaştırma

    score = lam * pw_norm + (1.0 - lam) * tw_norm - mult_bonus * mult
    return score, tw, pw, mult


def total_objective(reel_plans: List[ReelPlan], L: float, lam: float) -> Tuple[float, float, float, int, int]:
    used_plans = [r for r in reel_plans if r.used and r.pattern is not None]
    ns = len(reel_plans)

    total_pw = 0.0
    total_tw = 0
    prev_pat: Optional[Pattern] = None

    for r in used_plans:
        p = r.pattern
        total_pw += p.paper_waste(L)
        total_tw += compute_TW(prev_pat, p)
        prev_pat = p

    pw_norm = total_pw / (ns * L)
    tw_norm = total_tw / ns
    z = lam * pw_norm + (1.0 - lam) * tw_norm
    return z, pw_norm, tw_norm, total_pw, total_tw


# =========================================================
# LOCAL SEARCH
# =========================================================

def local_search(reel_plans: List[ReelPlan], L: float, lam: float) -> None:
    """
    Kullanılan reeller arasında swap deneyerek objective düşürmeye çalışır.
    Type uyumsuz swap yapmaz.
    """
    improved = True
    it = 0

    while improved and it < 100:
        improved = False
        it += 1

        current_z, _, _, _, _ = total_objective(reel_plans, L, lam)

        used_indices = [i for i, r in enumerate(reel_plans) if r.used and r.pattern is not None]

        for a in range(len(used_indices) - 1):
            for b in range(a + 1, len(used_indices)):
                i = used_indices[a]
                j = used_indices[b]

                ri = reel_plans[i]
                rj = reel_plans[j]

                if ri.pattern is None or rj.pattern is None:
                    continue

                # type compatibility
                if ri.reel_type != rj.pattern.piece_type:
                    continue
                if rj.reel_type != ri.pattern.piece_type:
                    continue

                ri.pattern, rj.pattern = rj.pattern, ri.pattern
                new_z, _, _, _, _ = total_objective(reel_plans, L, lam)

                if new_z + EPS < current_z:
                    current_z = new_z
                    improved = True
                else:
                    ri.pattern, rj.pattern = rj.pattern, ri.pattern

            if improved:
                break


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

    ns = len(S)
    remaining = {d: int(ND[d]) for d in D}

    reel_plans: List[ReelPlan] = []
    prev_used_pattern: Optional[Pattern] = None

    if verbose:
        print("=" * 70)
        print("MODEL 1 HEURISTIC SOLVER")
        print("=" * 70)
        print(f"ns={ns} | nd={len(D)} | L={L} | B={B} | lambda={lam}")
        print("=" * 70)

    j_idx = 0
    while j_idx < ns:
        reel_id = S[j_idx]
        reel_type = TJ[reel_id]

        # Bu reel type için hala kalan demand var mı?
        type_available = any(remaining[d] > 0 and TD[d] == reel_type for d in D)
        if not type_available:
            reel_plans.append(ReelPlan(reel_id=reel_id, reel_type=reel_type, used=False, pattern=None))
            j_idx += 1
            continue

        # 1) Önce mevcut pattern'i korumayı dene
        reused = False
        if prev_used_pattern is not None and prev_used_pattern.piece_type == reel_type:
            if can_apply_once(prev_used_pattern, remaining):
                reel_plans.append(ReelPlan(reel_id=reel_id, reel_type=reel_type, used=True, pattern=prev_used_pattern))
                apply_pattern_once(prev_used_pattern, remaining)
                reused = True
                j_idx += 1

        if reused:
            continue

        # 2) Yeni aday patternler oluştur
        pool = build_candidate_pool(D, TD, LD, remaining, reel_type, L, B)

        best_pattern: Optional[Pattern] = None
        best_score_val = float("inf")
        best_mult = -1
        best_pw = float("inf")

        for p in pool:
            mult = max_multiplicity(p, remaining)
            if mult <= 0:
                continue

            score, tw, pw, mult = pattern_score(
                p, prev_used_pattern, remaining, L, ns, lam, mult_bonus=0.001
            )

            if score + EPS < best_score_val:
                best_score_val = score
                best_pattern = p
                best_mult = mult
                best_pw = pw
            elif abs(score - best_score_val) <= EPS:
                if mult > best_mult:
                    best_pattern = p
                    best_mult = mult
                    best_pw = pw
                elif mult == best_mult and pw + EPS < best_pw:
                    best_pattern = p
                    best_mult = mult
                    best_pw = pw

        if best_pattern is None:
            reel_plans.append(ReelPlan(reel_id=reel_id, reel_type=reel_type, used=False, pattern=None))
            j_idx += 1
            continue

        # 3) Multiplicity kadar uygula ama kalan uygun reel sayısıyla sınırla
        feasible_mult = max_multiplicity(best_pattern, remaining)
        compatible_future = sum(1 for rid in S[j_idx:] if TJ[rid] == reel_type)
        repeat = min(feasible_mult, compatible_future)

        if verbose:
            score, tw, pw, mult = pattern_score(
                best_pattern, prev_used_pattern, remaining, L, ns, lam, mult_bonus=0.001
            )
            print(
                f"Reel {reel_id} | Type {reel_type} | "
                f"selected pattern -> PW={pw:.2f}, TW={tw}, mult={repeat}, score={score:.6f}"
            )

        applied = 0
        while applied < repeat and j_idx < ns and TJ[S[j_idx]] == reel_type:
            rid = S[j_idx]
            reel_plans.append(ReelPlan(reel_id=rid, reel_type=reel_type, used=True, pattern=best_pattern))
            apply_pattern_once(best_pattern, remaining)
            prev_used_pattern = best_pattern
            applied += 1
            j_idx += 1

        # Arada başka type varsa stop; sonraki loop devam eder

    # Local search
    if verbose:
        print("\n--- LOCAL SEARCH ---")
    local_search(reel_plans, L, lam)
    # ==============================
    # FEASIBILITY CHECK (CRITICAL)
    # ==============================
    unsatisfied = [d for d in D if remaining[d] != 0]

    if len(unsatisfied) > 0:
        print("\n" + "=" * 50)
        print("MODEL STATUS: INFEASIBLE")
        print("=" * 50)

        print("\nUnsatisfied Demands:")
        for d in unsatisfied:
            print(f"Demand {d} -> remaining = {remaining[d]}")

        return reel_plans

    # Final output
    z, pw_norm, tw_norm, total_pw, total_tw = total_objective(reel_plans, L, lam)

    print("\n==============================")
    print("OBJECTIVE FUNCTION DETAILS")
    print("==============================")

    print("\nZ = λ·(PW/(nL)) + (1-λ)·(TW/n)")

    print("\nVALUES:")
    print(f"Total PW = {round(total_pw, 1)}")
    print(f"Total TW = {int(total_tw)}")

    pw_norm = total_pw / (ns * L)
    tw_norm = total_tw / ns

    print("\nNORMALIZED:")
    print(f"PW_norm = {round(total_pw, 1)} / {float(ns * L)} = {round(pw_norm, 6)}")
    print(f"TW_norm = {int(total_tw)} / {ns} = {round(tw_norm, 6)}")

    Z = lam * pw_norm + (1 - lam) * tw_norm

    print("\nFINAL OBJECTIVE:")
    print(
        f"Z = {lam}×{round(pw_norm, 6)} + "
        f"{round(1 - lam, 1)}×{round(tw_norm, 6)} = {round(Z, 6)}"
    )

    print("\n" + "=" * 70)
    print("JUMBO REEL DETAILS")
    print("=" * 70)

    prev_pat = None

    for r in reel_plans:
        print(f"\nJumbo Reel {r.reel_id} (Type {r.reel_type})")

        if not r.used or r.pattern is None:
            print("  Not used | blades: 0 | PW: 0.0 | TW: 0")
            print("  Blade distances: ()")
            continue

        p = r.pattern
        reel_pw = p.paper_waste(L)
        reel_tw = compute_TW(prev_pat, p)

        print(f"  Used blades: {p.blade_count()}")

        for d, cnt in sorted(p.assignments.items()):
            print(f"  Regular cut -> d={d} | Type={TD[d]} | Length={LD[d]} | x{cnt}")

        print(f"  Last assigned length -> d={p.last_demand} | Type={TD[p.last_demand]} | Length={LD[p.last_demand]} | x1")

        if reel_pw > EPS:
            print(f"  Paper waste: {round(reel_pw, 4)}")
        else:
            print("  Paper waste: 0.0")

        print(f"  Time waste:  {reel_tw}")
        print(f"  Blade distances: {p.display_blade_distances(LD)}")
        print(f"  Used length: {round(p.used_length, 4)}")

        prev_pat = p

    return reel_plans


# =========================================================
# EXAMPLE DATA
# =========================================================


import time

import time

if __name__ == "__main__":

    start_time = time.time()

    S = list(range(1, 101))

    # -------------------
    # TJ YARI-KARISIK
    # -------------------
    TJ_list = []
    count1 = 83
    count2 = 17

    while count1 > 0 or count2 > 0:
        for _ in range(5):
            if count1 > 0:
                TJ_list.append(1)
                count1 -= 1
        if count2 > 0:
            TJ_list.append(2)
            count2 -= 1

    TJ = {j: TJ_list[j - 1] for j in S}

    data_model1_mixed20_pw80 = {

        "S": list(range(1, 21)),  # 20 jumbo reel
        "D": list(range(1, 13)),

        "B": 8,
        "L": 348.0,

        "lambda": 0.5,

        # Karışık TJ sırası
        "TJ": {
            1: 1, 2: 2, 3: 1, 4: 1, 5: 2,
            6: 2, 7: 1, 8: 2, 9: 1, 10: 1,
            11: 2, 12: 1, 13: 2, 14: 2, 15: 1,
            16: 2, 17: 1, 18: 1, 19: 2, 20: 2
        },

        "TD": {
            1: 1,  # 140
            2: 1,  # 104
            3: 1,  # 100 (Type 1)
            4: 1,  # 130
            5: 1,  # 120
            6: 1,  # 94  (Type 1)

            7: 2,  # 170
            8: 2,  # 94  (Type 2)
            9: 2,  # 80
            10: 2,  # 160
            11: 2,  # 100 (Type 2)
            12: 2  # 84
        },

        "LD": {
            1: 140.0,
            2: 104.0,
            3: 100.0,
            4: 130.0,
            5: 120.0,
            6: 94.0,

            7: 170.0,
            8: 94.0,
            9: 80.0,
            10: 160.0,
            11: 100.0,
            12: 84.0
        },

        "ND": {
            1: 5,  # 140
            2: 5,  # 104
            3: 5,  # 100 (Type 1)
            4: 5,  # 130
            5: 5,  # 120
            6: 5,  # 94  (Type 1)

            7: 5,  # 170
            8: 5,  # 94  (Type 2)
            9: 5,  # 80
            10: 5,  # 160
            11: 5,  # 100 (Type 2)
            12: 5  # 84
        }
    }

    solve_model1_heuristic(data_model1_mixed20_pw80, verbose=True)

    end_time = time.time()
    elapsed = end_time - start_time

    print("\n⏱️ Heuristic Model 1 Süresi:")
    print(f"{elapsed:.2f} saniye")
    print(f"{elapsed/60:.2f} dakika")

    minutes = int(elapsed // 60)
    seconds = elapsed % 60
    print(f"{minutes} dakika {seconds:.2f} saniye")

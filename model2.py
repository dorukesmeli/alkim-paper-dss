# MODEL 2 (TYPE IS DECISION VARIABLE)

import gurobipy as gp
from gurobipy import GRB


def choose_epsilon(lengths):
    w = sorted(set(lengths.values()))
    if all(float(x).is_integer() for x in w):
        return 1.0
    diffs = []
    for i in range(1, len(w)):
        d = w[i] - w[i - 1]
        if d > 0:
            diffs.append(d)
    if diffs:
        return min(diffs) / 2
    return 1e-3


def solve_jumbo_model(data, verbose=True):

    S = list(data["S"])
    D = list(data["D"])
    T = list(data["T"])   # 🔥 NEW

    B = int(data["B"])
    L_reel = float(data["L"])

    TD = data["TD"]
    LD = data["LD"]
    ND = data["ND"]

    lam = float(data["lambda"])
    lam1 = 1.0 - lam

    eps = choose_epsilon(LD)

    ordered_S = sorted(S)
    K = list(range(1, B + 1))

    m = gp.Model("jumbo_cutting_model2")

    if not verbose:
        m.Params.OutputFlag = 0

    # -----------------------------
    # VARIABLES
    # -----------------------------
    Bj = m.addVars(S, vtype=GRB.INTEGER, lb=0, ub=B, name="Bj")
    Y = m.addVars(K, S, vtype=GRB.BINARY, name="Y")
    P = m.addVars(K, S, vtype=GRB.CONTINUOUS, lb=0.0, name="P")
    U = m.addVars(S, vtype=GRB.BINARY, name="U")
    PW = m.addVars(S, vtype=GRB.CONTINUOUS, lb=0.0, name="PW")

    X = m.addVars(K, D, S, vtype=GRB.BINARY, name="X")
    Z = m.addVars(D, S, vtype=GRB.BINARY, name="Z")

    F = m.addVars(S, vtype=GRB.CONTINUOUS, lb=0.0, name="F")
    V = m.addVars(S, vtype=GRB.BINARY, name="V")
    TW = m.addVars(S, vtype=GRB.BINARY, name="TW")

    # 🔥 NEW: TYPE DECISION
    R = m.addVars(S, T, vtype=GRB.BINARY, name="R")

    # -----------------------------
    # OBJECTIVE
    # -----------------------------
    n = len(S)
    PW_max = n * L_reel

    m.setObjective(
        lam * (gp.quicksum(PW[j] for j in S) / PW_max)
        + lam1 * (gp.quicksum(TW[j] for j in S) / n),
        GRB.MINIMIZE
    )

    # -----------------------------
    # DEMAND
    # -----------------------------
    for d in D:
        m.addConstr(
            gp.quicksum(X[b, d, j] for b in K for j in S)
            + gp.quicksum(Z[d, j] for j in S)
            == ND[d]
        )

    # -----------------------------
    # 🔥 TYPE ASSIGNMENT (NEW)
    # -----------------------------
    for j in S:
        m.addConstr(gp.quicksum(R[j, t] for t in T) == U[j])

    # -----------------------------
    # 🔥 TYPE COMPATIBILITY (NEW)
    # -----------------------------
    for j in S:
        for d in D:
            for b in K:
                m.addConstr(X[b, d, j] <= R[j, TD[d]])
            m.addConstr(Z[d, j] <= R[j, TD[d]])

    # -----------------------------
    # ASSIGNMENT
    # -----------------------------
    for j in S:
        for b in K:
            m.addConstr(
                gp.quicksum(X[b, d, j] for d in D) == Y[b, j]
            )

    # CONTIGUOUS
    for j in S:
        for b in range(1, B):
            m.addConstr(Y[b, j] >= Y[b + 1, j])

    # BLADE COUNT
    for j in S:
        m.addConstr(
            Bj[j] == gp.quicksum(Y[b, j] for b in K) + V[j]
        )

    # USAGE
    for j in S:
        m.addConstr(Bj[j] <= B * U[j])
        m.addConstr(V[j] <= U[j])
        for b in K:
            m.addConstr(Y[b, j] <= U[j])

    # LAST LENGTH
    for j in S:
        m.addConstr(gp.quicksum(Z[d, j] for d in D) == U[j])

    # DISTANCE
    for j in S:
        m.addConstr(
            P[1, j] == gp.quicksum(LD[d] * X[1, d, j] for d in D)
        )
        for b in range(2, B + 1):
            m.addConstr(
                P[b, j] - P[b - 1, j]
                == gp.quicksum(LD[d] * X[b, d, j] for d in D)
            )

    # PAPER WASTE
    for j in S:
        m.addConstr(
            L_reel * U[j] - P[B, j]
            == gp.quicksum(LD[d] * Z[d, j] for d in D) + PW[j]
        )

    for j in S:
        m.addConstr(PW[j] <= L_reel * V[j])
        m.addConstr(PW[j] >= eps * V[j])

    # FINAL DISTANCE
    for j in S:
        final_len = gp.quicksum(LD[d] * Z[d, j] for d in D)

        m.addConstr(F[j] >= P[B, j])
        m.addConstr(F[j] <= P[B, j] + L_reel * V[j])
        m.addConstr(F[j] >= P[B, j] + final_len - L_reel * (1 - V[j]))
        m.addConstr(F[j] <= P[B, j] + final_len)

    # TIME WASTE
    for idx, j in enumerate(ordered_S):

        if idx == 0:
            m.addConstr(TW[j] >= U[j])
            prev_F = 0
            prev_U = 0
            prev_B = 0
        else:
            j_prev = ordered_S[idx - 1]
            m.addConstr(TW[j] >= U[j] - U[j_prev])

            prev_F = F[j_prev]
            prev_U = U[j_prev]
            prev_B = Bj[j_prev]

        m.addConstr(TW[j] <= U[j])

        if idx != 0:
            m.addConstr(
                B * TW[j] >= Bj[j] - prev_B - B * (2 - U[j] - prev_U)
            )
            m.addConstr(
                B * TW[j] >= prev_B - Bj[j] - B * (2 - U[j] - prev_U)
            )

            for b in K:
                m.addConstr(
                    L_reel * TW[j] >= P[b, j] - P[b, ordered_S[idx - 1]]
                    - L_reel * (2 - U[j] - prev_U)
                )
                m.addConstr(
                    L_reel * TW[j] >= P[b, ordered_S[idx - 1]] - P[b, j]
                    - L_reel * (2 - U[j] - prev_U)
                )

        m.addConstr(
            L_reel * TW[j] >= F[j] - prev_F - L_reel * (2 - U[j] - prev_U)
        )
        m.addConstr(
            L_reel * TW[j] >= prev_F - F[j] - L_reel * (2 - U[j] - prev_U)
        )

    m.optimize()

    if m.status != GRB.OPTIMAL:
        print("No optimal solution found")
        return None

    print("\n==============================")
    print("OBJECTIVE FUNCTION DETAILS")
    print("==============================")

    total_pw = sum(PW[j].X for j in S)
    total_tw = sum(TW[j].X for j in S)

    n = len(S)
    PW_max = n * L_reel

    print("\nZ = λ·(PW/(nL)) + (1-λ)·(TW/n)")

    print("\nVALUES:")
    print(f"Total PW = {round(total_pw, 4)}")
    print(f"Total TW = {int(round(total_tw))}")

    print("\nNORMALIZED:")
    print(f"PW_norm = {round(total_pw, 4)} / {PW_max} = {round(total_pw / PW_max, 6)}")
    print(f"TW_norm = {int(round(total_tw))} / {n} = {round(total_tw / n, 6)}")

    Z_norm = lam * (total_pw / PW_max) + lam1 * (total_tw / n)

    print("\nFINAL OBJECTIVE:")
    print(
        f"Z = {lam}×{round(total_pw / PW_max, 6)} + "
        f"{round(lam1, 4)}×{round(total_tw / n, 6)} = {round(Z_norm, 6)}"
    )

    for j in ordered_S:
        print()

        # 🔥 TYPE FIND
        assigned_type = None
        for t in T:
            if R[j, t].X > 0.5:
                assigned_type = t
                break

        title = f"Jumbo Reel {j} (Type {assigned_type})"
        print(title)
        print("-" * len(title))

        if U[j].X < 0.5:
            print("Used blades: 0")
            print("Not used")
            print("Paper waste:", 0.0)
            print("Time waste:", int(round(TW[j].X)))
            print("Blade distances: ()")
            continue

        regular_blades = sum(1 for b in K if Y[b, j].X > 0.5)
        total_blades = int(round(Bj[j].X))

        print(f"Used blades: {total_blades}")

        # Regular cuts
        regular_assignments = []
        for b in K:
            if Y[b, j].X > 0.5:
                for d in D:
                    if X[b, d, j].X > 0.5:
                        regular_assignments.append((b, d, TD[d], LD[d]))
                        break

        for b, d, td, ld in regular_assignments:
            print(f"d = {d} (Type {td} ) length {ld}")

        # Final length
        final_d = None
        for d in D:
            if Z[d, j].X > 0.5:
                final_d = d
                break

        if final_d is not None:
            if PW[j].X > eps / 2:
                print(f"Last assigned length: d = {final_d} (Type {TD[final_d]} ) length {LD[final_d]}")
            else:
                print(
                    f"Last assigned length (no paper waste): d = {final_d} (Type {TD[final_d]} ) length {LD[final_d]}"
                )

        print("Paper waste:", round(PW[j].X, 6))
        print("Time waste:", int(round(TW[j].X)))

        blade_distances = []

        for b in range(1, regular_blades + 1):
            blade_distances.append(P[b, j].X)

        if V[j].X > 0.5:
            blade_distances.append(F[j].X)

        print("Blade distances:", tuple(round(x, 1) for x in blade_distances))

"""
if __name__ == "__main__":
    data_model2 = {

        "S": list(range(1, 16)),
        "D": list(range(1, 11)),

        "T": [1, 2],

        "B": 6,
        "L": 200.0,

        "CT": 5.0,
        "lambda": 0.5,


        # demand types (AYNI)
        "TD": {
            1: 1, 2: 1, 3: 1, 4: 1, 5: 1,
            6: 2, 7: 2, 8: 2, 9: 2, 10: 2
        },

        # widths (AYNI)
        "LD": {
            1: 60.0, 2: 60.0, 3: 30.0, 4: 30.0, 5: 30.0,
            6: 50.0, 7: 50.0, 8: 40.0, 9: 40.0, 10: 20.0
        },

        # demands (AYNI)
        "ND": {
            1: 6, 2: 4, 3: 8, 4: 6, 5: 8,
            6: 6, 7: 4, 8: 6, 9: 4, 10: 9
        }
    }

    solve_jumbo_model(data_model2, verbose=True)
"""


"""COMPARISON FOR MODEL 1"""
if __name__ == "__main__":
    data_model2_mixed20_pw80 = {

        "S": list(range(1, 21)),
        "D": list(range(1, 13)),
        "T": [1, 2],

        "B": 8,
        "L": 348.0,

        "lambda": 0.5,

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
            1: 5,
            2: 5,
            3: 5,
            4: 5,
            5: 5,
            6: 5,

            7: 5,
            8: 5,
            9: 5,
            10: 5,
            11: 5,
            12: 5
        }
    }

    solve_jumbo_model(data_model2_mixed20_pw80)
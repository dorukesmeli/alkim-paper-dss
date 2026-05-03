# MODEL 1 — Enhanced adapter (identical math formulation, structured return + time limit)

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


def solve_jumbo_model(data, verbose=True, time_limit=3600):

    S = list(data["S"])
    D = list(data["D"])
    B = int(data["B"])
    L_reel = float(data["L"])

    TJ = data["TJ"]
    TD = data["TD"]
    LD = data["LD"]
    ND = data["ND"]

    lam = float(data["lambda"])
    lam1 = 1.0 - lam

    eps = choose_epsilon(LD)

    ordered_S = sorted(S)
    K = list(range(1, B + 1))

    m = gp.Model("jumbo_cutting")

    if not verbose:
        m.Params.OutputFlag = 0

    m.Params.TimeLimit = float(time_limit)

    # VARIABLES
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

    # OBJECTIVE
    n = len(S)
    PW_max = n * L_reel

    m.setObjective(
        lam * (gp.quicksum(PW[j] for j in S) / PW_max)
        + lam1 * (gp.quicksum(TW[j] for j in S) / n),
        GRB.MINIMIZE
    )

    # DEMAND
    for d in D:
        m.addConstr(
            gp.quicksum(X[b, d, j] for b in K for j in S)
            + gp.quicksum(Z[d, j] for j in S)
            == ND[d]
        )

    # TYPE
    for j in S:
        for d in D:
            if TD[d] != TJ[j]:
                for b in K:
                    m.addConstr(X[b, d, j] == 0)
                m.addConstr(Z[d, j] == 0)

    # ASSIGNMENT
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

    # Handle non-optimal statuses
    if m.status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        print("No optimal solution found")
        return {"status": "infeasible", "error": "Optimal çözüm bulunamadı."}

    if m.status == GRB.TIME_LIMIT and m.SolCount == 0:
        print("Zaman limiti doldu, uygun çözüm bulunamadı.")
        return {"status": "time_limit_no_solution", "error": "Zaman limiti doldu, uygun çözüm bulunamadı."}

    status_str = "optimal" if m.status == GRB.OPTIMAL else "time_limit"

    # Extract results
    total_pw = sum(PW[j].X for j in S)
    total_tw = sum(TW[j].X for j in S)
    n = len(S)
    PW_max = n * L_reel
    Z_norm = lam * (total_pw / PW_max) + lam1 * (total_tw / n)

    print("\n==============================")
    print("OBJECTIVE FUNCTION DETAILS")
    print("==============================")
    print(f"\nTotal PW = {round(total_pw, 4)}")
    print(f"Total TW = {int(round(total_tw))}")
    print(f"Z = {lam}×{round(total_pw / PW_max, 6)} + {round(lam1, 4)}×{round(total_tw / n, 6)} = {round(Z_norm, 6)}")

    roll_data = []
    for j in ordered_S:
        reel_used = U[j].X > 0.5

        if not reel_used:
            roll_data.append({
                "reel_id": j,
                "reel_type": TJ[j],
                "used": False,
                "blade_count": 0,
                "assignments": {},
                "last_demand": None,
                "paper_waste": 0.0,
                "time_waste": 0,
                "blade_distances": (),
                "used_length": 0.0,
            })
            continue

        regular_blades = sum(1 for b in K if Y[b, j].X > 0.5)
        total_blades = int(round(Bj[j].X))

        assignments = {}
        for b in K:
            if Y[b, j].X > 0.5:
                for d in D:
                    if X[b, d, j].X > 0.5:
                        assignments[d] = assignments.get(d, 0) + 1
                        break

        final_d = None
        for d in D:
            if Z[d, j].X > 0.5:
                final_d = d
                break

        blade_distances = []
        for b in range(1, regular_blades + 1):
            blade_distances.append(round(P[b, j].X, 4))
        if V[j].X > 0.5:
            blade_distances.append(round(F[j].X, 4))

        used_length = P[B, j].X
        if final_d is not None:
            used_length += LD[final_d]

        roll_data.append({
            "reel_id": j,
            "reel_type": TJ[j],
            "used": True,
            "blade_count": total_blades,
            "assignments": assignments,
            "last_demand": final_d,
            "paper_waste": round(PW[j].X, 4),
            "time_waste": int(round(TW[j].X)),
            "blade_distances": tuple(blade_distances),
            "used_length": round(used_length, 4),
        })

        print(f"\nJumbo Reel {j} (Type {TJ[j]})")
        print(f"  Blades: {total_blades} | PW: {round(PW[j].X, 4)} | TW: {int(round(TW[j].X))}")
        print(f"  Blade distances: {tuple(blade_distances)}")

    return {
        "status": status_str,
        "objective_value": round(Z_norm, 6),
        "total_pw": round(total_pw, 4),
        "total_tw": int(round(total_tw)),
        "n_reels": n,
        "roll_data": roll_data,
    }

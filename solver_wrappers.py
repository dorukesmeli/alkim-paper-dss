"""
solver_wrappers.py — Unified solver interface for all four optimization methods.

Standardized return dict:
{
    "status":             str   — "optimal" | "time_limit" | "infeasible" | "error"
    "objective_value":    float
    "total_paper_waste":  float
    "total_time_waste":   int
    "used_reel_count":    int
    "runtime":            float (seconds)
    "roll_data":          list[dict]   — per-reel structured data
    "raw_output":         str          — captured stdout
    "warning":            str | None
    "error":              str | None
}
"""

import sys
import io
import time
import traceback
from contextlib import redirect_stdout


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_selected_solver(method_name: str, data: dict,
                        time_limit: int = 3600, verbose: bool = False) -> dict:
    """
    Call the correct solver and return a standardized result dict.
    """
    start_time = time.time()
    raw_buf = io.StringIO()
    warning = None

    try:
        with redirect_stdout(raw_buf):
            if method_name == "Model 1":
                result = _run_model1(data, time_limit, verbose)
            elif method_name == "Model 2":
                result = _run_model2(data, time_limit, verbose)
            elif method_name == "Heuristic Model 1":
                result = _run_heuristic1(data, verbose)
            elif method_name == "Heuristic Model 2":
                result = _run_heuristic2(data, verbose)
            else:
                return _error_result(f"Bilinmeyen çözüm yöntemi: {method_name}")

    except ImportError as exc:
        msg = str(exc)
        if "gurobipy" in msg.lower():
            return _error_result(
                "Gurobi (gurobipy) bu ortamda kurulu değil. "
                "Exact model çalıştırmak için geçerli bir Gurobi kurulumuna ihtiyaç vardır. "
                "Hızlı sonuç için Heuristic Model 2'yi deneyin."
            )
        return _error_result(f"Modül yüklenemedi: {msg}\n{traceback.format_exc()}")

    except Exception as exc:
        msg = str(exc)
        tb = traceback.format_exc()

        # Gurobi license errors
        if any(kw in msg for kw in ("license", "License", "GRBException", "No Gurobi", "authorization")):
            return _error_result(
                "Gurobi lisansı bulunamadı veya geçersiz.\n"
                "Geçerli bir Gurobi lisansı (akademik, ticari veya WLS) gereklidir.\n"
                "Lisans sorunları için: https://www.gurobi.com/free-trial/"
            )

        return _error_result(f"Çözüm hatası:\n{msg}", raw_output=raw_buf.getvalue(), tb=tb)

    runtime = time.time() - start_time
    raw_output = raw_buf.getvalue()

    if result.get("status") == "time_limit":
        warning = "Zaman limiti doldu. En iyi bulunan çözüm gösteriliyor."

    # Standardize
    return {
        "status": result.get("status", "unknown"),
        "objective_value": result.get("objective_value", 0.0),
        "total_paper_waste": result.get("total_pw", 0.0),
        "total_time_waste": result.get("total_tw", 0),
        "used_reel_count": result.get("used_reel_count", 0),
        "runtime": runtime,
        "roll_data": result.get("roll_data", []),
        "raw_output": raw_output,
        "warning": warning,
        "error": result.get("error"),
    }


# ---------------------------------------------------------------------------
# Internal runners
# ---------------------------------------------------------------------------

def _run_model1(data: dict, time_limit: int, verbose: bool) -> dict:
    from models.model1 import solve_jumbo_model
    result = solve_jumbo_model(data, verbose=verbose, time_limit=time_limit)
    if result is None:
        return {"status": "infeasible", "error": "Optimal çözüm bulunamadı."}
    result["used_reel_count"] = sum(1 for r in result.get("roll_data", []) if r["used"])
    return result


def _run_model2(data: dict, time_limit: int, verbose: bool) -> dict:
    from models.model2 import solve_jumbo_model
    result = solve_jumbo_model(data, verbose=verbose, time_limit=time_limit)
    if result is None:
        return {"status": "infeasible", "error": "Optimal çözüm bulunamadı."}
    result["used_reel_count"] = sum(1 for r in result.get("roll_data", []) if r["used"])
    return result


def _run_heuristic1(data: dict, verbose: bool) -> dict:
    from models.heuristic1 import solve_model1_heuristic, total_objective, compute_TW
    reel_plans = solve_model1_heuristic(data, verbose=verbose)
    return _extract_heuristic_results(reel_plans, data, compute_TW)


def _run_heuristic2(data: dict, verbose: bool) -> dict:
    from models.heuristic2 import solve_model2_heuristic, total_objective, compute_TW
    reel_plans = solve_model2_heuristic(data, verbose=verbose)
    return _extract_heuristic_results(reel_plans, data, compute_TW)


# ---------------------------------------------------------------------------
# Heuristic result extraction
# ---------------------------------------------------------------------------

def _extract_heuristic_results(reel_plans, data: dict, compute_TW_fn) -> dict:
    L = float(data["L"])
    lam = float(data["lambda"])
    TD = data["TD"]
    LD = data["LD"]

    ns = len(reel_plans)
    total_pw = 0.0
    total_tw = 0
    prev_pat = None
    roll_data = []

    # Check feasibility
    remaining_check = {d: int(data["ND"][d]) for d in data["D"]}
    for r in reel_plans:
        if r.used and r.pattern is not None:
            p = r.pattern
            for d, cnt in p.assignments.items():
                remaining_check[d] = remaining_check.get(d, 0) - cnt
            remaining_check[p.last_demand] = remaining_check.get(p.last_demand, 0) - 1

    unsatisfied = {d: v for d, v in remaining_check.items() if v != 0}

    for r in reel_plans:
        if not r.used or r.pattern is None:
            roll_data.append({
                "reel_id": r.reel_id,
                "reel_type": r.reel_type,
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

        p = r.pattern
        pw = p.paper_waste(L)
        tw = compute_TW_fn(prev_pat, p)

        total_pw += pw
        total_tw += tw

        blade_dist = p.display_blade_distances(LD)

        roll_data.append({
            "reel_id": r.reel_id,
            "reel_type": r.reel_type,
            "used": True,
            "blade_count": p.blade_count(),
            "assignments": dict(p.assignments),
            "last_demand": p.last_demand,
            "paper_waste": round(pw, 4),
            "time_waste": tw,
            "blade_distances": blade_dist,
            "used_length": round(p.used_length, 4),
        })

        prev_pat = p

    PW_max = ns * L
    obj = lam * (total_pw / PW_max) + (1 - lam) * (total_tw / ns) if ns > 0 else 0.0

    status = "feasible"
    error_msg = None
    if unsatisfied:
        status = "infeasible"
        error_msg = (
            "Bazı talepler karşılanamadı. Jumbo Reel sayısı yeterli olmayabilir.\n"
            + "\n".join(f"  Talep d{d}: {v} adet eksik" for d, v in unsatisfied.items())
        )

    return {
        "status": status,
        "objective_value": round(obj, 6),
        "total_pw": round(total_pw, 4),
        "total_tw": int(total_tw),
        "used_reel_count": sum(1 for r in reel_plans if r.used),
        "roll_data": roll_data,
        "error": error_msg,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_result(message: str, raw_output: str = "", tb: str = "") -> dict:
    return {
        "status": "error",
        "objective_value": None,
        "total_paper_waste": None,
        "total_time_waste": None,
        "used_reel_count": None,
        "runtime": 0.0,
        "roll_data": [],
        "raw_output": raw_output,
        "warning": None,
        "error": message + (f"\n\nDetay:\n{tb}" if tb else ""),
    }

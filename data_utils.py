"""
data_utils.py — Order data validation, transformation, and reel estimation.
"""

import math
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_orders(df: pd.DataFrame):
    """
    Returns (is_valid: bool, errors: list[str]).
    """
    errors = []

    required_cols = {"paper_type", "length", "quantity"}
    missing = required_cols - set(df.columns)
    if missing:
        _col_tr = {"paper_type": "Kağıt Tipi", "length": "Uzunluk", "quantity": "Miktar"}
        for col in missing:
            errors.append(f"Gerekli sütun eksik: '{_col_tr.get(col, col)}'")
        return False, errors

    if df.empty:
        errors.append("Sipariş tablosu boş. En az bir sipariş girilmelidir.")
        return False, errors

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed + header row

        # paper_type
        if pd.isna(row["paper_type"]) or str(row["paper_type"]).strip() == "":
            errors.append(f"Satır {row_num}: Kağıt tipi boş olamaz.")

        # length
        try:
            length = float(row["length"])
            if length <= 0:
                errors.append(f"Satır {row_num}: Uzunluk pozitif bir sayı olmalıdır (şu an: {length}).")
        except (ValueError, TypeError):
            errors.append(f"Satır {row_num}: Uzunluk sayısal bir değer olmalıdır.")

        # quantity
        try:
            qty = float(row["quantity"])
            if qty <= 0 or qty != int(qty):
                errors.append(f"Satır {row_num}: Miktar pozitif tam sayı olmalıdır (şu an: {row['quantity']}).")
        except (ValueError, TypeError):
            errors.append(f"Satır {row_num}: Miktar tam sayı bir değer olmalıdır.")

    return len(errors) == 0, errors


def validate_params(L, B, CT, lam, time_limit):
    """Validate solver parameters. Returns (is_valid, errors)."""
    errors = []

    try:
        L = float(L)
        if L <= 0:
            errors.append("Jumbo Bobin uzunluğu (L) pozitif olmalıdır.")
    except (ValueError, TypeError):
        errors.append("Jumbo Bobin uzunluğu (L) sayısal bir değer olmalıdır.")

    try:
        B = int(B)
        if B <= 0:
            errors.append("Bıçak sayısı (B) pozitif tam sayı olmalıdır.")
    except (ValueError, TypeError):
        errors.append("Bıçak sayısı (B) tam sayı bir değer olmalıdır.")

    try:
        CT = float(CT)
        if CT < 0:
            errors.append("CT değeri negatif olamaz.")
    except (ValueError, TypeError):
        errors.append("CT değeri sayısal bir değer olmalıdır.")

    try:
        lam = float(lam)
        if not (0 <= lam <= 1):
            errors.append("Lambda değeri 0 ile 1 arasında olmalıdır.")
    except (ValueError, TypeError):
        errors.append("Lambda değeri sayısal bir değer olmalıdır.")

    try:
        time_limit = int(time_limit)
        if time_limit <= 0:
            errors.append("Zaman limiti pozitif tam sayı olmalıdır.")
    except (ValueError, TypeError):
        errors.append("Zaman limiti tam sayı bir değer olmalıdır.")

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Reel count estimation
# ---------------------------------------------------------------------------

def estimate_reel_count(df: pd.DataFrame, L: float, B: int):
    """
    Returns (safe_count: int, estimated_min: int).
    safe_count is the upper bound used for S (internal, never shown to user).
    estimated_min is kept for backward compatibility.
    """
    total_quantity = int(df["quantity"].sum())
    total_length = float((df["length"] * df["quantity"]).sum())

    # Lower bound from quantity: ceil(total_qty / B) — each reel handles at most B+1 items
    min_by_qty = math.ceil(total_quantity / (B + 1))
    # Lower bound from length
    min_by_len = math.ceil(total_length / L)

    estimated_min = max(min_by_qty, min_by_len, 1)
    # Safety margin: 60% overhead, minimum 3 (internal upper bound only)
    safe_count = max(int(math.ceil(estimated_min * 1.6)) + 2, 3)

    return safe_count, estimated_min


def estimate_reels_detailed(df: pd.DataFrame, L: float):
    """
    User-facing reel count estimation with per-type breakdown.

    Returns:
        estimated_total (int)  — suggested total reels (shown to user)
        per_type (dict)        — {paper_type_str: suggested_reel_count}
    """
    df = df.copy()
    df["paper_type"] = df["paper_type"].astype(str).str.strip()
    df["length"]     = pd.to_numeric(df["length"],   errors="coerce").fillna(0)
    df["quantity"]   = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)

    unique_types = sorted(df["paper_type"].unique())
    n_types = max(len(unique_types), 1)

    # ── Per-type estimate ──────────────────────────────────────────────────
    per_type = {}
    for tp in unique_types:
        mask = df["paper_type"] == tp
        tp_len = float((df.loc[mask, "length"] * df.loc[mask, "quantity"]).sum())
        raw = math.ceil(tp_len / L) if L > 0 else 1
        per_type[tp] = max(1, math.ceil(raw * 1.10))

    # ── Total estimate ─────────────────────────────────────────────────────
    total_length = float((df["length"] * df["quantity"]).sum())
    base = math.ceil(total_length / L) if L > 0 else n_types
    estimated_total = max(n_types, math.ceil(base * 1.15) + n_types)

    return estimated_total, per_type


# ---------------------------------------------------------------------------
# Data dict builder
# ---------------------------------------------------------------------------

def build_data_dict(df: pd.DataFrame, L: float, B: int, CT: float, lam: float,
                    method: str, tj_dict: dict = None):
    """
    Build the solver data dictionary from an orders DataFrame.

    Returns (data: dict, type_map: dict, safe_count: int).
    type_map maps original paper_type label → integer type ID.
    """

    # Normalize paper_type to string for consistent mapping
    df = df.copy()
    df["paper_type"] = df["paper_type"].astype(str).str.strip()

    unique_types = sorted(df["paper_type"].unique(), key=lambda x: (not x.isdigit(), x))
    type_map = {t: i + 1 for i, t in enumerate(unique_types)}

    D = []
    TD = {}
    LD = {}
    ND = {}

    d_idx = 1
    for _, row in df.iterrows():
        D.append(d_idx)
        TD[d_idx] = type_map[str(row["paper_type"]).strip()]
        LD[d_idx] = float(row["length"])
        ND[d_idx] = int(row["quantity"])
        d_idx += 1

    T = list(range(1, len(unique_types) + 1))

    safe_count, _ = estimate_reel_count(df, L, B)

    # ── S (available reels) ────────────────────────────────────────────────
    # Model 1 / Heuristic 1: the user's TJ assignment IS the source of truth.
    # S must be exactly the reels the user assigned — do NOT pad to safe_count.
    # Model 2 / Heuristic 2: no fixed assignment, use safe_count upper bound.
    if method in ("Model 1", "Heuristic Model 1") and tj_dict is not None:
        S = sorted(tj_dict.keys())
    else:
        S = list(range(1, safe_count + 1))

    data = {
        "S": S,
        "D": D,
        "B": B,
        "L": float(L),
        "CT": float(CT),
        "lambda": float(lam),
        "TD": TD,
        "LD": LD,
        "ND": ND,
    }

    if method in ("Model 2", "Heuristic Model 2"):
        data["T"] = T

    if method in ("Model 1", "Heuristic Model 1"):
        if tj_dict is not None:
            # Use the user's assignment verbatim — no auto-fill beyond it.
            data["TJ"] = dict(tj_dict)
        else:
            # Auto-distribute types proportionally (fallback / no UI assignment)
            data["TJ"] = _auto_tj(S, T, TD, ND, D)

    return data, type_map, safe_count


def _auto_tj(S, T, TD, ND, D):
    """
    Automatically assign jumbo reel types proportional to demand quantities.
    """
    if len(T) == 1:
        return {s: T[0] for s in S}

    # Compute demand count per type
    type_demand = {}
    for d in D:
        t = TD[d]
        type_demand[t] = type_demand.get(t, 0) + ND[d]

    total_demand = sum(type_demand.values())
    ns = len(S)

    # Allocate reels proportionally
    type_counts = {}
    allocated = 0
    for i, t in enumerate(T):
        if i < len(T) - 1:
            cnt = max(1, round(ns * type_demand.get(t, 0) / total_demand))
            type_counts[t] = cnt
            allocated += cnt
        else:
            type_counts[t] = max(1, ns - allocated)

    # Build TJ: group by type in blocks
    tj = {}
    s_iter = iter(S)
    for t in T:
        for _ in range(type_counts.get(t, 1)):
            try:
                s = next(s_iter)
                tj[s] = t
            except StopIteration:
                break

    # Fill any remaining
    for s in S:
        if s not in tj:
            tj[s] = T[-1]

    return tj


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _fmt(v) -> str:
    """Format a float cleanly: drop trailing .0 for whole numbers."""
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else f"{f:g}"
    except Exception:
        return str(v)


def build_roll_display_df(roll_data: list, TD: dict, LD: dict) -> pd.DataFrame:
    """Convert raw roll_data list to a display-ready DataFrame (used reels only)."""
    rows = []
    for r in roll_data:
        if not r["used"]:
            continue

        # Kesim Deseni — compact: "140 + 104 + 100"
        cutting_lengths = []
        for d, cnt in sorted(r["assignments"].items()):
            cutting_lengths.extend([_fmt(LD[d])] * cnt)
        if r["last_demand"] is not None:
            cutting_lengths.append(_fmt(LD[r["last_demand"]]))
        pattern_str = " + ".join(cutting_lengths) if cutting_lengths else "—"

        # Blade Mesafeleri — compact tuple string
        if r["blade_distances"]:
            bd_str = "(" + ", ".join(_fmt(x) for x in r["blade_distances"]) + ")"
        else:
            bd_str = "()"

        # Atanan Siparişler — right-most column; concise
        asgn_parts = []
        for d, cnt in sorted(r["assignments"].items()):
            asgn_parts.append(f"d{d} T{TD[d]} {_fmt(LD[d])}cm ×{cnt}")
        if r["last_demand"] is not None:
            ld = r["last_demand"]
            asgn_parts.append(f"d{ld} T{TD[ld]} {_fmt(LD[ld])}cm ×1[son]")
        assigned_str = " | ".join(asgn_parts) if asgn_parts else "—"

        rows.append({
            "Jumbo Bobin No":   r["reel_id"],
            "Jumbo Bobin Tipi": r["reel_type"] if r["reel_type"] is not None else "—",
            "Kesim Deseni":    pattern_str,
            "Kullanılan Uzunluk": r["used_length"],
            "Bıçak Mesafeleri": bd_str,
            "Bıçak Sayısı":    r["blade_count"],
            "Kağıt Kaybı":     r["paper_waste"],
            "Zaman Kaybı":     r["time_waste"],
            "Atanan Siparişler": assigned_str,
        })

    return pd.DataFrame(rows)


def normalize_orders_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce canonical dtypes for the orders DataFrame so st.data_editor
    never sees a type mismatch with its column configuration:
      paper_type → str
      length     → float64
      quantity   → Int64  (nullable integer)
    """
    df = df.copy()

    # paper_type must be string for TextColumn
    df["paper_type"] = df["paper_type"].astype(str).str.strip()

    # length must be float
    df["length"] = pd.to_numeric(df["length"], errors="coerce")

    # quantity must be integer (use nullable Int64 so NaN rows don't crash)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")

    return df


def get_sample_orders_df(csv_path: str = None) -> pd.DataFrame:
    """
    Load sample orders from example_orders.csv.
    csv_path should be the absolute path to the file.
    Falls back to an empty template DataFrame if the file is missing.
    """
    if csv_path is not None:
        try:
            df = pd.read_csv(csv_path)
            df["paper_type"] = df["paper_type"].astype(str).str.strip()
            df["length"]     = pd.to_numeric(df["length"],   errors="coerce")
            df["quantity"]   = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")
            return df[["paper_type", "length", "quantity"]].copy()
        except Exception:
            pass  # fall through to empty template

    # Fallback: return an empty template with the correct columns
    return pd.DataFrame(
        columns=["paper_type", "length", "quantity"]
    ).astype({"length": float, "quantity": "Int64"})

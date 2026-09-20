from __future__ import annotations

import pandas as pd


def dominance_validation(daily: pd.DataFrame, tolerance: float = 1e-5) -> dict:
    smart_violation = daily["sc_carbon_kg"] - daily["uc_carbon_kg"]
    v2g_violation = daily["v2g_carbon_kg"] - daily["sc_carbon_kg"]
    return {
        "maximum_smart_vs_uc_violation_kg": float(max(0.0, smart_violation.max())),
        "maximum_v2g_vs_smart_violation_kg": float(max(0.0, v2g_violation.max())),
        "pass": bool(
            smart_violation.max() <= tolerance and v2g_violation.max() <= tolerance
        ),
    }


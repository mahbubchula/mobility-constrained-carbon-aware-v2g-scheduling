from __future__ import annotations

import numpy as np
import pandas as pd


def soc_validation(ev_results: pd.DataFrame, tolerance: float = 1e-6) -> dict:
    sc_error = np.abs(ev_results["sc_departure_soc"] - ev_results["target_soc"])
    v2g_error = np.abs(ev_results["v2g_departure_soc"] - ev_results["target_soc"])
    v2g_min_soc = ev_results["arrival_soc"] + (
        ev_results["v2g_min_prefix_battery_kwh"] / ev_results["battery_kwh"]
    )
    v2g_max_soc = ev_results["arrival_soc"] + (
        ev_results["v2g_max_prefix_battery_kwh"] / ev_results["battery_kwh"]
    )
    return {
        "max_smart_departure_soc_error": float(sc_error.max()),
        "max_v2g_departure_soc_error": float(v2g_error.max()),
        "minimum_v2g_soc": float(v2g_min_soc.min()),
        "maximum_v2g_soc": float(v2g_max_soc.max()),
        "pass": bool(
            sc_error.max() <= tolerance
            and v2g_error.max() <= tolerance
            and v2g_min_soc.min() >= ev_results["arrival_soc"].min() - tolerance
            and v2g_max_soc.max() <= 0.95 + tolerance
        ),
    }


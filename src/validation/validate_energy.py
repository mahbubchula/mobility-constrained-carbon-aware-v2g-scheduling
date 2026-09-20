from __future__ import annotations

import numpy as np
import pandas as pd


def energy_validation(ev_results: pd.DataFrame, config: dict, tolerance: float = 1e-5) -> dict:
    required = ev_results["required_battery_energy_kwh"].to_numpy()
    sc_balance = (
        config["eta_ch"] * ev_results["sc_import_kwh"].to_numpy() - required
    )
    v2g_balance = (
        config["eta_ch"] * ev_results["v2g_import_kwh"].to_numpy()
        - ev_results["v2g_export_kwh"].to_numpy() / config["eta_dis"]
        - required
    )
    cap_violation = ev_results["v2g_export_kwh"].to_numpy() - (
        config["v2g_max_discharge_fraction_capacity"]
        * ev_results["battery_kwh"].to_numpy()
    )
    return {
        "max_smart_energy_balance_error_kwh": float(np.max(np.abs(sc_balance))),
        "max_v2g_energy_balance_error_kwh": float(np.max(np.abs(v2g_balance))),
        "max_discharge_cap_violation_kwh": float(max(0.0, cap_violation.max())),
        "pass": bool(
            np.max(np.abs(sc_balance)) <= tolerance
            and np.max(np.abs(v2g_balance)) <= tolerance
            and cap_violation.max() <= tolerance
        ),
    }


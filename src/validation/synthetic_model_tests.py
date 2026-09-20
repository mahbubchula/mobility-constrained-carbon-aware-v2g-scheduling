from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from src.optimization.model import solve_optimized_day
from src.optimization.uncontrolled import solve_uncontrolled_day


def _vehicle(arrival: int, departure: int, arrival_soc: float, target_soc: float) -> pd.DataFrame:
    battery = 60.0
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2025-01-01"),
                "day_index": 0,
                "ev_id": 0,
                "ev_day_id": 0,
                "arrival_interval": arrival,
                "departure_interval": departure,
                "arrival_soc": arrival_soc,
                "target_soc": target_soc,
                "battery_kwh": battery,
                "required_battery_energy_kwh": battery * (target_soc - arrival_soc),
            }
        ]
    )


def flat_carbon_test(config: dict) -> dict:
    ci = np.full(96, 0.25)
    vehicles = _vehicle(32, 64, 0.70, 0.80)
    uc, _ = solve_uncontrolled_day(vehicles, ci, config)
    sc = solve_optimized_day(vehicles, ci, config, "smart").ev_metrics
    v2g = solve_optimized_day(vehicles, ci, config, "v2g").ev_metrics
    return {
        "uc_carbon_kg": uc["uc_carbon_kg"].iloc[0],
        "sc_carbon_kg": sc["sc_carbon_kg"].iloc[0],
        "v2g_carbon_kg": v2g["v2g_carbon_kg"].iloc[0],
        "v2g_export_kwh": v2g["v2g_export_kwh"].iloc[0],
        "pass": bool(
            abs(uc["uc_carbon_kg"].iloc[0] - sc["sc_carbon_kg"].iloc[0]) < 1e-6
            and abs(sc["sc_carbon_kg"].iloc[0] - v2g["v2g_carbon_kg"].iloc[0]) < 1e-6
            and v2g["v2g_export_kwh"].iloc[0] < 1e-6
        ),
    }


def break_even_test(config: dict) -> dict:
    vehicles = _vehicle(0, 2, 0.60, 0.60)
    low = 0.20
    threshold = low / config["round_trip_efficiency"]
    ci_below = np.full(96, 0.20)
    ci_below[1] = threshold - 0.005
    ci_above = np.full(96, 0.20)
    ci_above[1] = threshold + 0.05
    below = solve_optimized_day(vehicles, ci_below, config, "v2g").ev_metrics
    above = solve_optimized_day(vehicles, ci_above, config, "v2g").ev_metrics
    below_export = below["v2g_export_kwh"].iloc[0]
    above_export = above["v2g_export_kwh"].iloc[0]
    return {
        "low_ci_kg_per_kwh": low,
        "analytical_threshold_kg_per_kwh": threshold,
        "below_threshold_export_kwh": below_export,
        "above_threshold_export_kwh": above_export,
        "pass": bool(below_export < 1e-6 and above_export > 1e-6),
    }


def zero_flexibility_test(config: dict) -> dict:
    local = copy.deepcopy(config)
    dt = local["delta_t_hours"]
    required = local["eta_ch"] * local["charging_power_kw"] * dt
    arrival_soc = 0.70
    vehicles = _vehicle(20, 21, arrival_soc, arrival_soc + required / 60.0)
    ci = np.linspace(0.1, 0.4, 96)
    uc, _ = solve_uncontrolled_day(vehicles, ci, local)
    sc = solve_optimized_day(vehicles, ci, local, "smart").ev_metrics
    v2g = solve_optimized_day(vehicles, ci, local, "v2g").ev_metrics
    return {
        "uc_carbon_kg": uc["uc_carbon_kg"].iloc[0],
        "sc_carbon_kg": sc["sc_carbon_kg"].iloc[0],
        "v2g_carbon_kg": v2g["v2g_carbon_kg"].iloc[0],
        "pass": bool(
            abs(uc["uc_carbon_kg"].iloc[0] - sc["sc_carbon_kg"].iloc[0]) < 1e-6
            and abs(sc["sc_carbon_kg"].iloc[0] - v2g["v2g_carbon_kg"].iloc[0]) < 1e-6
        ),
    }


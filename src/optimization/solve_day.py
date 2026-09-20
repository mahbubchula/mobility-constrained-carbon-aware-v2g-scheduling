from __future__ import annotations

import numpy as np
import pandas as pd

from src.optimization.model import solve_optimized_day
from src.optimization.uncontrolled import solve_uncontrolled_day


def solve_day(
    vehicles: pd.DataFrame,
    carbon_intensity: np.ndarray,
    config: dict,
    include_uncontrolled: bool = True,
    include_smart: bool = True,
    include_v2g: bool = True,
    evaluation_carbon_intensity: np.ndarray | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    metrics = vehicles.copy()
    schedules = pd.DataFrame(
        {"interval": np.arange(96), "carbon_intensity_kg_per_kwh": carbon_intensity}
    )
    diagnostics: dict[str, object] = {}
    if include_uncontrolled:
        uc_metrics, uc_schedule = solve_uncontrolled_day(vehicles, carbon_intensity, config)
        metrics = metrics.merge(uc_metrics, on="ev_day_id", how="left", validate="one_to_one")
        schedules = schedules.merge(
            uc_schedule.drop(columns="carbon_intensity_kg_per_kwh"), on="interval"
        )
    if include_smart:
        smart = solve_optimized_day(
            vehicles,
            carbon_intensity,
            config,
            "smart",
            evaluation_carbon_intensity=evaluation_carbon_intensity,
        )
        metrics = metrics.merge(smart.ev_metrics, on="ev_day_id", validate="one_to_one")
        schedules = schedules.merge(
            smart.schedule.drop(
                columns=["carbon_intensity_kg_per_kwh", "optimization_signal_kg_per_kwh"]
            ),
            on="interval",
        )
        diagnostics["smart_termination"] = smart.termination
        diagnostics["smart_objective_kg"] = smart.objective_kg
    if include_v2g:
        v2g = solve_optimized_day(
            vehicles,
            carbon_intensity,
            config,
            "v2g",
            evaluation_carbon_intensity=evaluation_carbon_intensity,
        )
        metrics = metrics.merge(v2g.ev_metrics, on="ev_day_id", validate="one_to_one")
        schedules = schedules.merge(
            v2g.schedule.drop(
                columns=["carbon_intensity_kg_per_kwh", "optimization_signal_kg_per_kwh"]
            ),
            on="interval",
        )
        diagnostics["v2g_termination"] = v2g.termination
        diagnostics["v2g_objective_kg"] = v2g.objective_kg
        diagnostics["simultaneous_intervals"] = v2g.simultaneous_intervals
    schedules.insert(0, "date", pd.Timestamp(vehicles["date"].iloc[0]))
    return metrics, schedules, diagnostics

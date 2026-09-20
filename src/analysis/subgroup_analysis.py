from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import ROOT, load_config


GROUP_VARIABLES = {
    "flexibility": "Mobility flexibility",
    "carbon_opportunity_kg_per_kwh": "Carbon opportunity",
    "required_battery_energy_kwh": "Required charging energy",
}


def _cluster_bootstrap_ci(
    group: pd.DataFrame, rng: np.random.Generator, repetitions: int
) -> tuple[float, float]:
    by_day = group.groupby("date")["incremental_v2g_saving_kg"].agg(["sum", "count"])
    values = []
    for _ in range(repetitions):
        sampled = by_day.iloc[rng.integers(0, len(by_day), len(by_day))]
        values.append(sampled["sum"].sum() / sampled["count"].sum())
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def subgroup_analysis(
    ev_results: pd.DataFrame | None = None, config: dict | None = None
) -> pd.DataFrame:
    config = config or load_config()
    if ev_results is None:
        ev_results = pd.read_parquet(ROOT / "results" / "results_ev_level.parquet")
    ev_results = ev_results.copy()
    ev_results["date"] = pd.to_datetime(ev_results["date"])
    rng = np.random.default_rng(config["seed"] + 211)
    rows = []
    for variable, label in GROUP_VARIABLES.items():
        quartile_column = f"{variable}_quartile"
        # Rank first so tied zero-demand/flexibility values are distributed
        # deterministically while retaining four equal-sized descriptive groups.
        ev_results[quartile_column] = pd.qcut(
            ev_results[variable].rank(method="first"),
            4,
            labels=["Q1", "Q2", "Q3", "Q4"],
        )
        for quartile, group in ev_results.groupby(quartile_column, observed=True):
            values = group["incremental_v2g_saving_kg"]
            lower, upper = _cluster_bootstrap_ci(
                group, rng, min(2000, config["bootstrap_repetitions"])
            )
            rows.append(
                {
                    "dimension": label,
                    "variable": variable,
                    "quartile": str(quartile),
                    "n_ev_days": len(group),
                    "range_min": group[variable].min(),
                    "range_max": group[variable].max(),
                    "mean_incremental_v2g_saving_kg_per_ev_day": values.mean(),
                    "median_incremental_v2g_saving_kg_per_ev_day": values.median(),
                    "iqr_incremental_v2g_saving_kg_per_ev_day": values.quantile(0.75)
                    - values.quantile(0.25),
                    "bootstrap_ci95_lower_mean_kg": lower,
                    "bootstrap_ci95_upper_mean_kg": upper,
                }
            )
    result = pd.DataFrame(rows)
    result.to_csv(ROOT / "results" / "tables" / "table05_subgroups.csv", index=False)
    return result


if __name__ == "__main__":
    subgroup_analysis()

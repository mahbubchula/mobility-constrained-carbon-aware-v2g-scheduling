from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import ROOT, load_config


def paired_daily_bootstrap(
    daily: pd.DataFrame | None = None, config: dict | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = config or load_config()
    if daily is None:
        daily = pd.read_csv(ROOT / "results" / "results_daily.csv", parse_dates=["date"])
    rng = np.random.default_rng(config["seed"] + 101)
    n_days = len(daily)
    draws = config["bootstrap_repetitions"]
    indices = rng.integers(0, n_days, size=(draws, n_days))
    smart = daily["smart_saving_kg"].to_numpy()[indices].sum(axis=1)
    v2g = daily["incremental_v2g_saving_kg"].to_numpy()[indices].sum(axis=1)
    results = pd.DataFrame(
        {
            "draw": np.arange(draws),
            "smart_saving_kg": smart,
            "incremental_v2g_saving_kg": v2g,
        }
    )
    summary = pd.DataFrame(
        [
            {
                "metric": metric,
                "estimate_kg": daily[column].sum(),
                "ci95_lower_kg": np.quantile(results[column], 0.025),
                "ci95_upper_kg": np.quantile(results[column], 0.975),
            }
            for metric, column in (
                ("Smart charging saving vs UC", "smart_saving_kg"),
                ("Incremental V2G saving vs SC", "incremental_v2g_saving_kg"),
            )
        ]
    )
    results.to_csv(ROOT / "results" / "bootstrap_results.csv", index=False)
    summary.to_csv(ROOT / "results" / "tables" / "bootstrap_summary.csv", index=False)
    return results, summary


if __name__ == "__main__":
    paired_daily_bootstrap()


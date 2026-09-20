from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance

from src.common import ROOT, load_config, setup_logging, weighted_choice_indices


VARIABLES = {
    "arrival_min": "Arrival time (minutes after midnight)",
    "departure_min": "Departure time (minutes after midnight)",
    "connection_hours": "Connection duration (h)",
    "inbound_distance_km": "Inbound commute distance (km)",
    "return_distance_km": "Return commute distance (km)",
}


def _summary(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    quantiles = np.quantile(values, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)),
        "p05": quantiles[0],
        "p25": quantiles[1],
        "median": quantiles[2],
        "p75": quantiles[3],
        "p95": quantiles[4],
    }


def validate_synthetic_data(config: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = config or load_config()
    logger = setup_logging()
    calibration = pd.read_parquet(
        ROOT / "data" / "processed" / "commuter_calibration_pool.parquet"
    )
    holdout = pd.read_parquet(ROOT / "data" / "processed" / "commuter_holdout.parquet")
    synthetic = pd.read_parquet(ROOT / "data" / "synthetic" / "synthetic_ev_days.parquet")

    # The NHTS is a weighted survey. A fixed weighted holdout reference sample
    # makes the two-sample metrics reflect the national travel weights while
    # retaining the record-level holdout N in the reporting tables.
    rng = np.random.default_rng(config["seed"] + 17)
    reference_size = min(50_000, len(synthetic))
    reference = holdout.iloc[
        weighted_choice_indices(rng, holdout["nhts_weight"].to_numpy(), reference_size)
    ].reset_index(drop=True)

    rows = []
    for variable, label in VARIABLES.items():
        synth_values = synthetic[variable].to_numpy()
        hold_values = reference[variable].to_numpy()
        cal_values = calibration[variable].to_numpy()
        synth_summary = _summary(synth_values)
        hold_summary = _summary(hold_values)
        cal_summary = _summary(cal_values)
        ks = ks_2samp(synth_values, hold_values, method="asymp").statistic
        wasserstein = wasserstein_distance(synth_values, hold_values)
        rows.append(
            {
                "variable": variable,
                "label": label,
                **{f"calibration_{k}": v for k, v in cal_summary.items()},
                **{f"synthetic_{k}": v for k, v in synth_summary.items()},
                **{f"holdout_{k}": v for k, v in hold_summary.items()},
                "ks_statistic": ks,
                "wasserstein_distance": wasserstein,
                "normalized_wasserstein": wasserstein / max(hold_summary["std"], 1e-12),
            }
        )
    validation = pd.DataFrame(rows)

    correlation_pairs = [
        ("arrival_min", "departure_min", "Corr(A,D)"),
        ("arrival_min", "inbound_distance_km", "Corr(A,d_in)"),
        ("connection_hours", "inbound_distance_km", "Corr(W,d_in)"),
    ]
    correlations = pd.DataFrame(
        [
            {
                "relationship": label,
                "calibration": calibration[x].corr(calibration[y]),
                "synthetic": synthetic[x].corr(synthetic[y]),
                "holdout_weighted_reference": reference[x].corr(reference[y]),
            }
            for x, y, label in correlation_pairs
        ]
    )
    # Effect-size thresholds are diagnostics, not significance hunting.
    validation["acceptable"] = (
        validation["ks_statistic"].le(0.15)
        & validation["normalized_wasserstein"].le(0.25)
    )
    validation.to_csv(
        ROOT / "results" / "validation" / "synthetic_distribution_validation.csv",
        index=False,
    )
    correlations.to_csv(
        ROOT / "results" / "validation" / "synthetic_correlation_validation.csv",
        index=False,
    )
    if not validation["acceptable"].all():
        logger.warning(
            "One or more synthetic validation diagnostics exceed the prespecified "
            "effect-size thresholds; inspect before optimization."
        )
    else:
        logger.info("Synthetic mobility validation passed all effect-size thresholds")
    return validation, correlations


if __name__ == "__main__":
    validate_synthetic_data()

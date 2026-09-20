from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import ROOT, dataframe_to_parquet, load_config, setup_logging


PRIVATE_VEHICLE_MODES = {1, 2, 3, 4}  # car, van, SUV/crossover, pickup


def hhmm_to_minutes(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    hours = np.floor(numeric / 100)
    minutes = numeric % 100
    valid = numeric.ge(0) & hours.between(0, 23) & minutes.between(0, 59)
    return pd.Series(np.where(valid, hours * 60 + minutes, np.nan), index=values.index)


def build_commuter_pool(config: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = config or load_config()
    logger = setup_logging()
    source = ROOT / "data" / "raw" / "nhts" / "tripv2pub.csv"
    trips = pd.read_csv(source, low_memory=False)
    trips["start_min"] = hhmm_to_minutes(trips["STRTTIME"])
    trips["end_min"] = hhmm_to_minutes(trips["ENDTIME"])

    valid = trips.loc[
        trips["TRPTRANS"].isin(PRIVATE_VEHICLE_MODES)
        & trips["TRPHHVEH"].eq(1)
        & trips["DRVR_FLG"].eq(1)
        & trips["TRPMILES"].gt(0)
        & trips["start_min"].notna()
        & trips["end_min"].notna()
    ].copy()
    keys = ["HOUSEID", "PERSONID", "TDAYDATE"]
    inbound = (
        valid.loc[valid["WHYFROM"].eq(1) & valid["WHYTO"].eq(3)]
        .sort_values(keys + ["end_min"])
        .groupby(keys, as_index=False)
        .first()
    )
    outbound = (
        valid.loc[valid["WHYFROM"].eq(3) & valid["WHYTO"].eq(1)]
        .sort_values(keys + ["start_min"])
        .groupby(keys, as_index=False)
        .last()
    )
    paired = inbound.merge(outbound, on=keys, suffixes=("_in", "_out"))
    paired = paired.loc[
        paired["end_min_in"].lt(paired["start_min_out"])
        & paired["TDWKND_in"].eq(paired["TDWKND_out"])
    ].copy()
    pool = pd.DataFrame(
        {
            "source_id": (
                paired["HOUSEID"].astype(str)
                + "-"
                + paired["PERSONID"].astype(str)
                + "-"
                + paired["TDAYDATE"].astype(str)
            ),
            "arrival_min": paired["end_min_in"].astype(float),
            "departure_min": paired["start_min_out"].astype(float),
            "inbound_distance_km": paired["TRPMILES_in"].astype(float) * 1.609344,
            "return_distance_km": paired["TRPMILES_out"].astype(float) * 1.609344,
            "nhts_weight": paired[["WTTRDFIN_in", "WTTRDFIN_out"]].mean(axis=1),
            "is_weekend": paired["TDWKND_in"].eq(1),
            "travel_month": pd.to_numeric(paired["TDAYDATE"], errors="coerce") % 100,
        }
    )
    pool["connection_hours"] = (pool["departure_min"] - pool["arrival_min"]) / 60

    # Transparent validity rules: direct same-day commute, 1 h to 18 h at work,
    # positive observed distance, and no distance trimming beyond physical validity.
    pool = pool.loc[
        pool["connection_hours"].between(1.0, 18.0)
        & pool["inbound_distance_km"].gt(0)
        & pool["return_distance_km"].gt(0)
    ].reset_index(drop=True)

    rng = np.random.default_rng(config["seed"])
    # Split independently by day type so the small weekend worker sample remains
    # represented in both calibration and holdout sets.
    calibration_parts = []
    holdout_parts = []
    for _, group in pool.groupby("is_weekend", sort=False):
        shuffled = rng.permutation(group.index.to_numpy())
        cut = int(np.floor(len(group) * config["calibration_fraction"]))
        calibration_parts.append(pool.loc[shuffled[:cut]])
        holdout_parts.append(pool.loc[shuffled[cut:]])
    calibration = pd.concat(calibration_parts).sort_values("source_id").reset_index(drop=True)
    holdout = pd.concat(holdout_parts).sort_values("source_id").reset_index(drop=True)

    dataframe_to_parquet(
        calibration, ROOT / "data" / "processed" / "commuter_calibration_pool.parquet"
    )
    dataframe_to_parquet(
        holdout, ROOT / "data" / "processed" / "commuter_holdout.parquet"
    )
    exclusions = pd.DataFrame(
        [
            {"stage": "raw trips", "n": len(trips)},
            {"stage": "valid private-vehicle driver trips", "n": len(valid)},
            {"stage": "paired direct home-work-home days", "n": len(paired)},
            {"stage": "final commuter pool", "n": len(pool)},
            {"stage": "calibration", "n": len(calibration)},
            {"stage": "holdout", "n": len(holdout)},
        ]
    )
    exclusions.to_csv(ROOT / "results" / "validation" / "nhts_selection_flow.csv", index=False)
    logger.info(
        "Constructed NHTS commuter pool: %d calibration, %d holdout",
        len(calibration),
        len(holdout),
    )
    return calibration, holdout


if __name__ == "__main__":
    build_commuter_pool()

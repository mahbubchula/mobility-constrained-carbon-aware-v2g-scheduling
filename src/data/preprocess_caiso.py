from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from src.common import ROOT, dataframe_to_parquet, load_config, setup_logging


def _verify_units(path: Path) -> None:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    text = "\n".join(
        str(value)
        for row in workbook["KEY"].iter_rows(values_only=True)
        for value in row
        if value is not None
    )
    required = ("AVG_EM_RATE", "MTCO2e", "MWh")
    if not all(token in text for token in required):
        raise ValueError(f"Could not verify CAISO AER units from {path.name}")


def preprocess_caiso(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    logger = setup_logging()
    files = sorted(Path(p) for p in glob.glob(str(ROOT / "data/raw/caiso/*.xlsx")))
    if len(files) != 12:
        raise FileNotFoundError(f"Expected 12 CAISO monthly workbooks, found {len(files)}")
    _verify_units(files[0])

    frames = []
    for path in files:
        frame = pd.read_excel(path, sheet_name="AER_SUMMARY")
        frame["source_file"] = path.name
        frames.append(frame)
    raw = pd.concat(frames, ignore_index=True)
    raw["date"] = pd.to_datetime(raw["TRADE_DT"], format="mixed")
    raw["trade_hour_original"] = pd.to_numeric(raw["TRADE_HR"])
    raw["ci_kg_per_kwh"] = pd.to_numeric(raw["AVG_EM_RATE"])
    if raw["date"].nunique() != config["n_days"]:
        raise ValueError("CAISO coverage does not contain the configured number of dates")
    if not raw["ci_kg_per_kwh"].between(0, 2).all():
        raise ValueError("CAISO AER failed the documented MTCO2e/MWh plausibility check")

    # Normalize each local calendar date to 24 clock hours. For the fall DST day,
    # average the two repeated 1-2 a.m. observations (HE2 and HE3), then shift
    # HE4..HE25 back to HE3..HE24. Spring HE3 and isolated missing observations
    # are interpolated and explicitly flagged.
    hourly_parts: list[pd.DataFrame] = []
    for day, group in raw.groupby("date", sort=True):
        group = group.sort_values("trade_hour_original").copy()
        dst_adjustment = "none"
        if group["trade_hour_original"].max() == 25:
            dst_adjustment = "fall_repeat_averaged"
            repeated = group.loc[group["trade_hour_original"].isin([2, 3])]
            row = repeated.iloc[0].copy()
            numeric_cols = group.select_dtypes(include=[np.number]).columns
            row[numeric_cols] = repeated[numeric_cols].mean()
            row["trade_hour_original"] = 2
            after = group.loc[group["trade_hour_original"].ge(4)].copy()
            after["trade_hour_original"] -= 1
            group = pd.concat(
                [group.loc[group["trade_hour_original"].eq(1)], row.to_frame().T, after],
                ignore_index=True,
            )
        indexed = group.set_index("trade_hour_original")[["ci_kg_per_kwh"]]
        indexed = indexed.groupby(level=0).mean().reindex(range(1, 25))
        indexed["ci_kg_per_kwh"] = pd.to_numeric(indexed["ci_kg_per_kwh"], errors="coerce")
        missing = indexed["ci_kg_per_kwh"].isna()
        indexed["ci_kg_per_kwh"] = indexed["ci_kg_per_kwh"].interpolate(
            method="linear", limit_direction="both"
        )
        # If a missing value occurs at a boundary, within-day filling above is
        # conservative; the annual interpolation below refines such boundaries.
        part = indexed.reset_index(names="trade_hour")
        part["date"] = day
        part["hour_imputed"] = missing.to_numpy()
        part["dst_adjustment"] = dst_adjustment
        hourly_parts.append(part)
    hourly = pd.concat(hourly_parts, ignore_index=True).sort_values(["date", "trade_hour"])
    hourly["ci_kg_per_kwh"] = pd.to_numeric(hourly["ci_kg_per_kwh"], errors="coerce")
    hourly["timestamp_local"] = hourly["date"] + pd.to_timedelta(
        hourly["trade_hour"] - 1, unit="h"
    )
    hourly = hourly.sort_values("timestamp_local")
    hourly["ci_kg_per_kwh"] = hourly["ci_kg_per_kwh"].interpolate(limit_direction="both")
    hourly.to_csv(ROOT / "data" / "interim" / "caiso_carbon_hourly.csv", index=False)

    repeated = hourly.loc[hourly.index.repeat(4)].copy().reset_index(drop=True)
    repeated["quarter"] = np.tile(np.arange(4), len(hourly))
    repeated["interval"] = (repeated["trade_hour"] - 1) * 4 + repeated["quarter"]
    repeated["timestamp_local"] = repeated["date"] + pd.to_timedelta(
        repeated["interval"] * config["time_step_minutes"], unit="m"
    )
    repeated["unit_original"] = "MTCO2e/MWh"
    repeated["unit_model"] = "kgCO2e/kWh"
    repeated["unit_conversion_factor"] = 1.0
    repeated["carbon_temporal_resolution_minutes"] = 60
    repeated = repeated[
        [
            "date",
            "interval",
            "timestamp_local",
            "ci_kg_per_kwh",
            "hour_imputed",
            "dst_adjustment",
            "unit_original",
            "unit_model",
            "unit_conversion_factor",
            "carbon_temporal_resolution_minutes",
        ]
    ].reset_index(drop=True)
    dataframe_to_parquet(
        repeated, ROOT / "data" / "processed" / "caiso_carbon_15min.parquet"
    )
    quality = pd.DataFrame(
        [
            {"check": "monthly workbooks", "value": len(files), "status": "PASS"},
            {"check": "calendar dates", "value": raw["date"].nunique(), "status": "PASS"},
            {
                "check": "source hourly rows",
                "value": len(raw),
                "status": "PASS",
            },
            {
                "check": "normalized hourly rows",
                "value": len(hourly),
                "status": "PASS" if len(hourly) == 365 * 24 else "FAIL",
            },
            {
                "check": "imputed clock hours",
                "value": int(hourly["hour_imputed"].sum()),
                "status": "DOCUMENTED",
            },
            {
                "check": "AER minimum kgCO2e/kWh",
                "value": hourly["ci_kg_per_kwh"].min(),
                "status": "PASS",
            },
            {
                "check": "AER maximum kgCO2e/kWh",
                "value": hourly["ci_kg_per_kwh"].max(),
                "status": "PASS",
            },
        ]
    )
    quality.to_csv(ROOT / "results" / "validation" / "caiso_data_quality.csv", index=False)
    logger.info(
        "Processed CAISO AER: %d hourly values, %d imputed, repeated to %d intervals",
        len(hourly),
        int(hourly["hour_imputed"].sum()),
        len(repeated),
    )
    return repeated


if __name__ == "__main__":
    preprocess_caiso()

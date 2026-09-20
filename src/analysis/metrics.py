from __future__ import annotations

import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.carbon_opportunity import add_carbon_opportunity
from src.common import ROOT, dataframe_to_parquet, load_config, setup_logging
from src.optimization.solve_day import solve_day


def _carbon_by_date(carbon: pd.DataFrame) -> dict[pd.Timestamp, np.ndarray]:
    return {
        pd.Timestamp(day): group.sort_values("interval")["ci_kg_per_kwh"].to_numpy()
        for day, group in carbon.groupby("date", sort=True)
    }


def daily_summary(metrics: pd.DataFrame, diagnostics: dict) -> dict:
    day = pd.Timestamp(metrics["date"].iloc[0])
    result = {
        "date": day,
        "n_evs": len(metrics),
        "required_battery_energy_kwh": metrics["required_battery_energy_kwh"].sum(),
        "mean_flexibility": metrics["flexibility"].mean(),
        "mean_carbon_opportunity_kg_per_kwh": metrics[
            "carbon_opportunity_kg_per_kwh"
        ].mean(),
    }
    for prefix in ("uc", "sc", "v2g"):
        if f"{prefix}_carbon_kg" not in metrics:
            continue
        for name in (
            "import_kwh",
            "export_kwh",
            "net_grid_kwh",
            "carbon_kg",
            "charge_carbon_kg",
            "discharge_carbon_credit_kg",
        ):
            result[f"{prefix}_{name}"] = metrics[f"{prefix}_{name}"].sum()
    if "uc_carbon_kg" in result and "sc_carbon_kg" in result:
        result["smart_saving_kg"] = result["uc_carbon_kg"] - result["sc_carbon_kg"]
    if "sc_carbon_kg" in result and "v2g_carbon_kg" in result:
        result["incremental_v2g_saving_kg"] = (
            result["sc_carbon_kg"] - result["v2g_carbon_kg"]
        )
        result["v2g_active_evs"] = int(metrics["v2g_v2g_active"].sum())
        result["simultaneous_intervals"] = diagnostics.get("simultaneous_intervals", 0)
    result.update(diagnostics)
    return result


def _solve_day_worker(payload: tuple) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    vehicles, ci, evaluation_ci, config, include_uncontrolled, include_smart = payload
    vehicles = add_carbon_opportunity(vehicles, ci)
    return solve_day(
        vehicles,
        ci,
        config,
        include_uncontrolled=include_uncontrolled,
        include_smart=include_smart,
        include_v2g=True,
        evaluation_carbon_intensity=evaluation_ci,
    )


def run_annual_analysis(
    fleet: pd.DataFrame | None = None,
    carbon: pd.DataFrame | None = None,
    config: dict | None = None,
    output_tag: str = "main",
    save_primary: bool = True,
    include_uncontrolled: bool = True,
    include_smart: bool = True,
    max_days: int | None = None,
    evaluation_carbon: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = config or load_config()
    logger = setup_logging()
    if fleet is None:
        fleet = pd.read_parquet(ROOT / "data" / "synthetic" / "synthetic_ev_days.parquet")
    if carbon is None:
        carbon = pd.read_parquet(ROOT / "data" / "processed" / "caiso_carbon_15min.parquet")
    fleet = fleet.copy()
    fleet["date"] = pd.to_datetime(fleet["date"])
    carbon = carbon.copy()
    carbon["date"] = pd.to_datetime(carbon["date"])
    lookup = _carbon_by_date(carbon)
    evaluation_lookup = (
        lookup if evaluation_carbon is None else _carbon_by_date(evaluation_carbon)
    )
    dates = sorted(fleet["date"].unique())
    if max_days is not None:
        dates = dates[:max_days]

    ev_parts: list[pd.DataFrame] = []
    schedule_parts: list[pd.DataFrame] = []
    daily_rows: list[dict] = []
    payloads = []
    for raw_day in dates:
        day = pd.Timestamp(raw_day)
        payloads.append(
            (
                fleet.loc[fleet["date"].eq(day)].copy(),
                lookup[day],
                evaluation_lookup[day],
                config,
                include_uncontrolled,
                include_smart,
            )
        )
    workers = max(1, min(int(config.get("n_workers", 1)), len(payloads)))
    start = time.monotonic()
    if workers == 1:
        solved = map(_solve_day_worker, payloads)
        executor = None
    else:
        executor = ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn"))
        solved = executor.map(_solve_day_worker, payloads, chunksize=1)
    try:
        for number, (metrics, schedule, diagnostics) in enumerate(solved, start=1):
            ev_parts.append(metrics)
            schedule_parts.append(schedule)
            daily_rows.append(daily_summary(metrics, diagnostics))
            if number == 1 or number % 10 == 0 or number == len(dates):
                logger.info(
                    "%s optimization: day %d/%d (%.1f min elapsed)",
                    output_tag,
                    number,
                    len(dates),
                    (time.monotonic() - start) / 60,
                )
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
    ev_results = pd.concat(ev_parts, ignore_index=True)
    schedules = pd.concat(schedule_parts, ignore_index=True)
    daily = pd.DataFrame(daily_rows)

    if "sc_carbon_kg" in ev_results and "v2g_carbon_kg" in ev_results:
        ev_results["incremental_v2g_saving_kg"] = (
            ev_results["sc_carbon_kg"] - ev_results["v2g_carbon_kg"]
        )
        ev_results["smart_saving_kg"] = (
            ev_results["uc_carbon_kg"] - ev_results["sc_carbon_kg"]
            if "uc_carbon_kg" in ev_results
            else np.nan
        )
    if save_primary:
        daily.to_csv(ROOT / "results" / "results_daily.csv", index=False)
        dataframe_to_parquet(ev_results, ROOT / "results" / "results_ev_level.parquet")
        dataframe_to_parquet(schedules, ROOT / "results" / "schedules_fleet_15min.parquet")
    else:
        directory = ROOT / "results" / "sensitivity" / "scenario_cache"
        directory.mkdir(parents=True, exist_ok=True)
        daily.to_csv(directory / f"daily_{output_tag}.csv", index=False)
    return daily, ev_results, schedules


def annual_performance_table(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy, prefix in (
        ("Uncontrolled", "uc"),
        ("Smart charging", "sc"),
        ("V2G", "v2g"),
    ):
        carbon = daily[f"{prefix}_carbon_kg"].sum()
        uc_carbon = daily["uc_carbon_kg"].sum()
        sc_carbon = daily["sc_carbon_kg"].sum()
        rows.append(
            {
                "strategy": strategy,
                "energy_imported_kwh": daily[f"{prefix}_import_kwh"].sum(),
                "energy_exported_kwh": daily[f"{prefix}_export_kwh"].sum(),
                "net_grid_energy_kwh": daily[f"{prefix}_net_grid_kwh"].sum(),
                "carbon_burden_kg": carbon,
                "saving_vs_uc_kg": uc_carbon - carbon,
                "saving_vs_uc_percent": 100 * (uc_carbon - carbon) / uc_carbon,
                "incremental_saving_vs_sc_kg": sc_carbon - carbon
                if prefix == "v2g"
                else 0.0,
                "incremental_saving_vs_sc_percent": 100 * (sc_carbon - carbon) / sc_carbon
                if prefix == "v2g"
                else 0.0,
            }
        )
    return pd.DataFrame(rows)

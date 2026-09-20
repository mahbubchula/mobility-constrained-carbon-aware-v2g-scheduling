from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.flexibility import recompute_flexibility
from src.analysis.metrics import run_annual_analysis
from src.common import ROOT, load_config, setup_logging
from src.simulation.soc_generation import departure_target


def _scenario_fleet(
    base_fleet: pd.DataFrame, config: dict, target: float | None = None
) -> pd.DataFrame:
    fleet = base_fleet.copy()
    if target is not None:
        fleet["target_soc"] = departure_target(
            fleet["arrival_soc"].to_numpy(),
            fleet["return_energy_kwh"].to_numpy(),
            fleet["battery_kwh"].to_numpy(),
            config,
            standard_target=target,
        )
    fleet = recompute_flexibility(fleet, config)
    capacity = (
        (fleet["departure_interval"] - fleet["arrival_interval"])
        * config["delta_t_hours"]
        * config["charging_power_kw"]
        * config["eta_ch"]
    )
    if (fleet["required_battery_energy_kwh"] > capacity + 1e-7).any():
        count = int((fleet["required_battery_energy_kwh"] > capacity + 1e-7).sum())
        raise RuntimeError(f"Sensitivity scenario contains {count} infeasible EV-days")
    return fleet


def _scenario_result(
    scenario_type: str,
    value: float,
    config: dict,
    fleet: pd.DataFrame,
    carbon: pd.DataFrame,
    max_days: int | None,
) -> dict:
    tag = f"{scenario_type}_{value:g}".replace(".", "p")
    cache = ROOT / "results" / "sensitivity" / "scenario_cache" / f"daily_{tag}.csv"
    if cache.exists() and max_days is None:
        daily = pd.read_csv(cache)
    else:
        daily, _, _ = run_annual_analysis(
            fleet=fleet,
            carbon=carbon,
            config=config,
            output_tag=tag,
            save_primary=False,
            include_uncontrolled=False,
            max_days=max_days,
        )
    smart = daily["sc_carbon_kg"].sum()
    v2g = daily["v2g_carbon_kg"].sum()
    return {
        "sensitivity": scenario_type,
        "value": value,
        "n_days": len(daily),
        "n_ev_days": int(daily["n_evs"].sum()),
        "smart_carbon_kg": smart,
        "v2g_carbon_kg": v2g,
        "incremental_v2g_saving_kg": smart - v2g,
        "incremental_v2g_saving_percent": 100 * (smart - v2g) / smart,
        "mean_incremental_saving_kg_per_ev_day": (smart - v2g) / daily["n_evs"].sum(),
    }


def participation_sensitivity(
    base_ev_results: pd.DataFrame, config: dict
) -> pd.DataFrame:
    rng = np.random.default_rng(config["seed"] + 313)
    savings = base_ev_results["incremental_v2g_saving_kg"].to_numpy()
    n = len(savings)
    rows = []
    for participation in config["participation_sensitivity"]:
        size = int(round(n * participation))
        for repetition in range(config["participation_repetitions"]):
            selected = rng.choice(n, size=size, replace=False)
            total = float(savings[selected].sum())
            rows.append(
                {
                    "sensitivity": "v2g_participation_fraction",
                    "value": participation,
                    "repetition": repetition,
                    "n_participating_ev_days": size,
                    "incremental_v2g_saving_kg": total,
                }
            )
    return pd.DataFrame(rows)


def run_sensitivity_analysis(
    config: dict | None = None, max_days: int | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = config or load_config()
    logger = setup_logging()
    base_fleet = pd.read_parquet(ROOT / "data" / "synthetic" / "synthetic_ev_days.parquet")
    base_fleet["date"] = pd.to_datetime(base_fleet["date"])
    carbon = pd.read_parquet(ROOT / "data" / "processed" / "caiso_carbon_15min.parquet")
    carbon["date"] = pd.to_datetime(carbon["date"])
    base_daily = pd.read_csv(ROOT / "results" / "results_daily.csv")
    base_ev = pd.read_parquet(ROOT / "results" / "results_ev_level.parquet")
    if max_days is not None:
        allowed = set(sorted(base_fleet["date"].unique())[:max_days])
        base_fleet = base_fleet.loc[base_fleet["date"].isin(allowed)].copy()
        carbon = carbon.loc[carbon["date"].isin(allowed)].copy()
        base_ev = base_ev.loc[pd.to_datetime(base_ev["date"]).isin(allowed)].copy()
        base_daily = base_daily.iloc[:max_days]

    rows: list[dict] = []
    base_smart = base_daily["sc_carbon_kg"].sum()
    base_v2g = base_daily["v2g_carbon_kg"].sum()

    def add_base(sensitivity: str, value: float) -> None:
        rows.append(
            {
                "sensitivity": sensitivity,
                "value": value,
                "n_days": len(base_daily),
                "n_ev_days": int(base_daily["n_evs"].sum()),
                "smart_carbon_kg": base_smart,
                "v2g_carbon_kg": base_v2g,
                "incremental_v2g_saving_kg": base_smart - base_v2g,
                "incremental_v2g_saving_percent": 100
                * (base_smart - base_v2g)
                / base_smart,
                "mean_incremental_saving_kg_per_ev_day": (base_smart - base_v2g)
                / base_daily["n_evs"].sum(),
            }
        )

    for efficiency in config["efficiency_sensitivity"]:
        if math.isclose(efficiency, config["round_trip_efficiency"]):
            add_base("round_trip_efficiency", efficiency)
            continue
        scenario_config = copy.deepcopy(config)
        scenario_config["round_trip_efficiency"] = efficiency
        scenario_config["eta_ch"] = math.sqrt(efficiency)
        scenario_config["eta_dis"] = math.sqrt(efficiency)
        scenario_fleet = _scenario_fleet(base_fleet, scenario_config)
        rows.append(
            _scenario_result(
                "round_trip_efficiency",
                efficiency,
                scenario_config,
                scenario_fleet,
                carbon,
                max_days,
            )
        )
        logger.info("Completed efficiency sensitivity %.2f", efficiency)

    for power in config["power_sensitivity_kw"]:
        if math.isclose(power, config["charging_power_kw"]):
            add_base("charger_v2g_power_kw", power)
            continue
        scenario_config = copy.deepcopy(config)
        scenario_config["charging_power_kw"] = power
        scenario_config["discharging_power_kw"] = power
        scenario_fleet = _scenario_fleet(base_fleet, scenario_config)
        rows.append(
            _scenario_result(
                "charger_v2g_power_kw",
                power,
                scenario_config,
                scenario_fleet,
                carbon,
                max_days,
            )
        )
        logger.info("Completed power sensitivity %.1f kW", power)

    for target in config["departure_target_sensitivity"]:
        if math.isclose(target, config["soc_standard_target"]):
            add_base("nominal_departure_soc_target", target)
            continue
        scenario_config = copy.deepcopy(config)
        scenario_fleet = _scenario_fleet(base_fleet, scenario_config, target=target)
        rows.append(
            _scenario_result(
                "nominal_departure_soc_target",
                target,
                scenario_config,
                scenario_fleet,
                carbon,
                max_days,
            )
        )
        logger.info("Completed target-SOC sensitivity %.0f%%", target * 100)

    scenario_results = pd.DataFrame(rows)
    participation = participation_sensitivity(base_ev, config)
    participation_summary = (
        participation.groupby(["sensitivity", "value"])["incremental_v2g_saving_kg"]
        .agg(
            incremental_v2g_saving_kg="mean",
            ci95_lower_kg=lambda x: x.quantile(0.025),
            ci95_upper_kg=lambda x: x.quantile(0.975),
        )
        .reset_index()
    )
    scenario_results.to_csv(ROOT / "results" / "sensitivity_results.csv", index=False)
    participation.to_csv(
        ROOT / "results" / "sensitivity" / "participation_resamples.csv", index=False
    )
    participation_summary.to_csv(
        ROOT / "results" / "sensitivity" / "participation_summary.csv", index=False
    )
    return scenario_results, participation_summary


if __name__ == "__main__":
    run_sensitivity_analysis()

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.metrics import run_annual_analysis
from src.common import ROOT, load_config, setup_logging
from src.simulation.generate_synthetic_fleet import generate_synthetic_fleet


OUT = ROOT / "results" / "robustness"


def _case_summary(
    name: str,
    category: str,
    value: str,
    config: dict,
    fleet: pd.DataFrame,
    carbon: pd.DataFrame,
    evaluation_carbon: pd.DataFrame | None = None,
    include_smart: bool = True,
    smart_reference_daily: pd.DataFrame | None = None,
) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / f"{name}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    daily, ev, schedules = run_annual_analysis(
        fleet=fleet,
        carbon=carbon,
        config=config,
        output_tag=f"robustness_{name}",
        save_primary=False,
        include_uncontrolled=False,
        include_smart=include_smart,
        evaluation_carbon=evaluation_carbon,
    )
    if include_smart:
        smart = float(daily["sc_carbon_kg"].sum())
    elif smart_reference_daily is not None:
        smart = float(smart_reference_daily["sc_carbon_kg"].sum())
    else:
        raise ValueError("A smart-reference table is required when include_smart=False")
    v2g = float(daily["v2g_carbon_kg"].sum())
    ramps = schedules.sort_values(["date", "interval"]).groupby("date")[
        "v2g_net_power_kw"
    ].diff()
    summary = {
        "case": name,
        "category": category,
        "value": value,
        "n_days": int(len(daily)),
        "n_ev_days": int(len(ev)),
        "smart_carbon_kg": smart,
        "v2g_carbon_kg": v2g,
        "incremental_saving_kg": smart - v2g,
        "incremental_saving_percent": 100.0 * (smart - v2g) / smart,
        "v2g_import_kwh": float(daily["v2g_import_kwh"].sum()),
        "v2g_export_kwh": float(daily["v2g_export_kwh"].sum()),
        "active_share_percent": 100.0 * float(ev["v2g_v2g_active"].mean()),
        "max_import_kw": float(schedules["v2g_net_power_kw"].max()),
        "max_export_kw": float(-schedules["v2g_net_power_kw"].min()),
        "max_abs_ramp_kw_per_15min": float(ramps.abs().max()),
        "ready_30min_early_percent": 100.0
        * float((ev["v2g_soc_30min_early"] + 1e-7 >= ev["target_soc"]).mean()),
        "ready_60min_early_percent": 100.0
        * float((ev["v2g_soc_60min_early"] + 1e-7 >= ev["target_soc"]).mean()),
    }
    cache.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _forecast_signal(carbon: pd.DataFrame, rmse: float, seed: int) -> tuple[pd.DataFrame, dict]:
    result = carbon.sort_values(["date", "interval"]).copy()
    rng = np.random.default_rng(seed)
    rho = 0.85
    innovations = rng.normal(0.0, rmse * math.sqrt(1.0 - rho**2), len(result))
    error = np.zeros(len(result))
    for i in range(1, len(error)):
        error[i] = rho * error[i - 1] + innovations[i]
    truth = result["ci_kg_per_kwh"].to_numpy(dtype=float)
    forecast = np.clip(truth + error, 0.01, None)
    result["ci_kg_per_kwh"] = forecast
    diagnostics = {
        "forecast_requested_rmse": rmse,
        "forecast_realized_rmse": float(np.sqrt(np.mean((forecast - truth) ** 2))),
        "forecast_realized_mae": float(np.mean(np.abs(forecast - truth))),
        "forecast_correlation": float(np.corrcoef(forecast, truth)[0, 1]),
    }
    return result, diagnostics


def _archetype_config(base: dict, selected: str) -> dict:
    config = copy.deepcopy(base)
    for name in config["vehicle_archetypes"]:
        config["vehicle_archetypes"][name]["share"] = 1.0 if name == selected else 0.0
    return config


def _targeting_table(ev: pd.DataFrame) -> pd.DataFrame:
    fractions = [0.25, 0.50, 0.75, 1.00]
    saving = ev["incremental_v2g_saving_kg"].clip(lower=0)
    score = ev["flexibility"] * ev["carbon_opportunity_kg_per_kwh"]
    rows: list[dict] = []
    for fraction in fractions:
        n = int(round(len(ev) * fraction))
        selectors = {
            "random_expected": saving.sum() * fraction,
            "high_flexibility": saving.loc[ev["flexibility"].nlargest(n).index].sum(),
            "high_flexibility_x_carbon_opportunity": saving.loc[score.nlargest(n).index].sum(),
            "oracle_upper_bound": saving.nlargest(n).sum(),
        }
        for method, total in selectors.items():
            rows.append(
                {
                    "participation_fraction": fraction,
                    "selection_method": method,
                    "incremental_saving_kg": float(total),
                    "share_of_full_saving_percent": 100.0 * float(total) / float(saving.sum()),
                }
            )
    return pd.DataFrame(rows)


def run_robustness_extensions() -> tuple[pd.DataFrame, pd.DataFrame]:
    logger = setup_logging("robustness-extensions")
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_config()
    fleet = pd.read_parquet(ROOT / "data" / "synthetic" / "synthetic_ev_days.parquet")
    fleet["date"] = pd.to_datetime(fleet["date"])
    carbon = pd.read_parquet(ROOT / "data" / "processed" / "caiso_carbon_15min.parquet")
    carbon["date"] = pd.to_datetime(carbon["date"])
    base_daily = pd.read_csv(ROOT / "results" / "results_daily.csv")
    base_daily["date"] = pd.to_datetime(base_daily["date"])
    stress_dates = set(sorted(fleet["date"].unique())[::6])
    stress_fleet = fleet.loc[fleet["date"].isin(stress_dates)].copy()
    stress_carbon = carbon.loc[carbon["date"].isin(stress_dates)].copy()
    stress_daily = base_daily.loc[base_daily["date"].isin(stress_dates)].copy()
    cases: list[dict] = []

    relaxed = copy.deepcopy(base)
    relaxed["same_session_provenance"] = False
    logger.info("Running full-year robustness extension: relaxed provenance")
    cases.append(
        _case_summary(
            "relaxed_provenance",
            "provenance",
            "pre-arrival energy allowed to SOC minimum",
            relaxed,
            fleet,
            carbon,
            include_smart=False,
            smart_reference_daily=base_daily,
        )
    )

    feeder = copy.deepcopy(base)
    feeder["fleet_import_limit_kw"] = 2000.0
    feeder["fleet_export_limit_kw"] = 2000.0
    feeder["fleet_ramp_limit_kw_per_interval"] = 500.0
    logger.info("Running full-year robustness extension: feeder constraints")
    cases.append(
        _case_summary(
            "feeder_2mw_ramp_0p5mw",
            "feeder",
            "±2 MW; 0.5 MW/15-min ramp",
            feeder,
            fleet,
            carbon,
        )
    )

    for penalty in (0.01, 0.03, 0.05):
        scenario = copy.deepcopy(base)
        scenario["v2g_export_penalty_kg_per_kwh"] = penalty
        name = f"degradation_{penalty:.2f}".replace(".", "p")
        logger.info("Running 61-day robustness extension: %s", name)
        cases.append(
            _case_summary(
                name,
                "degradation",
                f"{penalty:.2f} kg CO2e-equivalent/kWh export",
                scenario,
                stress_fleet,
                stress_carbon,
                include_smart=False,
                smart_reference_daily=stress_daily,
            )
        )

    for cap in (0.10, 0.50):
        scenario = copy.deepcopy(base)
        scenario["v2g_max_discharge_fraction_capacity"] = cap
        name = f"export_cap_{cap:.2f}".replace(".", "p")
        logger.info("Running 61-day robustness extension: %s", name)
        cases.append(
            _case_summary(
                name,
                "export_cap",
                f"{cap:.2f} B per session",
                scenario,
                stress_fleet,
                stress_carbon,
                include_smart=False,
                smart_reference_daily=stress_daily,
            )
        )

    for eta_ch, eta_dis, label in (
        (0.96, 0.9375, "higher charge efficiency"),
        (0.9375, 0.96, "higher discharge efficiency"),
    ):
        scenario = copy.deepcopy(base)
        scenario["eta_ch"] = eta_ch
        scenario["eta_dis"] = eta_dis
        name = f"asymmetric_{eta_ch:.4f}_{eta_dis:.4f}".replace(".", "p")
        logger.info("Running 61-day robustness extension: %s", name)
        cases.append(
            _case_summary(
                name,
                "asymmetric_efficiency",
                label,
                scenario,
                stress_fleet,
                stress_carbon,
            )
        )

    for rmse in (0.02, 0.05):
        forecast, diagnostics = _forecast_signal(
            stress_carbon, rmse, base["seed"] + int(rmse * 1000)
        )
        name = f"forecast_rmse_{rmse:.2f}".replace(".", "p")
        logger.info("Running robustness extension: %s", name)
        result = _case_summary(
            name,
            "forecast_error",
            f"AR(1) RMSE {rmse:.2f} kg CO2e/kWh",
            base,
            stress_fleet,
            forecast,
            evaluation_carbon=stress_carbon,
        )
        result.update(diagnostics)
        (OUT / f"{name}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        cases.append(result)

    for archetype in ("compact", "large"):
        scenario = _archetype_config(base, archetype)
        fleet_path = OUT / f"fleet_all_{archetype}.parquet"
        if fleet_path.exists():
            scenario_fleet = pd.read_parquet(fleet_path)
        else:
            logger.info("Generating all-%s fleet", archetype)
            scenario_fleet = generate_synthetic_fleet(scenario, output_path=fleet_path)
        scenario_fleet["date"] = pd.to_datetime(scenario_fleet["date"])
        scenario_fleet = scenario_fleet.loc[
            scenario_fleet["date"].isin(stress_dates)
        ].copy()
        name = f"battery_all_{archetype}"
        cases.append(
            _case_summary(
                name,
                "battery_archetype",
                f"100% {archetype}",
                scenario,
                scenario_fleet,
                stress_carbon,
            )
        )

    base_ev = pd.read_parquet(ROOT / "results" / "results_ev_level.parquet")
    base_sched = pd.read_parquet(ROOT / "results" / "schedules_fleet_15min.parquet")
    base_ev["date"] = pd.to_datetime(base_ev["date"])
    base_sched["date"] = pd.to_datetime(base_sched["date"])
    base_smart = float(base_daily["sc_carbon_kg"].sum())
    base_v2g = float(base_daily["v2g_carbon_kg"].sum())
    ramps = base_sched.sort_values(["date", "interval"]).groupby("date")["v2g_net_power_kw"].diff()
    base_row = {
        "case": "base",
        "category": "base",
        "value": "released configuration",
        "n_days": int(len(base_daily)),
        "n_ev_days": int(len(base_ev)),
        "smart_carbon_kg": base_smart,
        "v2g_carbon_kg": base_v2g,
        "incremental_saving_kg": base_smart - base_v2g,
        "incremental_saving_percent": 100.0 * (base_smart - base_v2g) / base_smart,
        "v2g_import_kwh": float(base_daily["v2g_import_kwh"].sum()),
        "v2g_export_kwh": float(base_daily["v2g_export_kwh"].sum()),
        "active_share_percent": 100.0 * float(base_ev["v2g_v2g_active"].mean()),
        "max_import_kw": float(base_sched["v2g_net_power_kw"].max()),
        "max_export_kw": float(-base_sched["v2g_net_power_kw"].min()),
        "max_abs_ramp_kw_per_15min": float(ramps.abs().max()),
        "ready_30min_early_percent": (
            100.0 * float((base_ev["v2g_soc_30min_early"] + 1e-7 >= base_ev["target_soc"]).mean())
            if "v2g_soc_30min_early" in base_ev else np.nan
        ),
        "ready_60min_early_percent": (
            100.0 * float((base_ev["v2g_soc_60min_early"] + 1e-7 >= base_ev["target_soc"]).mean())
            if "v2g_soc_60min_early" in base_ev else np.nan
        ),
    }
    panel_ev = base_ev.loc[base_ev["date"].isin(stress_dates)].copy()
    panel_sched = base_sched.loc[base_sched["date"].isin(stress_dates)].copy()
    panel_ramps = panel_sched.sort_values(["date", "interval"]).groupby("date")[
        "v2g_net_power_kw"
    ].diff()
    panel_smart = float(stress_daily["sc_carbon_kg"].sum())
    panel_v2g = float(stress_daily["v2g_carbon_kg"].sum())
    panel_row = {
        "case": "base_61day_panel",
        "category": "panel_reference",
        "value": "every sixth date across 2025",
        "n_days": int(len(stress_daily)),
        "n_ev_days": int(len(panel_ev)),
        "smart_carbon_kg": panel_smart,
        "v2g_carbon_kg": panel_v2g,
        "incremental_saving_kg": panel_smart - panel_v2g,
        "incremental_saving_percent": 100.0 * (panel_smart - panel_v2g) / panel_smart,
        "v2g_import_kwh": float(stress_daily["v2g_import_kwh"].sum()),
        "v2g_export_kwh": float(stress_daily["v2g_export_kwh"].sum()),
        "active_share_percent": 100.0 * float(panel_ev["v2g_v2g_active"].mean()),
        "max_import_kw": float(panel_sched["v2g_net_power_kw"].max()),
        "max_export_kw": float(-panel_sched["v2g_net_power_kw"].min()),
        "max_abs_ramp_kw_per_15min": float(panel_ramps.abs().max()),
        "ready_30min_early_percent": 100.0
        * float((panel_ev["v2g_soc_30min_early"] + 1e-7 >= panel_ev["target_soc"]).mean()),
        "ready_60min_early_percent": 100.0
        * float((panel_ev["v2g_soc_60min_early"] + 1e-7 >= panel_ev["target_soc"]).mean()),
    }
    results = pd.DataFrame([base_row, panel_row, *cases])
    results.to_csv(OUT / "robustness_results.csv", index=False)

    targeting = _targeting_table(base_ev)
    targeting.to_csv(OUT / "flexibility_based_participation.csv", index=False)
    return results, targeting


if __name__ == "__main__":
    run_robustness_extensions()

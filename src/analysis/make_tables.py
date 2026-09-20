from __future__ import annotations

import math

import pandas as pd

from src.common import ROOT, load_config


def _write_table(df: pd.DataFrame, stem: str) -> None:
    output = ROOT / "results" / "tables"
    df.to_csv(output / f"{stem}.csv", index=False)
    (output / f"{stem}.tex").write_text(
        df.to_latex(index=False, escape=True, float_format=lambda x: f"{x:.4g}"),
        encoding="utf-8",
    )


def make_all_tables(config: dict | None = None) -> dict[str, pd.DataFrame]:
    config = config or load_config()
    calibration = pd.read_parquet(ROOT / "data/processed/commuter_calibration_pool.parquet")
    holdout = pd.read_parquet(ROOT / "data/processed/commuter_holdout.parquet")
    synthetic = pd.read_parquet(ROOT / "data/synthetic/synthetic_ev_days.parquet")
    validation = pd.read_csv(ROOT / "results/validation/synthetic_distribution_validation.csv")
    daily = pd.read_csv(ROOT / "results/results_daily.csv")
    strategy = pd.read_csv(ROOT / "results/tables/table04_strategy_results.csv")
    bootstrap = pd.read_csv(ROOT / "results/tables/bootstrap_summary.csv")
    subgroup = pd.read_csv(ROOT / "results/tables/table05_subgroups.csv")
    sensitivity = pd.read_csv(ROOT / "results/sensitivity_results.csv")
    participation = pd.read_csv(ROOT / "results/sensitivity/participation_summary.csv")

    rows = [
        {
            "characteristic": "Number of records / EV-days",
            "calibration": len(calibration),
            "holdout": len(holdout),
            "synthetic": len(synthetic),
            "unit": "count",
        }
    ]
    for label, variable, unit in (
        ("Arrival time", "arrival_min", "minutes after midnight"),
        ("Departure time", "departure_min", "minutes after midnight"),
        ("Connection duration", "connection_hours", "h"),
        ("Inbound commute distance", "inbound_distance_km", "km"),
        ("Return commute distance", "return_distance_km", "km"),
    ):
        rows.append(
            {
                "characteristic": label,
                "calibration": calibration[variable].mean(),
                "holdout": holdout[variable].mean(),
                "synthetic": synthetic[variable].mean(),
                "unit": unit,
            }
        )
    for label, variable, unit in (
        ("Battery capacity", "battery_kwh", "kWh"),
        ("Arrival SOC", "arrival_soc", "fraction"),
        ("Departure target SOC", "target_soc", "fraction"),
    ):
        rows.append(
            {
                "characteristic": label,
                "calibration": math.nan,
                "holdout": math.nan,
                "synthetic": synthetic[variable].mean(),
                "unit": unit,
            }
        )
    table1 = pd.DataFrame(rows)

    table2 = pd.DataFrame(
        [
            ("EV-days per day", "N", config["n_evs_per_day"], "EV/day", "Study design", "—"),
            ("Time step", "Δt", config["time_step_minutes"], "min", "Study design", "—"),
            ("Minimum SOC", "SOCmin", config["soc_min"], "fraction", "Operational assumption", "—"),
            ("Maximum SOC", "SOCmax", config["soc_max"], "fraction", "Operational assumption", "—"),
            ("Nominal target SOC", "SOCstandard", config["soc_standard_target"], "fraction", "User-energy assumption", "0.70–0.90"),
            ("Mobility reserve", "SOCreserve", config["soc_reserve"], "fraction", "Conservative mobility reserve", "—"),
            ("Round-trip efficiency", "ηrt", config["round_trip_efficiency"], "fraction", "Technical assumption", "0.80–0.95"),
            ("Charging power", "Pch,max", config["charging_power_kw"], "kW", "Level-2 workplace charging", "3.6–11"),
            ("Discharging power", "Pdis,max", config["discharging_power_kw"], "kW", "Symmetric V2G interface", "3.6–11"),
            ("Session export cap", "Edis,max/B", config["v2g_max_discharge_fraction_capacity"], "fraction", "Conservative cycling limit", "—"),
            ("Bootstrap draws", "B", config["bootstrap_repetitions"], "draws", "Study design", "—"),
        ],
        columns=["parameter", "symbol", "base_value", "unit", "source_or_rationale", "sensitivity_range"],
    )

    table3 = validation[
        [
            "label",
            "calibration_mean",
            "synthetic_mean",
            "holdout_mean",
            "ks_statistic",
            "wasserstein_distance",
            "normalized_wasserstein",
            "acceptable",
        ]
    ].rename(columns={"label": "variable"})

    smart_ci = bootstrap.loc[bootstrap["metric"].str.startswith("Smart")].iloc[0]
    v2g_ci = bootstrap.loc[bootstrap["metric"].str.startswith("Incremental")].iloc[0]
    strategy["ci95_lower_kg"] = math.nan
    strategy["ci95_upper_kg"] = math.nan
    strategy["ci_metric"] = "not applicable"
    strategy.loc[strategy["strategy"].eq("Smart charging"), ["ci95_lower_kg", "ci95_upper_kg"]] = [
        smart_ci["ci95_lower_kg"],
        smart_ci["ci95_upper_kg"],
    ]
    strategy.loc[strategy["strategy"].eq("Smart charging"), "ci_metric"] = "saving vs UC"
    strategy.loc[strategy["strategy"].eq("V2G"), ["ci95_lower_kg", "ci95_upper_kg"]] = [
        v2g_ci["ci95_lower_kg"],
        v2g_ci["ci95_upper_kg"],
    ]
    strategy.loc[strategy["strategy"].eq("V2G"), "ci_metric"] = "incremental saving vs SC"
    table4 = strategy
    table5 = subgroup
    participation_compact = participation.assign(
        sensitivity="v2g_participation_fraction",
        n_days=len(daily),
        n_ev_days=len(synthetic),
        n_participating_ev_days=(participation["value"] * len(synthetic)).round().astype(int),
        smart_carbon_kg=math.nan,
        v2g_carbon_kg=math.nan,
        incremental_v2g_saving_percent=math.nan,
        mean_incremental_saving_kg_per_ev_day=math.nan,
    )
    table6 = pd.concat([sensitivity, participation_compact], ignore_index=True, sort=False)

    tables = {
        "table01_dataset_characteristics": table1,
        "table02_model_parameters": table2,
        "table03_synthetic_validation": table3,
        "table04_strategy_results": table4,
        "table05_subgroups": table5,
        "table06_sensitivity": table6,
    }
    for stem, table in tables.items():
        _write_table(table, stem)
    return tables


if __name__ == "__main__":
    make_all_tables()

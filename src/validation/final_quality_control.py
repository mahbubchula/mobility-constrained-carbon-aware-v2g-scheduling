from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.common import ROOT, load_config


def _record(rows: list[dict], check: str, passed: bool, observed: str, expected: str) -> None:
    rows.append(
        {
            "check": check,
            "status": "PASS" if passed else "FAIL",
            "observed": observed,
            "expected": expected,
        }
    )


def run_final_quality_control(config: dict | None = None) -> pd.DataFrame:
    """Audit the generated study artifacts against the blueprint's final checklist."""
    config = config or load_config()
    rows: list[dict] = []

    required_data = [
        ROOT / "data/raw/manifest.csv",
        ROOT / "data/processed/commuter_calibration_pool.parquet",
        ROOT / "data/processed/commuter_holdout.parquet",
        ROOT / "data/processed/caiso_carbon_15min.parquet",
        ROOT / "data/synthetic/synthetic_ev_days.parquet",
        ROOT / "results/results_daily.csv",
        ROOT / "results/results_ev_level.parquet",
        ROOT / "results/sensitivity_results.csv",
        ROOT / "results/bootstrap_results.csv",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required_data if not path.exists()]
    _record(rows, "Required saved datasets exist", not missing, ", ".join(missing) or "all present", "all present")

    fleet = pd.read_parquet(ROOT / "data/synthetic/synthetic_ev_days.parquet")
    daily = pd.read_csv(ROOT / "results/results_daily.csv")
    ev = pd.read_parquet(ROOT / "results/results_ev_level.parquet")
    carbon = pd.read_parquet(ROOT / "data/processed/caiso_carbon_15min.parquet")
    synth_validation = pd.read_csv(ROOT / "results/validation/synthetic_distribution_validation.csv")
    model_validation = pd.read_csv(ROOT / "results/validation/model_validation.csv")
    sensitivity = pd.read_csv(ROOT / "results/sensitivity_results.csv")

    expected_ev_days = config["n_evs_per_day"] * config["n_days"]
    _record(rows, "Full synthetic fleet size", len(fleet) == expected_ev_days, f"{len(fleet):,}", f"{expected_ev_days:,}")
    counts = fleet.groupby("date").size()
    balanced = len(counts) == config["n_days"] and counts.eq(config["n_evs_per_day"]).all()
    _record(
        rows,
        "Balanced daily fleet",
        balanced,
        f"{len(counts)} days; {counts.min()}-{counts.max()} EVs/day",
        f"{config['n_days']} days; {config['n_evs_per_day']} EVs/day",
    )
    expected_intervals = config["n_days"] * 24 * (60 // config["time_step_minutes"])
    _record(rows, "Complete carbon series", len(carbon) == expected_intervals, f"{len(carbon):,} intervals", f"{expected_intervals:,} intervals")
    _record(rows, "Holdout mobility validation", synth_validation["acceptable"].all(), f"{synth_validation['acceptable'].sum()}/{len(synth_validation)} passed", "all passed")
    _record(rows, "Daily base-study coverage", len(daily) == config["n_days"], f"{len(daily)} days", f"{config['n_days']} days")
    _record(rows, "EV-level result coverage", len(ev) == expected_ev_days, f"{len(ev):,} EV-days", f"{expected_ev_days:,} EV-days")
    _record(rows, "All model validation tests", model_validation["status"].eq("PASS").all(), f"{model_validation['status'].eq('PASS').sum()}/{len(model_validation)} passed", "all passed")

    smart_dominance = (daily["sc_carbon_kg"] <= daily["uc_carbon_kg"] + 1e-7).all()
    v2g_dominance = (daily["v2g_carbon_kg"] <= daily["sc_carbon_kg"] + 1e-7).all()
    _record(rows, "Smart charging weakly dominates UC", smart_dominance, f"{int((daily['sc_carbon_kg'] > daily['uc_carbon_kg'] + 1e-7).sum())} violating days", "0 violating days")
    _record(rows, "V2G weakly dominates smart charging", v2g_dominance, f"{int((daily['v2g_carbon_kg'] > daily['sc_carbon_kg'] + 1e-7).sum())} violating days", "0 violating days")

    expected_sensitivity = {
        "round_trip_efficiency": set(map(float, config["efficiency_sensitivity"])),
        "charger_v2g_power_kw": set(map(float, config["power_sensitivity_kw"])),
        "nominal_departure_soc_target": set(map(float, config["departure_target_sensitivity"])),
    }
    actual_sensitivity = {
        name: set(group["value"].astype(float))
        for name, group in sensitivity.groupby("sensitivity")
    }
    sensitivity_complete = all(actual_sensitivity.get(name, set()) == values for name, values in expected_sensitivity.items())
    _record(rows, "All prescribed sensitivity scenarios", sensitivity_complete, str({k: sorted(v) for k, v in actual_sensitivity.items()}), str({k: sorted(v) for k, v in expected_sensitivity.items()}))

    scenario_cache = ROOT / "results/sensitivity/scenario_cache"
    base_values = {
        "round_trip_efficiency": float(config["round_trip_efficiency"]),
        "charger_v2g_power_kw": float(config["charging_power_kw"]),
        "nominal_departure_soc_target": float(config["soc_standard_target"]),
    }
    scenario_daily: list[pd.DataFrame] = []
    missing_cache: list[str] = []
    for name, values in expected_sensitivity.items():
        for value in values:
            if value == base_values[name]:
                continue
            tag = f"{name}_{value:g}".replace(".", "p")
            path = scenario_cache / f"daily_{tag}.csv"
            if path.exists():
                scenario_daily.append(pd.read_csv(path))
            else:
                missing_cache.append(path.name)
    scenario_integrity = not missing_cache and all(
        len(frame) == config["n_days"]
        and frame["smart_termination"].astype(str).str.endswith("optimal").all()
        and frame["v2g_termination"].astype(str).str.endswith("optimal").all()
        and (frame["v2g_carbon_kg"] <= frame["sc_carbon_kg"] + 1e-7).all()
        for frame in scenario_daily
    )
    _record(
        rows,
        "Sensitivity daily-solve integrity",
        scenario_integrity,
        ", ".join(missing_cache) if missing_cache else f"{len(scenario_daily)} non-base annual caches verified",
        "7 non-base annual caches; all optimal and dominant",
    )

    participation = pd.read_csv(ROOT / "results/sensitivity/participation_resamples.csv")
    expected_resamples = len(config["participation_sensitivity"]) * config["participation_repetitions"]
    participation_complete = (
        len(participation) == expected_resamples
        and set(participation["value"].astype(float))
        == set(map(float, config["participation_sensitivity"]))
    )
    _record(
        rows,
        "Participation resampling complete",
        participation_complete,
        f"{len(participation)} draws across {participation['value'].nunique()} levels",
        f"{expected_resamples} draws across {len(config['participation_sensitivity'])} levels",
    )

    table_stems = [f"table{i:02d}" for i in range(1, 8)]
    table_files = list((ROOT / "results/tables").glob("table*.csv"))
    tables_complete = all(any(path.name.startswith(stem) for path in table_files) for stem in table_stems)
    _record(rows, "Seven publication tables", tables_complete, f"{len([p for p in table_files if p.name.startswith('table')])} CSV table files", "Tables 1-7")

    figure_files = list((ROOT / "results/figures").glob("figure*.*"))
    figures_complete = all(
        (ROOT / "results/figures" / f"figure{number:02d}_{suffix}.{extension}").exists()
        for number, suffix in (
            (1, "research_framework"),
            (2, "synthetic_validation"),
            (3, "grid_carbon_conditions"),
            (4, "representative_daily_schedules"),
            (5, "main_carbon_comparison"),
            (6, "flexibility_carbon_opportunity_map"),
            (7, "sensitivity_analysis"),
            (8, "temporal_savings"),
            (9, "v2g_activity_and_concentration"),
            (10, "subgroup_effects"),
            (11, "quantile_daily_schedules"),
            (12, "revised_workflow"),
            (13, "robustness"),
            (14, "deployment_readiness"),
        )
        for extension in ("pdf", "png", "svg")
    )
    _record(rows, "Fourteen figures in PDF/PNG/SVG", figures_complete, f"{len(figure_files)} figure files", "42 figure files")

    report = pd.DataFrame(rows)
    output_dir = ROOT / "results/validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_dir / "final_quality_control.csv", index=False)
    passed = int(report["status"].eq("PASS").sum())
    headers = list(report.columns)
    markdown_table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in report.iterrows():
        values = [str(row[column]).replace("|", "\\|").replace("\n", " ") for column in headers]
        markdown_table.append("| " + " | ".join(values) + " |")
    markdown = [
        "# Final Quality-Control Report",
        "",
        f"Overall status: **{'PASS' if passed == len(report) else 'FAIL'}** ({passed}/{len(report)} checks passed).",
        "",
        *markdown_table,
        "",
    ]
    (ROOT / "results/quality_control.md").write_text("\n".join(markdown), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run_final_quality_control()
    if not result["status"].eq("PASS").all():
        raise SystemExit("Final quality control failed; see results/quality_control.md")

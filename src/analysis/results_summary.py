from __future__ import annotations

import pandas as pd

from src.common import ROOT


def generate_results_summary() -> str:
    daily = pd.read_csv(ROOT / "results/results_daily.csv", parse_dates=["date"])
    ev = pd.read_parquet(ROOT / "results/results_ev_level.parquet")
    bootstrap = pd.read_csv(ROOT / "results/tables/bootstrap_summary.csv")
    validation = pd.read_csv(ROOT / "results/validation/model_validation.csv")
    synth_validation = pd.read_csv(
        ROOT / "results/validation/synthetic_distribution_validation.csv"
    )
    subgroups = pd.read_csv(ROOT / "results/tables/table05_subgroups.csv")
    sensitivity = pd.read_csv(ROOT / "results/sensitivity_results.csv")

    uc = daily["uc_carbon_kg"].sum()
    sc = daily["sc_carbon_kg"].sum()
    v2g = daily["v2g_carbon_kg"].sum()
    smart_saving = uc - sc
    incremental = sc - v2g
    smart_ci = bootstrap.loc[bootstrap["metric"].str.startswith("Smart")].iloc[0]
    v2g_ci = bootstrap.loc[bootstrap["metric"].str.startswith("Incremental")].iloc[0]
    active = ev["v2g_v2g_active"].sum()
    export = ev["v2g_export_kwh"].sum()
    charge_ci = ev["v2g_charge_carbon_kg"].sum() / ev["v2g_import_kwh"].sum()
    discharge_ci = (
        ev["v2g_discharge_carbon_credit_kg"].sum() / export if export else float("nan")
    )
    median_day = daily.loc[
        (daily["incremental_v2g_saving_kg"] - daily["incremental_v2g_saving_kg"].median())
        .abs()
        .idxmin()
    ]
    daily["month"] = daily["date"].dt.month
    monthly_incremental = daily.groupby("month")["incremental_v2g_saving_kg"].sum()
    ordered_savings = ev["incremental_v2g_saving_kg"].clip(lower=0).sort_values(ascending=False)
    cumulative_savings = ordered_savings.cumsum() / ordered_savings.sum()
    half_value_share = (cumulative_savings.to_numpy().searchsorted(0.50) + 1) / len(ev)
    ninety_value_share = (cumulative_savings.to_numpy().searchsorted(0.90) + 1) / len(ev)
    quantile_days = {}
    for quantile in (0.10, 0.50, 0.90):
        target = daily["incremental_v2g_saving_kg"].quantile(quantile)
        quantile_days[quantile] = daily.loc[
            (daily["incremental_v2g_saving_kg"] - target).abs().idxmin()
        ]
    flex_groups = subgroups.loc[subgroups["variable"].eq("flexibility")]
    carbon_groups = subgroups.loc[
        subgroups["variable"].eq("carbon_opportunity_kg_per_kwh")
    ]

    text = f"""# Traceable Results Summary

Generated from saved CSV/Parquet outputs. All values below are computed, not manually entered.

## Study coverage

- Calendar days: {len(daily):,}
- Synthetic EV-days: {len(ev):,}
- EVs per day: {int(daily['n_evs'].min()):,}
- Daily smart/V2G optimization problems: {len(daily) * 2:,}
- Synthetic validation diagnostics passed: {int(synth_validation['acceptable'].sum())}/{len(synth_validation)}
- Model-validation checks passed: {int(validation['status'].eq('PASS').sum())}/{len(validation)}

## Main carbon results

- Uncontrolled charging burden: {uc:,.3f} kg CO2e
- Smart-charging burden: {sc:,.3f} kg CO2e
- V2G burden: {v2g:,.3f} kg CO2e
- Smart-charging saving vs uncontrolled: {smart_saving:,.3f} kg ({100 * smart_saving / uc:.3f}%)
- Paired daily bootstrap 95% CI for smart saving: [{smart_ci['ci95_lower_kg']:,.3f}, {smart_ci['ci95_upper_kg']:,.3f}] kg
- Incremental V2G saving vs smart charging: {incremental:,.3f} kg ({100 * incremental / sc:.3f}%)
- Paired daily bootstrap 95% CI for incremental V2G saving: [{v2g_ci['ci95_lower_kg']:,.3f}, {v2g_ci['ci95_upper_kg']:,.3f}] kg
- Total V2G saving vs uncontrolled: {uc - v2g:,.3f} kg ({100 * (uc - v2g) / uc:.3f}%)

## Energy and V2G activity

- V2G grid import: {ev['v2g_import_kwh'].sum():,.3f} kWh
- V2G grid export: {export:,.3f} kWh
- V2G-active EV-days: {int(active):,} ({100 * active / len(ev):.3f}%)
- Mean export per active EV-day: {export / active if active else 0:,.3f} kWh
- Mean equivalent full-cycle export throughput across all EV-days: {ev['v2g_efc'].mean():.5f}
- Energy-weighted charging-period carbon intensity: {charge_ci:.4f} kg CO2e/kWh
- Energy-weighted discharge-period carbon intensity: {discharge_ci:.4f} kg CO2e/kWh

## Temporal distribution and concentration

- Highest monthly incremental V2G saving: month {int(monthly_incremental.idxmax())}, {monthly_incremental.max():,.3f} kg
- Lowest monthly incremental V2G saving: month {int(monthly_incremental.idxmin())}, {monthly_incremental.min():,.3f} kg
- EV-days supplying 50% of incremental saving: {100 * half_value_share:.3f}%
- EV-days supplying 90% of incremental saving: {100 * ninety_value_share:.3f}%
- Quantile-selected daily examples (P10/P50/P90): {quantile_days[0.10]['date']:%Y-%m-%d} / {quantile_days[0.50]['date']:%Y-%m-%d} / {quantile_days[0.90]['date']:%Y-%m-%d}
- Corresponding daily incremental savings: {quantile_days[0.10]['incremental_v2g_saving_kg']:.3f} / {quantile_days[0.50]['incremental_v2g_saving_kg']:.3f} / {quantile_days[0.90]['incremental_v2g_saving_kg']:.3f} kg

## Conditions and representative day

- Median-benefit representative date: {median_day['date']:%Y-%m-%d}
- Representative-day incremental saving: {median_day['incremental_v2g_saving_kg']:.3f} kg
- Lowest flexibility quartile mean incremental saving: {flex_groups.loc[flex_groups['quartile'].eq('Q1'), 'mean_incremental_v2g_saving_kg_per_ev_day'].iloc[0]:.5f} kg/EV-day
- Highest flexibility quartile mean incremental saving: {flex_groups.loc[flex_groups['quartile'].eq('Q4'), 'mean_incremental_v2g_saving_kg_per_ev_day'].iloc[0]:.5f} kg/EV-day
- Lowest carbon-opportunity quartile mean incremental saving: {carbon_groups.loc[carbon_groups['quartile'].eq('Q1'), 'mean_incremental_v2g_saving_kg_per_ev_day'].iloc[0]:.5f} kg/EV-day
- Highest carbon-opportunity quartile mean incremental saving: {carbon_groups.loc[carbon_groups['quartile'].eq('Q4'), 'mean_incremental_v2g_saving_kg_per_ev_day'].iloc[0]:.5f} kg/EV-day

## Sensitivity range

- Minimum scenario mean incremental saving: {sensitivity['mean_incremental_saving_kg_per_ev_day'].min():.5f} kg/EV-day
- Maximum scenario mean incremental saving: {sensitivity['mean_incremental_saving_kg_per_ev_day'].max():.5f} kg/EV-day
- Scenarios evaluated (excluding participation resamples): {len(sensitivity)}

## Traceability

Main values: `results/results_daily.csv` and `results/results_ev_level.parquet`  
Uncertainty: `results/bootstrap_results.csv`  
Sensitivity: `results/sensitivity_results.csv` and `results/sensitivity/participation_resamples.csv`  
Validation: `results/validation/model_validation.csv`
"""
    (ROOT / "results/results_summary.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    generate_results_summary()

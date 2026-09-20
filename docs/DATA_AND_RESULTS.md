# Data and Results Guide

## Data layers

| Layer | Location | Role |
|---|---|---|
| Raw | `data/raw/` | Archived public mobility and grid-source inputs used by the workflow |
| Processed | `data/processed/` | Cleaned, harmonized, and analysis-ready variables |
| Synthetic | `data/synthetic/` | Seeded EV-day populations and mobility-constrained scenario inputs |

The workflow preserves raw source files separately from derived data. Processing code records the transformations needed for analysis; synthetic populations are generated from configured distributions and mobility evidence rather than interpreted as observed individual drivers.

## Principal result files

| Artifact | Location | Description |
|---|---|---|
| Headline summary | `results/results_summary.md` | Main annual energy, emissions, and comparison metrics |
| EV-level outcomes | `results/results_ev_level.parquet` | Vehicle-day strategy outcomes for distributional analysis |
| Fleet schedules | `results/schedules_fleet_15min.parquet` | Aggregated 15-minute fleet charging and discharging schedules |
| Publication figures | `results/figures/` | Fourteen figures in PNG, PDF, and SVG |
| Publication tables | `results/tables/` | Main and supplementary tabular results |
| Sensitivity results | `results/sensitivity/` | Parameter-grid and scenario sensitivity outputs |
| Extended robustness | `results/robustness/` | Forecast-error, infrastructure, temporal, and fleet-composition experiments |
| Validation evidence | `results/validation/` | Machine-readable quality-control reports |

## Units and conventions

- Energy is reported in kWh or MWh as identified in each table or figure.
- Power is reported in kW.
- Carbon intensity is expressed as mass of CO₂-equivalent per unit of electricity.
- Annual avoided emissions are reported in tCO₂.
- Charging is positive grid-to-vehicle power; discharging is treated explicitly in the V2G schedules.
- Percentage reductions use the stated comparator as the denominator.

## Responsible use

Outputs should be interpreted with the assumptions in `config/config.yaml` and the documented scientific limits. The included datasets may contain third-party public information governed by original provider terms. Do not redistribute source data or unpublished project materials outside the authorized collaboration without checking those terms and the repository license.

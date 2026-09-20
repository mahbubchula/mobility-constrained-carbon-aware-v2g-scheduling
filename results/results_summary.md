# Traceable Results Summary

Generated from saved CSV/Parquet outputs. All values below are computed, not manually entered.

## Study coverage

- Calendar days: 365
- Synthetic EV-days: 182,500
- EVs per day: 500
- Daily smart/V2G optimization problems: 730
- Synthetic validation diagnostics passed: 5/5
- Model-validation checks passed: 8/8

## Main carbon results

- Uncontrolled charging burden: 199,700.369 kg CO2e
- Smart-charging burden: 172,900.737 kg CO2e
- V2G burden: 159,267.597 kg CO2e
- Smart-charging saving vs uncontrolled: 26,799.632 kg (13.420%)
- Paired daily bootstrap 95% CI for smart saving: [25,711.071, 27,824.772] kg
- Incremental V2G saving vs smart charging: 13,633.140 kg (7.885%)
- Paired daily bootstrap 95% CI for incremental V2G saving: [12,566.558, 14,762.580] kg
- Total V2G saving vs uncontrolled: 40,432.772 kg (20.247%)

## Energy and V2G activity

- V2G grid import: 1,488,185.170 kWh
- V2G grid export: 506,824.633 kWh
- V2G-active EV-days: 78,642 (43.092%)
- Mean export per active EV-day: 6.445 kWh
- Mean equivalent full-cycle export throughput across all EV-days: 0.04498
- Energy-weighted charging-period carbon intensity: 0.1849 kg CO2e/kWh
- Energy-weighted discharge-period carbon intensity: 0.2286 kg CO2e/kWh

## Temporal distribution and concentration

- Highest monthly incremental V2G saving: month 2, 1,980.601 kg
- Lowest monthly incremental V2G saving: month 8, 526.229 kg
- EV-days supplying 50% of incremental saving: 7.671%
- EV-days supplying 90% of incremental saving: 23.012%
- Quantile-selected daily examples (P10/P50/P90): 2025-10-09 / 2025-05-29 / 2025-01-19
- Corresponding daily incremental savings: 6.345 / 30.301 / 75.018 kg

## Conditions and representative day

- Median-benefit representative date: 2025-05-29
- Representative-day incremental saving: 30.301 kg
- Lowest flexibility quartile mean incremental saving: 0.04682 kg/EV-day
- Highest flexibility quartile mean incremental saving: 0.07120 kg/EV-day
- Lowest carbon-opportunity quartile mean incremental saving: 0.00137 kg/EV-day
- Highest carbon-opportunity quartile mean incremental saving: 0.15695 kg/EV-day

## Sensitivity range

- Minimum scenario mean incremental saving: 0.02650 kg/EV-day
- Maximum scenario mean incremental saving: 0.11388 kg/EV-day
- Scenarios evaluated (excluding participation resamples): 10

## Traceability

Main values: `results/results_daily.csv` and `results/results_ev_level.parquet`  
Uncertainty: `results/bootstrap_results.csv`  
Sensitivity: `results/sensitivity_results.csv` and `results/sensitivity/participation_resamples.csv`  
Validation: `results/validation/model_validation.csv`

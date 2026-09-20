# Final Quality-Control Report

Overall status: **PASS** (15/15 checks passed).

| check | status | observed | expected |
| --- | --- | --- | --- |
| Required saved datasets exist | PASS | all present | all present |
| Full synthetic fleet size | PASS | 182,500 | 182,500 |
| Balanced daily fleet | PASS | 365 days; 500-500 EVs/day | 365 days; 500 EVs/day |
| Complete carbon series | PASS | 35,040 intervals | 35,040 intervals |
| Holdout mobility validation | PASS | 5/5 passed | all passed |
| Daily base-study coverage | PASS | 365 days | 365 days |
| EV-level result coverage | PASS | 182,500 EV-days | 182,500 EV-days |
| All model validation tests | PASS | 8/8 passed | all passed |
| Smart charging weakly dominates UC | PASS | 0 violating days | 0 violating days |
| V2G weakly dominates smart charging | PASS | 0 violating days | 0 violating days |
| All prescribed sensitivity scenarios | PASS | {'charger_v2g_power_kw': [3.6, 7.2, 11.0], 'nominal_departure_soc_target': [0.7, 0.8, 0.9], 'round_trip_efficiency': [0.8, 0.85, 0.9, 0.95]} | {'round_trip_efficiency': [0.8, 0.85, 0.9, 0.95], 'charger_v2g_power_kw': [3.6, 7.2, 11.0], 'nominal_departure_soc_target': [0.7, 0.8, 0.9]} |
| Sensitivity daily-solve integrity | PASS | 7 non-base annual caches verified | 7 non-base annual caches; all optimal and dominant |
| Participation resampling complete | PASS | 400 draws across 4 levels | 400 draws across 4 levels |
| Seven publication tables | PASS | 8 CSV table files | Tables 1-7 |
| Fourteen figures in PDF/PNG/SVG | PASS | 42 figure files | 42 figure files |

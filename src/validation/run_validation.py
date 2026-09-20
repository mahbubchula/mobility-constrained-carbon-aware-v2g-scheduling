from __future__ import annotations

import pandas as pd

from src.common import ROOT, load_config
from src.validation.synthetic_model_tests import (
    break_even_test,
    flat_carbon_test,
    zero_flexibility_test,
)
from src.validation.validate_dominance import dominance_validation
from src.validation.validate_energy import energy_validation
from src.validation.validate_soc import soc_validation


def run_model_validation(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    daily = pd.read_csv(ROOT / "results" / "results_daily.csv")
    ev = pd.read_parquet(ROOT / "results" / "results_ev_level.parquet")
    checks = {
        "SOC and exact departure target": soc_validation(ev, config["solver_tolerance"] * 20),
        "Energy balance and throughput cap": energy_validation(ev, config),
        "Strategy dominance": dominance_validation(daily),
        "No simultaneous charge/discharge": {
            "simultaneous_intervals": int(daily["simultaneous_intervals"].sum()),
            "pass": int(daily["simultaneous_intervals"].sum()) == 0,
        },
        "Flat carbon": flat_carbon_test(config),
        "Two-period carbon break-even": break_even_test(config),
        "Zero flexibility": zero_flexibility_test(config),
        "All daily solves optimal": {
            "nonoptimal_smart_days": int(
                (~daily["smart_termination"].astype(str).str.contains("optimal", case=False)).sum()
            ),
            "nonoptimal_v2g_days": int(
                (~daily["v2g_termination"].astype(str).str.contains("optimal", case=False)).sum()
            ),
            "pass": bool(
                daily["smart_termination"].astype(str).str.contains("optimal", case=False).all()
                and daily["v2g_termination"].astype(str).str.contains("optimal", case=False).all()
            ),
        },
    }
    rows = []
    for check, details in checks.items():
        rows.append(
            {
                "check": check,
                "status": "PASS" if details.pop("pass") else "FAIL",
                "details": "; ".join(f"{key}={value}" for key, value in details.items()),
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(ROOT / "results" / "validation" / "model_validation.csv", index=False)
    if not result["status"].eq("PASS").all():
        failures = result.loc[result["status"].eq("FAIL"), "check"].tolist()
        raise AssertionError(f"Model validation failed: {failures}")
    return result


if __name__ == "__main__":
    run_model_validation()


#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.bootstrap import paired_daily_bootstrap
from src.analysis.metrics import annual_performance_table, run_annual_analysis
from src.analysis.subgroup_analysis import subgroup_analysis
from src.common import ROOT as PROJECT_ROOT, load_config
from src.validation.run_validation import run_model_validation


def run_main(config: dict | None = None, max_days: int | None = None):
    config = config or load_config()
    daily, ev, schedules = run_annual_analysis(config=config, max_days=max_days)
    annual_performance_table(daily).to_csv(
        PROJECT_ROOT / "results" / "tables" / "table04_strategy_results.csv", index=False
    )
    run_model_validation(config)
    paired_daily_bootstrap(daily, config)
    subgroup_analysis(ev, config)
    return daily, ev, schedules


if __name__ == "__main__":
    run_main()


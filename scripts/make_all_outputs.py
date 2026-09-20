#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.make_tables import make_all_tables
from src.analysis.results_summary import generate_results_summary
from src.validation.final_quality_control import run_final_quality_control
from src.visualization.fig01_framework import make_figure as figure01
from src.visualization.fig02_synthetic_validation import make_figure as figure02
from src.visualization.fig03_carbon_profile import make_figure as figure03
from src.visualization.fig04_daily_profiles import make_figure as figure04
from src.visualization.fig05_carbon_comparison import make_figure as figure05
from src.visualization.fig06_flexibility_map import make_figure as figure06
from src.visualization.fig07_sensitivity import make_figure as figure07
from src.visualization.fig08_temporal_savings import make_figure as figure08
from src.visualization.fig09_v2g_activity import make_figure as figure09
from src.visualization.fig10_subgroup_effects import make_figure as figure10
from src.visualization.fig11_quantile_schedules import make_figure as figure11


def make_all_outputs() -> None:
    make_all_tables()
    generate_results_summary()
    for function in (
        figure01,
        figure02,
        figure03,
        figure04,
        figure05,
        figure06,
        figure07,
        figure08,
        figure09,
        figure10,
        figure11,
    ):
        function()
    quality = run_final_quality_control()
    if not quality["status"].eq("PASS").all():
        raise RuntimeError("Final quality control failed; see results/quality_control.md")


if __name__ == "__main__":
    make_all_outputs()

from __future__ import annotations

import pandas as pd

from src.common import ROOT


LABELS = {
    "base": "Base (full year)",
    "relaxed_provenance": "Relaxed provenance (full year)",
    "feeder_2mw_ramp_0p5mw": "2 MW feeder + 0.5 MW/15-min ramp (full year)",
    "base_61day_panel": "Base (61-day panel)",
    "degradation_0p01": "Export penalty 0.01 kg/kWh",
    "degradation_0p03": "Export penalty 0.03 kg/kWh",
    "degradation_0p05": "Export penalty 0.05 kg/kWh",
    "export_cap_0p10": "10% battery export cap",
    "export_cap_0p50": "50% battery export cap",
    "asymmetric_0p9600_0p9375": "Asymmetric efficiency (0.960/0.9375)",
    "asymmetric_0p9375_0p9600": "Asymmetric efficiency (0.9375/0.960)",
    "forecast_rmse_0p02": "Forecast RMSE 0.02 kg/kWh",
    "forecast_rmse_0p05": "Forecast RMSE 0.05 kg/kWh",
    "battery_all_compact": "All-compact fleet",
    "battery_all_large": "All-large fleet",
}


def make_tables() -> None:
    source = pd.read_csv(
        ROOT / "results" / "robustness" / "robustness_results.csv"
    )
    table = source.loc[source["case"].isin(LABELS)].copy()
    table["scenario"] = table["case"].map(LABELS)
    table = table[
        [
            "scenario",
            "n_days",
            "incremental_saving_kg",
            "incremental_saving_percent",
            "v2g_export_kwh",
            "active_share_percent",
            "max_import_kw",
            "max_export_kw",
        ]
    ]
    table.to_csv(ROOT / "results" / "tables" / "table07_robustness.csv", index=False)
    (ROOT / "results" / "tables" / "table07_robustness.tex").write_text(
        table.to_latex(index=False, float_format="%.2f"), encoding="utf-8"
    )

    abbreviations = pd.DataFrame(
        [
            ("AER", "Average Emissions Rate"),
            ("BEV", "Battery Electric Vehicle"),
            ("CAISO", "California Independent System Operator"),
            ("CI", "Carbon Intensity"),
            ("EFC", "Equivalent Full Cycle"),
            ("EV", "Electric Vehicle"),
            ("G2V", "Grid-to-Vehicle"),
            ("HiGHS", "High-performance software for linear optimization"),
            ("KS", "Kolmogorov–Smirnov"),
            ("LP", "Linear Program"),
            ("MEF", "Marginal Emissions Factor"),
            ("MPC", "Model Predictive Control"),
            ("NHTS", "National Household Travel Survey"),
            ("SOC", "State of Charge"),
            ("V2G", "Vehicle-to-Grid"),
        ],
        columns=["abbreviation", "definition"],
    )
    abbreviations.to_csv(ROOT / "results" / "tables" / "table08_abbreviations.csv", index=False)
    (ROOT / "results" / "tables" / "table08_abbreviations.tex").write_text(
        abbreviations.to_latex(index=False), encoding="utf-8"
    )


if __name__ == "__main__":
    make_tables()

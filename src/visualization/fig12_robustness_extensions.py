from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

from src.common import ROOT
from src.visualization.style import COLORS, save_figure, set_publication_style


def _box(ax, xy, width, height, text, facecolor, fontsize=8.2):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=facecolor,
        edgecolor="#4A5568",
        linewidth=1.0,
    )
    ax.add_patch(patch)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=fontsize)
    return patch


def _arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=11, color="#4A5568", linewidth=1.0))


def make_flowchart() -> None:
    set_publication_style()
    fig, ax = plt.subplots(figsize=(10.5, 7.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    _box(ax, (0.04, 0.82), 0.26, 0.11, "2022 NHTS worker-day tuples\narrival, departure, distances, survey weight", "#E8F0FE")
    _box(ax, (0.37, 0.82), 0.26, 0.11, "2025 CAISO AER\n8,760 hourly values → 35,040 intervals", "#FDECEC")
    _box(ax, (0.70, 0.82), 0.26, 0.11, "Predeclared technical inputs\nSOC, power, efficiency, battery archetypes", "#EAF7EF")
    _box(ax, (0.04, 0.62), 0.26, 0.12, "Selection and split\n1,033 calibration + 445 holdout\ncomplete mobility tuples retained", "#E8F0FE")
    _box(
        ax,
        (0.37, 0.62),
        0.26,
        0.12,
        "Stratum-normalized sampling\n" + r"$p_j=w_j/\sum_{k\in s}w_k$" + "\nweekday/weekend stratum",
        "#FFF5DB",
    )
    _box(ax, (0.70, 0.62), 0.26, 0.12, "Bootstrap Monte Carlo\ntuple draw + bounded time/distance perturbation\nSOC resampled only for feasibility", "#EAF7EF")
    _box(ax, (0.04, 0.40), 0.26, 0.12, "Holdout validation\nKS ≤ 0.15; normalized Wasserstein ≤ 0.25\ndependence diagnostics", "#F1ECFA")
    _box(ax, (0.37, 0.40), 0.26, 0.12, "Common mobility service\nidentical connection windows and exact\nvehicle-specific departure SOC", "#EAF7EF")
    _box(ax, (0.70, 0.40), 0.26, 0.12, "Nested strategies\nuncontrolled → smart G2V → V2G\nHiGHS sparse linear programs", "#E8F0FE")
    _box(ax, (0.04, 0.16), 0.26, 0.14, "Post-solve verification\nSOC and energy reconstruction\nflat-carbon, break-even, zero-flexibility tests", "#F1ECFA")
    _box(ax, (0.37, 0.16), 0.26, 0.14, "Primary evidence\n365-day paired comparison\nbootstrap CI + subgroup heterogeneity", "#FFF5DB")
    _box(
        ax,
        (0.70, 0.16),
        0.26,
        0.14,
        "Robustness analysis layer\nprovenance, feeder/ramp, degradation, forecast,\nexport cap, asymmetry, battery mix, early departure",
        "#FDECEC",
        fontsize=7.2,
    )
    for start, end in [
        ((0.17, 0.82), (0.17, 0.74)),
        ((0.30, 0.68), (0.37, 0.68)),
        ((0.50, 0.82), (0.50, 0.74)),
        ((0.63, 0.735), (0.70, 0.735)),
        ((0.83, 0.82), (0.83, 0.74)),
        ((0.83, 0.62), (0.83, 0.52)),
        ((0.70, 0.46), (0.63, 0.46)),
        ((0.37, 0.46), (0.30, 0.46)),
        ((0.17, 0.40), (0.17, 0.30)),
        ((0.30, 0.23), (0.37, 0.23)),
        ((0.63, 0.23), (0.70, 0.23)),
    ]:
        _arrow(ax, start, end)
    ax.text(0.02, 0.98, "Figure 12. End-to-end sampling, optimization, validation, and robustness workflow", weight="bold", fontsize=11, va="top")
    fig.tight_layout()
    save_figure(fig, "figure12_revised_workflow")


def make_robustness() -> None:
    set_publication_style()
    data = pd.read_csv(ROOT / "results/robustness/robustness_results.csv")
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.2))

    ax = axes[0, 0]
    keys = ["base", "feeder_2mw_ramp_0p5mw", "relaxed_provenance"]
    labels = ["Base", "Feeder + ramp", "No-provenance\nupper bound"]
    s = data.set_index("case").loc[keys]
    ax.bar(labels, s["incremental_saving_percent"], color=[COLORS["v2g"], COLORS["sc"], COLORS["accent"]])
    ax.set_ylabel("Incremental saving (% of smart burden)")
    ax.set_title("A. Full-year structural tests", loc="left", weight="bold")

    ax = axes[0, 1]
    keys = ["base_61day_panel", "degradation_0p01", "degradation_0p03", "degradation_0p05"]
    s = data.set_index("case").loc[keys]
    x = np.array([0.0, 0.01, 0.03, 0.05])
    ax.plot(x, s["incremental_saving_percent"], marker="o", color=COLORS["v2g"], label="Saving")
    ax.set(xlabel="Export penalty (kg CO₂e-equivalent/kWh)", ylabel="Incremental saving (%)")
    ax.axvline(0.0269, color=COLORS["carbon"], linestyle="--", linewidth=1, label="Base analytical break-even")
    ax2 = ax.twinx()
    ax2.plot(x, s["v2g_export_kwh"] / 1000, marker="s", color=COLORS["accent"], label="Export")
    ax2.set_ylabel("Panel export (MWh)")
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines], loc="upper right", frameon=False)
    ax.set_title("B. Degradation/lifecycle penalty", loc="left", weight="bold")

    ax = axes[1, 0]
    keys = ["base_61day_panel", "forecast_rmse_0p02", "forecast_rmse_0p05"]
    s = data.set_index("case").loc[keys]
    ax.plot([0.0, 0.02, 0.05], s["incremental_saving_percent"], marker="o", color=COLORS["carbon"])
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.set(xlabel="Forecast RMSE (kg CO₂e/kWh)", ylabel="Realized incremental saving (%)")
    ax.set_title("C. Forecast-error robustness", loc="left", weight="bold")

    ax = axes[1, 1]
    keys = ["base_61day_panel", "export_cap_0p10", "export_cap_0p50", "asymmetric_0p9600_0p9375", "asymmetric_0p9375_0p9600", "battery_all_compact", "battery_all_large"]
    labels = ["Base", "10% cap", "50% cap", r"$\eta_{ch}$ high", r"$\eta_{dis}$ high", "All compact", "All large"]
    s = data.set_index("case").loc[keys]
    ax.barh(labels[::-1], s["incremental_saving_percent"].to_numpy()[::-1], color=COLORS["sc"])
    ax.set_xlabel("Incremental saving (% of smart burden)")
    ax.set_title("D. Technical and fleet composition", loc="left", weight="bold")
    fig.tight_layout()
    save_figure(fig, "figure13_robustness")


def make_deployment() -> None:
    set_publication_style()
    data = pd.read_csv(ROOT / "results/robustness/robustness_results.csv").set_index("case")
    targeting = pd.read_csv(ROOT / "results/robustness/flexibility_based_participation.csv")
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.2))

    ax = axes[0, 0]
    cases = ["base", "feeder_2mw_ramp_0p5mw", "relaxed_provenance"]
    labels = ["Base", "Feeder + ramp", "No provenance"]
    x = np.arange(len(cases))
    ax.bar(x - 0.18, data.loc[cases, "ready_30min_early_percent"], 0.36, label="30 min early", color=COLORS["sc"])
    ax.bar(x + 0.18, data.loc[cases, "ready_60min_early_percent"], 0.36, label="60 min early", color=COLORS["v2g"])
    ax.set_xticks(x, labels)
    ax.set_ylim(60, 100)
    ax.set_ylabel("Sessions meeting departure target (%)")
    ax.legend(frameon=False)
    ax.set_title("A. Early-departure readiness", loc="left", weight="bold")

    ax = axes[0, 1]
    styles = {
        "random_expected": ("Random expected", "--", COLORS["uc"]),
        "high_flexibility": ("High flexibility", "-.", COLORS["sc"]),
        "high_flexibility_x_carbon_opportunity": ("Flexibility × carbon opportunity", "-", COLORS["v2g"]),
        "oracle_upper_bound": ("Oracle upper bound", ":", COLORS["accent"]),
    }
    for key, (label, ls, color) in styles.items():
        s = targeting.loc[targeting["selection_method"].eq(key)].sort_values("participation_fraction")
        ax.plot(s["participation_fraction"] * 100, s["share_of_full_saving_percent"], marker="o", linestyle=ls, color=color, label=label)
    ax.set(xlabel="Participating EV-days (%)", ylabel="Share of full annual saving (%)")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title("B. Participation targeting", loc="left", weight="bold")

    ax = axes[1, 0]
    cases = ["base", "feeder_2mw_ramp_0p5mw"]
    labels = ["Base", "Feeder + ramp"]
    vals = np.array(
        [
            data.loc[cases, "max_import_kw"].to_numpy(),
            data.loc[cases, "max_export_kw"].to_numpy(),
            data.loc[cases, "max_abs_ramp_kw_per_15min"].to_numpy(),
        ]
    ) / 1000
    width = 0.25
    x = np.arange(2)
    for j, (name, color) in enumerate([("Peak import", COLORS["sc"]), ("Peak export", COLORS["v2g"]), ("Max |ramp|", COLORS["carbon"]) ]):
        ax.bar(x + (j - 1) * width, vals[j], width, label=name, color=color)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Power or 15-min ramp (MW)")
    ax.legend(frameon=False)
    ax.set_title("C. Aggregate infrastructure exposure", loc="left", weight="bold")

    ax = axes[1, 1]
    prices = np.array([30, 50, 100, 150, 200])
    kg_per_vehicle_year = 0.0747021365 * 250
    values = kg_per_vehicle_year / 1000 * prices
    ax.plot(prices, values, marker="o", color=COLORS["accent"])
    ax.set_xticks(prices)
    ax.set(xlabel="Carbon value (US$/t CO₂e)", ylabel="Annual carbon value per EV (US$) ")
    ax.text(0.03, 0.94, "18.68 kg CO₂e/EV-year\n(250 workplace days)", transform=ax.transAxes, va="top")
    ax.set_title("D. Carbon-only owner value", loc="left", weight="bold")
    fig.tight_layout()
    save_figure(fig, "figure14_deployment_readiness")


def make_figures() -> None:
    make_flowchart()
    make_robustness()
    make_deployment()


if __name__ == "__main__":
    make_figures()

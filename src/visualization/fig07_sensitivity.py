from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from src.common import ROOT
from src.visualization.style import COLORS, save_figure, set_publication_style


LABELS = {
    "round_trip_efficiency": ("Round-trip efficiency", "Efficiency"),
    "charger_v2g_power_kw": ("Charger/V2G power", "Power (kW)"),
    "nominal_departure_soc_target": ("Nominal departure SOC", "SOC target"),
}


def make_figure() -> None:
    set_publication_style()
    results = pd.read_csv(ROOT / "results/sensitivity_results.csv")
    participation = pd.read_csv(ROOT / "results/sensitivity/participation_summary.csv")
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.8))
    for ax, (key, (title, xlabel)), letter in zip(axes.flat[:3], LABELS.items(), "ABC"):
        subset = results.loc[results["sensitivity"].eq(key)].sort_values("value")
        ax.plot(
            subset["value"],
            subset["mean_incremental_saving_kg_per_ev_day"],
            marker="o",
            color=COLORS["v2g"],
        )
        ax.set(xlabel=xlabel, ylabel="Incremental saving\n(kg CO₂e/EV-day)")
        ax.set_title(f"{letter}. {title}", loc="left", weight="bold")
    ax = axes.flat[3]
    x = participation["value"]
    ax.plot(x, participation["incremental_v2g_saving_kg"] / 1000, marker="o", color=COLORS["v2g"])
    ax.fill_between(
        x,
        participation["ci95_lower_kg"] / 1000,
        participation["ci95_upper_kg"] / 1000,
        color=COLORS["v2g"],
        alpha=0.2,
    )
    ax.set(xlabel="V2G participation fraction", ylabel="Annual incremental saving (t CO₂e)")
    ax.set_title("D. Participation", loc="left", weight="bold")
    fig.tight_layout()
    save_figure(fig, "figure07_sensitivity_analysis")


if __name__ == "__main__":
    make_figure()

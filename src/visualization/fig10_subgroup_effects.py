from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.common import ROOT
from src.visualization.style import COLORS, save_figure, set_publication_style


PANELS = [
    ("flexibility", "Mobility flexibility"),
    ("carbon_opportunity_kg_per_kwh", "Carbon opportunity"),
    ("required_battery_energy_kwh", "Required charging energy"),
]


def make_figure() -> None:
    set_publication_style()
    groups = pd.read_csv(ROOT / "results/tables/table05_subgroups.csv")
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.6), sharey=True)
    for ax, (variable, title), letter in zip(axes, PANELS, "ABC"):
        subset = groups.loc[groups["variable"].eq(variable)].copy()
        subset["order"] = subset["quartile"].str.extract(r"(\d+)").astype(int)
        subset = subset.sort_values("order")
        mean = subset["mean_incremental_v2g_saving_kg_per_ev_day"].to_numpy()
        lower = subset["bootstrap_ci95_lower_mean_kg"].to_numpy()
        upper = subset["bootstrap_ci95_upper_mean_kg"].to_numpy()
        x = np.arange(1, 5)
        ax.errorbar(
            x,
            mean,
            yerr=np.vstack([mean - lower, upper - mean]),
            marker="o",
            capsize=4,
            linewidth=1.5,
            color=COLORS["v2g"],
        )
        ax.axhline(0, color="#777777", linewidth=0.8)
        ax.set(xticks=x, xticklabels=["Q1\nlow", "Q2", "Q3", "Q4\nhigh"], xlabel="Within-sample quartile")
        ax.set_title(f"{letter}. {title}", loc="left", weight="bold")
    axes[0].set_ylabel("Mean incremental V2G saving\n(kg CO₂e/EV-day; 95% day-clustered CI)")
    fig.tight_layout()
    save_figure(fig, "figure10_subgroup_effects")


if __name__ == "__main__":
    make_figure()

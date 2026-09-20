from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.common import ROOT
from src.visualization.style import save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    ev = pd.read_parquet(ROOT / "results/results_ev_level.parquet")
    ev["Flexibility quartile"] = pd.qcut(
        ev["flexibility"].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]
    )
    ev["Carbon-opportunity quartile"] = pd.qcut(
        ev["carbon_opportunity_kg_per_kwh"].rank(method="first"),
        4,
        labels=["Q1", "Q2", "Q3", "Q4"],
    )
    heat = ev.pivot_table(
        index="Carbon-opportunity quartile",
        columns="Flexibility quartile",
        values="incremental_v2g_saving_kg",
        aggfunc="mean",
        observed=True,
    )
    counts = ev.pivot_table(
        index="Carbon-opportunity quartile",
        columns="Flexibility quartile",
        values="ev_day_id",
        aggfunc="count",
        observed=True,
    )
    annotations = heat.copy().astype(str)
    for row in heat.index:
        for col in heat.columns:
            annotations.loc[row, col] = f"{heat.loc[row, col]:.3f}\n(n={counts.loc[row, col]:,.0f})"
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    sns.heatmap(
        heat,
        annot=annotations,
        fmt="",
        cmap="YlGnBu",
        linewidths=0.5,
        cbar_kws={"label": "Mean incremental V2G saving\n(kg CO₂e per EV-day)"},
        ax=ax,
    )
    ax.set_title("Joint mobility-flexibility and carbon-opportunity map", loc="left", weight="bold")
    ax.set_xlabel("Mobility-flexibility quartile")
    ax.set_ylabel("Within-connection carbon-opportunity quartile")
    fig.tight_layout()
    save_figure(fig, "figure06_flexibility_carbon_opportunity_map")


if __name__ == "__main__":
    make_figure()

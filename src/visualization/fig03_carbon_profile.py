from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.common import ROOT
from src.visualization.style import COLORS, save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    carbon = pd.read_parquet(ROOT / "data/processed/caiso_carbon_15min.parquet")
    hourly = carbon.loc[carbon["interval"] % 4 == 0].copy()
    hourly["hour"] = hourly["interval"] // 4
    hourly["month"] = pd.to_datetime(hourly["date"]).dt.month
    profile = hourly.groupby("hour")["ci_kg_per_kwh"].agg(["mean", "median", "std"])
    heatmap = hourly.pivot_table(index="month", columns="hour", values="ci_kg_per_kwh", aggfunc="mean")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    ax.plot(profile.index, profile["mean"], color=COLORS["carbon"], label="Mean")
    ax.plot(profile.index, profile["median"], color="#333333", linestyle="--", label="Median")
    ax.fill_between(
        profile.index,
        profile["mean"] - profile["std"],
        profile["mean"] + profile["std"],
        color=COLORS["carbon"],
        alpha=0.15,
        label="±1 SD",
    )
    ax.set(xlabel="Hour of day", ylabel="Average emissions rate (kg CO₂e/kWh)")
    ax.set_title("A. Hour-of-day carbon profile", loc="left", weight="bold")
    ax.set_xticks(range(0, 24, 3))
    ax.legend(frameon=False)

    sns.heatmap(
        heatmap,
        ax=axes[1],
        cmap="mako_r",
        cbar_kws={"label": "kg CO₂e/kWh"},
        vmin=hourly["ci_kg_per_kwh"].quantile(0.02),
        vmax=hourly["ci_kg_per_kwh"].quantile(0.98),
    )
    axes[1].set(xlabel="Hour of day", ylabel="Month")
    axes[1].set_title("B. Month × hour carbon-intensity heatmap", loc="left", weight="bold")
    fig.tight_layout()
    save_figure(fig, "figure03_grid_carbon_conditions")


if __name__ == "__main__":
    make_figure()


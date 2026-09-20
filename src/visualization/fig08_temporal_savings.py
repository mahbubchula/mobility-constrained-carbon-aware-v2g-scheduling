from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.common import ROOT
from src.visualization.style import COLORS, save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    daily = pd.read_csv(ROOT / "results/results_daily.csv", parse_dates=["date"])
    daily["month"] = daily["date"].dt.month
    monthly = daily.groupby("month", as_index=False).agg(
        uc_carbon_kg=("uc_carbon_kg", "sum"),
        sc_carbon_kg=("sc_carbon_kg", "sum"),
        v2g_carbon_kg=("v2g_carbon_kg", "sum"),
        smart_saving_kg=("smart_saving_kg", "sum"),
        incremental_v2g_saving_kg=("incremental_v2g_saving_kg", "sum"),
    )

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    ax = axes[0]
    for column, label, color in (
        ("uc_carbon_kg", "Uncontrolled", COLORS["uc"]),
        ("sc_carbon_kg", "Smart charging", COLORS["sc"]),
        ("v2g_carbon_kg", "V2G", COLORS["v2g"]),
    ):
        ax.plot(monthly["month"], monthly[column] / 1000, marker="o", label=label, color=color)
    ax.set(xticks=range(1, 13), xlabel="Month", ylabel="Monthly carbon burden (t CO₂e)")
    ax.set_title("A. Monthly strategy burdens", loc="left", weight="bold")
    ax.legend(frameon=False)

    ax = axes[1]
    x = monthly["month"].to_numpy()
    smart = monthly["smart_saving_kg"].to_numpy() / 1000
    incremental = monthly["incremental_v2g_saving_kg"].to_numpy() / 1000
    ax.bar(x, smart, color=COLORS["sc"], label="Smart vs UC")
    ax.bar(x, incremental, bottom=smart, color=COLORS["v2g"], label="V2G vs smart")
    ax.set(xticks=range(1, 13), xlabel="Month", ylabel="Monthly carbon saving (t CO₂e)")
    ax.set_title("B. Decomposition of monthly saving", loc="left", weight="bold")
    ax.legend(frameon=False)

    ax = axes[2]
    values = daily["incremental_v2g_saving_kg"].to_numpy()
    ax.hist(values, bins=28, color=COLORS["v2g"], alpha=0.85, edgecolor="white")
    median = float(np.median(values))
    ax.axvline(median, color="#333333", linestyle="--", linewidth=1.2)
    ax.text(
        median,
        0.97,
        f"Median {median:.1f} kg/day",
        transform=ax.get_xaxis_transform(),
        ha="left",
        va="top",
        fontsize=8,
    )
    ax.set(xlabel="Daily incremental V2G saving (kg CO₂e)", ylabel="Number of days")
    ax.set_title("C. Daily incremental-benefit distribution", loc="left", weight="bold")

    fig.tight_layout()
    save_figure(fig, "figure08_temporal_savings")


if __name__ == "__main__":
    make_figure()

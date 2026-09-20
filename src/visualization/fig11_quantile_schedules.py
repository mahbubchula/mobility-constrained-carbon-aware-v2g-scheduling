from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.common import ROOT
from src.visualization.style import COLORS, save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    daily = pd.read_csv(ROOT / "results/results_daily.csv", parse_dates=["date"])
    schedules = pd.read_parquet(ROOT / "results/schedules_fleet_15min.parquet")
    schedules["date"] = pd.to_datetime(schedules["date"])
    selections = []
    for quantile, label in ((0.10, "Low-benefit day (P10)"), (0.50, "Median-benefit day (P50)"), (0.90, "High-benefit day (P90)")):
        target = daily["incremental_v2g_saving_kg"].quantile(quantile)
        row = daily.loc[(daily["incremental_v2g_saving_kg"] - target).abs().idxmin()]
        selections.append((row, label))

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.0), sharey=True)
    legend_handles = None
    legend_labels = None
    for ax, (row, label), letter in zip(axes, selections, "ABC"):
        subset = schedules.loc[schedules["date"].eq(row["date"])].sort_values("interval")
        hour = subset["interval"].to_numpy() / 4
        ax.plot(hour, subset["uc_net_power_kw"], color=COLORS["uc"], label="Uncontrolled")
        ax.plot(hour, subset["sc_net_power_kw"], color=COLORS["sc"], label="Smart charging")
        ax.plot(hour, subset["v2g_net_power_kw"], color=COLORS["v2g"], label="V2G net power")
        ax.axhline(0, color="#777777", linewidth=0.7)
        ax.set(xlim=(0, 24), xticks=np.arange(0, 25, 4), xlabel="Hour of day")
        ax.set_title(
            f"{letter}. {label}\n{row['date']:%d %b %Y}; {row['incremental_v2g_saving_kg']:.1f} kg",
            loc="left",
            weight="bold",
            fontsize=9,
        )
        twin = ax.twinx()
        twin.plot(hour, subset["carbon_intensity_kg_per_kwh"], color=COLORS["carbon"], linestyle="--", label="Carbon intensity")
        twin.set_ylim(0.08, 0.43)
        twin.tick_params(axis="y", colors=COLORS["carbon"], labelsize=7)
        if ax is axes[-1]:
            twin.set_ylabel("Carbon intensity (kg CO₂e/kWh)", color=COLORS["carbon"])
        if legend_handles is None:
            handles1, labels1 = ax.get_legend_handles_labels()
            handles2, labels2 = twin.get_legend_handles_labels()
            legend_handles = handles1 + handles2
            legend_labels = labels1 + labels2
    axes[0].set_ylabel("Fleet net grid power (kW)")
    fig.legend(legend_handles, legend_labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save_figure(fig, "figure11_quantile_daily_schedules")


if __name__ == "__main__":
    make_figure()

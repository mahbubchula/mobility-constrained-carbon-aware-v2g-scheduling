from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.common import ROOT
from src.visualization.style import COLORS, save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    daily = pd.read_csv(ROOT / "results/results_daily.csv", parse_dates=["date"])
    schedules = pd.read_parquet(ROOT / "results/schedules_fleet_15min.parquet")
    median = daily["incremental_v2g_saving_kg"].median()
    selected = daily.loc[(daily["incremental_v2g_saving_kg"] - median).abs().idxmin(), "date"]
    day = schedules.loc[pd.to_datetime(schedules["date"]).eq(selected)].sort_values("interval")
    hours = day["interval"] / 4

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(hours, day["uc_net_power_kw"], color=COLORS["uc"], label="Uncontrolled")
    ax.plot(hours, day["sc_net_power_kw"], color=COLORS["sc"], label="Smart charging")
    ax.plot(hours, day["v2g_net_power_kw"], color=COLORS["v2g"], label="V2G net power")
    ax.axhline(0, color="#777777", linewidth=0.7)
    ax.set(xlabel="Hour of day", ylabel="Fleet net grid power (kW)")
    ax.set_xticks(range(0, 25, 2))
    ax2 = ax.twinx()
    ax2.plot(
        hours,
        day["carbon_intensity_kg_per_kwh"],
        color=COLORS["carbon"],
        linestyle="--",
        linewidth=1.5,
        label="Carbon intensity",
    )
    ax2.set_ylabel("Carbon intensity (kg CO₂e/kWh)", color=COLORS["carbon"])
    lines = [
        line
        for line in list(ax.get_lines()) + list(ax2.get_lines())
        if not line.get_label().startswith("_")
    ]
    labels = [line.get_label() for line in lines]
    ax.legend(lines, labels, loc="upper left", frameon=False, ncol=2)
    ax.set_title(
        f"Representative day nearest median incremental V2G benefit: {selected:%d %b %Y}",
        loc="left",
        weight="bold",
    )
    fig.tight_layout()
    save_figure(fig, "figure04_representative_daily_schedules")


if __name__ == "__main__":
    make_figure()

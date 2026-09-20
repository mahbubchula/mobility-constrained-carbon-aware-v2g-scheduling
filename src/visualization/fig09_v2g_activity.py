from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.common import ROOT, load_config
from src.visualization.style import COLORS, save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    config = load_config()
    daily = pd.read_csv(ROOT / "results/results_daily.csv", parse_dates=["date"])
    ev = pd.read_parquet(ROOT / "results/results_ev_level.parquet")
    ev["date"] = pd.to_datetime(ev["date"])
    ev["month"] = ev["date"].dt.month

    fig, axes = plt.subplots(2, 2, figsize=(9.5, 7.0))
    ax = axes[0, 0]
    labels = ["Uncontrolled", "Smart charging", "V2G"]
    imports = np.array([daily[f"{p}_import_kwh"].sum() for p in ("uc", "sc", "v2g")]) / 1000
    exports = np.array([daily[f"{p}_export_kwh"].sum() for p in ("uc", "sc", "v2g")]) / 1000
    net = imports - exports
    x = np.arange(3)
    ax.bar(x, imports, color=[COLORS["uc"], COLORS["sc"], COLORS["v2g"]], alpha=0.85, label="Import")
    ax.bar(x, -exports, color=COLORS["accent"], alpha=0.85, label="Export")
    ax.scatter(x, net, marker="D", s=28, color="#222222", label="Net grid energy", zorder=3)
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.set_xticks(x, labels, rotation=12)
    ax.set_ylabel("Annual grid energy (MWh)")
    ax.set_title("A. Strategy energy accounting", loc="left", weight="bold")
    ax.legend(frameon=False)

    monthly = ev.groupby("month").agg(
        active_share=("v2g_v2g_active", "mean"),
        export_kwh=("v2g_export_kwh", "sum"),
        active_count=("v2g_v2g_active", "sum"),
    )
    monthly["export_per_active_kwh"] = monthly["export_kwh"] / monthly["active_count"]
    ax = axes[0, 1]
    ax.bar(monthly.index, 100 * monthly["active_share"], color=COLORS["v2g"], alpha=0.8)
    ax.set(xticks=range(1, 13), xlabel="Month", ylabel="V2G-active EV-days (%)")
    twin = ax.twinx()
    twin.plot(monthly.index, monthly["export_per_active_kwh"], color=COLORS["accent"], marker="o")
    twin.set_ylabel("Export per active EV-day (kWh)", color=COLORS["accent"])
    twin.tick_params(axis="y", colors=COLORS["accent"])
    ax.set_title("B. Monthly activity and export", loc="left", weight="bold")

    ax = axes[1, 0]
    active_efc = ev.loc[ev["v2g_v2g_active"], "v2g_efc"]
    ax.hist(active_efc, bins=np.linspace(0, config["v2g_max_discharge_fraction_capacity"], 26), color=COLORS["v2g"], alpha=0.85, edgecolor="white")
    ax.axvline(config["v2g_max_discharge_fraction_capacity"], color=COLORS["carbon"], linestyle="--")
    ax.text(
        config["v2g_max_discharge_fraction_capacity"] - 0.004,
        0.97,
        "Session cap",
        transform=ax.get_xaxis_transform(),
        rotation=90,
        va="top",
        ha="right",
        color=COLORS["carbon"],
        fontsize=8,
    )
    ax.set(xlabel="Export equivalent full cycles per active EV-day", ylabel="Active EV-days")
    ax.set_title("C. Distribution of V2G throughput", loc="left", weight="bold")

    ax = axes[1, 1]
    savings = np.clip(ev["incremental_v2g_saving_kg"].to_numpy(), 0, None)
    savings = np.sort(savings)[::-1]
    population = np.arange(1, len(savings) + 1) / len(savings)
    cumulative = np.cumsum(savings) / savings.sum()
    ax.plot(population, cumulative, color=COLORS["v2g"], linewidth=2)
    ax.plot([0, 1], [0, 1], color="#777777", linestyle="--", linewidth=1, label="Equal contribution")
    half_index = int(np.searchsorted(cumulative, 0.5))
    half_share = population[half_index]
    ax.scatter([half_share], [0.5], color=COLORS["accent"], zorder=3)
    ax.annotate(
        f"{100*half_share:.1f}% of EV-days\nprovide 50% of saving",
        (half_share, 0.5),
        xytext=(10, -30),
        textcoords="offset points",
        fontsize=8,
        arrowprops={"arrowstyle": "-", "color": "#555555"},
    )
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Cumulative share of EV-days (highest value first)", ylabel="Cumulative share of incremental saving")
    ax.set_title("D. Concentration of incremental value", loc="left", weight="bold")
    ax.legend(frameon=False, loc="lower right")

    fig.tight_layout()
    save_figure(fig, "figure09_v2g_activity_and_concentration")


if __name__ == "__main__":
    make_figure()

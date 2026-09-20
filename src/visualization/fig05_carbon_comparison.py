from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from src.common import ROOT
from src.visualization.style import COLORS, save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    table = pd.read_csv(ROOT / "results/tables/table04_strategy_results.csv")
    values = table["carbon_burden_kg"] / 1000
    labels = ["Uncontrolled", "Smart charging", "V2G"]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    bars = ax.bar(labels, values, color=[COLORS["uc"], COLORS["sc"], COLORS["v2g"]], width=0.62)
    ax.set_ylabel("Annual carbon burden (t CO₂e)")
    ax.set_title("Carbon performance under identical departure-energy requirements", loc="left", weight="bold")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:,.1f}", ha="center", va="bottom")
    smart_saving = values.iloc[0] - values.iloc[1]
    v2g_saving = values.iloc[1] - values.iloc[2]
    y_top = values.max() * 1.10
    ax.annotate(
        f"Smart-charging benefit\n{smart_saving:,.1f} t",
        xy=(0.5, (values.iloc[0] + values.iloc[1]) / 2),
        xytext=(0.5, y_top),
        ha="center",
        arrowprops={"arrowstyle": "-[,widthB=3.5", "color": COLORS["sc"]},
        color=COLORS["sc"],
    )
    ax.annotate(
        f"Incremental bidirectionality benefit\n{v2g_saving:,.1f} t",
        xy=(1.5, (values.iloc[1] + values.iloc[2]) / 2),
        xytext=(1.5, y_top * 0.90),
        ha="center",
        arrowprops={"arrowstyle": "-[,widthB=3.5", "color": COLORS["v2g"]},
        color=COLORS["v2g"],
    )
    ax.set_ylim(0, y_top * 1.16)
    fig.tight_layout()
    save_figure(fig, "figure05_main_carbon_comparison")


if __name__ == "__main__":
    make_figure()


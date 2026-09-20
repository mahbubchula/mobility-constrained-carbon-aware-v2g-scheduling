from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.common import ROOT, load_config, weighted_choice_indices
from src.visualization.style import COLORS, save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    config = load_config()
    synthetic = pd.read_parquet(ROOT / "data/synthetic/synthetic_ev_days.parquet")
    holdout = pd.read_parquet(ROOT / "data/processed/commuter_holdout.parquet")
    rng = np.random.default_rng(config["seed"] + 17)
    reference = holdout.iloc[
        weighted_choice_indices(rng, holdout["nhts_weight"].to_numpy(), 50_000)
    ]
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.5))
    specifications = [
        ("arrival_min", "Arrival time", "Minutes after midnight", (0, 1440)),
        ("departure_min", "Departure time", "Minutes after midnight", (0, 1440)),
        ("connection_hours", "Connection duration (h)", "Connection duration (h)", None),
        ("inbound_distance_km", "Inbound distance (km)", "Inbound distance (km)", (0, 120)),
    ]
    for letter, (variable, title, xlabel, limit), ax in zip("ABCD", specifications, axes.flat[:4]):
        sns.ecdfplot(reference[variable], ax=ax, label="NHTS holdout", color="#333333")
        sns.ecdfplot(synthetic[variable], ax=ax, label="Synthetic", color=COLORS["sc"])
        if limit:
            ax.set_xlim(limit)
        ax.set_title(f"{letter}. {title}", loc="left", weight="bold")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Cumulative probability")
        ax.legend(frameon=False)

    ax = axes.flat[4]
    quantiles = np.linspace(0.01, 0.99, 99)
    variables = ["arrival_min", "departure_min", "connection_hours", "inbound_distance_km"]
    markers = ["o", "s", "^", "D"]
    for variable, marker in zip(variables, markers):
        h = np.quantile(reference[variable], quantiles)
        s = np.quantile(synthetic[variable], quantiles)
        # Standardize to permit multiple variables on one Q-Q panel.
        h = (h - h.mean()) / h.std()
        s = (s - s.mean()) / s.std()
        ax.scatter(h[::4], s[::4], s=12, marker=marker, alpha=0.7, label=variable.replace("_", " "))
    ax.plot([-2.5, 2.5], [-2.5, 2.5], color="#333333", linewidth=1)
    ax.set(xlabel="Holdout standardized quantile", ylabel="Synthetic standardized quantile")
    ax.set_title("E. Quantile agreement", loc="left", weight="bold")
    ax.legend(frameon=False, fontsize=7)

    validation = pd.read_csv(ROOT / "results/validation/synthetic_distribution_validation.csv")
    ax = axes.flat[5]
    y = np.arange(len(validation))
    ax.barh(y, validation["ks_statistic"], color=COLORS["sc"], alpha=0.85)
    ax.axvline(0.15, linestyle="--", color=COLORS["carbon"])
    ax.set_yticks(y, validation["variable"].str.replace("_", " "))
    ax.invert_yaxis()
    ax.set_xlabel("Kolmogorov–Smirnov statistic")
    ax.set_title("F. Distribution diagnostics", loc="left", weight="bold")
    ax.text(
        0.148,
        0.97,
        "KS threshold",
        transform=ax.get_xaxis_transform(),
        rotation=90,
        ha="right",
        va="top",
        color=COLORS["carbon"],
        fontsize=7,
    )
    fig.tight_layout()
    save_figure(fig, "figure02_synthetic_validation")


if __name__ == "__main__":
    make_figure()

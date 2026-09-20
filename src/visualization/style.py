from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from src.common import ROOT


COLORS = {
    "uc": "#5B6573",
    "sc": "#2878B5",
    "v2g": "#1B9E77",
    "carbon": "#C44E52",
    "accent": "#E69F00",
}


def set_publication_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 120,
            "savefig.bbox": "tight",
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    output = ROOT / "results" / "figures"
    output.mkdir(parents=True, exist_ok=True)
    fig.savefig(output / f"{stem}.pdf")
    fig.savefig(output / f"{stem}.svg")
    fig.savefig(output / f"{stem}.png", dpi=600)
    plt.close(fig)


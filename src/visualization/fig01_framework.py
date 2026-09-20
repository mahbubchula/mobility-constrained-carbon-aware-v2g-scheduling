from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

from src.visualization.style import COLORS, save_figure, set_publication_style


def make_figure() -> None:
    set_publication_style()
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5)
    ax.axis("off")

    boxes = [
        (0.2, 3.3, 2.0, 0.9, "2022 NHTS\ncommuter records", "#E8F1F8"),
        (0.2, 1.0, 2.0, 0.9, "2025 CAISO\naverage emissions rate", "#F8E8E8"),
        (2.8, 3.3, 2.0, 0.9, "Bootstrap-calibrated\nsynthetic EV-days", "#E8F1F8"),
        (5.4, 3.3, 2.0, 0.9, "Mobility, SOC, power,\nefficiency constraints", "#EEF4E8"),
        (5.4, 1.0, 2.0, 0.9, "Hourly carbon signal\nrepeated to 15 minutes", "#F8E8E8"),
        (8.0, 3.7, 2.4, 0.65, "Uncontrolled charging", "#EFF0F2"),
        (8.0, 2.7, 2.4, 0.65, "Carbon-aware smart charging", "#E8F1F8"),
        (8.0, 1.7, 2.4, 0.65, "Carbon-aware V2G", "#E5F3ED"),
        (8.0, 0.35, 2.4, 0.75, "Incremental V2G value\nSC emissions − V2G emissions", "#FFF2D9"),
    ]
    for x, y, width, height, text, face in boxes:
        patch = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.04,rounding_size=0.06",
            linewidth=1,
            edgecolor="#44515E",
            facecolor=face,
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, y + height / 2, text, ha="center", va="center")

    junction = Circle((7.7, 3.0), radius=0.055, facecolor="#596773", edgecolor="none")
    ax.add_patch(junction)

    arrows = [
        ((2.2, 3.75), (2.8, 3.75)),
        ((4.8, 3.75), (5.4, 3.75)),
        ((2.2, 1.45), (5.4, 1.45)),
        ((7.4, 3.75), (7.68, 3.07)),
        ((7.4, 1.45), (7.68, 2.93)),
        ((7.72, 3.04), (8.0, 4.02)),
        ((7.75, 3.0), (8.0, 3.02)),
        ((7.72, 2.96), (8.0, 2.02)),
        ((9.2, 1.7), (9.2, 1.1)),
    ]
    for start, end in arrows:
        ax.add_patch(
            FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=11, color="#596773")
        )
    ax.text(5.5, 4.65, "Mobility-constrained carbon-aware scheduling framework", ha="center", fontsize=12, weight="bold")
    save_figure(fig, "figure01_research_framework")


if __name__ == "__main__":
    make_figure()

"""Figure 1: how the raw corpus becomes the analysis set.

Reads data/processed/funnel.json and draws message counts after each step.
Usage: uv run python -m enron_importance.figures.funnel
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt

from ..config import load_config
from ..provenance import record_stage
from .style import GRID, RC, SERIES, TEXT_PRIMARY, TEXT_SECONDARY, save

STEPS = [
    ("parsed_files", "Files in the corpus"),
    ("in_window", "Dated 1998–2002"),
    ("unique_messages", "After removing duplicate copies"),
    ("with_authored_text", "With estimated authored text"),
    ("analysis_messages", "Staff prose, excl. automated, records, reports"),
]


def draw(funnel: dict) -> plt.Figure:
    labels = [label for _, label in STEPS]
    values = [funnel[key] for key, _ in STEPS]
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(6.5, 2.6))
        positions = range(len(values))[::-1]
        ax.barh(list(positions), values, height=0.55, color=SERIES[0])
        ax.set_yticks(list(positions), labels)
        ax.tick_params(axis="y", length=0)
        ax.set_xlim(0, max(values) * 1.18)
        ax.xaxis.set_major_formatter(lambda x, _: f"{x / 1000:,.0f}k")
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        for y, value in zip(positions, values):
            share = value / values[0]
            ax.text(value + max(values) * 0.01, y, f"{value:,}  ({share:.0%})", va="center",
                    color=TEXT_PRIMARY, fontsize=8)
        ax.set_title("From raw corpus to analysis set")
        ax.set_xlabel("Messages", color=TEXT_SECONDARY)
    return fig


def main() -> None:
    config = load_config()
    funnel = json.loads((config["paths"]["processed"] / "funnel.json").read_text())["funnel"]
    for path in save(draw(funnel), config["paths"]["figures"], "fig01_data_funnel"):
        print(f"Wrote {path}")
    record_stage(config, "figures.funnel")


if __name__ == "__main__":
    main()

"""Figure 6: how well each network measure recovers formal rank.

Reads results/baselines_formal_rank.csv. Points are pairwise accuracy with
95% person-bootstrap intervals; the dashed line is chance (0.5).
Usage: uv run python -m enron_importance.figures.baselines
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from ..config import load_config
from .style import GRID, RC, SERIES, TEXT_PRIMARY, TEXT_SECONDARY, save

LABELS = {
    "degree": "Degree (distinct contacts)",
    "pagerank": "PageRank",
    "in_strength": "Email received (weighted)",
    "betweenness": "Betweenness (exact)",
    "out_strength": "Email sent (messages)",
}


def draw(table: pd.DataFrame) -> plt.Figure:
    table = table.sort_values("accuracy").reset_index(drop=True)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(6.5, 2.6))
        y = range(len(table))
        ax.axvline(0.5, color=TEXT_SECONDARY, linewidth=0.8, linestyle=(0, (3, 3)))
        ax.text(0.5, len(table) - 0.35, "chance", color=TEXT_SECONDARY, fontsize=8, ha="center")
        ax.hlines(list(y), table["ci_low"], table["ci_high"], color=SERIES[0], linewidth=2)
        ax.plot(table["accuracy"], list(y), "o", color=SERIES[0], markersize=7,
                markeredgecolor="#fcfcfb", markeredgewidth=1.5)
        for i, row in table.iterrows():
            ax.text(row["ci_high"] + 0.008, i, f"{row['accuracy']:.1%}", va="center", color=TEXT_PRIMARY, fontsize=8)
        ax.set_yticks(list(y), [LABELS.get(m, m) for m in table["measure"]])
        ax.tick_params(axis="y", length=0)
        ax.set_xlim(0.4, 0.8)
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        ax.set_ylim(-0.6, len(table) - 0.1)
        ax.set_title("Which network measure recovers formal rank?")
        ax.set_xlabel("Pairwise ordering accuracy (95% person bootstrap)", color=TEXT_SECONDARY)
    return fig


def main() -> None:
    config = load_config()
    table = pd.read_csv(config["paths"]["results"] / "baselines_formal_rank.csv")
    for path in save(draw(table), config["paths"]["figures"], "fig06_baselines_formal_rank"):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()

"""Shared figure style: one place for colors, type and axis treatment.

Colors are the validated reference palette (light mode): categorical slots
are assigned in fixed order, text never takes a series color, and axes and
grids stay recessive so the data carries the figure.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # first three categorical slots

RC = {
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelcolor": TEXT_SECONDARY,
    "axes.edgecolor": GRID,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": TEXT_SECONDARY,
    "ytick.color": TEXT_PRIMARY,
    "text.color": TEXT_PRIMARY,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
}


def save(fig, directory: Path, name: str) -> list[Path]:
    """Write vector (PDF, for the paper) and PNG (for the web) versions."""
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for suffix, kwargs in ((".pdf", {}), (".png", {"dpi": 200})):
        path = directory / f"{name}{suffix}"
        fig.savefig(path, bbox_inches="tight", metadata={"CreationDate": None} if suffix == ".pdf" else {}, **kwargs)
        written.append(path)
    plt.close(fig)
    return written

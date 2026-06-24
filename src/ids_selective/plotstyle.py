"""Shared figure style for the paper's plots.

A single place for the colour-blind-safe Okabe--Ito palette, restrained spines, and consistent
fonts/sizes so every figure in the paper looks like it belongs to the same document. Import and call
``use()`` once at the top of a figure script, then pull colours from ``C`` by name.
"""
from __future__ import annotations
import matplotlib as mpl
import matplotlib.pyplot as plt

# Okabe--Ito qualitative palette (distinguishable in grayscale and for all common colour-vision types).
C = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "grey": "#999999",
}
CYCLE = [C["blue"], C["vermillion"], C["green"], C["orange"], C["purple"], C["sky"]]


def use() -> None:
    """Apply the shared rcParams (idempotent)."""
    mpl.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "axes.grid": True,
        "grid.color": C["grey"],
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
        "lines.linewidth": 1.6,
        "patch.linewidth": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "axes.prop_cycle": mpl.cycler(color=CYCLE),
    })


def despine(ax) -> None:
    """Drop the top/right spines on an axis that was built outside the global rc (e.g. imshow grids)."""
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fig(w: float = 3.3, h: float = 2.4):
    """A single-column figure of the house size."""
    return plt.subplots(figsize=(w, h))

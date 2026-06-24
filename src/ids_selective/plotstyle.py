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


# --- Perceptually-uniform sequential colormaps -------------------------------------------------
# The single most important lever for vibrant-yet-honest figures (Crameri scientific maps and
# cmocean, both colour-vision-safe); we degrade gracefully to matplotlib's viridis-family built-ins
# so the scripts still run without the optional packages.
_FALLBACK = {"batlow": "cividis", "oslo": "cividis", "lipari": "viridis", "lajolla": "magma",
             "thermal": "inferno", "dense": "viridis", "matter": "magma", "amp": "magma"}


def seq(name: str = "batlow"):
    """Return a perceptually-uniform sequential colormap by friendly name (Crameri/cmocean if present)."""
    try:
        import cmcrameri.cm as _cmc
        if hasattr(_cmc, name):
            return getattr(_cmc, name)
    except Exception:
        pass
    try:
        import cmocean
        if name in cmocean.cm.cmapnames:
            return cmocean.cm.cmap_d[name]
    except Exception:
        pass
    return plt.get_cmap(_FALLBACK.get(name, "magma"))


def ridgeline(ax, rows, labels, colors=None, overlap: float = 0.6, edge: str = "white"):
    """Joyplot/ridgeline: stacked filled density curves, one row per dataset (bottom row first).

    `rows` is a list of (x, density) pairs sharing comparable scale; densities are normalised to a
    common max so row heights are honest relative to one another. Returns the baseline y-positions.
    """
    import numpy as np
    n = len(rows)
    colors = colors or [CYCLE[i % len(CYCLE)] for i in range(n)]
    peak = max(float(np.max(y)) for _, y in rows) or 1.0
    scale = (1.0 + overlap) / peak
    bases = []
    for i, (x, y) in enumerate(rows):
        base = float(i)
        top = base + np.asarray(y, float) * scale
        ax.fill_between(x, base, top, color=colors[i], alpha=0.85, lw=0, zorder=2 * (n - i))
        ax.plot(x, top, color=edge, lw=0.8, zorder=2 * (n - i) + 1)
        bases.append(base)
    ax.set_yticks(bases); ax.set_yticklabels(labels)
    ax.set_ylim(-0.1, n + overlap)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    return bases

"""Confidence-interval helpers for multi-seed evaluation (shared by the experiment scripts)."""
from __future__ import annotations
import numpy as np
from scipy import stats


def ci(vals):
    """Return (mean, half-width) of a 95% t-interval across seeds."""
    a = np.asarray(vals, float)
    m = float(a.mean())
    if len(a) < 2:
        return m, 0.0
    h = float(stats.t.ppf(0.975, len(a) - 1) * a.std(ddof=1) / np.sqrt(len(a)))
    return m, h


def pm(vals, d=3, signed=False):
    """Format as a LaTeX 'mean $\\pm$ half-width' string at `d` decimals."""
    m, h = ci(vals)
    s = f"{m:+.{d}f}" if signed else f"{m:.{d}f}"
    return f"{s} $\\pm$ {h:.{d}f}"

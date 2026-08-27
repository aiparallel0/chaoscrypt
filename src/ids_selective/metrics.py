"""Calibration and selective-prediction metrics.

- `ece`: Expected Calibration Error (equal-width confidence bins), the standard over/under-confidence
  summary (Guo et al. 2017).
- `risk_coverage`: the selective-prediction curve (El-Yaniv & Wiener). Sorting predictions by
  confidence and accepting the most-confident fraction `c` gives selective risk r(c); the area under
  r(c) (AURC) summarizes how usefully the confidence ranks errors. Lower AURC = better.
"""
from __future__ import annotations
import numpy as np


def ece(confidence: np.ndarray, correct: np.ndarray, n_bins: int = 15) -> float:
    """Expected Calibration Error. `confidence` = predicted prob of the chosen class in [0,1];
    `correct` = 1 if that prediction was right. Weighted mean |confidence - accuracy| over bins."""
    confidence = np.asarray(confidence, float)
    correct = np.asarray(correct, float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(confidence)
    out = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (confidence > lo) & (confidence <= hi) if lo > 0 else (confidence >= lo) & (confidence <= hi)
        if not m.any():
            continue
        out += (m.sum() / n) * abs(confidence[m].mean() - correct[m].mean())
    return float(out)


def risk_coverage(confidence: np.ndarray, correct: np.ndarray):
    """Return (coverages, risks, aurc). Accept the most-confident points first; risk = error rate
    among accepted. coverages run 1/n..1; aurc = mean risk over that curve."""
    confidence = np.asarray(confidence, float)
    error = 1.0 - np.asarray(correct, float)
    order = np.argsort(-confidence)  # most confident first
    err_sorted = error[order]
    n = len(err_sorted)
    cum_err = np.cumsum(err_sorted)
    k = np.arange(1, n + 1)
    risks = cum_err / k
    coverages = k / n
    aurc = float(risks.mean())
    return coverages, risks, aurc


def risk_at_coverage(confidence: np.ndarray, correct: np.ndarray, coverage: float) -> float:
    """Selective risk (error rate) when accepting the top-`coverage` fraction by confidence."""
    confidence = np.asarray(confidence, float)
    error = 1.0 - np.asarray(correct, float)
    order = np.argsort(-confidence)
    k = max(1, int(round(coverage * len(confidence))))
    return float(error[order][:k].mean())

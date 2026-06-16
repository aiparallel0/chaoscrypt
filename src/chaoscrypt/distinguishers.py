"""Statistical distinguishers and standard image-cipher metrics.

`chi_square_uniformity` detects the non-uniformity of a chaotic-map keystream (a secondary, target-
independent weakness). `npcr` / `uaci` are the standard differential metrics; the module-level ideals
let a paper make the point that near-ideal NPCR/UACI does NOT imply chosen-plaintext resistance.
"""
from __future__ import annotations
from typing import Tuple
import numpy as np
from scipy import stats

# Ideal values for an 8-bit (256 gray-level) image (Wu, Noonan & Agaian, 2011).
NPCR_IDEAL = 99.6094
UACI_IDEAL = 33.4635


def chi_square_uniformity(byte_seq) -> Tuple[float, float]:
    """Chi-square goodness-of-fit of a byte sequence against the uniform distribution.
    Returns (statistic, p_value). Small p (e.g. < 1e-3) => distinguishable from random."""
    counts = np.bincount(np.asarray(byte_seq, dtype=np.uint8).ravel(), minlength=256)
    chi2, p = stats.chisquare(counts)
    return float(chi2), float(p)


def npcr(c1, c2) -> float:
    """Number of Pixels Change Rate (%) between two ciphertexts."""
    c1 = np.asarray(c1)
    c2 = np.asarray(c2)
    return 100.0 * float(np.mean(c1 != c2))


def uaci(c1, c2) -> float:
    """Unified Average Changing Intensity (%) between two ciphertexts."""
    c1 = np.asarray(c1, dtype=np.float64)
    c2 = np.asarray(c2, dtype=np.float64)
    return 100.0 * float(np.mean(np.abs(c1 - c2) / 255.0))

"""Preprocessing and open-set splits for NSL-KDD.

Numeric features are standardized; the three categorical features are one-hot encoded with
`handle_unknown="ignore"` so test-only categories don't break the transform. The encoder is fit on
TRAIN only (no test leakage — an Arp et al. 2022 "Dos and Don'ts" requirement).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .data import CATEGORICAL, COLUMNS

_DROP = {"label", "difficulty", "family", "y"}
FEATURES = [c for c in COLUMNS if c not in _DROP]
NUMERIC = [c for c in FEATURES if c not in CATEGORICAL]


def make_encoder() -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
        ]
    )


def encode(train: pd.DataFrame, test: pd.DataFrame):
    """Fit on train, transform both. Returns (Xtr, ytr, Xte, yte, encoder)."""
    enc = make_encoder()
    Xtr = enc.fit_transform(train[FEATURES])
    Xte = enc.transform(test[FEATURES])
    return Xtr, train["y"].to_numpy(), Xte, test["y"].to_numpy(), enc


def family_holdout_mask(train: pd.DataFrame, holdout: str) -> np.ndarray:
    """Boolean mask selecting TRAIN rows to KEEP when holding out one attack family
    (normal rows always kept). Used to simulate 'this attack family is unknown at train time'."""
    return ~(train["family"] == holdout)

"""CIC-IDS-2017 loader (flow-based, 78 numeric features) for the second-dataset / drift study.

Cleans column-name whitespace, coerces non-numeric cells, replaces +/-Inf with NaN and drops NaN rows,
builds a binary target and an attack-family label (mapping the mojibaked 'Web Attack ...' variants to
'Web'). Day files load separately so we can train on one day and test on another (cross-day drift).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA = "papers/paper2-ids-selective/data/cicids"
FRIDAY = ["Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
          "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"]
THURSDAY = ["Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"]


def _family(lbl: str) -> str:
    u = str(lbl).strip().upper()
    if u == "BENIGN":
        return "benign"
    if u.startswith("WEB"):
        return "Web"
    if u == "DDOS":
        return "DDoS"
    if u == "PORTSCAN":
        return "PortScan"
    return u.title()


def load_day(files, data_dir: str = DATA, subsample: int | None = None, seed: int = 42):
    """Return (frame_with_family_and_y, feature_names). Numeric features are float32."""
    parts = []
    for f in files:
        d = pd.read_csv(Path(data_dir) / f, low_memory=False)
        d.columns = [c.strip() for c in d.columns]
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    feats = [c for c in df.columns if c != "Label"]
    for c in feats:
        if df[c].dtype == object:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df[feats] = df[feats].replace([np.inf, -np.inf], np.nan)
    keep = df[feats].notna().all(axis=1)
    df = df[keep].reset_index(drop=True)
    out = df[feats].astype(np.float32).copy()
    out["family"] = df["Label"].map(_family).values
    out["y"] = (out["family"] != "benign").astype(int)
    if subsample and len(out) > subsample:
        out = out.sample(subsample, random_state=seed).reset_index(drop=True)
    return out, feats

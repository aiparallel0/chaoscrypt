"""Paper 2, external validity: cross-corpus transfer CIC-IDS-2017 -> CSE-CIC-IDS-2018, multi-seed.

Train on CIC-2017 (DDoS/PortScan/Web + benign), test on CIC-2018 (Thursday-01-03 = Infiltration +
benign), a different network/year, using the features whose CICFlowMeter names match exactly across the
two releases. Over K seeds we resample the 2017 training subset and the model seed; we report means and
a max 95% CI half-width. The 2018 test partition is held fixed.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ids_selective.cicids import load_day, FRIDAY, THURSDAY
from ids_selective.metrics import ece, risk_coverage, risk_at_coverage
from ids_selective.ci import ci

HERE = Path(__file__).parent
RES = HERE / "results"
CIC2018 = HERE / "data/cicids2018/Thursday-01-03-2018.csv"
K = 5


def load_2018(path, subsample=120000, seed=42):
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    feats = [c for c in df.columns if c not in ("Label", "Timestamp")]
    df[feats] = df[feats].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    df = df[df[feats].notna().all(axis=1)].reset_index(drop=True)
    df["y"] = (df["Label"].astype(str).str.strip().str.upper() != "BENIGN").astype(int)
    if subsample and len(df) > subsample:
        df = df.sample(subsample, random_state=seed).reset_index(drop=True)
    return df


def main() -> None:
    tr, feats17 = load_day(FRIDAY + THURSDAY, subsample=200000)
    te = load_2018(CIC2018)
    common = [c for c in feats17 if c in set(te.columns)]
    Xtr_all, ytr_all = tr[common].to_numpy(), tr["y"].to_numpy()
    Xte0, yte = te[common].to_numpy(), te["y"].to_numpy()
    atk = yte == 1

    acc, ece_, aurc, rfull, r80, idet, irej, in_acc, in_aurc = ([] for _ in range(9))
    for seed in range(K):
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(Xtr_all), min(150000, len(Xtr_all)), replace=False)
        Xtr, ytr = Xtr_all[idx], ytr_all[idx]
        sc = StandardScaler().fit(Xtr)
        Xtr_s, Xte = sc.transform(Xtr), sc.transform(Xte0)
        # within-2017 baseline (same features)
        Xa, Xb, ya, yb = train_test_split(Xtr_s, ytr, test_size=0.3, random_state=seed, stratify=ytr)
        rf0 = RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=seed).fit(Xa, ya)
        p0 = rf0.predict_proba(Xb); c0 = (p0.argmax(1) == yb).astype(float)
        in_acc.append(float(c0.mean())); in_aurc.append(float(risk_coverage(p0.max(1), c0)[2]))
        # transfer
        rf = RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=seed).fit(Xtr_s, ytr)
        p = rf.predict_proba(Xte); conf, pred = p.max(1), p.argmax(1); cor = (pred == yte).astype(float)
        tau = np.quantile(conf, 0.20)
        acc.append(float(cor.mean())); ece_.append(float(ece(conf, cor)))
        aurc.append(float(risk_coverage(conf, cor)[2])); rfull.append(float(1 - cor.mean()))
        r80.append(float(risk_at_coverage(conf, cor, 0.8)))
        idet.append(float((pred[atk] == 1).mean())); irej.append(float((conf[atk] < tau).mean()))
        print(f"seed {seed} done")

    flat = {"xfer_n_common": len(common), "xfer_n_test": int(len(yte)),
            "xfer_attack_rate": round(float(yte.mean()), 3)}
    hws = []
    for key, store in (("xfer_in2017_acc", in_acc), ("xfer_in2017_aurc", in_aurc), ("xfer_acc", acc),
                       ("xfer_ece", ece_), ("xfer_aurc", aurc), ("xfer_risk_full", rfull),
                       ("xfer_risk80", r80), ("xfer_infil_detect", idet), ("xfer_infil_reject", irej)):
        m, h = ci(store); flat[key] = round(m, 4 if "aurc" in key or "ece" in key else 3); hws.append(h)
    flat["xfer_maxhw"] = round(max(hws), 4)
    RES.mkdir(exist_ok=True); (RES / "transfer.json").write_text(json.dumps(flat, indent=2))
    print(flat)


if __name__ == "__main__":
    main()

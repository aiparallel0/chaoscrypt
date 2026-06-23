"""Paper 2, external validity: cross-corpus transfer CIC-IDS-2017 -> CSE-CIC-IDS-2018.

A stronger genuine-unknown test than cross-day: train on CIC-2017 (DDoS/PortScan/Web + benign), test on
CIC-2018 (a different network/year) whose Thursday-01-03 traffic is Infiltration + benign -- an attack
type ABSENT from training. The two releases renamed many CICFlowMeter columns, so we use the features
whose names match exactly across both (a documented, conservative choice) and ask whether the paper's
mechanisms survive a real domain change: does accuracy/calibration degrade, does max-softmax stay a
strong signal, and does abstention flag the cross-corpus unknown attack?
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

HERE = Path(__file__).parent
RES = HERE / "results"
CIC2018 = HERE / "data/cicids2018/Thursday-01-03-2018.csv"


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
    tr, feats17 = load_day(FRIDAY + THURSDAY, subsample=150000)
    te = load_2018(CIC2018)
    common = [c for c in feats17 if c in set(te.columns)]   # exact-name shared CICFlowMeter features
    Xtr, ytr = tr[common].to_numpy(), tr["y"].to_numpy()
    Xte, yte = te[common].to_numpy(), te["y"].to_numpy()
    sc = StandardScaler().fit(Xtr)
    Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)

    flat = {"xfer_n_common": len(common), "xfer_n_test": int(len(yte)),
            "xfer_attack_rate": round(float(yte.mean()), 3)}

    # within-2017 baseline on the same features (degradation context)
    Xa, Xb, ya, yb = train_test_split(Xtr, ytr, test_size=0.3, random_state=0, stratify=ytr)
    rf0 = RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=0).fit(Xa, ya)
    p0 = rf0.predict_proba(Xb); c0 = (p0.argmax(1) == yb).astype(float)
    flat["xfer_in2017_acc"] = round(float(c0.mean()), 3)
    flat["xfer_in2017_aurc"] = round(float(risk_coverage(p0.max(1), c0)[2]), 4)

    # transfer: train all 2017, test 2018
    rf = RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=0).fit(Xtr, ytr)
    p = rf.predict_proba(Xte); conf, pred = p.max(1), p.argmax(1); cor = (pred == yte).astype(float)
    atk = yte == 1
    tau = np.quantile(conf, 0.20)                          # 80% coverage
    flat.update({
        "xfer_acc": round(float(cor.mean()), 3),
        "xfer_ece": round(float(ece(conf, cor)), 4),
        "xfer_aurc": round(float(risk_coverage(conf, cor)[2]), 4),
        "xfer_risk_full": round(float(1 - cor.mean()), 4),
        "xfer_risk80": round(float(risk_at_coverage(conf, cor, 0.8)), 4),
        "xfer_infil_detect": round(float((pred[atk] == 1).mean()), 3),
        "xfer_infil_reject": round(float((conf[atk] < tau).mean()), 3),
    })
    print(f"common features: {len(common)} | test n={len(yte)} attack-rate={flat['xfer_attack_rate']}")
    print(f"within-2017 acc={flat['xfer_in2017_acc']} AURC={flat['xfer_in2017_aurc']}")
    print(f"transfer acc={flat['xfer_acc']} ECE={flat['xfer_ece']} AURC={flat['xfer_aurc']} "
          f"risk {flat['xfer_risk_full']}->{flat['xfer_risk80']}@80%")
    print(f"Infiltration: detection={flat['xfer_infil_detect']} abstention-rejects={flat['xfer_infil_reject']}")
    RES.mkdir(exist_ok=True)
    (RES / "transfer.json").write_text(json.dumps(flat, indent=2))


if __name__ == "__main__":
    main()

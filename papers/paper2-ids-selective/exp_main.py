"""Paper 2 main experiment: calibration + selective prediction on NSL-KDD.

For each model: test accuracy, ECE (raw and after Platt scaling), risk-coverage/AURC, risk@80%
coverage, and detection rate on known vs novel (unknown) attacks. Dumps a flat results JSON for the
paper's \\PH{} placeholders and writes two figures (risk-coverage curves; RF reliability raw vs
calibrated). Calibrator is fit on a held-out split of TRAIN (no test leakage).
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode
from ids_selective.metrics import ece, risk_coverage, risk_at_coverage

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
RNG = 42


def reliability(conf, correct, n_bins=15):
    edges = np.linspace(0, 1, n_bins + 1)
    xs, ys = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            xs.append(conf[m].mean())
            ys.append(np.asarray(correct)[m].mean())
    return np.array(xs), np.array(ys)


def main() -> None:
    ds = NslKdd.load()
    Xtr, ytr, Xte, yte, _ = encode(ds.train, ds.test)
    novel = set(ds.novel_attack_labels())
    is_novel = ds.test["label"].isin(novel).to_numpy()
    is_known_atk = ((ds.test["y"] == 1).to_numpy()) & (~is_novel)

    # fit (60%) / calibrate (20%) / in-distribution validation (20%) split of TRAIN
    Xtr2, Xval, ytr2, yval = train_test_split(
        Xtr, ytr, test_size=0.2, random_state=RNG, stratify=ytr)
    Xfit, Xcal, yfit, ycal = train_test_split(
        Xtr2, ytr2, test_size=0.25, random_state=RNG, stratify=ytr2)

    models = {
        "logreg": LogisticRegression(max_iter=300),
        "rf": RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=0),
        "histgb": HistGradientBoostingClassifier(random_state=0),
    }
    flat: dict = {"n_train": int(len(ytr)), "n_test": int(len(yte)),
                  "n_novel_types": len(novel), "n_novel_rows": int(is_novel.sum())}
    curves, rf_arrays, ece_store = {}, {}, {}

    for name, base in models.items():
        base.fit(Xfit, yfit)
        proba = base.predict_proba(Xte)
        conf, pred = proba.max(1), proba.argmax(1)
        correct = (pred == yte).astype(float)
        acc = correct.mean()
        e_raw = ece(conf, correct)
        cov, risks, aurc = risk_coverage(conf, correct)
        r80 = risk_at_coverage(conf, correct, 0.80)
        cal = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid").fit(Xcal, ycal)
        pcal = cal.predict_proba(Xte)
        conf_c, pred_c = pcal.max(1), pcal.argmax(1)
        e_cal = ece(conf_c, (pred_c == yte).astype(float))
        # in-distribution calibration: ECE on a held-out TRAIN split (same distribution as fit)
        pv = base.predict_proba(Xval)
        ev_raw = ece(pv.max(1), (pv.argmax(1) == yval).astype(float))
        pvc = cal.predict_proba(Xval)
        ev_cal = ece(pvc.max(1), (pvc.argmax(1) == yval).astype(float))
        det_known = (pred[is_known_atk] == 1).mean()
        det_novel = (pred[is_novel] == 1).mean()
        flat.update({
            f"{name}_acc": round(float(acc), 4),
            f"{name}_ece_raw": round(float(e_raw), 4),
            f"{name}_ece_cal": round(float(e_cal), 4),
            f"{name}_aurc": round(float(aurc), 4),
            f"{name}_risk_full": round(float(1 - acc), 4),
            f"{name}_risk80": round(float(r80), 4),
            f"{name}_det_known": round(float(det_known), 4),
            f"{name}_det_novel": round(float(det_novel), 4),
            f"{name}_ece_val_raw": round(float(ev_raw), 4),
            f"{name}_ece_val_cal": round(float(ev_cal), 4),
        })
        curves[name] = (cov, risks)
        ece_store[name] = (float(ev_raw), float(e_raw))
        if name == "rf":
            rf_arrays = dict(conf=conf, correct=correct, conf_c=conf_c,
                             correct_c=(pred_c == yte).astype(float))
        print(f"[{name}] acc={acc:.4f} ECE {e_raw:.4f}->{e_cal:.4f} AURC={aurc:.4f} "
              f"risk {1-acc:.4f}->{r80:.4f}@80% det known/novel={det_known:.3f}/{det_novel:.3f}")

    RES.mkdir(exist_ok=True)
    (RES / "main.json").write_text(json.dumps(flat, indent=2))

    FIG.mkdir(exist_ok=True)
    # Fig 1: risk-coverage
    plt.figure(figsize=(3.4, 2.6))
    for name, (cov, risks) in curves.items():
        plt.plot(cov, risks, label=name, lw=1.4)
    plt.xlabel("coverage"); plt.ylabel("selective risk (error)")
    plt.legend(fontsize=7); plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(FIG / "risk_coverage.pdf"); plt.close()

    # Fig 2: RF reliability raw vs calibrated
    plt.figure(figsize=(3.4, 2.6))
    plt.plot([0, 1], [0, 1], "k--", lw=.8, label="perfect")
    for key, lab in [("", "raw"), ("_c", "calibrated")]:
        xs, ys = reliability(rf_arrays[f"conf{key}"], rf_arrays[f"correct{key}"])
        plt.plot(xs, ys, marker="o", ms=3, lw=1.2, label=f"RF {lab}")
    plt.xlabel("confidence"); plt.ylabel("accuracy"); plt.legend(fontsize=7)
    plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(FIG / "reliability_rf.pdf"); plt.close()

    # Fig 3: ECE in-distribution vs shifted test, per model -- the calibration-under-shift finding
    names = list(ece_store)
    x = np.arange(len(names))
    plt.figure(figsize=(3.4, 2.4))
    plt.bar(x - 0.2, [ece_store[n][0] for n in names], 0.4, label="in-distribution")
    plt.bar(x + 0.2, [ece_store[n][1] for n in names], 0.4, label="shifted test")
    plt.xticks(x, names); plt.ylabel("ECE"); plt.legend(fontsize=7)
    plt.grid(axis="y", alpha=.3); plt.tight_layout()
    plt.savefig(FIG / "ece_shift.pdf"); plt.close()
    print(f"wrote {RES/'main.json'} and 3 figures")


if __name__ == "__main__":
    main()

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
    from ids_selective import plotstyle as ps
    ps.use()
    disp = {"logreg": "Logistic reg.", "rf": "Random forest", "histgb": "Hist-GB"}
    mcol = {"logreg": ps.C["blue"], "rf": ps.C["green"], "histgb": ps.C["orange"]}

    # Fig 1: risk-coverage with the 80%-coverage operating point ringed on each curve. The gap between
    # the flat linear model (uninformative confidence) and the falling tree ensembles is the point.
    fig, ax = ps.fig(3.3, 2.5)
    for name, (cov, risks) in curves.items():
        ax.plot(cov, risks, label=disp[name], color=mcol[name])
        ax.scatter(0.8, float(np.interp(0.8, cov, risks)), s=34, facecolor="white",
                   edgecolor=mcol[name], linewidth=1.4, zorder=5)
    ax.axvline(0.8, color=ps.C["grey"], ls=":", lw=1.0, zorder=0)
    ax.text(0.79, ax.get_ylim()[1] * 0.98, "accept top 80%", rotation=90, va="top", ha="right",
            fontsize=6.5, color=ps.C["grey"])
    ax.set_xlabel("coverage (fraction accepted)"); ax.set_ylabel("selective risk (error)")
    ax.set_xlim(0, 1); ax.set_ylim(bottom=0); ax.legend(loc="upper center")
    fig.tight_layout(); fig.savefig(FIG / "risk_coverage.pdf"); plt.close(fig)

    # Fig 2: RF reliability raw vs Platt-scaled on the shifted test set; the shaded wedge below the
    # diagonal is the over-confidence (accuracy < confidence) that source-fit calibration cannot remove.
    fig, ax = ps.fig(3.3, 2.5)
    ax.plot([0, 1], [0, 1], color=ps.C["black"], ls="--", lw=0.9, label="perfect calibration")
    xs_r, ys_r = reliability(rf_arrays["conf"], rf_arrays["correct"])
    xs_c, ys_c = reliability(rf_arrays["conf_c"], rf_arrays["correct_c"])
    ax.fill_between(xs_r, ys_r, xs_r, where=(ys_r < xs_r), interpolate=True,
                    color=ps.C["vermillion"], alpha=0.18, label="over-confidence")
    ax.plot(xs_r, ys_r, marker="o", ms=3.5, color=ps.C["vermillion"], label="RF raw")
    ax.plot(xs_c, ys_c, marker="s", ms=3.5, color=ps.C["blue"], label="RF Platt-scaled")
    ax.set_xlabel("confidence"); ax.set_ylabel("accuracy")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.legend(loc="upper left")
    fig.tight_layout(); fig.savefig(FIG / "reliability_rf.pdf"); plt.close(fig)

    # Fig 3: calibration inflates under shift -- a dumbbell per model from in-distribution ECE (well
    # calibrated) to shifted-test ECE (badly miscalibrated). Replaces a generic grouped bar chart.
    order = ["logreg", "rf", "histgb"]
    fig, ax = ps.fig(3.3, 2.15)
    for i, n in enumerate(order):
        indist, shift = ece_store[n]
        ax.annotate("", xy=(shift, i), xytext=(indist, i),
                    arrowprops=dict(arrowstyle="-|>", color=ps.C["grey"], lw=1.5,
                                    shrinkA=4, shrinkB=4))
        ax.scatter(indist, i, s=46, color=ps.C["green"], zorder=3, edgecolor="white", linewidth=0.5,
                   label="in-distribution" if i == 0 else None)
        ax.scatter(shift, i, s=46, color=ps.C["vermillion"], zorder=3, edgecolor="white", linewidth=0.5,
                   label="shifted test" if i == 0 else None)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([disp[n] for n in order])
    ax.set_ylim(-0.5, len(order) - 0.5); ax.set_xlim(-0.008, max(s for _, s in ece_store.values()) * 1.12)
    ax.set_xlabel("expected calibration error (ECE)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, columnspacing=1.3, handletextpad=0.4)
    fig.tight_layout(); fig.savefig(FIG / "ece_shift.pdf"); plt.close(fig)
    print(f"wrote {RES/'main.json'} and 3 figures")


if __name__ == "__main__":
    main()

"""Paper 2, blind-spot remedy: a benign-only novelty stage as a second control.

Confidence-based abstention barely flags R2L/U2R (they mimic benign traffic). The apt detector for that
regime is a BENIGN-ONLY density model (one-class), NOT the two-class Mahalanobis used for error ranking.
We fit Isolation Forest and One-Class SVM on benign training rows only, then measure how much of each
attack family they recover at a fixed benign false-positive budget, and the AUROC ceiling (novelty score
separating each family from benign). This turns the blind spot into a studied mechanism with a measured
remedy and a measured cost.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score
from sklearn.svm import OneClassSVM

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
FAMILIES = ["DoS", "Probe", "R2L", "U2R"]
FPS = (0.05, 0.10)


def recovery_at_fp(anom, fam_te, family, benign_mask, fp):
    thr = np.quantile(anom[benign_mask], 1 - fp)          # threshold giving `fp` benign false positives
    m = fam_te == family
    return float((anom[m] >= thr).mean()) if m.any() else float("nan")


def main() -> None:
    ds = NslKdd.load()
    Xtr, ytr, Xte, yte, _ = encode(ds.train, ds.test)
    fam_te = ds.test["family"].to_numpy()
    benign_mask = yte == 0                                 # NSL-KDD labels benign as "normal"
    benign_tr = Xtr[ytr == 0]                              # benign-only training (the key distinction)

    detectors = {
        "if": IsolationForest(n_estimators=200, random_state=0, n_jobs=-1).fit(benign_tr),
        "ocsvm": OneClassSVM(nu=0.05, gamma="scale").fit(
            benign_tr[np.random.default_rng(0).choice(len(benign_tr), 5000, replace=False)]),
    }
    flat: dict = {}
    aurocs = {}
    for dname, det in detectors.items():
        anom = -det.score_samples(Xte) if dname == "if" else -det.decision_function(Xte)
        aurocs[dname] = {}
        for fam in FAMILIES:
            m = fam_te == fam
            au = roc_auc_score(np.r_[np.zeros(benign_mask.sum()), np.ones(m.sum())],
                               np.r_[anom[benign_mask], anom[m]])
            aurocs[dname][fam] = au
            flat[f"nov_{dname}_auroc_{fam}"] = round(float(au), 3)
            for fp in FPS:
                flat[f"nov_{dname}_rec_{fam}_fp{int(fp*100)}"] = round(recovery_at_fp(anom, fam_te, fam, benign_mask, fp), 3)
        print(f"[{dname}] AUROC " + " ".join(f"{f}={aurocs[dname][f]:.3f}" for f in FAMILIES))
        print(f"      recovery@10%FP " + " ".join(f"{f}={flat[f'nov_{dname}_rec_{f}_fp10']}" for f in FAMILIES))

    RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
    (RES / "novelty.json").write_text(json.dumps(flat, indent=2))
    x = np.arange(len(FAMILIES))
    plt.figure(figsize=(3.4, 2.5))
    plt.bar(x - 0.2, [aurocs["if"][f] for f in FAMILIES], 0.4, label="Isolation Forest")
    plt.bar(x + 0.2, [aurocs["ocsvm"][f] for f in FAMILIES], 0.4, label="One-Class SVM")
    plt.axhline(0.5, color="k", ls="--", lw=.7)
    plt.xticks(x, FAMILIES); plt.ylabel("novelty AUROC vs benign"); plt.ylim(0, 1)
    plt.legend(fontsize=7); plt.grid(axis="y", alpha=.3); plt.tight_layout()
    plt.savefig(FIG / "novelty_auroc.pdf"); plt.close()
    print("wrote results/novelty.json and novelty_auroc.pdf")


if __name__ == "__main__":
    main()

"""Paper 2 upgrade: benchmark uncertainty signals beyond maximum-softmax (MSP), and a split-conformal
coverage check. Max-softmax is the weakest OOD/uncertainty baseline; we compare it against random-forest
ensemble disagreement (epistemic), Mahalanobis distance to class-conditional Gaussians, and kNN distance
in feature space, on (a) error ranking (AURC, lower better) and (b) unknown-attack separation (AUROC of
the uncertainty score vs the novel-attack indicator, higher better). Split conformal then shows coverage
is valid in-distribution but erodes under the train->test shift (the guarantee-erosion phenomenon).
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode
from ids_selective.metrics import risk_coverage

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
RNG = 42


def mahalanobis_scores(Xtr, ytr, Xte):
    """Min over classes of Mahalanobis distance to class-conditional Gaussian (shared covariance)."""
    means = {c: Xtr[ytr == c].mean(0) for c in np.unique(ytr)}
    centered = np.vstack([Xtr[ytr == c] - means[c] for c in means])
    cov = np.cov(centered, rowvar=False) + 1e-3 * np.eye(Xtr.shape[1])
    inv = np.linalg.pinv(cov)
    d = []
    for c, m in means.items():
        diff = Xte - m
        d.append(np.einsum("ij,jk,ik->i", diff, inv, diff))
    return np.min(np.vstack(d), axis=0)


def main() -> None:
    ds = NslKdd.load()
    Xtr_all, ytr_all, Xte, yte, _ = encode(ds.train, ds.test)
    is_novel = ds.test["label"].isin(set(ds.novel_attack_labels())).to_numpy()

    Xtr2, Xval, ytr2, yval = train_test_split(Xtr_all, ytr_all, test_size=0.2, random_state=RNG, stratify=ytr_all)
    Xfit, Xcal, yfit, ycal = train_test_split(Xtr2, ytr2, test_size=0.25, random_state=RNG, stratify=ytr2)

    rf = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=0).fit(Xfit, yfit)
    proba = rf.predict_proba(Xte)
    pred = proba.argmax(1)
    correct = (pred == yte).astype(float)

    # uncertainty signals (higher = less certain)
    per_tree = np.stack([t.predict_proba(Xte)[:, 1] for t in rf.estimators_])  # (T, n)
    ref = Xfit[np.random.default_rng(RNG).choice(len(Xfit), size=min(20000, len(Xfit)), replace=False)]
    knn = NearestNeighbors(n_neighbors=5).fit(ref)
    signals = {
        "msp": 1.0 - proba.max(1),
        "rf_disagreement": per_tree.std(0),
        "mahalanobis": mahalanobis_scores(Xfit, yfit, Xte),
        "knn": knn.kneighbors(Xte)[0][:, -1],
    }
    flat, curves = {}, {}
    for name, unc in signals.items():
        _, _, aurc = risk_coverage(-unc, correct)          # rank RF errors by the signal
        au = roc_auc_score(is_novel, unc)                  # separate novel attacks
        flat[f"sig_{name}_aurc"] = round(float(aurc), 4)
        flat[f"sig_{name}_unkauroc"] = round(float(au), 4)
        cov, risks, _ = risk_coverage(-unc, correct)
        curves[name] = (cov, risks)
        print(f"[{name:16s}] AURC={aurc:.4f}  unknown-AUROC={au:.4f}")

    # split conformal: threshold from calibration nonconformity (1 - p_true); coverage in-dist vs shift
    alpha = 0.10
    pcal = rf.predict_proba(Xcal)
    nc_cal = 1.0 - pcal[np.arange(len(ycal)), ycal]
    q = np.quantile(nc_cal, np.ceil((len(ycal) + 1) * (1 - alpha)) / len(ycal), method="higher")

    def coverage(X, y):
        p = rf.predict_proba(X)
        in_set = (1.0 - p) <= q                              # prediction set per class
        return float(in_set[np.arange(len(y)), y].mean())

    flat["conf_alpha"] = alpha
    flat["conf_cov_indist"] = round(coverage(Xval, yval), 4)
    flat["conf_cov_shift"] = round(coverage(Xte, yte), 4)
    print(f"conformal target {1-alpha:.2f}: coverage in-dist={flat['conf_cov_indist']} "
          f"shift={flat['conf_cov_shift']}")

    RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
    (RES / "signals.json").write_text(json.dumps(flat, indent=2))
    plt.figure(figsize=(3.4, 2.6))
    for name, (cov, risks) in curves.items():
        plt.plot(cov, risks, label=name, lw=1.3)
    plt.xlabel("coverage"); plt.ylabel("selective risk"); plt.legend(fontsize=7)
    plt.grid(alpha=.3); plt.tight_layout(); plt.savefig(FIG / "signals_riskcov.pdf"); plt.close()
    print("wrote results/signals.json and signals_riskcov.pdf")


if __name__ == "__main__":
    main()

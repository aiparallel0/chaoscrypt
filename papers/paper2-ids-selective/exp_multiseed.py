"""Paper 2 statistical rigor: multi-seed evaluation with bootstrap/t confidence intervals.

Over K seeds we resample the fit/calibration/validation split AND model randomness, evaluating on the
fixed NSL-KDD test set. Every headline metric becomes mean [95% CI] (t-interval across seeds), and the
equivalence claim ("max-softmax suffices") is tested with the PAIRED per-seed difference
delta-AURC = signal - MSP and its CI -- the correct statistic for a no-difference claim. Across-seed CIs
capture train+model variance (the dominant source); the NSL-KDD test partition is canonical and fixed.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode
from ids_selective.metrics import ece, risk_coverage, risk_at_coverage

HERE = Path(__file__).parent
RES = HERE / "results"
K = 15


def ci(vals):
    """mean and 95% t-CI across seeds."""
    a = np.asarray(vals, float)
    m = a.mean()
    if len(a) < 2:
        return m, m, m
    h = stats.t.ppf(0.975, len(a) - 1) * a.std(ddof=1) / np.sqrt(len(a))
    return m, m - h, m + h


def fmt(vals, d=4):
    m, lo, hi = ci(vals)
    return f"{m:.{d}f} $\\pm$ {(hi - lo) / 2:.{d}f}"


def maha(Xtr, ytr, Xte):
    means = {c: Xtr[ytr == c].mean(0) for c in np.unique(ytr)}
    centered = np.vstack([Xtr[ytr == c] - means[c] for c in means])
    inv = np.linalg.pinv(np.cov(centered, rowvar=False) + 1e-3 * np.eye(Xtr.shape[1]))
    return np.min(np.vstack([np.einsum("ij,jk,ik->i", Xte - m, inv, Xte - m) for m in means.values()]), 0)


def main() -> None:
    ds = NslKdd.load()
    Xtr_all, ytr_all, Xte, yte, _ = encode(ds.train, ds.test)
    is_novel = ds.test["label"].isin(set(ds.novel_attack_labels())).to_numpy()

    acc = {m: [] for m in ("logreg", "rf", "histgb")}
    ece_, aurc, risk80 = ({m: [] for m in acc} for _ in range(3))
    sig_aurc = {s: [] for s in ("msp", "rf_disagreement", "mahalanobis", "knn")}
    sig_unk = {s: [] for s in sig_aurc}
    dmsp = {s: [] for s in ("rf_disagreement", "mahalanobis", "knn")}  # paired delta vs MSP
    cov_in, cov_sh = [], []

    for seed in range(K):
        Xtr2, Xval, ytr2, yval = train_test_split(Xtr_all, ytr_all, test_size=0.2, random_state=seed, stratify=ytr_all)
        Xfit, Xcal, yfit, ycal = train_test_split(Xtr2, ytr2, test_size=0.25, random_state=seed, stratify=ytr2)
        models = {"logreg": LogisticRegression(max_iter=300),
                  "rf": RandomForestClassifier(n_estimators=120, n_jobs=-1, random_state=seed),
                  "histgb": HistGradientBoostingClassifier(random_state=seed)}
        rf = None
        for name, clf in models.items():
            clf.fit(Xfit, yfit)
            p = clf.predict_proba(Xte); conf, pred = p.max(1), p.argmax(1)
            cor = (pred == yte).astype(float)
            acc[name].append(cor.mean()); ece_[name].append(ece(conf, cor))
            aurc[name].append(risk_coverage(conf, cor)[2]); risk80[name].append(risk_at_coverage(conf, cor, .8))
            if name == "rf":
                rf, rf_proba, rf_pred, rf_cor = clf, p, pred, cor
        # signals on the RF base (same errors), seed's fit set as reference
        per_tree = np.stack([t.predict_proba(Xte)[:, 1] for t in rf.estimators_])
        ref = Xfit[np.random.default_rng(seed).choice(len(Xfit), min(8000, len(Xfit)), replace=False)]
        kd = NearestNeighbors(n_neighbors=5).fit(ref).kneighbors(Xte)[0][:, -1]
        sig = {"msp": 1 - rf_proba.max(1), "rf_disagreement": per_tree.std(0),
               "mahalanobis": maha(Xfit, yfit, Xte), "knn": kd}
        a_msp = risk_coverage(-sig["msp"], rf_cor)[2]
        for s, u in sig.items():
            a = risk_coverage(-u, rf_cor)[2]
            sig_aurc[s].append(a); sig_unk[s].append(roc_auc_score(is_novel, u))
            if s != "msp":
                dmsp[s].append(a - a_msp)
        # split conformal coverage (alpha=0.1) in-distribution (val) vs shift (test)
        pcal = rf.predict_proba(Xcal); nc = 1 - pcal[np.arange(len(ycal)), ycal]
        q = np.quantile(nc, np.ceil((len(ycal) + 1) * 0.9) / len(ycal), method="higher")
        cov_in.append(float(((1 - rf.predict_proba(Xval)) <= q)[np.arange(len(yval)), yval].mean()))
        cov_sh.append(float(((1 - rf_proba) <= q)[np.arange(len(yte)), yte].mean()))
        print(f"seed {seed}: rf AURC={aurc['rf'][-1]:.4f} msp/maha AURC={sig_aurc['msp'][-1]:.4f}/{sig_aurc['mahalanobis'][-1]:.4f}")

    flat = {"ms_K": K}
    for name in acc:
        flat[f"ms_{name}_acc"] = fmt(acc[name], 3)
        flat[f"ms_{name}_ece"] = fmt(ece_[name], 4)
        flat[f"ms_{name}_aurc"] = fmt(aurc[name], 4)
        flat[f"ms_{name}_risk80"] = fmt(risk80[name], 4)
    for s in sig_aurc:
        flat[f"ms_sig_{s}_aurc"] = fmt(sig_aurc[s], 4)
        flat[f"ms_sig_{s}_unk"] = fmt(sig_unk[s], 3)
    for s in dmsp:
        m, lo, hi = ci(dmsp[s])
        flat[f"ms_dmsp_{s}"] = f"{m:+.4f} $\\pm$ {(hi - lo) / 2:.4f}"
    flat["ms_conf_indist"] = fmt(cov_in, 3)
    flat["ms_conf_shift"] = fmt(cov_sh, 3)
    RES.mkdir(exist_ok=True)
    (RES / "multiseed.json").write_text(json.dumps(flat, indent=2))
    print("\n=== paired delta-AURC vs MSP (95% CI) ===")
    for s in dmsp:
        print(f"  {s}: {flat[f'ms_dmsp_{s}']}")
    print("conformal coverage in-dist:", flat["ms_conf_indist"], "shift:", flat["ms_conf_shift"])


if __name__ == "__main__":
    main()

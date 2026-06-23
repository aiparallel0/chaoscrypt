"""Paper 2 blind-spot remedy: a benign-only novelty stage (multi-seed).

Confidence-based abstention barely flags R2L (benign-mimicking). The apt detector is a BENIGN-ONLY
density model -- one-class, distinct from the two-class Mahalanobis used for error ranking. We fit an
Isolation Forest and a one-class SVM on benign records only and measure family recovery at a 10% benign
false-positive budget and the AUROC ceiling. Over K seeds we vary the model/seed and the one-class-SVM
benign subsample; we report means with 95% CI error bars (figure) and a max CI half-width.
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
from ids_selective.ci import ci

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
FAMILIES = ["DoS", "Probe", "R2L", "U2R"]
K = 8


def rec_at_fp(anom, fam_te, fam, benign_mask, fp):
    thr = np.quantile(anom[benign_mask], 1 - fp)
    m = fam_te == fam
    return float((anom[m] >= thr).mean()) if m.any() else float("nan")


def main() -> None:
    ds = NslKdd.load()
    Xtr, ytr, Xte, yte, _ = encode(ds.train, ds.test)
    fam_te = ds.test["family"].to_numpy()
    bmask = yte == 0
    benign_tr = Xtr[ytr == 0]

    auroc = {d: {F: [] for F in FAMILIES} for d in ("if", "ocsvm")}
    rec10 = {d: {F: [] for F in FAMILIES} for d in ("if", "ocsvm")}
    for seed in range(K):
        rng = np.random.default_rng(seed)
        det = {"if": IsolationForest(n_estimators=200, random_state=seed, n_jobs=-1).fit(benign_tr),
               "ocsvm": OneClassSVM(nu=0.05, gamma="scale").fit(
                   benign_tr[rng.choice(len(benign_tr), 5000, replace=False)])}
        for dn, d in det.items():
            anom = -d.score_samples(Xte) if dn == "if" else -d.decision_function(Xte)
            for F in FAMILIES:
                m = fam_te == F
                auroc[dn][F].append(roc_auc_score(
                    np.r_[np.zeros(bmask.sum()), np.ones(m.sum())], np.r_[anom[bmask], anom[m]]))
                rec10[dn][F].append(rec_at_fp(anom, fam_te, F, bmask, 0.10))
        print(f"seed {seed} done")

    flat, hws = {}, []
    for dn in ("if", "ocsvm"):
        for F in FAMILIES:
            for tag, store in (("auroc", auroc), ("rec_" + "", rec10)):
                key = f"nov_{dn}_auroc_{F}" if tag == "auroc" else f"nov_{dn}_rec_{F}_fp10"
                m, h = ci(store[dn][F]); flat[key] = round(m, 3); hws.append(h)
    flat["nov_maxhw"] = round(max(hws), 3)
    RES.mkdir(exist_ok=True)
    (RES / "novelty.json").write_text(json.dumps(flat, indent=2))

    FIG.mkdir(exist_ok=True)
    x = np.arange(len(FAMILIES))
    if_m = [ci(auroc["if"][F]) for F in FAMILIES]
    oc_m = [ci(auroc["ocsvm"][F]) for F in FAMILIES]
    plt.figure(figsize=(3.4, 2.5))
    plt.bar(x - 0.2, [m for m, _ in if_m], 0.4, yerr=[h for _, h in if_m], capsize=2, label="Isolation Forest")
    plt.bar(x + 0.2, [m for m, _ in oc_m], 0.4, yerr=[h for _, h in oc_m], capsize=2, label="One-Class SVM")
    plt.axhline(0.5, color="k", ls="--", lw=.7)
    plt.xticks(x, FAMILIES); plt.ylabel("novelty AUROC vs benign"); plt.ylim(0, 1)
    plt.legend(fontsize=7); plt.grid(axis="y", alpha=.3); plt.tight_layout()
    plt.savefig(FIG / "novelty_auroc.pdf"); plt.close()
    print("novelty means + max CI half-width", flat["nov_maxhw"])


if __name__ == "__main__":
    main()

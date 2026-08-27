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
    from ids_selective import plotstyle as ps
    ps.use()

    # Fig A: novelty AUROC as a dot plot (both detectors per family), families ordered by separability
    # with a chance reference -- replaces a generic grouped bar chart.
    order = sorted(FAMILIES, key=lambda F: ci(auroc["if"][F])[0], reverse=True)
    y = np.arange(len(order))
    fig, ax = ps.fig(3.3, 2.35)
    for det, mk, col, off, lab in (("if", "o", ps.C["blue"], 0.12, "Isolation Forest"),
                                   ("ocsvm", "s", ps.C["orange"], -0.12, "One-Class SVM")):
        m = [ci(auroc[det][F])[0] for F in order]
        h = [ci(auroc[det][F])[1] for F in order]
        ax.errorbar(m, y + off, xerr=h, fmt=mk, color=col, ms=6, capsize=2, elinewidth=0.9,
                    linestyle="none", label=lab)
    ax.axvline(0.5, color=ps.C["grey"], ls="--", lw=0.9, label="chance")
    ax.set_yticks(y); ax.set_yticklabels(order); ax.set_ylim(-0.5, len(order) - 0.5)
    ax.invert_yaxis(); ax.set_xlabel("novelty AUROC vs benign"); ax.set_xlim(0.4, 1.01)
    ax.grid(axis="y", visible=False); ax.legend(loc="lower left", fontsize=6.5)
    fig.tight_layout(); fig.savefig(FIG / "novelty_auroc.pdf"); plt.close(fig)

    # Fig B: the benign manifold. Each test record is placed by how anomalous the two benign-only
    # detectors find it (z-scored so benign sits near 0); R2L falls inside the benign envelope -- it
    # mimics normal traffic and so evades both abstention and novelty -- while DoS/Probe/U2R separate.
    iff = IsolationForest(n_estimators=200, random_state=0, n_jobs=-1).fit(benign_tr)
    rng0 = np.random.default_rng(0)
    ocs = OneClassSVM(nu=0.05, gamma="scale").fit(benign_tr[rng0.choice(len(benign_tr), 5000, replace=False)])
    zif = (-iff.score_samples(Xte)); zif = (zif - zif[bmask].mean()) / (zif[bmask].std() + 1e-9)
    zoc = (-ocs.decision_function(Xte)); zoc = (zoc - zoc[bmask].mean()) / (zoc[bmask].std() + 1e-9)

    def _samp(mask, k):
        idx = np.where(mask)[0]
        return rng0.choice(idx, min(k, len(idx)), replace=False) if len(idx) else idx

    # Wide two-panel "benign manifold" (a figure* spanning both columns): (a) the (IF, OCSVM) joint
    # novelty space, (b) a ridgeline of per-family IF anomaly. Both show R2L's distribution sitting on
    # top of benign's -- overlapping support -- while DoS/Probe/U2R separate.
    from scipy.stats import gaussian_kde
    fcol = {"benign": ps.C["grey"], "DoS": ps.C["blue"], "Probe": ps.C["green"],
            "U2R": ps.C["purple"], "R2L": ps.C["vermillion"]}
    masks = {"benign": bmask, "DoS": fam_te == "DoS", "Probe": fam_te == "Probe",
             "U2R": fam_te == "U2R", "R2L": fam_te == "R2L"}
    fig = plt.figure(figsize=(7.1, 2.9))
    gs = fig.add_gridspec(1, 2, width_ratios=(1.1, 1), wspace=0.22)
    axj = fig.add_subplot(gs[0, 0]); axd = fig.add_subplot(gs[0, 1])
    xlim = np.percentile(zif, [0.5, 99]); ylim = np.percentile(zoc, [0.5, 99])
    for name in ("benign", "DoS", "Probe", "U2R", "R2L"):
        idx = _samp(masks[name], 4000 if name == "benign" else 1200)
        axj.scatter(zif[idx], zoc[idx], s=5 if name == "benign" else 9, color=fcol[name],
                    alpha=0.25 if name == "benign" else 0.6, linewidths=0, label=name, rasterized=True)
    bx = np.percentile(zif[bmask], [2.5, 97.5]); by = np.percentile(zoc[bmask], [2.5, 97.5])
    axj.add_patch(plt.Rectangle((bx[0], by[0]), bx[1] - bx[0], by[1] - by[0], fill=False,
                                ls="--", ec=ps.C["black"], lw=1.0, zorder=4))
    axj.text(bx[1], by[0], " benign\n envelope", fontsize=6.5, va="bottom", ha="left", zorder=5)
    axj.set_xlim(*xlim); axj.set_ylim(*ylim)
    axj.set_xlabel("Isolation-Forest anomaly (benign SDs)")
    axj.set_ylabel("One-Class-SVM anomaly (benign SDs)")
    axj.legend(loc="upper left", framealpha=0.85, handletextpad=0.2, borderpad=0.3,
               labelspacing=0.25, markerscale=1.4, fontsize=6.5)
    axj.set_title("(a) joint novelty space", fontsize=8)
    order = sorted(masks, key=lambda n: np.median(zif[masks[n]]))
    xg = np.linspace(*np.percentile(zif, [0.5, 99.5]), 300)
    ps.ridgeline(axd, [(xg, gaussian_kde(zif[masks[n]])(xg)) for n in order], order,
                 colors=[fcol[n] for n in order], overlap=0.85)
    axd.set_xlim(xg[0], xg[-1]); axd.set_xlabel("Isolation-Forest anomaly (benign SDs)")
    axd.set_title("(b) per-family anomaly (ridgeline)", fontsize=8)
    fig.savefig(FIG / "benign_manifold.pdf", bbox_inches="tight"); plt.close(fig)
    print("novelty means + max CI half-width", flat["nov_maxhw"])


if __name__ == "__main__":
    main()

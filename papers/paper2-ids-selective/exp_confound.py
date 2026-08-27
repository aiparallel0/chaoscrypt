"""Paper 2 confounder controls: is R2L's near-zero detection a benign-mimicry blind spot, or just an
unbalanced classifier thresholded at argmax? And are the tight CIs hiding evaluation uncertainty?

Three threshold-free / resampling controls the reviewers asked for:

  (I1) Per-family AUROC of the attack score (benign vs. family F) -- threshold-free, so it cannot be an
       artifact of the 0.5 argmax cut. We also DECOMPOSE R2L's seen-detection three ways: argmax recall,
       recall under class_weight="balanced", and recall at a per-family 10% benign-FPR operating point.
       If the AUROC is low AND none of these rescue R2L, the blind spot is structural, not a threshold.
  (I2) Detection collapse as an AUROC delta (seen -> family held out), so the "collapse" is a pure
       detectability statement, not an operating-point/calibration effect.
  (I4) Evaluation-distribution bootstrap: the canonical KDDTest+ partition is resampled with replacement
       to get a CI that reflects test-set uncertainty -- the uncertainty the fixed-partition multi-seed
       CIs miss by construction.

NSL-KDD is ~balanced at the BINARY level (46.5% attack), so class_weight balances attack-vs-normal,
which is already even; it does not specifically target the within-attack rarity of R2L. That is the
point of reporting it.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode, family_holdout_mask
from ids_selective.ci import ci

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
FAMILIES = ["DoS", "Probe", "R2L", "U2R"]
K = 6
B_BOOT = 1000


def _auroc_benign_vs(score, y_is_benign_or_F, fam_mask, benign_mask):
    """AUROC separating family-F rows (positive) from benign rows (negative) by attack score."""
    yld = np.r_[np.zeros(benign_mask.sum()), np.ones(fam_mask.sum())]
    sc = np.r_[score[benign_mask], score[fam_mask]]
    return float(roc_auc_score(yld, sc))


def _recall_at_benign_fpr(score, fam_mask, benign_mask, fpr=0.10):
    """Per-family recall when the threshold is set to a fixed benign false-positive rate (a sane
    per-family operating point, unlike the global argmax cut)."""
    thr = np.quantile(score[benign_mask], 1 - fpr)
    return float((score[fam_mask] >= thr).mean())


def main() -> None:
    ds = NslKdd.load()
    Xtr, ytr, Xte, yte, _ = encode(ds.train, ds.test)
    fam_te = ds.test["family"].to_numpy()
    benign = yte == 0
    masks = {F: fam_te == F for F in FAMILIES}

    auroc_seen = {F: [] for F in FAMILIES}
    auroc_unk = {F: [] for F in FAMILIES}
    rec_seen = {F: [] for F in FAMILIES}
    rec_unk = {F: [] for F in FAMILIES}

    for seed in range(K):
        tr = ds.train.sample(frac=0.8, random_state=seed)
        Xa, ya, Xb, _, _ = encode(tr, ds.test)
        full = HistGradientBoostingClassifier(random_state=seed).fit(Xa, ya)
        sfull = full.predict_proba(Xb)[:, 1]
        pfull = (sfull >= 0.5).astype(int)
        for F in FAMILIES:
            auroc_seen[F].append(_auroc_benign_vs(sfull, None, masks[F], benign))
            rec_seen[F].append(float(pfull[masks[F]].mean()))
            trh = tr[family_holdout_mask(tr, F)]
            Xh, yh, Xhe, _, _ = encode(trh, ds.test)
            sh = HistGradientBoostingClassifier(random_state=seed).fit(Xh, yh).predict_proba(Xhe)[:, 1]
            auroc_unk[F].append(_auroc_benign_vs(sh, None, masks[F], benign))
            rec_unk[F].append(float((sh[masks[F]] >= 0.5).mean()))
        print(f"seed {seed} done")

    # R2L decomposition on a single fit (argmax vs class-balanced vs per-family FPR operating point)
    full0 = HistGradientBoostingClassifier(random_state=0).fit(Xtr, ytr)
    s0 = full0.predict_proba(Xte)[:, 1]
    bal = HistGradientBoostingClassifier(random_state=0, class_weight="balanced").fit(Xtr, ytr)
    sbal = bal.predict_proba(Xte)[:, 1]
    r2l = masks["R2L"]
    decomp = {
        "r2l_auroc_seen": round(float(np.mean(auroc_seen["R2L"])), 3),
        "r2l_recall_argmax": round(float((s0[r2l] >= 0.5).mean()), 3),
        "r2l_recall_balanced": round(float((sbal[r2l] >= 0.5).mean()), 3),
        "r2l_recall_fpr10": round(_recall_at_benign_fpr(s0, r2l, benign, 0.10), 3),
        "probe_auroc_seen": round(float(np.mean(auroc_seen["Probe"])), 3),
        "probe_recall_argmax": round(float((s0[masks["Probe"]] >= 0.5).mean()), 3),
    }

    # (I4) evaluation-distribution bootstrap of overall accuracy on the fixed test partition
    pred0 = (s0 >= 0.5).astype(int)
    correct0 = (pred0 == yte).astype(float)
    rng = np.random.default_rng(0)
    n = len(correct0)
    boot_acc = np.array([correct0[rng.integers(0, n, n)].mean() for _ in range(B_BOOT)])
    eval_hw = float(1.96 * boot_acc.std())

    flat = {}
    for F in FAMILIES:
        flat[f"pf_auroc_seen_{F}"], hs = round(float(np.mean(auroc_seen[F])), 3), ci(auroc_seen[F])[1]
        flat[f"pf_auroc_unk_{F}"], hu = round(float(np.mean(auroc_unk[F])), 3), ci(auroc_unk[F])[1]
        flat[f"pf_auroc_delta_{F}"] = round(flat[f"pf_auroc_seen_{F}"] - flat[f"pf_auroc_unk_{F}"], 3)
        flat[f"pf_recall_seen_{F}"] = round(float(np.mean(rec_seen[F])), 3)
        flat[f"pf_recall_unk_{F}"] = round(float(np.mean(rec_unk[F])), 3)
    flat.update(decomp)
    flat["pf_auroc_maxhw"] = round(max([ci(auroc_seen[F])[1] for F in FAMILIES]
                                       + [ci(auroc_unk[F])[1] for F in FAMILIES]), 3)
    flat["acc_point"] = round(float(correct0.mean()), 4)
    flat["acc_eval_boot_hw"] = round(eval_hw, 4)             # evaluation-distribution CI half-width
    flat["n_boot"] = B_BOOT
    RES.mkdir(exist_ok=True)
    (RES / "confound.json").write_text(json.dumps(flat, indent=2))
    print("R2L: AUROC(seen)={r2l_auroc_seen}  recall argmax/balanced/fpr10 = "
          "{r2l_recall_argmax}/{r2l_recall_balanced}/{r2l_recall_fpr10}".format(**flat))
    print(f"acc {flat['acc_point']} +/- {eval_hw:.4f} (eval bootstrap, B={B_BOOT})")

    _figure(flat)
    print("wrote results/confound.json + figures/perfamily_auroc.pdf")


def _figure(flat: dict) -> None:
    """I8 figure: per-family AUROC dumbbell, seen -> held-out (unknown). A threshold-free companion to
    the operating-point slopegraph: DoS/Probe stay separable when unknown (small drop); R2L sits near
    chance (0.5) whether seen or not -- the blind spot is in the representation, not the threshold."""
    FIG.mkdir(exist_ok=True)
    from ids_selective import plotstyle as ps
    ps.use()
    order = sorted(FAMILIES, key=lambda F: flat[f"pf_auroc_seen_{F}"])
    y = np.arange(len(order))
    fig, ax = ps.fig(3.3, 2.4)
    ax.axvline(0.5, color=ps.C["grey"], ls="--", lw=0.9, zorder=1)
    ax.text(0.5, len(order) - 0.45, "chance", rotation=90, va="top", ha="right",
            fontsize=6.5, color=ps.C["grey"])
    for i, F in zip(y, order):
        a_seen, a_unk = flat[f"pf_auroc_seen_{F}"], flat[f"pf_auroc_unk_{F}"]
        ax.plot([a_unk, a_seen], [i, i], color=ps.C["grey"], lw=1.4, alpha=0.5, zorder=2)
        ax.scatter(a_seen, i, s=52, color=ps.C["blue"], edgecolor="white", linewidth=0.5, zorder=4,
                   label="family seen in training" if i == 0 else None)
        ax.scatter(a_unk, i, s=52, color=ps.C["vermillion"], edgecolor="white", linewidth=0.5, zorder=4,
                   label="family held out (unknown)" if i == 0 else None)
    ax.set_yticks(y); ax.set_yticklabels(order); ax.set_ylim(-0.5, len(order) - 0.5)
    ax.set_xlim(0.45, 1.02); ax.set_xlabel("per-family detection AUROC (attack score, benign vs. family)")
    ax.tick_params(axis="y", length=0); ax.grid(axis="y", visible=False)
    ax.legend(loc="lower left", fontsize=6.5)
    fig.tight_layout(); fig.savefig(FIG / "perfamily_auroc.pdf"); plt.close(fig)


if __name__ == "__main__":
    main()

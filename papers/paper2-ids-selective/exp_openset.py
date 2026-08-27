"""Paper 2 LOFO open-set: leave-one-family-out, multi-seed.

For each attack family F we remove all of F from training (keeping benign + the other families),
retrain, and measure detection (seen vs. held-out) and the fraction of unknown-F that abstention
rejects at 80% coverage. Over K seeds we resample an 80% train subset and the model seed; table cells
report the mean and the caption the max 95% CI half-width (kept compact to fit the page).
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode, family_holdout_mask
from ids_selective.ci import ci

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
FAMILIES = ["DoS", "Probe", "R2L", "U2R"]  # U2R rare (train 52 / test 67): high variance
K = 10


def fit_predict(train_df, test_df, seed):
    Xtr, ytr, Xte, _, _ = encode(train_df, test_df)
    proba = HistGradientBoostingClassifier(random_state=seed).fit(Xtr, ytr).predict_proba(Xte)
    return proba.argmax(1), proba.max(1)


def main() -> None:
    ds = NslKdd.load()
    fam_test = ds.test["family"].to_numpy()
    seen = {F: [] for F in FAMILIES}
    unseen = {F: [] for F in FAMILIES}
    reject = {F: [] for F in FAMILIES}

    for seed in range(K):
        tr = ds.train.sample(frac=0.8, random_state=seed)
        pred_full, conf_full = fit_predict(tr, ds.test, seed)
        tau = np.quantile(conf_full, 0.20)
        for F in FAMILIES:
            fmask = fam_test == F
            seen[F].append(float((pred_full[fmask] == 1).mean()))
            pred_h, conf_h = fit_predict(tr[family_holdout_mask(tr, F)], ds.test, seed)
            unseen[F].append(float((pred_h[fmask] == 1).mean()))
            reject[F].append(float((conf_h[fmask] < tau).mean()))
        print(f"seed {seed} done")

    flat, hws = {}, []
    for F in FAMILIES:
        for name, vals in (("det_seen", seen[F]), ("det_unseen", unseen[F]), ("reject_unseen", reject[F])):
            m, h = ci(vals)
            flat[f"{name}_{F}"] = round(m, 3)
            hws.append(h)
    flat["openset_maxhw"] = round(max(hws), 3)
    RES.mkdir(exist_ok=True)
    (RES / "openset.json").write_text(json.dumps(flat, indent=2))

    # figure: a slopegraph of the detection collapse. Each family's detection rate when SEEN in
    # training drops to when it is HELD OUT (unknown); the steep DoS/Probe/U2R slopes contrast with
    # R2L, which sits low even when seen -- it mimics benign, so there is little detection to lose.
    FIG.mkdir(exist_ok=True)
    from ids_selective import plotstyle as ps
    ps.use()
    fcol = {"DoS": ps.C["blue"], "Probe": ps.C["green"], "R2L": ps.C["vermillion"], "U2R": ps.C["purple"]}
    fig, ax = ps.fig(3.3, 2.6)
    for F in FAMILIES:
        ms, hs = ci(seen[F]); mu, hu = ci(unseen[F])
        ax.errorbar([0, 1], [ms, mu], yerr=[hs, hu], fmt="none", ecolor=fcol[F],
                    elinewidth=0.8, capsize=2, alpha=0.6, zorder=2)
        ax.plot([0, 1], [ms, mu], "-o", color=fcol[F], ms=5, lw=1.8, zorder=3)
        ax.text(1.05, mu, F, color=fcol[F], va="center", ha="left", fontsize=8, fontweight="bold")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["seen in\ntraining", "held out\n(unknown)"])
    ax.set_xlim(-0.18, 1.34); ax.set_ylim(0, 1)
    ax.set_ylabel("detection rate"); ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(FIG / "openset_detection.pdf"); plt.close(fig)
    print("openset means + max CI half-width", flat["openset_maxhw"])


if __name__ == "__main__":
    main()

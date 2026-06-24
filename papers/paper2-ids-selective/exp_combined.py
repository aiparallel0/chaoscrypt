"""Paper 2 operational recipe, evaluated end-to-end: classifier + abstention + benign-novelty as ONE
gate, on the hardest case (unknown, benign-mimicking R2L held out of training).

The paper recommends stacking three signals; the reviewers noted we never measured the stack. A test
flow is sent for analyst review if ANY gate fires:
  G_clf : the supervised classifier calls it an attack (argmax),
  G_abs : selective-prediction abstention -- max-softmax confidence below the 80%-coverage threshold,
  G_nov : a benign-only Isolation Forest scores it anomalous at a 10% benign false-positive budget.
We report each gate's recall on held-out R2L and the union's recall, against the analyst review load
the union costs on benign traffic. The point: no single gate sees unknown benign-mimicking attacks,
but the union recovers a usable fraction at a bounded review budget. Multi-seed CIs.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode, family_holdout_mask
from ids_selective.ci import ci

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
K = 6
TARGET = "R2L"            # unknown, benign-mimicking family -- the worst case for any single gate


def main() -> None:
    ds = NslKdd.load()
    fam_te = ds.test["family"].to_numpy()
    yte_full = ds.test["y"].to_numpy()
    tgt = fam_te == TARGET

    g = {k: [] for k in ("clf", "abs", "nov", "clf_abs", "union")}
    review = []
    for seed in range(K):
        tr = ds.train.sample(frac=0.8, random_state=seed)
        trh = tr[family_holdout_mask(tr, TARGET)]                  # R2L unknown at train time
        Xh, yh, Xte, _, _ = encode(trh, ds.test)
        clf = HistGradientBoostingClassifier(random_state=seed).fit(Xh, yh)
        p = clf.predict_proba(Xte); conf, pred = p.max(1), p.argmax(1)
        Xtr_all, ytr_all, _, _, _ = encode(tr, ds.test)
        iforest = IsolationForest(n_estimators=200, random_state=seed, n_jobs=-1).fit(Xtr_all[ytr_all == 0])
        anom = -iforest.score_samples(Xte)

        benign = yte_full == 0
        tau_c = np.quantile(conf, 0.20)                            # 80% coverage abstention threshold
        tau_a = np.quantile(anom[benign], 0.90)                    # 10% benign-FPR novelty threshold
        G_clf = pred == 1
        G_abs = conf < tau_c
        G_nov = anom > tau_a
        U = G_clf | G_abs | G_nov
        g["clf"].append(float(G_clf[tgt].mean()))
        g["abs"].append(float(G_abs[tgt].mean()))
        g["nov"].append(float(G_nov[tgt].mean()))
        g["clf_abs"].append(float((G_clf | G_abs)[tgt].mean()))
        g["union"].append(float(U[tgt].mean()))
        review.append(float(U[benign].mean()))                     # analyst load: benign flagged
        print(f"seed {seed}: clf {g['clf'][-1]:.3f} +abs {g['clf_abs'][-1]:.3f} "
              f"+nov(union) {g['union'][-1]:.3f} | benign review {review[-1]:.3f}")

    flat = {}
    for k in g:
        m, h = ci(g[k]); flat[f"comb_recall_{k}"] = round(m, 3); flat[f"comb_recall_{k}_hw"] = round(h, 3)
    m, h = ci(review); flat["comb_benign_review"] = round(m, 3); flat["comb_benign_review_hw"] = round(h, 3)
    flat["comb_target"] = TARGET
    RES.mkdir(exist_ok=True)
    (RES / "combined.json").write_text(json.dumps(flat, indent=2))
    print(f"\nUnion recall on unknown {TARGET}: {flat['comb_recall_union']} "
          f"(clf {flat['comb_recall_clf']} -> +abs {flat['comb_recall_clf_abs']} -> +nov {flat['comb_recall_union']}) "
          f"at {flat['comb_benign_review']} benign review load")

    _figure(flat)
    print("wrote results/combined.json + figures/combined_pipeline.pdf")


def _figure(flat: dict) -> None:
    """A cumulative 'gate-stacking' bar: classifier alone barely sees unknown R2L; adding abstention,
    then benign novelty, lifts the union recall -- the operational case for stacking, in one figure."""
    FIG.mkdir(exist_ok=True)
    from ids_selective import plotstyle as ps
    ps.use()
    stages = [("classifier\nalone", "comb_recall_clf", ps.C["grey"]),
              ("+ abstention", "comb_recall_clf_abs", ps.C["blue"]),
              ("+ benign\nnovelty (union)", "comb_recall_union", ps.C["green"])]
    vals = [flat[k] for _, k, _ in stages]
    hws = [flat["comb_recall_clf_hw"], flat["comb_recall_clf_abs_hw"], flat["comb_recall_union_hw"]]
    cols = [c for _, _, c in stages]
    x = np.arange(len(stages))
    fig, ax = ps.fig(3.3, 2.4)
    ax.bar(x, vals, color=cols, width=0.62, zorder=3)
    ax.errorbar(x, vals, yerr=hws, fmt="none", ecolor=ps.C["black"], elinewidth=0.9, capsize=2.5, zorder=4)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.025, f"{v:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.axhline(flat["comb_benign_review"], color=ps.C["vermillion"], ls="--", lw=1.0, zorder=2)
    ax.text(len(stages) - 0.5, flat["comb_benign_review"] + 0.01,
            f"benign review load {flat['comb_benign_review']:.2f}", ha="right", va="bottom",
            fontsize=6.5, color=ps.C["vermillion"])
    ax.set_xticks(x); ax.set_xticklabels([s for s, _, _ in stages], fontsize=7.5)
    ax.set_ylim(0, max(vals) * 1.25 + 0.05); ax.set_ylabel(f"recall on unknown {flat['comb_target']}")
    ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(FIG / "combined_pipeline.pdf"); plt.close(fig)


if __name__ == "__main__":
    main()

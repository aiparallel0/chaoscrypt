"""Paper 2 operational recipe, re-baselined honestly: classifier vs the stacked gate, AT MATCHED COST.

The earlier version compared the stacked gate (classifier + abstention + benign-novelty) only against the
argmax operating point (recall ~0.003) -- a strawman, since argmax is a terrible threshold for a minority
benign-mimicking family. A budget-matched control (exp_validatefix.py) shows the stack does not beat a
single threshold tuned to the same analyst review load. So we re-baseline: on held-out (unknown) R2L we
report three policies at the SAME realized benign review budget --
  * classifier at the default argmax cut (the naive default),
  * a single global threshold TUNED to that review budget (the "mundane fix"),
  * the full stack: argmax OR abstention OR benign-only novelty.
The honest finding: nearly all the recovery from argmax comes from moving the operating point; the tuned
threshold matches the stack at equal cost, so the novelty stage is not a free win. This supports the
paper's thesis (the contribution is the diagnosis; the fix is an operating point) rather than a new
mechanism. Multi-seed CIs; we report the paired stack-minus-tuned gap.
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
    benign = yte_full == 0

    argmax, tuned, union, review = [], [], [], []
    for seed in range(K):
        tr = ds.train.sample(frac=0.8, random_state=seed)
        trh = tr[family_holdout_mask(tr, TARGET)]                  # R2L unknown at train time
        Xh, yh, Xte, _, _ = encode(trh, ds.test)
        clf = HistGradientBoostingClassifier(random_state=seed).fit(Xh, yh)
        p = clf.predict_proba(Xte); conf, pred = p.max(1), p.argmax(1); s_clf = p[:, 1]
        Xtr_all, ytr_all, _, _, _ = encode(tr, ds.test)
        iforest = IsolationForest(n_estimators=200, random_state=seed, n_jobs=-1).fit(Xtr_all[ytr_all == 0])
        s_nov = -iforest.score_samples(Xte)

        G_clf = pred == 1                                          # argmax default
        G_abs = conf < np.quantile(conf, 0.20)                    # 80%-coverage abstention
        G_nov = s_nov > np.quantile(s_nov[benign], 0.90)          # 10% benign-FPR novelty
        U = G_clf | G_abs | G_nov                                 # the full stack
        b = float(U[benign].mean())                               # realized benign review budget
        tau = np.quantile(s_clf[benign], 1 - b)                   # SINGLE threshold tuned to the SAME budget

        argmax.append(float(G_clf[tgt].mean()))
        union.append(float(U[tgt].mean()))
        tuned.append(float((s_clf[tgt] >= tau).mean()))
        review.append(b)
        print(f"seed {seed}: argmax {argmax[-1]:.3f} | tuned@{b:.3f} {tuned[-1]:.3f} | "
              f"stack {union[-1]:.3f}")

    delta = np.array(union) - np.array(tuned)                     # stack minus tuned threshold (matched cost)
    md, hd = ci(list(delta))
    flat = {"comb_target": TARGET}
    for k, v in (("comb_recall_argmax", argmax), ("comb_recall_tuned", tuned),
                 ("comb_recall_union", union), ("comb_review", review)):
        m, h = ci(v); flat[k] = round(m, 3); flat[k + "_hw"] = round(h, 3)
    flat["comb_delta_union_tuned"] = round(md, 3); flat["comb_delta_union_tuned_hw"] = round(hd, 3)
    flat["comb_stack_beats_tuned"] = bool((md - hd) > 0)
    RES.mkdir(exist_ok=True)
    (RES / "combined.json").write_text(json.dumps(flat, indent=2))
    print(f"\nunknown {TARGET} at matched review {flat['comb_review']}: argmax {flat['comb_recall_argmax']} "
          f"-> tuned {flat['comb_recall_tuned']} -> stack {flat['comb_recall_union']} "
          f"(stack-minus-tuned {md:+.3f} +/- {hd:.3f}; "
          f"{'stack wins' if flat['comb_stack_beats_tuned'] else 'no gain over the tuned threshold'})")

    _figure(flat)
    print("wrote results/combined.json + figures/combined_pipeline.pdf")


def _figure(flat: dict) -> None:
    """Three policies on unknown R2L at the SAME review budget: the naive argmax default, a single
    threshold tuned to that budget, and the full stack. The tuned threshold matches the stack, so the
    recovery is the operating point, not the gates -- the honest re-baseline."""
    FIG.mkdir(exist_ok=True)
    from ids_selective import plotstyle as ps
    ps.use()
    bars = [("classifier\n(argmax default)", "comb_recall_argmax", ps.C["grey"]),
            ("single threshold\ntuned to budget", "comb_recall_tuned", ps.C["blue"]),
            ("full stack\n(+abstain +novelty)", "comb_recall_union", ps.C["green"])]
    vals = [flat[k] for _, k, _ in bars]; hws = [flat[k + "_hw"] for _, k, _ in bars]
    cols = [c for _, _, c in bars]; x = np.arange(len(bars))
    fig, ax = ps.fig(3.3, 2.5)
    ax.bar(x, vals, color=cols, width=0.62, zorder=3)
    ax.errorbar(x, vals, yerr=hws, fmt="none", ecolor=ps.C["black"], elinewidth=0.9, capsize=2.5, zorder=4)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.axhline(flat["comb_review"], color=ps.C["vermillion"], ls="--", lw=1.0, zorder=2)
    ax.text(len(bars) - 0.5, flat["comb_review"] + 0.01,
            f"matched review load {flat['comb_review']:.2f}", ha="right", va="bottom",
            fontsize=6.5, color=ps.C["vermillion"])
    ax.set_xticks(x); ax.set_xticklabels([s for s, _, _ in bars], fontsize=7)
    ax.set_ylim(0, max(vals) * 1.25 + 0.05); ax.set_ylabel(f"recall on unknown {flat['comb_target']}")
    ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(FIG / "combined_pipeline.pdf"); plt.close(fig)


if __name__ == "__main__":
    main()

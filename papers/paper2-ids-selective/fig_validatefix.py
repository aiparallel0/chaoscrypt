"""Validate-the-fix figure: does stacking a benign-only novelty union beat a budget-matched tuned
threshold? At equal analyst review budget (benign FPR), on unknown R2L (NSL-KDD, family held out) and
on cross-corpus Infiltration (CIC-2018), we compare BASE = a single global threshold tuned to the budget
against FIX = classifier-union-novelty. The union beats the tuned threshold in only 1 of 6 budget x
setting cells -- the negative result behind the paper's re-baseline: the lever is the operating point,
not the stack."""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
import sys; sys.path.insert(0, str(HERE.parent.parent / "src"))
from ids_selective import plotstyle as ps

d = json.loads((HERE / "results" / "validatefix.json").read_text())
ps.use()
fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.5))
budgets = [5, 10, 20]
panels = [("nslkdd_r2l", "NSL-KDD: unknown R2L (held out)"), ("cic2018_infil", "CIC-2018: Infiltration (cross-corpus)")]

for ax, (tag, title) in zip(axes, panels):
    base = [d[f"vf_{tag}_b{b}_base"] for b in budgets]
    fix = [d[f"vf_{tag}_b{b}_fix"] for b in budgets]
    dhw = [d[f"vf_{tag}_b{b}_delta_hw"] for b in budgets]
    x = np.arange(len(budgets)); w = 0.36
    ax.bar(x - w / 2, base, w, color=ps.C["blue"], label="tuned threshold", zorder=3)
    ax.bar(x + w / 2, fix, w, color=ps.C["orange"], label="+abstain +novelty (stack)", zorder=3)
    for xi, bb, ff, hw in zip(x, base, fix, dhw):
        dv = ff - bb
        ax.annotate(f"$\\Delta{{=}}{dv:+.2f}$", (xi, max(bb, ff) + 0.03), ha="center", fontsize=6.2,
                    color=(ps.C["green"] if dv > 0 else ps.C["vermillion"]))
    ax.set_xticks(x); ax.set_xticklabels([f"{b}%" for b in budgets])
    ax.set_xlabel("analyst review budget (benign FPR)")
    ax.set_ylim(0, max(max(base), max(fix)) * 1.28 + 0.05)
    ax.set_title(title, fontsize=7.5)
    ax.grid(axis="x", visible=False)
axes[0].set_ylabel("recall on the held-out family")
axes[0].legend(fontsize=6.2, loc="upper left", frameon=False)
fig.suptitle("Validate the fix: the novelty stack does not beat a budget-matched tuned threshold",
             fontsize=8.2, y=1.02)
fig.tight_layout(); fig.savefig(HERE / "figures" / "validatefix.pdf"); plt.close(fig)
print("wrote figures/validatefix.pdf")

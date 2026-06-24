"""Figures for the Plaintext-Keying Capacity (beta) contribution (F1-F6).

beta = log2(N_eff) plaintext-keying bits; rho = invertible-position fraction (the paper's recovery
integrity); q = chosen-plaintext cost. Every figure is grayscale-safe: distinct MARKER SHAPES per verdict
(circle=BROKEN, square=PARTIAL, triangle=fragile-RESISTS, diamond=genuine-RESISTS), shaded bands, no
reliance on colour. Numbers from results/beta.json, beta_curves.json, published_audit.json.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "src"))
from ids_selective import plotstyle as ps

B = json.loads((HERE / "results" / "beta.json").read_text())
CURVES = json.loads((HERE / "results" / "beta_curves.json").read_text())
AUD = {s["scheme"]: s for s in json.loads((HERE / "results" / "published_audit.json").read_text())["schemes"]}
FIG = HERE / "figures"

# verdict -> (marker, facecolor) ; shapes carry the meaning in B/W
MK = {"BROKEN": ("o", ps.C["vermillion"]), "PARTIAL": ("s", ps.C["orange"]),
      "FRAGILE": ("^", ps.C["blue"]), "GENUINE": ("D", ps.C["green"])}


def _legend(ax, loc="lower right", fs=6.0):
    from matplotlib.lines import Line2D
    h = [Line2D([0], [0], marker=m, color="none", markerfacecolor=c, markeredgecolor="k",
                markersize=7, label=l)
         for (m, c), l in zip(MK.values(), ["BROKEN (beta=0)", "PARTIAL (rho<1)",
                                             "fragile RESISTS", "genuine RESISTS"])]
    ax.legend(handles=h, loc=loc, fontsize=fs, frameon=True, framealpha=0.9, handletextpad=0.3)


def f1_phase_plane():
    """F1 (headline): the (beta, rho) phase plane in three bands, every audited scheme placed, with the
    MIEA-PRHM -> Li-DNA dashed arrow showing the two formerly-overlapping points separated along beta."""
    ps.use()
    fig, ax = ps.fig(7.0, 3.6)
    # bands
    ax.axvspan(-3, 1.5, color=ps.C["vermillion"], alpha=0.10, zorder=0)
    ax.axvspan(1.5, 40, color=ps.C["orange"], alpha=0.10, zorder=0)
    ax.axvspan(40, 118, color="0.5", alpha=0.08, hatch="//", zorder=0)
    ax.axvspan(118, 145, color=ps.C["green"], alpha=0.10, zorder=0)
    for x, t in [(-1.5, "beta = 0\nBROKEN"), (20, "0 < beta <~ 40\nfragile (false assurance)"),
                 (79, "lower-bound only\n(saturation)"), (131, "beta >= 128\ncryptographic (RESISTS)")]:
        ax.text(x, 1.085, t, ha="center", va="bottom", fontsize=6.6, fontweight="bold")
    ax.axvline(0, color=ps.C["vermillion"], lw=1.2, ls=":", zorder=1)

    def mark(x, y, verdict):
        m, c = MK[verdict]
        ax.scatter([x], [y], s=85, marker=m, facecolor=c, edgecolor="k", lw=0.7, zorder=5)

    def lab(x, y, tx, ty, t, ha="left", color="k"):
        ax.annotate(t, (x, y), xytext=(tx, ty), fontsize=6.5, ha=ha, va="center", color=color,
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="0.4"), zorder=6)

    # BROKEN cluster at beta=0, rho=1 (cheap) + LSCM-CA + even-multiplier (lossy)
    mark(0, 1.0, "BROKEN"); lab(0, 1.0, 4, 1.10, "LLEO, perm-only, AES-CTR (q=4-5);\nLSCM-CA (q=12, bitlinear)")
    mark(0, 0.515, "PARTIAL"); lab(0, 0.515, 5, 0.515, "even-multiplier (lossy, rho=0.51)")
    # MIEA-PRHM: measured beta = 8 (collision observed)
    mark(float(B["beta_miea"]), 1.0, "FRAGILE")
    lab(float(B["beta_miea"]), 1.0, 12, 0.70, "MIEA-PRHM:  beta=8,\ncollision observed", color=ps.C["blue"])
    # MILE: naive lower-bound beta, collapses to 0 under the seed-block probe
    mark(float(B["beta_mile"]), 0.96, "FRAGILE")
    ax.add_patch(FancyArrowPatch((float(B["beta_mile"]) - 0.5, 0.96), (1.0, 0.985),
                 arrowstyle="-|>", mutation_scale=11, lw=1.1, ls="--", color=ps.C["blue"], zorder=4))
    lab(float(B["beta_mile"]), 0.96, 40, 0.72, "MILE: fix seed block\n-> beta collapses to 0",
        color=ps.C["blue"])
    # Li-DNA: certified lower bound (>=32) extending to structural beta=256 (right arrow)
    xlb = float(B["beta_li"])
    ax.add_patch(FancyArrowPatch((xlb, 1.0), (143, 1.0), arrowstyle="-|>", mutation_scale=11, lw=1.0,
                 color=ps.C["green"], zorder=4))
    mark(125, 1.0, "GENUINE"); lab(125, 1.0, 92, 1.10, "Li-DNA: SHA-256, genuine binding\n"
        "(measured >= %.0f, structural 256)" % xlb, ha="left")
    mark(136, 0.93, "GENUINE"); lab(136, 0.93, 104, 0.80, "SHA-256 + nonce:\nno collision -> beta large",
        ha="left")
    # headline arrow: the two points the old (A,R) plane overlapped
    ax.add_patch(FancyArrowPatch((float(B["beta_miea"]) + 1, 0.965), (118, 0.965), arrowstyle="-|>",
                 mutation_scale=12, lw=1.3, ls="--", color="k", zorder=4))
    ax.text(63, 0.57, "the two points the old (A, R) plane overlapped\nnow separate along beta",
            ha="center", va="center", fontsize=6.8, style="italic",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.6", lw=0.5))

    ax.set_xlim(-4, 146); ax.set_ylim(0.45, 1.17)
    ax.set_xlabel("beta  =  plaintext-keying capacity (bits, PKC)")
    ax.set_ylabel("rho  =  invertible-position fraction")
    ax.set_yticks([0.5, 0.75, 1.0])
    from matplotlib.lines import Line2D
    h = [Line2D([0], [0], marker=m, color="none", markerfacecolor=c, markeredgecolor="k", markersize=7,
                label=l) for (m, c), l in zip(MK.values(),
                ["BROKEN (beta=0)", "PARTIAL (rho<1)", "fragile RESISTS", "genuine RESISTS"])]
    ax.legend(handles=h, loc="center", bbox_to_anchor=(0.60, 0.52), fontsize=6.2, frameon=True,
              framealpha=0.95, labelspacing=0.35, ncol=2, columnspacing=1.0)
    fig.tight_layout(); fig.savefig(FIG / "beta_phase_plane.pdf"); plt.close(fig)


def f2_ladder():
    """F2: the 'how many bits?' 1-D beta ladder with anchors and every audited scheme placed."""
    ps.use()
    fig, ax = ps.fig(7.0, 1.7)
    ax.axvspan(-3, 1.5, color=ps.C["vermillion"], alpha=0.10); ax.axvspan(1.5, 40, color=ps.C["orange"], alpha=0.10)
    ax.axvspan(40, 118, color="0.5", alpha=0.08, hatch="//"); ax.axvspan(118, 150, color=ps.C["green"], alpha=0.10)
    ax.axhline(0, color="k", lw=1.0)
    # the SEEDING MECHANISM ladder: how many plaintext bits each mechanism injects (schemes placed in F1)
    anchors = [(0, "BROKEN", "key-only\nbeta = 0", "right", -2),
               (8, "FRAGILE", "256-way\nscalar\nbeta = 8", "left", 2),
               (64, "GENUINE", "SHA-256[:8]\nstructural 64", "center", 0),
               (128, "GENUINE", "SHA-256\nbeta >= 128", "center", 0)]
    for x, v, t, ha, dx in anchors:
        m, c = MK[v]
        ax.plot([x, x], [0, 0.30], color="0.3", lw=0.8)
        ax.scatter([x], [0], s=80, marker=m, facecolor=c, edgecolor="k", lw=0.6, zorder=5)
        ax.text(x + dx, 0.40, t, ha=ha, va="bottom", fontsize=6.6)
    ax.add_patch(FancyArrowPatch((128, 0), (150, 0), arrowstyle="-|>", mutation_scale=9, lw=0.9,
                 ls=":", color=ps.C["green"]))
    ax.text(75, -0.28, "(each audited scheme is placed on this axis in the phase plane)", ha="center",
            fontsize=6.0, style="italic", color="0.4")
    ax.set_xlim(-10, 152); ax.set_ylim(-0.4, 1.25); ax.set_yticks([])
    ax.set_xlabel("beta  (plaintext-keying bits)")
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "beta_ladder.pdf"); plt.close(fig)


def f3_estimator():
    """F3: the collision estimator schematic -- draw P, P', recover the map from P, test on P', and the
    birthday collapse, with the rule 'collision = fragile / no collision = genuine'."""
    ps.use()
    fig, ax = ps.fig(7.0, 2.7); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 5)

    def box(x, y, w, h, t, fc="white"):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec="k", lw=0.9, zorder=2))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=7, zorder=3)

    def arr(x0, y0, x1, y1, t=None, ls="-"):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11, lw=1.0,
                     ls=ls, color="k", zorder=1))
        if t:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.18, t, ha="center", fontsize=6.3)
    box(0.2, 3.4, 1.7, 0.9, "draw P, P'\n(random)")
    box(2.6, 3.4, 2.2, 0.9, "recover map M\nfrom P (Prop. 2)", ps.C["blue"] + "33" if False else "white")
    box(5.6, 3.4, 2.2, 0.9, "predict C(P')\nwith M")
    arr(1.9, 3.85, 2.6, 3.85); arr(4.8, 3.85, 5.6, 3.85)
    box(5.6, 1.6, 2.2, 1.0, "exact match on\ninvertible positions?")
    arr(6.7, 3.4, 6.7, 2.6)
    box(8.4, 2.55, 1.5, 0.8, "COLLISION\n(same map)", ps.C["orange"] + "44" if False else "white")
    box(8.4, 0.9, 1.5, 0.8, "no collision", "white")
    arr(7.8, 2.3, 8.4, 2.95, "yes"); arr(7.8, 1.9, 8.4, 1.3, "no")
    ax.text(9.15, 3.5, "fragile:\nbeta = -log2(a)", ha="center", fontsize=6.4, color=ps.C["vermillion"])
    ax.text(9.15, 0.55, "genuine:\nbeta >= 2 log2(k)", ha="center", fontsize=6.4, color=ps.C["green"])
    ax.text(5.0, 0.35, "a = map-collision rate over k draws  (birthday: a ~ 1/N_eff,  beta = log2 N_eff)",
            ha="center", fontsize=6.6, style="italic")
    fig.tight_layout(); fig.savefig(FIG / "beta_estimator.pdf"); plt.close(fig)


def f4_collision_curve():
    """F4: collisions-vs-samples (log-log). MIEA accumulates collisions (beta~8); Li-DNA/MILE show none
    within feasible k -- a certified lower bound, the saturation made visual."""
    ps.use()
    fig, ax = ps.fig(4.6, 3.0)
    for tag, lab, m, c in [("miea", "MIEA-PRHM (beta=8)", "^", ps.C["blue"]),
                           ("li", "Li-DNA (SHA-256)", "D", ps.C["green"]),
                           ("mile", "MILE (random probe)", "v", "0.5")]:
        k = np.array(CURVES[tag]["k"], float); col = np.array(CURVES[tag]["collisions"], float)
        exp = k * (k - 1) / 2 / (2 ** 8)                       # expected for an 8-bit seed (reference)
        ax.plot(k[col > 0], col[col > 0], marker=m, ms=3.5, color=c, lw=1.2, label=lab)
        if (col == 0).all():
            ax.plot(k, np.full_like(k, 0.5), marker=m, ms=3, color=c, lw=1.0, ls=":")  # floored at 0 -> show at 0.5
    ax.plot(k, k * (k - 1) / 2 / 256, color="k", lw=0.8, ls="--", label="slope for beta=8 (1/256)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("samples k"); ax.set_ylabel("observed map-collisions (pairs)")
    ax.set_ylim(0.4, None)
    ax.text(2e3, 0.6, "Li-DNA / MILE: 0 collisions ->\ncertified beta >= 2 log2 k", fontsize=6.0, color="0.3")
    ax.legend(fontsize=6.0, loc="upper left", frameon=True)
    fig.tight_layout(); fig.savefig(FIG / "beta_collision_curve.pdf"); plt.close(fig)


def f5_three_axis():
    """F5: the (beta, rho, q) decomposition -- the four corner cases the old single bit conflated."""
    ps.use()
    fig, ax = ps.fig(4.8, 3.0); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    ax.text(5, 5.7, "one bit  ->  three axes", ha="center", fontsize=8, fontweight="bold")
    cases = [
        (0.6, 3.7, "cheap-broken", "beta=0, rho=1, q=4-5", "BROKEN", "LLEO, perm, AES-CTR, LSCM-CA"),
        (5.2, 3.7, "expensive-broken", "beta=0, rho=1, q=256/pos", "BROKEN", "key-only nonlinear S-box"),
        (0.6, 1.0, "lossy-broken", "beta=0, rho=0.51", "PARTIAL", "even-multiplier"),
        (5.2, 1.0, "resistant", "beta large, rho=1", "GENUINE", "SHA-256-seeded (Li-DNA)"),
    ]
    for x, y, title, coord, v, ex in cases:
        m, c = MK[v]
        ax.add_patch(plt.Rectangle((x, y), 4.2, 2.2, fc="white", ec="k", lw=0.9))
        ax.scatter([x + 0.4], [y + 1.75], s=80, marker=m, facecolor=c, edgecolor="k", lw=0.7)
        ax.text(x + 0.8, y + 1.75, title, ha="left", va="center", fontsize=7.2, fontweight="bold")
        ax.text(x + 0.25, y + 1.05, coord, ha="left", fontsize=6.8, family="monospace")
        ax.text(x + 0.25, y + 0.4, ex, ha="left", fontsize=6.2, style="italic", color="0.3")
    ax.text(5, 0.2, "beta: how secure   rho: how completely recovered   q: how cheaply",
            ha="center", fontsize=6.6)
    fig.tight_layout(); fig.savefig(FIG / "beta_three_axis.pdf"); plt.close(fig)


def f6_before_after():
    """F6: the payoff in one figure -- OLD avalanche-vs-R plane (MIEA & Li-DNA overlap) beside the NEW
    beta axis (separated)."""
    ps.use()
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.9))
    # OLD: (A*n, R) -- the two points overlap at (full avalanche, R ~ chance)
    a0 = ax[0]
    for name, m, c, lab in [("MIEA-PRHM (Feng 2024, Mathematics)", "^", ps.C["blue"], "MIEA-PRHM"),
                            ("Li dual-chaotic+DNA (2024, Sci.Rep.)", "D", ps.C["green"], "Li-DNA")]:
        s = AUD[name]
        a0.scatter([s["avalanche_x_n"]], [s["recoverability"]], s=90, marker=m, facecolor=c, edgecolor="k", lw=0.7)
    a0.annotate("MIEA-PRHM and Li-DNA\nOVERLAP here", (16000, 0.004), xytext=(700, 0.18), fontsize=6.6,
                arrowprops=dict(arrowstyle="-|>", lw=0.8))
    a0.set_xscale("log"); a0.set_xlim(0.8, 4e4); a0.set_ylim(-0.05, 1.05)
    a0.set_xlabel("avalanche  A*n"); a0.set_ylabel("recoverability  R")
    a0.set_title("OLD: (A, R) cannot separate them", fontsize=7.5)
    # NEW: beta axis -- separated
    a1 = ax[1]
    a1.axvspan(-3, 1.5, color=ps.C["vermillion"], alpha=0.10); a1.axvspan(1.5, 40, color=ps.C["orange"], alpha=0.10)
    a1.axvspan(40, 150, color=ps.C["green"], alpha=0.08, hatch="//")
    a1.scatter([B["beta_miea"]], [0.5], s=90, marker="^", facecolor=ps.C["blue"], edgecolor="k", lw=0.7)
    a1.scatter([B["beta_li"]], [0.5], s=90, marker="D", facecolor=ps.C["green"], edgecolor="k", lw=0.7)
    a1.add_patch(FancyArrowPatch((B["beta_li"], 0.5), (150, 0.5), arrowstyle="-|>", mutation_scale=9, lw=0.9, color=ps.C["green"]))
    a1.annotate("MIEA-PRHM\nbeta=8 (fragile)", (B["beta_miea"], 0.5), xytext=(B["beta_miea"], 0.78), fontsize=6.4, ha="center")
    a1.annotate("Li-DNA\nbeta>=32 (genuine)", (B["beta_li"], 0.5), xytext=(B["beta_li"] + 5, 0.22), fontsize=6.4)
    a1.set_xlim(-5, 155); a1.set_ylim(0, 1); a1.set_yticks([])
    a1.set_xlabel("beta  (plaintext-keying bits)")
    a1.set_title("NEW: beta separates them", fontsize=7.5)
    fig.tight_layout(); fig.savefig(FIG / "beta_before_after.pdf"); plt.close(fig)


if __name__ == "__main__":
    f1_phase_plane(); f2_ladder(); f3_estimator(); f4_collision_curve(); f5_three_axis(); f6_before_after()
    print("wrote 6 beta figures to figures/")

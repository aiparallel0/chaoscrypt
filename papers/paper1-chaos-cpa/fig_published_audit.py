"""Table-V companion figure: the real-corpus audit in the two signals the oracle measures.

x = avalanche A*n (ciphertext bytes moved by a one-pixel flip; ~1 = no diffusion, ~n = full).
y = recoverability R (held-out exact-prediction rate of the recovered equivalent key; ~1 = broken).
The plane shows where four real 2023-2025 schemes land. LSCM-CA (key-only) sits top-left: no diffusion AND
the key recovers -> BROKEN. The three plaintext-bound schemes sit at R~0. Honest limitation made visible:
Li+DNA (genuine SHA-256-of-image binding) and MIEA-PRHM (a single 256-way plaintext scalar) coincide --
both full-avalanche, both unrecoverable -- so these two signals alone cannot separate strong binding from
a fragile near-miss. MILE shows no diffusion yet resists only because its seed is the first 8x8 block;
the dashed arrow shows it collapsing to a recovered fixed map once that block is held constant.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
import sys; sys.path.insert(0, str(HERE.parent.parent / "src"))
from ids_selective import plotstyle as ps

d = json.loads((HERE / "results" / "published_audit.json").read_text())
S = {s["scheme"]: s for s in d["schemes"]}
ps.use()
fig, ax = ps.fig(3.6, 2.9)

# light quadrant guides
ax.axhline(0.999, color=ps.C["grey"], ls=":", lw=0.9, zorder=1)
ax.text(2.6e4, 1.005, "BROKEN  $R\\geq0.999$", fontsize=6.3, color=ps.C["grey"], va="bottom", ha="right")
ax.axvline(50, color=ps.C["grey"], ls=":", lw=0.7, zorder=1)
ax.text(7, -0.045, "no diffusion", fontsize=6.3, color=ps.C["grey"], ha="center")
ax.text(4e3, -0.045, "full avalanche", fontsize=6.3, color=ps.C["grey"], ha="center")

ann = dict(fontsize=6.7, va="center", arrowprops=dict(arrowstyle="-", lw=0.6, color=ps.C["black"]))

def point(name, col, x, y):
    s = S[name]
    ax.scatter([max(s["avalanche_x_n"], 1.0)], [s["recoverability"]], s=72, color=col,
               edgecolor=ps.C["black"], lw=0.6, zorder=5)
    return max(s["avalanche_x_n"], 1.0), s["recoverability"]

# LSCM-CA: broken fixed map (top-left)
x, y = point("LSCM-CA (Sun 2025, Sci.Rep.)", ps.C["vermillion"], 1, 1)
ax.annotate("LSCM-CA (Sun 2025)\nkey-only fixed map;\nBROKEN via bitlinear, 12 q",
            (x, y), xytext=(3.2, 0.72), color=ps.C["vermillion"], ha="left", **ann)

# MILE: fragile seed block (bottom-left) + collapse arrow
x, y = point("MILE+Q-matrix (Mansour 2025, Sci.Rep.)", ps.C["blue"], 1, 0.004)
ax.annotate("MILE (Mansour 2025)\nno diffusion, but seed =\nfirst 8$\\times$8 block", (x, y),
            xytext=(1.5, 0.30), color=ps.C["blue"], ha="left", **ann)
r_fix = d["fragility"]["recoverability"]
ax.annotate("", xy=(1.0, r_fix), xytext=(1.0, 0.02),
            arrowprops=dict(arrowstyle="->", color=ps.C["blue"], lw=1.1, ls="--"), zorder=4)
ax.scatter([1.0], [r_fix], s=42, marker="D", color=ps.C["blue"], edgecolor=ps.C["black"], lw=0.6, zorder=5)
ax.annotate("fix seed block:\n$R$ 0.004$\\to$1.0 off-block", (1.0, r_fix), xytext=(3.2, 0.97),
            color=ps.C["blue"], ha="left", **ann)

# Li+DNA and MIEA-PRHM coincide at (full avalanche, R~0): the two signals cannot separate them
x1, y1 = point("Li dual-chaotic+DNA (2024, Sci.Rep.)", ps.C["green"], 1, 0.004)
x2, y2 = point("MIEA-PRHM (Feng 2024, Mathematics)", ps.C["orange"], 1, 0.004)
ax.annotate("Li+DNA (2024): genuine\nSHA-256(image) binding", (x1, y1), xytext=(60, 0.52),
            color=ps.C["green"], ha="left", **ann)
ax.annotate("MIEA-PRHM (Feng 2024):\nfragile 256-way scalar", (x2, y2), xytext=(60, 0.30),
            color=ps.C["orange"], ha="left", **ann)
ax.text(1.7e4, 0.135, "signals coincide\n(genuine $\\approx$ near-miss\nhere)", fontsize=5.9,
        color=ps.C["grey"], ha="center", va="top")

ax.set_xscale("log")
ax.set_xlim(0.8, 4e4); ax.set_ylim(-0.06, 1.10)
ax.set_xlabel("avalanche  $A\\cdot n$  (ciphertext bytes moved by a 1-pixel flip)")
ax.set_ylabel("recoverability  $R$")
ax.set_title("Real-corpus audit: four 2023--2025 chaos ciphers", fontsize=8)
fig.tight_layout(); fig.savefig(HERE / "figures" / "published_audit.pdf"); plt.close(fig)
print("wrote figures/published_audit.pdf")

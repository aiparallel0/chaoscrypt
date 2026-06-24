"""Paper 1 generalization: run the black-box structural oracle over a corpus of schemes.

Three outputs:
  (C3) results/oracle_corpus.json + a printed verdict table: for every scheme the avalanche, the
       equivalent-key recoverability on held-out plaintexts, the chosen-plaintext count, and the
       BROKEN/RESISTS verdict -- the oracle never sees a scheme's internals.
  (C4) the invertibility analysis: LLEO's multipliers are 100% odd (units mod 256) BY CONSTRUCTION,
       so E(0)=0 and inversion never hits a 2-to-1 map; the even-multiplier member shows the graceful
       degradation when that gift is removed.
  (C5) figures/oracle_corpus.pdf: a structural-audit panel (recoverability lollipop + avalanche
       regime + query count per scheme).
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from structural_oracle import (CORPUS, run_oracle, recover_structure, lleo_encrypt,
                               even_multiplier_encrypt, MOD)

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
KEY = 0xC0FFEE
SHAPE = (128, 128)            # n = 16384; query count also reported in closed form for 512x512

plt.rcParams.update({
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "font.size": 8, "axes.titlesize": 8,
    "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "legend.frameon": False, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.7,
})
OK_BLUE, OK_VERM, OK_GREEN, OK_GREY, OK_ORANGE = "#0072B2", "#D55E00", "#009E73", "#999999", "#E69F00"


def invertibility_analysis() -> dict:
    """C4: parity of LLEO's multipliers, E(0)=0, and the even-multiplier degradation -- all black-box."""
    enc = lleo_encrypt(KEY, SHAPE)
    n = SHAPE[0] * SHAPE[1]
    rec = recover_structure(enc, n)[0]                      # affine fit; b == 0 (monomial), so a = C(1)
    odd_frac = float(np.mean(rec.a % 2 == 1))               # forced odd by LLEO's _odd_units
    e0 = enc(np.zeros(n, np.uint8))
    e0_is_zero = bool(np.all(e0 == 0))                       # C = K*0 = 0 at every position
    ev = run_oracle(even_multiplier_encrypt(KEY, SHAPE), SHAPE)
    out = {
        "lleo_mult_odd_frac": round(odd_frac, 4),
        "lleo_E0_is_zero": e0_is_zero,
        "even_invertible_frac": round(ev["invertible_frac"], 4),
        "even_recoverability": round(ev["recoverability"], 4),
        "even_verdict": ev["verdict"],
    }
    print(f"[C4] LLEO multipliers odd: {odd_frac:.1%} (units mod 256) | E(0)=0: {e0_is_zero} | "
          f"even-mult variant: invertible {ev['invertible_frac']:.1%}, R={ev['recoverability']:.3f} "
          f"-> {ev['verdict']}")
    return out


def main() -> None:
    RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
    rows = []
    for name, klass, builder in CORPUS:
        o = run_oracle(builder(KEY, SHAPE), SHAPE)
        o["scheme"], o["class"] = name, klass
        rows.append(o)
        print(f"  {name:24s} {klass:15s} det={o['deterministic']!s:5s} "
              f"A*n={o['avalanche_x_n']:7.1f} R={o['recoverability']:.3f} q={o['queries']} "
              f"inv={o['invertible_frac']:.2f} -> {o['verdict']}")

    inv = invertibility_analysis()
    flat = {"shape": list(SHAPE), "n": SHAPE[0] * SHAPE[1], "chance_R": round(1.0 / MOD, 5),
            "schemes": rows, **inv}
    (RES / "oracle_corpus.json").write_text(json.dumps(flat, indent=2))

    # convenient scalars for the paper's \PH{} placeholders. "key-only" (strict) are the realistic
    # published-style schemes; the starred even-multiplier is a deliberate edge-case stress test.
    n_broken = sum(r["verdict"] == "BROKEN" for r in rows)
    keyonly = [r for r in rows if r["class"] == "key-only"]
    n_keyonly_broken = sum(r["verdict"] == "BROKEN" for r in keyonly)
    n_bound_resist = sum(r["verdict"] == "RESISTS" for r in rows if r["class"] in ("plaintext-bound", "nonce-bound"))
    flat_scalars = {
        "oracle_n_schemes": len(rows),
        "oracle_n_broken": n_broken,
        "oracle_n_keyonly": len(keyonly),
        "oracle_n_keyonly_broken": n_keyonly_broken,
        "oracle_n_bound_resist": n_bound_resist,
        "oracle_max_queries": max(r["queries_512sq"] for r in keyonly),
    }
    (RES / "oracle_scalars.json").write_text(json.dumps(flat_scalars, indent=2))

    # flattened per-scheme scalars so the LaTeX table can be filled by scripts/fill_tex.py (no
    # hand-typed numbers; fill_tex ignores the nested "schemes" list above).
    tag = {"LLEO (chaos monomial)": "lleo", "Permutation-only": "perm", "Additive stream (P+K)": "add",
           "Affine (KP+B)": "affine", "AES-CTR key-only": "aes", "Even-multiplier affine": "even",
           "SHA-256(P)-seeded": "sha", "Per-image nonce stream": "nonce"}
    table = {}
    for r in rows:
        t = tag[r["scheme"]]
        table[f"orc_{t}_R"] = round(r["recoverability"], 3)
        table[f"orc_{t}_q"] = r["queries_512sq"]
        table[f"orc_{t}_v"] = r["verdict"]
        table[f"orc_{t}_av"] = "1 px" if r["avalanche_x_n"] < 8 else "$n{-}1$"
    (RES / "oracle_table.json").write_text(json.dumps(table, indent=2))

    _figure(rows)
    print(f"\n[C3] {n_keyonly_broken}/{len(keyonly)} realistic key-only schemes BROKEN at R=1 "
          f"(<= {flat_scalars['oracle_max_queries']} chosen plaintexts at 512^2); even-multiplier "
          f"edge case partial; {n_bound_resist}/2 plaintext/nonce-bound RESIST. "
          f"wrote results/oracle_corpus.json + figures/oracle_corpus.pdf")


def _figure(rows: list) -> None:
    """C5: structural-audit panel. One row per scheme (broken at top), a lollipop for equivalent-key
    recoverability R, the avalanche regime as the marker, and the chosen-plaintext count at the right.
    The visual claim: every key-only scheme lands at R=1 with a 1-pixel-local cipher; binding the
    keystream to the plaintext or a nonce is the only thing that escapes to R~chance."""
    order = sorted(rows, key=lambda r: (r["recoverability"], -r["avalanche"]))   # worst (secure) first
    labels = [r["scheme"] for r in order]
    y = np.arange(len(order))
    vcol = {"BROKEN": OK_VERM, "RESISTS": OK_GREEN}

    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    ax.axvspan(0.999, 1.04, color=OK_VERM, alpha=0.07, zorder=0)        # "broken" band at R=1
    ax.axvline(1.0 / MOD, color=OK_GREY, ls=":", lw=0.9, zorder=1)
    ax.text(1.0 / MOD + 0.012, 0.0, "chance", rotation=90, va="bottom", ha="left",
            fontsize=6, color=OK_GREY)
    from matplotlib.lines import Line2D
    for i, r in zip(y, order):
        c = vcol[r["verdict"]]
        ax.plot([0, r["recoverability"]], [i, i], color=c, lw=1.4, alpha=0.5, zorder=2)
        # marker shape encodes the diffusion regime: circle = 1-pixel-local (no diffusion), square = avalanche
        local = r["avalanche_x_n"] < 8
        ax.scatter(r["recoverability"], i, s=60, marker=("o" if local else "s"),
                   color=c, edgecolor="white", linewidth=0.6, zorder=4)
        ax.text(1.05, i, f"q={r['queries_512sq']}", va="center", ha="left", fontsize=6.5, color="#333")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlim(-0.03, 1.18); ax.set_ylim(-0.6, len(order) - 0.35)
    ax.set_xlabel("equivalent-key recoverability $R$ (held-out ciphertext predicted)")
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(axis="y", length=0)
    for s in ("left", "top", "right"):
        ax.spines[s].set_visible(False)
    # legend: marker shape = diffusion regime; colour = verdict; q = chosen plaintexts at 512^2
    leg = [Line2D([0], [0], marker="o", color="none", markerfacecolor=OK_GREY, markeredgecolor="white",
                  markersize=7, label="1-pixel-local"),
           Line2D([0], [0], marker="s", color="none", markerfacecolor=OK_GREY, markeredgecolor="white",
                  markersize=7, label="avalanche"),
           Line2D([0], [0], marker="o", color="none", markerfacecolor=OK_VERM, markeredgecolor="white",
                  markersize=7, label="broken"),
           Line2D([0], [0], marker="o", color="none", markerfacecolor=OK_GREEN, markeredgecolor="white",
                  markersize=7, label="resists")]
    ax.legend(handles=leg, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, fontsize=6,
              handletextpad=0.15, columnspacing=0.8)
    ax.text(1.16, -0.5, "q: chosen plaintexts at $512^2$", fontsize=5.6, color=OK_GREY,
            ha="right", va="center")
    fig.tight_layout(); fig.savefig(FIG / "oracle_corpus.pdf"); plt.close(fig)


if __name__ == "__main__":
    main()

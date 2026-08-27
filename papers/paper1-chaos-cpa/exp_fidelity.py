"""Reconstruction-fidelity evidence for the real-corpus audit (reviewer ask: show the reconstructions
behave like faithful builds). For each reconstructed scheme we compute, on the standard 512x512 Cameraman
image, the three statistics this literature reports as evidence of security:

  * ciphertext Shannon entropy  (ideal 8.0 bits/pixel),
  * inter-image NPCR             (two unrelated plaintexts; the figure papers report, ideal 99.61%),
  * true 1-pixel-change NPCR     (flip ONE plaintext pixel; the differential metric measured correctly).

The first two should be near-ideal for every reconstruction -- evidence it reproduces the published
statistical profile. The third is the debunk: it is ~99.6% only when the keystream is bound to the whole
plaintext (Li-DNA, MIEA-PRHM), and ~100/MN (=0.000381% at 512^2) when it is not (LSCM-CA key-only; MILE
when the flipped pixel lies outside its 8x8 seed block). Matching entropy/NPCR is necessary, not
sufficient -- which is the paper's own thesis -- so this is fidelity evidence, not a security claim.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from skimage.data import camera

from published_schemes import build_lscm_ca, build_li_dna, build_mile, build_mieaprhm
from chaoscrypt.distinguishers import npcr

HERE = Path(__file__).parent
SHAPE = (512, 512)
KEY = 0xC0FFEE


def entropy(x: np.ndarray) -> float:
    c = np.bincount(np.asarray(x, np.uint8).ravel(), minlength=256)
    p = c[c > 0] / c.sum()
    return float(-(p * np.log2(p)).sum())


def main() -> None:
    n = SHAPE[0] * SHAPE[1]
    P = camera().astype(np.uint8).reshape(-1)                      # 512x512 standard test image
    assert P.size == n, P.size
    rng = np.random.default_rng(7)
    Pu = rng.integers(0, 256, n).astype(np.uint8)                 # an unrelated image
    j = n // 2                                                     # a pixel OUTSIDE MILE's 8x8 seed block
    schemes = [("lscm", build_lscm_ca), ("li", build_li_dna), ("mile", build_mile), ("miea", build_mieaprhm)]
    flat = {"pub_npcr_ideal": 99.61, "pub_npcr_1px_512": f"{100.0 / n:.6f}"}

    def fmt_npcr(v):                                              # small (no diffusion) needs 6 dp; large 2 dp
        return f"{v:.6f}" if v < 1 else f"{v:.2f}"
    for tag, build in schemes:
        enc = build(KEY, SHAPE)
        C = enc(P)
        Pf = P.copy(); Pf[j] ^= 1; Cf = enc(Pf)                   # one-pixel flip
        flat[f"pub_{tag}_ent"] = f"{entropy(C):.3f}"
        flat[f"pub_{tag}_npcr1"] = fmt_npcr(npcr(C, Cf))         # TRUE 1-pixel-change NPCR
        flat[f"pub_{tag}_npcrX"] = f"{npcr(C, enc(Pu)):.2f}"     # inter-image NPCR (what papers report)
        print(f"  {tag:5s} entropy={flat[f'pub_{tag}_ent']}  inter-NPCR={flat[f'pub_{tag}_npcrX']}%  "
              f"1px-NPCR={flat[f'pub_{tag}_npcr1']}%")
    (HERE / "results" / "fidelity.json").write_text(json.dumps(flat, indent=2))
    print("wrote results/fidelity.json")


if __name__ == "__main__":
    main()

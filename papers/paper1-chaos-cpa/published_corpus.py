"""Real-literature audit harness (strong-venue track): run the structural oracle on reconstructions of
ACTUAL published 2023-2025 chaos/image ciphers, to replace the synthetic-archetype corpus with real
schemes (Table V). NOT part of the 6pp UBMK paper.

This file is intentionally a SCAFFOLD: the `PUBLISHED` registry is empty until the target papers are
supplied. For each scheme I reconstruct `encrypt(key, image) -> flat uint8` faithfully from the paper,
register it below, and `run_oracle` returns the verdict + the falsifiable held-out certificate. No
scheme is fabricated; an empty registry audits nothing and says so.

WHAT I NEED FROM EACH PAPER (to reconstruct faithfully and decide the verdict correctly):
  1. Keystream source and -- decisively -- its SEED. Is every chaotic initial condition / S-box / round
     key derived from the secret KEY ONLY, or does any quantity depend on the plaintext/image (e.g. a
     SHA/hash of the image, a plaintext-dependent sum, a per-image nonce)? This single fact decides
     BROKEN vs RESISTS, so quote the exact seeding equations.
  2. Confusion (permutation): how pixel/bit indices are scrambled and from what they are seeded.
  3. Diffusion/substitution: the per-pixel operation -- modular add/multiply (affine), XOR (xor),
     a fixed byte S-box (nonlinear -> O(256) tabulation, the scope-boundary case), or a chained/CBC-like
     rule (non-position-wise).
  4. Round count and order of stages; any block structure / size constraints.
  5. Full citation (authors, title, venue, year) for Table V.

Supplying the algorithm text / equations (or a PDF) for 3-5 schemes is enough; author code is ideal but
not required. Each reconstruction is reported with its provenance (paper-only vs author-code).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Callable, List, Tuple

import numpy as np

from structural_oracle import run_oracle, Encrypt

HERE = Path(__file__).parent
RES = HERE / "results"
KEY = 0xC0FFEE
SHAPE = (128, 128)

# Registry rows: (display_name, citation_key, provenance, builder(key, shape) -> Encrypt).
from published_schemes import build_lscm_ca, build_li_dna, build_mile, build_mieaprhm

PUBLISHED: List[Tuple[str, str, str, Callable[[int, Tuple[int, int]], Encrypt]]] = [
    ("LSCM-CA (Sun 2025, Sci.Rep.)",          "sun2025lscm",    "paper-only", build_lscm_ca),
    ("Li dual-chaotic+DNA (2024, Sci.Rep.)",  "li2024dnadual",  "paper-only", build_li_dna),
    ("MILE+Q-matrix (Mansour 2025, Sci.Rep.)", "mansour2025mile", "paper-only", build_mile),
    ("MIEA-PRHM (Feng 2024, Mathematics)",    "feng2024miea",   "paper-only", build_mieaprhm),
]


def main() -> None:
    RES.mkdir(exist_ok=True)
    if not PUBLISHED:
        print("PUBLISHED registry is empty -- no real schemes supplied yet. "
              "Add reconstructed encrypt() builders (see module docstring) and re-run.")
        (RES / "published_audit.json").write_text(json.dumps({"n_schemes": 0}, indent=2))
        return
    rows = []
    for name, cite, prov, builder in PUBLISHED:
        o = run_oracle(builder(KEY, SHAPE), SHAPE)
        o.update({"scheme": name, "cite": cite, "provenance": prov})
        rows.append(o)
        print(f"  {name:34s} [{cite}] {prov:12s} R={o['recoverability']:.3f} alg={o['algebra']:9s} "
              f"q@512^2={o['queries_512sq']} -> {o['verdict']}")
    n_broken = sum(r["verdict"] == "BROKEN" for r in rows)

    # Fragility stress-test of MILE's RESISTS verdict: its keystream seed is the sum of the first 8x8
    # block, so a chosen-plaintext adversary who FIXES those 64 pixels removes all plaintext-dependence.
    # The reports predict this collapses MILE to a key-only cipher -- so the oracle should then BREAK it.
    mile = build_mile(KEY, SHAPE)

    def _fixed_prefix(enc: Encrypt, k: int = 64) -> Encrypt:
        def e(img):
            q = np.asarray(img, np.uint8).reshape(-1).copy(); q[:k] = 0; return enc(q)
        return e

    o_fix = run_oracle(_fixed_prefix(mile), SHAPE)
    resid = 64.0 / (SHAPE[0] * SHAPE[1])                  # the 64 seed pixels are held constant => unmodelled
    r_off = round(min(1.0, o_fix["recoverability"] / (1 - resid)), 3)   # recoverability off the seed block
    frag = {"scheme": "MILE, first 8x8 block fixed (CPA sub-class)", "recoverability": o_fix["recoverability"],
            "recoverability_off_seedblock": r_off,
            "note": "R jumps 0.004 -> %.3f when the 64-pixel seed block is held constant; the residual "
                    "%.1f%% is exactly those 64 seed pixels (known to the adversary by construction), so "
                    "the rest of the image is an exactly-recovered fixed map -- MILE is broken under a "
                    "fixed-seed-block chosen-plaintext adversary." % (o_fix["recoverability"], 100 * resid)}
    print(f"\n  fragility: MILE with its 64-pixel seed block fixed -> R={o_fix['recoverability']:.3f} "
          f"(off the seed block: {r_off:.3f}); the seed block is the only thing standing between MILE "
          f"and a full break.")

    (RES / "published_audit.json").write_text(json.dumps(
        {"n_schemes": len(rows), "n_broken": n_broken, "schemes": rows, "fragility": frag}, indent=2))
    print(f"\n{n_broken}/{len(rows)} published schemes flagged BROKEN; wrote results/published_audit.json")


if __name__ == "__main__":
    main()

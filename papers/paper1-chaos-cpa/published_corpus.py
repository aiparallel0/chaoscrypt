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

from structural_oracle import run_oracle, Encrypt

HERE = Path(__file__).parent
RES = HERE / "results"
KEY = 0xC0FFEE
SHAPE = (128, 128)

# Registry rows: (display_name, citation_key, provenance, builder(key, shape) -> Encrypt).
# Populated per supplied paper. Example shape of an entry (commented; not a real scheme):
#   ("Author2024 chaotic perm-diffusion", "author2024", "paper-only", _build_author2024),
PUBLISHED: List[Tuple[str, str, str, Callable[[int, Tuple[int, int]], Encrypt]]] = []


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
        print(f"  {name:34s} [{cite}] {prov:12s} R={o['recoverability']:.3f} "
              f"q@512^2={o['queries_512sq']} -> {o['verdict']}")
    n_broken = sum(r["verdict"] == "BROKEN" for r in rows)
    (RES / "published_audit.json").write_text(json.dumps(
        {"n_schemes": len(rows), "n_broken": n_broken, "schemes": rows}, indent=2))
    print(f"\n{n_broken}/{len(rows)} published schemes flagged BROKEN; wrote results/published_audit.json")


if __name__ == "__main__":
    main()

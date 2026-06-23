"""Paper 1 generality: the equivalent-key CPA is not specific to LLEO. It also breaks a structurally
different key-only permutation-diffusion cipher with CBC-like XOR diffusion (the toolkit's canonical
model of a large published class). One effective round is recovered exactly; the construction stays
affine across rounds (so statistics, not round count, are the issue), while a plaintext-hash-seeded
variant of the same structure resists."""
from __future__ import annotations
import json
import time
from pathlib import Path
import numpy as np
from chaoscrypt.ciphers import PermDiffusionCipher, SEED_KEY_ONLY, SEED_PLAINTEXT_HASH
from chaoscrypt.attacks import affine_test, equivalent_key_cpa

HERE = Path(__file__).parent
RES = HERE / "results"
N = 128 * 128


def main() -> None:
    secret = np.random.default_rng(0).integers(0, 256, N, dtype=np.uint8)
    c = PermDiffusionCipher(key=0xBEEF, n=N, rounds=1, seed_mode=SEED_KEY_ONLY)
    t = time.time()
    dec, info = equivalent_key_cpa(c.encrypt, N)
    rec = dec(c.encrypt(secret))
    dt = time.time() - t
    c3 = PermDiffusionCipher(key=0xBEEF, n=N, rounds=3, seed_mode=SEED_KEY_ONLY)
    cdef = PermDiffusionCipher(key=0xBEEF, n=N, rounds=1, seed_mode=SEED_PLAINTEXT_HASH)
    ddef, _ = equivalent_key_cpa(cdef.encrypt, N)
    flat = {
        "gen_cpt": int(info["chosen_plaintexts"]),
        "gen_broken": int(np.array_equal(rec, secret)),
        "gen_s": round(dt, 3),
        "gen_affine_r1": int(affine_test(c.encrypt, N)),
        "gen_affine_r3": int(affine_test(c3.encrypt, N)),
        "gen_defended_broken": int(np.array_equal(ddef(cdef.encrypt(secret)), secret)),
    }
    RES.mkdir(exist_ok=True)
    (RES / "generality.json").write_text(json.dumps(flat, indent=2))
    print(flat)


if __name__ == "__main__":
    main()

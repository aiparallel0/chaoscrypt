"""Chi-square keystream non-uniformity, and the NPCR caveat (high NPCR != CPA-resistant)."""
import os
import numpy as np
from chaoscrypt.ciphers import PermDiffusionCipher, logistic_keystream, SEED_KEY_ONLY
from chaoscrypt.distinguishers import chi_square_uniformity, npcr, uaci, NPCR_IDEAL, UACI_IDEAL

M = 1_000_000
chi_log, p_log = chi_square_uniformity(logistic_keystream(0.4131, M))
chi_rnd, p_rnd = chi_square_uniformity(np.frombuffer(os.urandom(M), dtype=np.uint8))
print(f"logistic keystream  chi2={chi_log:,.0f}  p={p_log:.1e}  (distinguishable from random)")
print(f"os.urandom baseline chi2={chi_rnd:,.0f}  p={p_rnd:.3f}")

N = 64 * 64
c = PermDiffusionCipher(key=0xC0FFEE, n=N, rounds=1, seed_mode=SEED_KEY_ONLY)
img = np.random.default_rng(1).integers(0, 256, N, dtype=np.uint8)
img2 = img.copy(); img2[0] ^= 1
print(f"\nNPCR caveat (key-only cipher): NPCR={npcr(c.encrypt(img), c.encrypt(img2)):.4f}% "
      f"(ideal {NPCR_IDEAL}), UACI={uaci(c.encrypt(img), c.encrypt(img2)):.4f}% (ideal {UACI_IDEAL})")
print("  -> near-ideal NPCR/UACI yet the cipher is fully broken by 02_equivalent_key_cpa.py")

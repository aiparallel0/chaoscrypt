"""Equivalent-key chosen-plaintext attack: recover the key-equivalent and decrypt without the key."""
import numpy as np
from chaoscrypt.ciphers import PermDiffusionCipher, SEED_KEY_ONLY, SEED_PLAINTEXT_HASH
from chaoscrypt.attacks import equivalent_key_cpa

N = 64 * 64
secret = np.random.default_rng(0).integers(0, 256, N, dtype=np.uint8)

c = PermDiffusionCipher(key=0xC0FFEE, n=N, rounds=1, seed_mode=SEED_KEY_ONLY)
decrypt, info = equivalent_key_cpa(c.encrypt, N)
print(f"key-only: chosen plaintexts = {info['chosen_plaintexts']}, "
      f"broken = {np.array_equal(decrypt(c.encrypt(secret)), secret)}")

# Against a plaintext-hash-seeded cipher the recovered keystream is wrong for other images:
c2 = PermDiffusionCipher(key=0xC0FFEE, n=N, rounds=1, seed_mode=SEED_PLAINTEXT_HASH)
d2, _ = equivalent_key_cpa(c2.encrypt, N)
print(f"plaintext-hash: broken = {np.array_equal(d2(c2.encrypt(secret)), secret)}  (resists)")

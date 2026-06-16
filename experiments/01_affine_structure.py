"""Show that a key-only permutation-diffusion cipher is affine over GF(2), across rounds,
while a plaintext-hash-seeded variant is not."""
from chaoscrypt.ciphers import PermDiffusionCipher, SEED_KEY_ONLY, SEED_PLAINTEXT_HASH
from chaoscrypt.attacks import affine_test

N = 64 * 64
print("affine test  E(a)^E(b)^E(0) == E(a^b)")
for rounds in (1, 2, 3, 4):
    c = PermDiffusionCipher(key=12345, n=N, rounds=rounds, seed_mode=SEED_KEY_ONLY)
    print(f"  key-only, rounds={rounds}: affine = {affine_test(c.encrypt, N)}")
c = PermDiffusionCipher(key=12345, n=N, rounds=2, seed_mode=SEED_PLAINTEXT_HASH)
print(f"  plaintext-hash, rounds=2: affine = {affine_test(c.encrypt, N)}  (defended)")

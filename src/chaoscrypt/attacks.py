"""Chosen-plaintext attacks on permutation-diffusion ciphers.

`affine_test` is a structural diagnostic: a True result proves the cipher is a fixed affine map over
GF(2) and is therefore breakable by an equivalent-key chosen-plaintext attack regardless of the number
of rounds. `equivalent_key_cpa` is the concrete attack for the canonical single-effective-round
CBC-like XOR permutation-diffusion structure; adapt it to the target's exact step order if it differs.
"""
from __future__ import annotations
import math
from typing import Callable, Tuple, Dict
import numpy as np


def affine_test(encrypt: Callable[[np.ndarray], np.ndarray], n: int,
                trials: int = 4, seed: int = 0) -> bool:
    """Test E(a) ^ E(b) ^ E(0) == E(a ^ b) on random pairs. True => affine => vulnerable."""
    rng = np.random.default_rng(seed)
    e0 = encrypt(np.zeros(n, dtype=np.uint8))
    for _ in range(trials):
        a = rng.integers(0, 256, n, dtype=np.uint8)
        b = rng.integers(0, 256, n, dtype=np.uint8)
        if not np.array_equal(encrypt(a) ^ encrypt(b) ^ e0, encrypt(a ^ b)):
            return False
    return True


def recover_keystream_chain(encrypt: Callable[[np.ndarray], np.ndarray], n: int) -> np.ndarray:
    """Equivalent keystream for a CBC-like chained XOR cipher from one all-zeros query:
    with p = 0 the permutation maps 0 -> 0, so c0[i] = ks[i] ^ c0[i-1], hence ks[i] = c0[i] ^ c0[i-1]."""
    c0 = encrypt(np.zeros(n, dtype=np.uint8)).astype(np.int64)
    ks = np.empty(n, dtype=np.uint8)
    prev = 0
    for i in range(n):
        ks[i] = int(c0[i]) ^ prev
        prev = int(c0[i])
    return ks


def equivalent_key_cpa(encrypt: Callable[[np.ndarray], np.ndarray], n: int
                       ) -> Tuple[Callable[[np.ndarray], np.ndarray], Dict]:
    """Recover an equivalent key (keystream + permutation) for a CBC-like chained XOR
    permutation-diffusion cipher with a plaintext-independent keystream, and return a
    decrypt(c) that inverts ANY ciphertext under the same key.

    Method (matches the standard 'cancel the basic parts, recover the equivalent key' template):
      1. all-zeros query        -> equivalent keystream ks
      2. ceil(log_256 n) index-digit queries -> the permutation (each pixel carries a digit of its index)
      3. decrypt(c): undo the chain+keystream to get the permuted plaintext, then invert the permutation
    """
    ks = recover_keystream_chain(encrypt, n).astype(np.int64)

    def unchain(c: np.ndarray) -> np.ndarray:
        c = np.asarray(c, dtype=np.int64)
        out = np.empty(n, dtype=np.uint8)
        prev = 0
        for i in range(n):
            out[i] = int(c[i]) ^ int(ks[i]) ^ prev
            prev = int(c[i])
        return out  # == plaintext[permutation]

    n_digits = max(1, math.ceil(math.log(n, 256)))
    perm = np.zeros(n, dtype=np.int64)
    idx = np.arange(n)
    for k in range(n_digits):
        probe = ((idx >> (8 * k)) & 0xFF).astype(np.uint8)
        digits = unchain(encrypt(probe)).astype(np.int64)   # digits[i] = digit_k(perm[i])
        perm |= digits << (8 * k)
    # On a vulnerable (plaintext-independent) cipher this is an exact permutation in [0, n).
    # On a defended cipher the recovered indices are meaningless; reduce mod n so decrypt still
    # runs and simply returns a non-matching image (i.e. the attack reports failure, not a crash).
    perm = (perm % n).astype(np.intp)

    def decrypt(c: np.ndarray) -> np.ndarray:
        permuted = unchain(c)
        x = np.zeros(n, dtype=np.uint8)
        x[perm] = permuted
        return x

    info = {
        "chosen_plaintexts": 1 + n_digits,
        "keystream": ks.astype(np.uint8),
        "permutation": perm,
    }
    return decrypt, info

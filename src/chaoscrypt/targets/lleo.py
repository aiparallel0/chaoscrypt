"""The "LLEO" chaos image cipher (Jain et al., Optik 327:172304, 2025) and its equivalent-key break.

Faithful reconstruction from the published description (docs/TARGET.md), reimplemented from scratch:
a key-only per-position multiplicative substitution (logistic keystream on odd horizontal strips,
Lorenz keystream on even strips) followed by two Fisher-Yates block permutations (16 horizontal, then
16 vertical). Every key element derives from the secret key alone, so encryption is a fixed,
plaintext-independent monomial map over Z_256:  C[j] = K[s[j]] * P[s[j]]  for a fixed source map s and
odd multiplier K.  `break_lleo` recovers (s, K) from a handful of chosen plaintexts and inverts it
without the key.

Reproduction choices where the paper is ambiguous are documented inline. They do not affect the break,
which only assumes plaintext-independence.
"""
from __future__ import annotations
from typing import Callable, Dict, Tuple
import numpy as np

from ..ciphers import logistic_keystream

BLOCKS = 16

# modular inverses mod 256 (odd residues are units; even -> 0, i.e. non-invertible)
_INV256 = np.zeros(256, dtype=np.int64)
for _a in range(1, 256, 2):
    _INV256[_a] = pow(_a, -1, 256)


def lorenz_keystream(n: int, x0: float = 0.1, y0: float = 0.0, z0: float = 0.0,
                     sigma: float = 10.0, rho: float = 28.0, beta: float = 8.0 / 3.0,
                     dt: float = 0.002) -> np.ndarray:
    """RK4 Lorenz keystream; byte = fractional part of x. We use the standard chaotic rho=28; the
    paper's rho=88500 is numerically unstable and atypical, and the keystream source is irrelevant to
    the attack (the cipher is key-only either way)."""
    def f(s):
        x, y, z = s
        return np.array([sigma * (y - x), x * (rho - z) - y, x * y - beta * z])
    s = np.array([x0, y0, z0], dtype=float)
    out = np.empty(n, dtype=np.uint8)
    for i in range(n):
        k1 = f(s); k2 = f(s + dt / 2 * k1); k3 = f(s + dt / 2 * k2); k4 = f(s + dt * k3)
        s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        frac = s[0] - np.floor(s[0])
        out[i] = int(frac * 256) & 0xFF
    return out


def _odd_units(ks: np.ndarray) -> np.ndarray:
    """Force keystream bytes odd so the per-position multiply is invertible mod 256 (the paper
    inverts via 'conj', which requires units)."""
    return (ks.astype(np.uint8) | np.uint8(1))


def _fisher_yates(nblocks: int, rng: np.random.Generator) -> np.ndarray:
    p = np.arange(nblocks)
    for i in range(nblocks - 1, 0, -1):
        j = int(rng.integers(0, i + 1))
        p[i], p[j] = p[j], p[i]
    return p


class LLEOCipher:
    """Reproduction of the LLEO cipher. `encrypt`/`decrypt` operate on flat uint8 arrays of length M*N."""

    def __init__(self, key: int, shape: Tuple[int, int], r: float = 3.99) -> None:
        self.M, self.N = shape
        if self.M % BLOCKS or self.N % BLOCKS:
            raise ValueError("image dimensions must be divisible by 16")
        self.n = self.M * self.N
        x0 = 0.1 + (key % 1000) / 1e4
        log2d = _odd_units(logistic_keystream(x0, self.n, r)).reshape(self.M, self.N)
        lor2d = _odd_units(lorenz_keystream(self.n, x0=0.05 + (key % 997) / 1e4)).reshape(self.M, self.N)
        rows = self.M // BLOCKS
        block_of_row = (np.arange(self.M) // rows)[:, None]          # 0..15 per row
        self.K = np.where(block_of_row % 2 == 1, log2d, lor2d).astype(np.uint8)  # odd strips logistic
        self.hperm = _fisher_yates(BLOCKS, np.random.default_rng(2 * key + 1))
        self.vperm = _fisher_yates(BLOCKS, np.random.default_rng(3 * key + 7))

    @staticmethod
    def _gather_rowblocks(a: np.ndarray, perm: np.ndarray) -> np.ndarray:
        b = np.split(a, BLOCKS, axis=0)
        return np.concatenate([b[perm[i]] for i in range(BLOCKS)], axis=0)

    @staticmethod
    def _gather_colblocks(a: np.ndarray, perm: np.ndarray) -> np.ndarray:
        b = np.split(a, BLOCKS, axis=1)
        return np.concatenate([b[perm[i]] for i in range(BLOCKS)], axis=1)

    def encrypt(self, img: np.ndarray) -> np.ndarray:
        x = np.asarray(img, dtype=np.uint8).reshape(self.M, self.N)
        sub = (x.astype(np.uint16) * self.K) % 256              # per-position multiply
        e1 = self._gather_rowblocks(sub.astype(np.uint8), self.hperm)   # horizontal block shuffle
        e2 = self._gather_colblocks(e1, self.vperm)                     # vertical block shuffle
        return e2.reshape(-1).astype(np.uint8)

    def decrypt(self, cipher: np.ndarray) -> np.ndarray:
        """Legitimate key-based decryption (for reproduction sanity checks)."""
        e2 = np.asarray(cipher, dtype=np.uint8).reshape(self.M, self.N)
        e1 = self._gather_colblocks(e2, np.argsort(self.vperm))
        sub = self._gather_rowblocks(e1, np.argsort(self.hperm))
        kinv = _INV256[self.K]
        x = (sub.astype(np.int64) * kinv) % 256
        return x.reshape(-1).astype(np.uint8)


def break_lleo(encrypt: Callable[[np.ndarray], np.ndarray], shape: Tuple[int, int]
               ) -> Tuple[Callable[[np.ndarray], np.ndarray], Dict]:
    """Equivalent-key chosen-plaintext attack. Recovers the source permutation s and the per-position
    multiplier K (as seen at the output) and returns a key-free `decrypt`.

    Model: C[j] = kk[j] * digit-carrying plaintext at source s[j], with kk[j] = K[s[j]] (odd).
      1. all-ones query              -> kk[j] = C[j]            (multiplier at each output position)
      2. ceil(log_256 n) digit queries -> s[j] (each pixel carries a base-256 digit of its index)
    Chosen plaintexts: 1 + ceil(log_256 n) (= 4 for a 512x512 image)."""
    M, N = shape
    n = M * N
    kk = encrypt(np.ones(n, dtype=np.uint8)).astype(np.int64)       # multiplier at each output pos
    inv = _INV256[kk % 256]                                         # 0 where non-invertible (even)

    n_digits = max(1, int(np.ceil(np.log(n) / np.log(256))))
    idx = np.arange(n)
    s = np.zeros(n, dtype=np.int64)
    for t in range(n_digits):
        probe = ((idx >> (8 * t)) & 0xFF).astype(np.uint8)
        out = encrypt(probe).astype(np.int64)
        digit = (out * inv) % 256                                   # = digit_t(s[j])
        s |= digit << (8 * t)
    s = (s % n).astype(np.intp)

    def decrypt(cipher: np.ndarray) -> np.ndarray:
        c = np.asarray(cipher, dtype=np.int64).reshape(-1)
        plain = np.zeros(n, dtype=np.uint8)
        plain[s] = ((c * inv) % 256).astype(np.uint8)              # invert the multiply + permutation
        return plain

    info = {
        "chosen_plaintexts": 1 + n_digits,
        "source_permutation": s,
        "multiplier": kk.astype(np.uint8),
    }
    return decrypt, info

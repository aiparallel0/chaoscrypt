"""Models of permutation-diffusion ("chaos") image ciphers.

Generic, configurable reconstructions of the permutation-diffusion architecture used by most
chaos-based image-encryption schemes. Reproduce a *published target cipher* from its description
(adapt the maps / step order as needed), then attack it with `chaoscrypt.attacks`.

The seeding mode captures the decisive security distinction:
  SEED_KEY_ONLY       diffusion keystream depends only on the key      -> affine, breakable
  SEED_PIXEL_SUM      keystream seeded by sum(pixels) mod 256          -> weak association, breakable
  SEED_PLAINTEXT_HASH keystream seeded by SHA-256(plaintext)           -> resists equivalent-key CPA
"""
from __future__ import annotations
import hashlib
import numpy as np

SEED_KEY_ONLY = "key_only"
SEED_PIXEL_SUM = "pixel_sum"
SEED_PLAINTEXT_HASH = "plaintext_hash"


def logistic_keystream(x0: float, n: int, r: float = 3.99) -> np.ndarray:
    """Byte keystream from the logistic map x -> r*x*(1-x). Replace with the target's map."""
    x = float(x0)
    out = np.empty(n, dtype=np.uint8)
    for i in range(n):
        x = r * x * (1.0 - x)
        out[i] = int(x * 256) & 0xFF
    return out


def permutation_from_key(key: int, n: int) -> np.ndarray:
    """Key-seeded permutation of n positions. Replace with the target's permutation generator."""
    return np.random.default_rng(key).permutation(n)


class PermDiffusionCipher:
    """A configurable permutation-diffusion cipher.

    Parameters
    ----------
    key : int            secret key (seeds permutation and, in key-only mode, the keystream)
    n : int              number of pixels (flattened image length)
    rounds : int         number of (permute, diffuse) rounds
    seed_mode : str      one of SEED_KEY_ONLY / SEED_PIXEL_SUM / SEED_PLAINTEXT_HASH
    chain : bool         if True use CBC-like diffusion c[i] = x[i] ^ ks[i] ^ c[i-1]; else plain XOR
    r : float            logistic-map parameter
    """

    def __init__(self, key: int, n: int, rounds: int = 1,
                 seed_mode: str = SEED_KEY_ONLY, chain: bool = True, r: float = 3.99) -> None:
        if seed_mode not in (SEED_KEY_ONLY, SEED_PIXEL_SUM, SEED_PLAINTEXT_HASH):
            raise ValueError(f"unknown seed_mode {seed_mode!r}")
        self.key, self.n, self.rounds = key, n, rounds
        self.seed_mode, self.chain, self.r = seed_mode, chain, r
        self.perms = [permutation_from_key(key * 97 + i, n) for i in range(rounds)]

    def _seed(self, round_idx: int, img: np.ndarray) -> float:
        base = 0.1 + 0.0001 * round_idx + (self.key % 1000) / 1e6
        if self.seed_mode == SEED_KEY_ONLY:
            return base
        if self.seed_mode == SEED_PIXEL_SUM:
            return ((base + (int(img.sum()) % 256) / 256.0) % 1.0) * 0.8 + 0.1
        h = int.from_bytes(hashlib.sha256(img.tobytes()).digest(), "big")
        return 0.1 + ((h >> (round_idx * 8)) % 10_000) / 1e5

    def encrypt(self, img: np.ndarray) -> np.ndarray:
        x = np.asarray(img, dtype=np.uint8).copy()
        for d in range(self.rounds):
            ks = logistic_keystream(self._seed(d, img), self.n, self.r)
            x = x[self.perms[d]]                       # confusion
            if self.chain:                             # diffusion (CBC-like)
                c = np.empty(self.n, dtype=np.uint8)
                prev = 0
                for i in range(self.n):
                    c[i] = x[i] ^ int(ks[i]) ^ prev
                    prev = int(c[i])
                x = c
            else:
                x = x ^ ks
        return x

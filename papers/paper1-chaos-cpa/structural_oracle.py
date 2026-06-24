"""Generic black-box structural oracle for image ciphers (Paper 1, generalization).

A single break is an exercise; a test that retires the genre is a contribution. This module turns the
LLEO break into a reusable, black-box decision procedure. Given ONLY an ``encrypt(flat_uint8) ->
flat_uint8`` oracle (no key, no source), it decides whether the cipher is a fixed, plaintext-
independent affine-permutation map

        C[j] = a_j * P[s_j] + b_j   (mod 256)

which is the structural class that EVERY key-only permutation/substitution image cipher collapses to
(monomial, additive/XOR stream, affine, pure permutation, or a key-only AES-CTR stream alike). If it
is, the oracle recovers an equivalent key in a handful of chosen plaintexts and verifies the recovered
key predicts held-out ciphertexts exactly. Two cheap, model-light signals drive the verdict:

  * avalanche A(): the fraction of ciphertext bytes that change when ONE plaintext pixel is flipped.
    A ~ 1/n  <=>  no diffusion -- a one-pixel change stays local. This is the diffusion-free signature
    that the (mis)reported ~99.6% NPCR hides.
  * recoverability R(): after recovering (a, b, s) from 1 + ceil(log_256 n) (b=0) or 2 + ceil(log_256 n)
    chosen plaintexts, the exact-match rate when PREDICTING the ciphertext of fresh random plaintexts.
    R ~ 1  <=>  the equivalent key generalizes, i.e. the scheme is broken.

A construction whose keystream is bound to the plaintext (SHA-256(P)-seeded) or to a fresh per-image
nonce breaks the affine-permutation model: the recovered key fails to predict held-out ciphertext
(R ~ chance) and a one-pixel change avalanches (A ~ 1/2). The oracle therefore separates "key-only,
image-reused keystream" (broken -- chaos or AES, the chaos is irrelevant) from genuinely plaintext/
nonce-bound encryption, across a corpus, with no knowledge of any scheme's internals.
"""
from __future__ import annotations
import hashlib
import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple
import numpy as np

from chaoscrypt.targets import LLEOCipher

MOD = 256
Encrypt = Callable[[np.ndarray], np.ndarray]

# modular inverses mod 256 (odd residues are units; even -> 0, marking a non-invertible multiplier)
_INV = np.zeros(MOD, dtype=np.int64)
for _a in range(1, MOD, 2):
    _INV[_a] = pow(_a, -1, MOD)


def n_digits_for(n: int) -> int:
    """Base-256 digits needed to address n positions = ceil(log_256 n)."""
    return max(1, int(np.ceil(np.log(n) / np.log(MOD))))


@dataclass
class Recovery:
    algebra: str             # "affine" (C = a*P[s]+b mod 256) or "xor" (C = P[s] ^ k)
    a: np.ndarray            # per-output multiplier a_j (affine; all-ones for xor)
    b: np.ndarray            # per-output offset b_j (affine) / key byte k_j (xor); = C(0)
    s: np.ndarray            # source index s_j feeding output j
    invertible: np.ndarray   # bool: position is uniquely decryptable (affine: a_j odd; xor: always)
    queries: int             # minimal chosen plaintexts to break the IDENTIFIED algebra at this n
    monomial: bool           # affine with b == 0 (pure substitution-permutation, no additive term)

    def predict(self, plaintext: np.ndarray) -> np.ndarray:
        """Forward-predict the ciphertext of `plaintext` from the recovered equivalent key."""
        p = np.asarray(plaintext, np.int64).reshape(-1)
        if self.algebra == "xor":
            return (p[self.s].astype(np.uint8) ^ self.b.astype(np.uint8))
        return ((self.a * p[self.s] + self.b) % MOD).astype(np.uint8)


def _recover_one(c0, c1, digit_outs, n, algebra: str) -> Recovery:
    """Fit one position-wise algebra from shared probe outputs (zeros, ones, base-256 digit images)."""
    b = c0 % MOD                                     # affine offset / xor key byte: f_j(0)
    nd = len(digit_outs)
    s = np.zeros(n, np.int64)
    if algebra == "xor":                             # C = P[s] ^ k,  k = C(0)
        a = np.ones(n, np.int64)
        invertible = np.ones(n, bool)                # every xor is a bijection
        monomial = False
        for t, out in enumerate(digit_outs):
            digit = (out.astype(np.int64) ^ b) & 0xFF      # D[s_j] = C[j] ^ k_j
            s |= digit << (8 * t)
        queries = 1 + nd                             # k = C(0), then nd digit images
    else:                                            # affine: C = a*P[s] + b
        a = (c1 - c0) % MOD
        monomial = bool(np.all(b == 0))
        invertible = a % 2 == 1
        inv_a = _INV[a]                              # 0 where a is even
        for t, out in enumerate(digit_outs):
            digit = ((out.astype(np.int64) - b) * inv_a) % MOD   # = digit_t(s_j) where invertible
            s |= digit << (8 * t)
        trivial_a = bool(np.all(a == 1))             # additive stream (a==1) needs no 'ones' probe
        queries = (1 if (monomial or trivial_a) else 2) + nd
    s = (s % n).astype(np.intp)
    return Recovery(algebra=algebra, a=a, b=b, s=s, invertible=invertible, queries=queries,
                    monomial=monomial)


def recover_structure(encrypt: Encrypt, n: int) -> List[Recovery]:
    """Issue the shared probe set once and fit both the affine and xor position-wise models.

    Probes: the all-zeros and all-ones images plus ceil(log_256 n) base-256 digit images (output j of
    a digit image carries digit_t of its source index s_j). The same outputs fit both algebras, so the
    genre -- per-position modular multiply/add (chaos ciphers) OR per-position xor (stream ciphers) --
    is identified with no scheme-specific knowledge."""
    zeros = np.zeros(n, np.uint8)
    ones = np.ones(n, np.uint8)
    c0 = encrypt(zeros).astype(np.int64)
    c1 = encrypt(ones).astype(np.int64)
    idx = np.arange(n)
    nd = n_digits_for(n)
    digit_outs = [encrypt(((idx >> (8 * t)) & 0xFF).astype(np.uint8)) for t in range(nd)]
    return [_recover_one(c0, c1, digit_outs, n, alg) for alg in ("affine", "xor")]


def recoverability(encrypt: Encrypt, n: int, trials: int = 8, seed: int = 0) -> Tuple[float, Recovery]:
    """Best exact ciphertext-prediction rate on fresh random plaintexts over the fitted algebras.

    Returns (R, recovery) for whichever algebra predicts held-out ciphertext best. R ~ 1 means the
    cipher is CPA-broken (a fixed plaintext-independent map); R ~ chance (~1/256) means no fixed
    position-wise map holds (the keystream is not plaintext-independent)."""
    cands = recover_structure(encrypt, n)
    rng = np.random.default_rng(seed)
    probes = [rng.integers(0, MOD, n).astype(np.uint8) for _ in range(trials)]
    truths = [encrypt(p).astype(np.uint8) for p in probes]
    best_R, best = -1.0, cands[0]
    for rec in cands:
        rates = [float(np.mean(t == rec.predict(p))) for p, t in zip(probes, truths)]
        R = float(np.mean(rates))
        if R > best_R:
            best_R, best = R, rec
    return best_R, best


def avalanche(encrypt: Encrypt, n: int, trials: int = 16, seed: int = 1) -> float:
    """Mean fraction of ciphertext bytes that change under a single-pixel plaintext flip.

    ~1/n for a diffusion-free (key-only permutation/substitution) cipher; ~1/2 once a one-pixel change
    propagates (proper diffusion or a plaintext/nonce-bound keystream)."""
    rng = np.random.default_rng(seed)
    fracs = []
    for _ in range(trials):
        p = rng.integers(0, MOD, n).astype(np.uint8)
        q = p.copy()
        j = int(rng.integers(0, n))
        q[j] ^= 1                                    # flip one bit of one pixel
        c0 = encrypt(p).astype(np.int64)
        c1 = encrypt(q).astype(np.int64)
        fracs.append(float(np.mean(c0 != c1)))
    return float(np.mean(fracs))


def is_deterministic(encrypt: Encrypt, n: int, seed: int = 2) -> bool:
    """True if re-encrypting the same plaintext yields the same ciphertext (no per-image nonce)."""
    rng = np.random.default_rng(seed)
    p = rng.integers(0, MOD, n).astype(np.uint8)
    return bool(np.array_equal(encrypt(p), encrypt(p)))


def run_oracle(encrypt: Encrypt, shape: Tuple[int, int], trials: int = 8) -> Dict:
    """Black-box verdict for one cipher. Returns the signals and a BROKEN/RESISTS decision."""
    n = int(shape[0] * shape[1])
    det = is_deterministic(encrypt, n)
    A = avalanche(encrypt, n)
    R, rec = recoverability(encrypt, n, trials=trials)
    inv_frac = float(np.mean(rec.invertible))
    broken = bool(R >= 0.999)                         # equivalent key predicts held-out ciphertext exactly
    overhead = rec.queries - n_digits_for(n)          # structural probes beyond the digit images
    return {
        "n": n,
        "deterministic": det,
        "algebra": rec.algebra,                        # which position-wise group fit: affine or xor
        "avalanche": A,                               # ~1/n if no diffusion
        "avalanche_x_n": A * n,                        # ~1 if a single pixel flip moves a single byte
        "recoverability": R,                           # ~1 if broken
        "queries": rec.queries,                        # chosen plaintexts used at this size
        "queries_512sq": overhead + n_digits_for(512 * 512),
        "invertible_frac": inv_frac,                   # <1 reveals even (non-invertible) multipliers
        "monomial": rec.monomial,
        "plaintext_independent": broken,               # the key generalizes => keystream independent of P
        "verdict": "BROKEN" if broken else "RESISTS",
    }


# --------------------------------------------------------------------------------------------------
# Corpus of reconstructed toy schemes (C2). Each builder returns an encrypt(flat_uint8)->flat_uint8.
# The chaos is deliberately incidental: an "AES-CTR" key-only stream is exactly as broken as LLEO.
# --------------------------------------------------------------------------------------------------

def _prg(key: int, n: int, tag: bytes = b"") -> np.ndarray:
    """Key-only counter-mode byte stream (SHA-256 in CTR -- an AES-CTR stand-in, no extra deps)."""
    out = bytearray()
    ctr = 0
    kb = int(key).to_bytes(8, "big")
    while len(out) < n:
        out += hashlib.sha256(kb + tag + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return np.frombuffer(bytes(out[:n]), np.uint8).copy()


def lleo_encrypt(key: int, shape: Tuple[int, int]) -> Encrypt:
    """LLEO monomial chaos cipher (the published target): C = K * P (mod 256), permuted. b = 0."""
    return LLEOCipher(key, shape).encrypt


def sha_seeded_encrypt(key: int, shape: Tuple[int, int]) -> Encrypt:
    """Defended LLEO: the keystream is reseeded from SHA-256(plaintext) -- plaintext-bound."""
    return LLEOCipher(key, shape, plaintext_seeded=True).encrypt


def permutation_only_encrypt(key: int, shape: Tuple[int, int]) -> Encrypt:
    """Pure key-only pixel permutation: C[j] = P[s[j]]. a = 1, b = 0, s nontrivial."""
    n = shape[0] * shape[1]
    s = np.random.default_rng(int(key) & 0x7FFFFFFF).permutation(n)

    def enc(img: np.ndarray) -> np.ndarray:
        return np.asarray(img, np.uint8).reshape(-1)[s].copy()
    return enc


def additive_stream_encrypt(key: int, shape: Tuple[int, int]) -> Encrypt:
    """Key-only additive (Vigenere-style) stream: C = P + K (mod 256). a = 1, b = K, s = id."""
    n = shape[0] * shape[1]
    k = _prg(key, n, b"add").astype(np.int64)

    def enc(img: np.ndarray) -> np.ndarray:
        return ((np.asarray(img, np.int64).reshape(-1) + k) % MOD).astype(np.uint8)
    return enc


def affine_encrypt(key: int, shape: Tuple[int, int]) -> Encrypt:
    """Key-only affine substitution: C = (Kodd * P + B) (mod 256). a = Kodd, b = B, s = id."""
    n = shape[0] * shape[1]
    k = (_prg(key, n, b"mul").astype(np.int64) | 1)          # force odd -> invertible
    b = _prg(key, n, b"add").astype(np.int64)

    def enc(img: np.ndarray) -> np.ndarray:
        return ((k * np.asarray(img, np.int64).reshape(-1) + b) % MOD).astype(np.uint8)
    return enc


def aes_ctr_keyonly_encrypt(key: int, shape: Tuple[int, int]) -> Encrypt:
    """A modern-looking key-only AES-CTR-style stream, keystream REUSED across images: C = P ^ ks.
    No chaos at all -- and just as broken as LLEO (one known plaintext recovers ks)."""
    n = shape[0] * shape[1]
    ks = _prg(key, n, b"ctr")

    def enc(img: np.ndarray) -> np.ndarray:
        return (np.asarray(img, np.uint8).reshape(-1) ^ ks).astype(np.uint8)
    return enc


def even_multiplier_encrypt(key: int, shape: Tuple[int, int]) -> Encrypt:
    """Affine variant that does NOT force the multiplier odd: ~half the a_j are even (non-invertible).
    Exercises the edge case x |-> a*x being 2-to-1 at even a_j: there both the digit-probe read of s_j
    and the inverse fail, so the oracle degrades gracefully -- invertible_frac and recoverability both
    fall to ~the odd fraction (a quantified PARTIAL break) instead of silently asserting a full one.
    LLEO avoids this entirely by forcing the multiplier odd, which is exactly what makes it 100%
    recoverable; this member shows what an attacker loses without that gift."""
    n = shape[0] * shape[1]
    k = _prg(key, n, b"evenmul").astype(np.int64)            # NOT forced odd
    b = _prg(key, n, b"evenadd").astype(np.int64)

    def enc(img: np.ndarray) -> np.ndarray:
        return ((k * np.asarray(img, np.int64).reshape(-1) + b) % MOD).astype(np.uint8)
    return enc


def nonce_stream_encrypt(key: int, shape: Tuple[int, int]) -> Encrypt:
    """Randomized stream: a fresh per-image nonce seeds the keystream (C = P ^ PRG(key,nonce)).
    Non-deterministic; the affine-permutation model cannot hold across calls."""
    n = shape[0] * shape[1]

    def enc(img: np.ndarray) -> np.ndarray:
        nonce = os.urandom(8)
        ks = _prg(key, n, b"nonce" + nonce)
        return (np.asarray(img, np.uint8).reshape(-1) ^ ks).astype(np.uint8)
    return enc


# ground-truth class for each corpus member (for the results table only; the oracle never sees it)
CORPUS: List[Tuple[str, str, Callable[[int, Tuple[int, int]], Encrypt]]] = [
    ("LLEO (chaos monomial)", "key-only", lleo_encrypt),
    ("Permutation-only", "key-only", permutation_only_encrypt),
    ("Additive stream (P+K)", "key-only", additive_stream_encrypt),
    ("Affine (KP+B)", "key-only", affine_encrypt),
    ("AES-CTR key-only", "key-only", aes_ctr_keyonly_encrypt),
    ("Even-multiplier affine", "key-only*", even_multiplier_encrypt),
    ("SHA-256(P)-seeded", "plaintext-bound", sha_seeded_encrypt),
    ("Per-image nonce stream", "nonce-bound", nonce_stream_encrypt),
]


def _selftest() -> None:
    """Sanity check on the published target: LLEO must be flagged BROKEN with R = 1, A*n ~ 1."""
    shape = (64, 64)
    o = run_oracle(lleo_encrypt(0xC0FFEE, shape), shape)
    assert o["verdict"] == "BROKEN", o
    assert o["recoverability"] > 0.999, o
    assert o["avalanche_x_n"] < 2.0, o
    s = run_oracle(sha_seeded_encrypt(0xC0FFEE, shape), shape)
    assert s["verdict"] == "RESISTS", s
    print("selftest OK:", {k: round(v, 4) if isinstance(v, float) else v for k, v in o.items()})


if __name__ == "__main__":
    _selftest()

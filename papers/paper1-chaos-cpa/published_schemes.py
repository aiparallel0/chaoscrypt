"""Faithful reconstructions of four real 2023-2025 chaos image ciphers, for the structural-oracle audit
(Table V). Each builder returns encrypt(flat_uint8)->flat_uint8 on a single grayscale plane of n pixels;
the oracle supplies the key in the closure and decides BROKEN/RESISTS from a held-out certificate.

We reconstruct the STRUCTURE that the oracle tests -- decisively, the SEEDING (key-only vs plaintext-
bound) and the per-pixel diffusion algebra -- from the equations the three supplied extraction reports
quote. Colour/bit-plane bookkeeping that does not change the structural class is reduced to one plane;
every such reduction is noted. Sources (all open access):

  * LSCM-CA  -- Sun, Yang, Yin, Tian, Li, Deng, "A color image encryption scheme utilizing a logistic-
                sine chaotic map and cellular automata," Scientific Reports 15:21603 (2025).
                doi:10.1038/s41598-025-04968-4. Key-only LSCM keystream + fixed permutation + XOR + a
                per-pixel cellular-automata bit stage (4 iters). Full Algorithm 1-3 pseudocode (HIGH).
  * Li-DNA   -- Li, Liu, Yin, "An encryption algorithm for color images based on an improved dual-chaotic
                system combined with DNA encoding," Scientific Reports 14:20733 (2024).
                doi:10.1038/s41598-024-71267-9. Logistic+Chen seeds = SHA-256 of plaintext sub-regions
                -> plaintext-bound keystream; dynamic DNA add/sub/XOR/XNOR diffusion (HIGH).
  * MILE     -- Mansour, Aboelenin, Eltoukhy, Mohamed, Elkomy, Hosny, "A new medical image encryption
                using modular integrated logistic exponential map and multi-level Q-Sequence matrix,"
                Scientific Reports 15:31383 (2025). doi:10.1038/s41598-025-16343-4. Chaotic seeds =
                sum of the first 8x8 plaintext block -> plaintext-bound (but only via the first 64
                pixels: structurally fragile). XOR + modular-multiply diffusion (MED-HIGH).
  * MIEA-PRHM-- Feng, Yang, Zhao, Qin, Zhang, Zhu, Wen, Qian, "A Novel Multi-Channel Image Encryption
                Algorithm Leveraging Pixel Reorganization and Hyperchaotic Maps," Mathematics 12(24):3917
                (2024). doi:10.3390/math12243917. The hyperchaotic KEYSTREAM is key-only (K = {x0,y0,...});
                plaintext-dependence enters ONLY as an additive term h_sum = sum(V), V from SHA-256 of the
                fused image. A designed "near-miss": key-only keystream + a single plaintext scalar (HIGH).

The decisive per-scheme fact (seeding class) is reproduced exactly; where a paper leaves a constant
unspecified (e.g. LSCM default x0,r,b) we pick a key-derived value -- it does not affect the structural
verdict, which depends on WHETHER the plaintext enters the seed, not on the numeric constant.
"""
from __future__ import annotations
import hashlib
import numpy as np

from structural_oracle import Encrypt, _prg

MOD = 256


# --- LSCM-CA helpers ------------------------------------------------------------------------------

def _lscm_keystream(x0: float, r: float, b: float, n: int) -> np.ndarray:
    """Modified Logistic-Sine Chaotic Map x_{i+1}=sin(r*pi*(1-x_i)*b*x_i), scaled to a byte. KEY-ONLY."""
    x = float(x0)
    out = np.empty(n, np.uint8)
    for i in range(n):
        x = np.sin(r * np.pi * (1.0 - x) * b * x)
        out[i] = int((x * 0.5 + 0.5) * 256.0) & 0xFF           # map [-1,1] -> [0,256)
    return out


def _ca_lut() -> np.ndarray:
    """Per-pixel cellular-automata bit stage as a 256-entry byte LUT (4 iterations). Each iteration is a
    GF(2)-affine bijection on the 8 bits: low bits XOR their neighbour (unit-upper-triangular -> always
    invertible), high four bits complemented. This is the bit-mixing layer the paper applies pixel-wise;
    crucially it is plaintext-INDEPENDENT, so the whole LSCM-CA map is a fixed bijection."""
    bits = ((np.arange(256)[:, None] >> np.arange(8)) & 1).astype(np.uint8)   # [256,8], bit k of x
    for _ in range(4):
        nb = bits.copy()
        nb[:, 0:7] = bits[:, 0:7] ^ bits[:, 1:8]               # XOR neighbour (invertible bit mix)
        nb[:, 4:8] ^= 1                                        # complement high four (affine offset)
        bits = nb
    lut = (bits << np.arange(8)).sum(1).astype(np.uint8)
    assert len(np.unique(lut)) == 256, "CA stage must be a bijection"
    return lut


_CA = _ca_lut()


def build_lscm_ca(key: int, shape) -> Encrypt:
    """KEY-ONLY: C[j] = CA( P[s_j] XOR K_j ). Keystream K and permutation s derive from the key only;
    the plaintext never enters them, so the per-image map is fixed -> the oracle should break it (once
    its model spans the GF(2)-affine CA layer)."""
    n = shape[0] * shape[1]
    rng = np.random.default_rng(int(key) & 0x7FFFFFFF)
    x0, r, b = 0.1 + 0.8 * rng.random(), 0.7 + 0.6 * rng.random(), 0.7 + 0.6 * rng.random()
    K = _lscm_keystream(x0, r, b, n)                           # key-only keystream
    s = rng.permutation(n)                                     # key-only fixed permutation

    def enc(img: np.ndarray) -> np.ndarray:
        p = np.asarray(img, np.uint8).reshape(-1)
        return _CA[(p[s] ^ K)].astype(np.uint8)               # shuffle -> XOR -> CA bit stage
    return enc


# --- plaintext-bound schemes ----------------------------------------------------------------------

def build_li_dna(key: int, shape) -> Encrypt:
    """PLAINTEXT-BOUND (SHA-256). Li et al. seed the improved-logistic and Chen systems from SHA-256 of
    plaintext sub-regions (Eqs. 6-7), so the DNA keystream is a function of the image. We reduce the
    dynamic-DNA add/sub/XOR/XNOR diffusion to a plaintext-seeded byte keystream (the algebra is downstream
    of the decisive fact: a one-pixel change reseeds the whole stream). -> expected RESISTS."""
    n = shape[0] * shape[1]

    def enc(img: np.ndarray) -> np.ndarray:
        p = np.asarray(img, np.uint8).reshape(-1)
        h = hashlib.sha256(p.tobytes()).digest()              # SHA-256 of the plaintext (the seed)
        seed = int(key) ^ int.from_bytes(h[:8], "big")        # key + plaintext-hash -> chaotic seed
        ks = _prg(seed, n, b"li-dna")                         # plaintext-bound keystream
        return (p ^ ks).astype(np.uint8)
    return enc


def build_mile(key: int, shape) -> Encrypt:
    """PLAINTEXT-BOUND but FRAGILE. Mansour et al. seed the MILE map from the SUM of the first 8x8 block
    (x1,x2,u1,u2 = block-group sums), so the keystream depends on the image -- yet only through the first
    64 pixels. -> expected RESISTS, but an adversary who FIXES the first block collapses it to key-only;
    we surface that in the audit notes."""
    n = shape[0] * shape[1]

    def enc(img: np.ndarray) -> np.ndarray:
        p = np.asarray(img, np.uint8).reshape(-1)
        g = p[:64].astype(np.int64)                           # first 8x8 block
        x1, x2, u1, u2 = g[:16].sum(), g[16:32].sum(), g[32:48].sum(), g[48:64].sum()
        seed = (int(key) ^ (x1 << 1) ^ (x2 << 11) ^ (u1 << 21) ^ (u2 << 31)) & 0x7FFFFFFFFFFF
        ks = _prg(seed, n, b"mile")                          # seed depends on first-block sums
        return (p ^ ks).astype(np.uint8)
    return enc


def build_mieaprhm(key: int, shape) -> Encrypt:
    """NEAR-MISS: key-only keystream + a single plaintext SCALAR. Feng et al. keep the hyperchaotic
    matrices key-only (K={x0,y0,...}); the image enters ONLY via h_sum=sum(V), V from SHA-256 of the
    fused image, added to every pixel: C[j] = (P[s_j] + R_j + h_sum) mod 256. The map is NOT a fixed
    plaintext-independent map (h_sum varies per image) -> expected RESISTS -- but the plaintext-dependence
    is one scalar (256-way), so the resistance is structurally fragile; we flag that the oracle certifies
    'not a fixed map', NOT 'cryptographically strong'."""
    n = shape[0] * shape[1]
    rng = np.random.default_rng((int(key) ^ 0x5151) & 0x7FFFFFFF)
    R = _prg(int(key), n, b"miea-R").astype(np.int64)         # key-only additive keystream
    s = rng.permutation(n)                                    # key-only permutation

    def enc(img: np.ndarray) -> np.ndarray:
        p = np.asarray(img, np.int64).reshape(-1)
        h = hashlib.sha256(p.astype(np.uint8).tobytes()).digest()
        h_sum = sum(h) & 0xFF                                 # single plaintext-dependent scalar
        return ((p[s] + R + h_sum) % MOD).astype(np.uint8)
    return enc

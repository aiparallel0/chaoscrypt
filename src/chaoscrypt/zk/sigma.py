"""Prime-order group + Schnorr / Chaum-Pedersen / OR Sigma-protocols (Fiat-Shamir, non-interactive).

Each protocol exposes flags (`bind_commitment`, `bind_context`, `check_challenge_split`) so the
Fiat-Shamir checker can toggle a single transcript element and observe whether soundness breaks.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import secrets


def _miller_rabin(n: int, k: int = 24) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(k):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


@dataclass
class Group:
    """Prime-order subgroup of Z_p* of order q, with two generators g, h (dlog unknown)."""
    p: int
    q: int
    g: int
    h: int

    def rand(self) -> int:
        return secrets.randbelow(self.q - 1) + 1

    def exp(self, base: int, e: int) -> int:
        return pow(base, e % self.q, self.p)

    def mul(self, a: int, b: int) -> int:
        return a * b % self.p

    def hashint(self, *vals) -> int:
        data = b"|".join(str(v).encode() for v in vals)
        return int.from_bytes(hashlib.sha256(data).digest(), "big") % self.q


def make_group(bits: int = 256) -> Group:
    """Generate a safe prime p = 2q+1 and an order-q subgroup with two generators."""
    while True:
        q = secrets.randbits(bits - 1) | (1 << (bits - 2)) | 1
        if _miller_rabin(q) and _miller_rabin(2 * q + 1):
            p = 2 * q + 1
            break
    qr = lambda: pow(secrets.randbelow(p - 2) + 2, 2, p)
    return Group(p=p, q=q, g=qr(), h=qr())


_DEFAULT: Group | None = None


def default_group() -> Group:
    """Lazily generated default group (kept out of import time)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = make_group(256)
    return _DEFAULT


# ---- Schnorr: prove knowledge of x with Y = g^x ----
def schnorr_prove(x: int, G: Group, context: str = "", bind_context: bool = True):
    Y = G.exp(G.g, x)
    k = G.rand()
    T = G.exp(G.g, k)
    c = G.hashint("schnorr", context if bind_context else "", G.g, Y, T)
    s = (k + c * x) % G.q
    return {"Y": Y, "T": T, "c": c, "s": s}


def schnorr_verify(pf, G: Group, context: str = "",
                   bind_commitment: bool = True, bind_context: bool = True) -> bool:
    Y, T, c, s = pf["Y"], pf["T"], pf["c"], pf["s"]
    parts = ["schnorr", context if bind_context else "", G.g, Y] + ([T] if bind_commitment else [])
    if c != G.hashint(*parts):
        return False
    return G.exp(G.g, s) == G.mul(T, G.exp(Y, c))


# ---- OR-proof: prove knowledge of dlog of Y1 OR Y2 ----
def or_prove(known_index: int, x: int, Y1: int, Y2: int, G: Group):
    Ys = [Y1, Y2]
    other = 1 - known_index
    c_o = secrets.randbelow(G.q)
    s_o = secrets.randbelow(G.q)
    T_o = G.mul(G.exp(G.g, s_o), G.exp(Ys[other], (-c_o) % G.q))
    k = G.rand()
    T_k = G.exp(G.g, k)
    T = [None, None]
    T[known_index], T[other] = T_k, T_o
    c = G.hashint("or", G.g, Y1, Y2, T[0], T[1])
    c_k = (c - c_o) % G.q
    s_k = (k + c_k * x) % G.q
    cs, ss = [None, None], [None, None]
    cs[known_index], ss[known_index] = c_k, s_k
    cs[other], ss[other] = c_o, s_o
    return {"T": T, "c": cs, "s": ss}


def or_verify(pf, Y1: int, Y2: int, G: Group, check_challenge_split: bool = True) -> bool:
    T, cs, ss = pf["T"], pf["c"], pf["s"]
    c = G.hashint("or", G.g, Y1, Y2, T[0], T[1])
    if check_challenge_split and (cs[0] + cs[1]) % G.q != c:
        return False
    b0 = G.exp(G.g, ss[0]) == G.mul(T[0], G.exp(Y1, cs[0]))
    b1 = G.exp(G.g, ss[1]) == G.mul(T[1], G.exp(Y2, cs[1]))
    return b0 and b1

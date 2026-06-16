"""Forgery-based Fiat-Shamir completeness checks.

Each check returns a dict reporting whether the *correct* verifier resists a forgery for a FALSE
statement and whether a *weakened* verifier (one transcript element dropped) is forgeable. This is the
kernel of an automated linter: a sound implementation must pass all three.
"""
from __future__ import annotations
import secrets
from . import sigma


def _qr(G):
    return pow(secrets.randbelow(G.p - 2) + 2, 2, G.p)


def check_commitment_binding(G, trials: int = 20000) -> dict:
    """Schnorr: omitting the commitment T from the challenge lets you forge a false statement."""
    Yf = _qr(G)  # random target with unknown discrete log -> false statement
    hits = 0
    for _ in range(trials):
        c = secrets.randbelow(G.q)
        s = secrets.randbelow(G.q)
        T = G.mul(G.exp(G.g, s), G.exp(Yf, (-c) % G.q))
        if sigma.schnorr_verify({"Y": Yf, "T": T, "c": c, "s": s}, G):
            hits += 1
    c_w = G.hashint("schnorr", "", G.g, Yf)            # weak challenge: omits T
    s_w = secrets.randbelow(G.q)
    T_w = G.mul(G.exp(G.g, s_w), G.exp(Yf, (-c_w) % G.q))
    weak_forged = sigma.schnorr_verify(
        {"Y": Yf, "T": T_w, "c": c_w, "s": s_w}, G, bind_commitment=False)
    return {
        "correct_verifier_forgeries": hits,
        "correct_verifier_sound": hits == 0,
        "weak_verifier_forged_false_statement": weak_forged,
    }


def check_challenge_split(G) -> dict:
    """OR-proof: omitting the c1+c2=c check lets you simulate BOTH branches (false OR)."""
    Y1, Y2 = _qr(G), _qr(G)  # prover knows neither discrete log
    c1, s1 = secrets.randbelow(G.q), secrets.randbelow(G.q)
    T1 = G.mul(G.exp(G.g, s1), G.exp(Y1, (-c1) % G.q))
    c2, s2 = secrets.randbelow(G.q), secrets.randbelow(G.q)
    T2 = G.mul(G.exp(G.g, s2), G.exp(Y2, (-c2) % G.q))
    pf = {"T": [T1, T2], "c": [c1, c2], "s": [s1, s2]}
    return {
        "weak_verifier_forged_false_or": sigma.or_verify(pf, Y1, Y2, G, check_challenge_split=False),
        "correct_verifier_sound": not sigma.or_verify(pf, Y1, Y2, G, check_challenge_split=True),
    }


def check_context_binding(G) -> dict:
    """Schnorr: omitting the context/domain lets a proof replay across domains."""
    x = G.rand()
    bound = sigma.schnorr_prove(x, G, context="login", bind_context=True)
    replay_bound = sigma.schnorr_verify(bound, G, context="admin", bind_context=True)
    unbound = sigma.schnorr_prove(x, G, context="login", bind_context=False)
    replay_unbound = sigma.schnorr_verify(unbound, G, context="admin", bind_context=False)
    return {
        "context_bound_proof_rejected_in_other_domain": not replay_bound,
        "context_unbound_proof_replays": replay_unbound,
    }


def run_all(G=None) -> dict:
    """Run the three completeness checks against a group (default: a fresh 256-bit group)."""
    G = G or sigma.default_group()
    return {
        "commitment_binding": check_commitment_binding(G),
        "challenge_split": check_challenge_split(G),
        "context_binding": check_context_binding(G),
    }

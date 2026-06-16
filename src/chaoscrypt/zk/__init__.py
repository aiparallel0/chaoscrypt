"""Secondary module: Sigma-protocol NIZKs and a Fiat-Shamir completeness checker.

Fallback project: an automated check that a Sigma/Fiat-Shamir implementation binds all public values.
A complete transcript must hash (a) the statement/context, (b) every prover commitment, and (c) for
compound (OR) proofs, enforce the challenge split. Omitting any of these is the publicly documented
"weak Fiat-Shamir" / Frozen-Heart vulnerability class (see docs/RESEARCH_NOTES.md).
"""
from .sigma import make_group, default_group, Group
from . import sigma, fiat_shamir

__all__ = ["make_group", "default_group", "Group", "sigma", "fiat_shamir"]

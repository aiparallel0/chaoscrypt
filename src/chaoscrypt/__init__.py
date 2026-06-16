"""chaoscrypt: cryptanalysis of permutation-diffusion image ciphers + a ZK Fiat-Shamir module."""
from .ciphers import (
    PermDiffusionCipher,
    logistic_keystream,
    permutation_from_key,
    SEED_KEY_ONLY,
    SEED_PIXEL_SUM,
    SEED_PLAINTEXT_HASH,
)
from .attacks import affine_test, equivalent_key_cpa, recover_keystream_chain
from .distinguishers import chi_square_uniformity, npcr, uaci, NPCR_IDEAL, UACI_IDEAL

__all__ = [
    "PermDiffusionCipher", "logistic_keystream", "permutation_from_key",
    "SEED_KEY_ONLY", "SEED_PIXEL_SUM", "SEED_PLAINTEXT_HASH",
    "affine_test", "equivalent_key_cpa", "recover_keystream_chain",
    "chi_square_uniformity", "npcr", "uaci", "NPCR_IDEAL", "UACI_IDEAL",
]
__version__ = "0.1.0"

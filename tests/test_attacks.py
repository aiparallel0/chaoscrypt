import numpy as np
import pytest
from chaoscrypt.ciphers import PermDiffusionCipher, logistic_keystream, SEED_KEY_ONLY, SEED_PLAINTEXT_HASH
from chaoscrypt.attacks import affine_test, equivalent_key_cpa
from chaoscrypt.distinguishers import chi_square_uniformity

N = 32 * 32


def test_key_only_is_affine():
    for rounds in (1, 2, 3):
        c = PermDiffusionCipher(key=7, n=N, rounds=rounds, seed_mode=SEED_KEY_ONLY)
        assert affine_test(c.encrypt, N) is True


def test_plaintext_hash_is_not_affine():
    c = PermDiffusionCipher(key=7, n=N, rounds=2, seed_mode=SEED_PLAINTEXT_HASH)
    assert affine_test(c.encrypt, N) is False


def test_equivalent_key_cpa_breaks_key_only():
    c = PermDiffusionCipher(key=0xABCDEF, n=N, rounds=1, seed_mode=SEED_KEY_ONLY)
    decrypt, info = equivalent_key_cpa(c.encrypt, N)
    assert info["chosen_plaintexts"] <= 4
    secret = np.random.default_rng(3).integers(0, 256, N, dtype=np.uint8)
    assert np.array_equal(decrypt(c.encrypt(secret)), secret)


def test_chi_square_flags_logistic_but_not_uniform():
    import os
    _, p_log = chi_square_uniformity(logistic_keystream(0.31, 200_000))
    _, p_rnd = chi_square_uniformity(np.frombuffer(os.urandom(200_000), dtype=np.uint8))
    assert p_log < 1e-3
    assert p_rnd > 1e-3

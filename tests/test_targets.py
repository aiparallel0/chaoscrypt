import numpy as np
from chaoscrypt.targets import LLEOCipher, break_lleo


def test_lleo_key_roundtrip():
    M = N = 64
    img = np.random.default_rng(1).integers(0, 256, M * N, dtype=np.uint8)
    c = LLEOCipher(7, (M, N))
    assert np.array_equal(c.decrypt(c.encrypt(img)), img)


def test_lleo_broken_by_equivalent_key_cpa():
    M = N = 64
    c = LLEOCipher(0xABCDEF, (M, N))
    decrypt, info = break_lleo(c.encrypt, (M, N))
    assert info["chosen_plaintexts"] <= 3  # 1 + ceil(log_256 4096)
    secret = np.random.default_rng(2).integers(0, 256, M * N, dtype=np.uint8)
    assert np.array_equal(decrypt(c.encrypt(secret)), secret)  # pixel-exact, no key

from chaoscrypt.zk import make_group
from chaoscrypt.zk import fiat_shamir, sigma


def test_fiat_shamir_completeness():
    G = make_group(192)  # smaller for test speed
    r = fiat_shamir.run_all(G)
    assert r["commitment_binding"]["correct_verifier_sound"]
    assert r["commitment_binding"]["weak_verifier_forged_false_statement"]
    assert r["challenge_split"]["correct_verifier_sound"]
    assert r["challenge_split"]["weak_verifier_forged_false_or"]
    assert r["context_binding"]["context_bound_proof_rejected_in_other_domain"]
    assert r["context_binding"]["context_unbound_proof_replays"]


def test_honest_schnorr_verifies():
    G = make_group(192)
    pf = sigma.schnorr_prove(G.rand(), G)
    assert sigma.schnorr_verify(pf, G)

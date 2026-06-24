# Strong-venue track — formal characterization of the structural oracle

> NOT part of the 6-page UBMK submission. This is the "cheap formal theorem" for a longer
> (SoK/tool-paper) version. It states what the oracle decides, with soundness, query complexity,
> the completeness boundary, and the nonlinear-substitution scope limit. No new experiments needed.

## Model

An encryption oracle `Enc : Z_256^n -> Z_256^n` (deterministic, fixed unknown key) is **position-wise**
if there is a fixed permutation `s : [n] -> [n]` and fixed per-position bijections `f_j` on `Z_256` with

    Enc(P)[j] = f_j( P[s(j)] )   for all plaintexts P and all output positions j.

Two sub-classes the oracle fits:
- **Affine-permutation:** `f_j(x) = a_j*x + b_j (mod 256)` with `a_j` a unit (odd).
- **XOR-permutation:** `f_j(x) = x XOR k_j`.

Both subsume the chaos-image-cipher genre (per-position modular multiply/add then permute) and key-only
XOR-diffusion stream ciphers.

## Proposition 1 (Soundness and query complexity)

For a position-wise affine-permutation cipher with every `a_j` a unit mod 256, the oracle recovers
`(a_j, b_j, s)` **exactly** from the chosen plaintexts `{ 0, 1, D_0, ..., D_{m-1} }`, where
`m = ceil(log_256 n)` and `D_t[i]` is the t-th base-256 digit of index `i`. The recovered triple is an
equivalent key (decrypts every ciphertext), at a cost of `1 + m` chosen plaintexts when `b = 0`
(monomial) and `2 + m` in general. The XOR class is identical with `k_j = Enc(0)[j]`.

*Proof.* `Enc(0)[j] = a_j*0 + b_j = b_j`. `Enc(1)[j] - b_j = a_j`. Since `a_j` is a unit, `a_j^{-1}`
exists; for digit image `D_t`, `(Enc(D_t)[j] - b_j) * a_j^{-1} = digit_t(s(j))`. Concatenating the `m`
digits determines `s(j) in [n]` uniquely because `n <= 256^m`. Then `X[s(j)] = a_j^{-1}(C[j] - b_j)`
inverts any `C`. (XOR: replace `-` by `XOR`, `a_j^{-1}` by identity; `f_j` is always a bijection, so
`invertible_frac = 1`.) ∎

The `1 + m` bound is order-optimal: it matches Li and Lo's lower bound `ceil(log_L n)` for
permutation-only recovery (`L = 256`), so the additive structural probe is the only overhead.

## Proposition 2 (Held-out certificate => equivalent key; verdict correctness)

Let `M̂` be the recovered fixed model and run it on `t` independent uniform-random plaintexts.

(a) **Sound on the class.** If `Enc` is position-wise affine/XOR and `M̂` predicts all `t` ciphertexts
exactly, then `M̂ = Enc` everywhere: the `t` probes pin each `a_j` (>=2 distinct values at coordinate
`s(j)` w.h.p.) and the digit probes pin `s`, so `R = 1` certifies a true equivalent key.

(b) **Correct RESISTS.** If the keystream depends on the plaintext (there exist `P, P'` for which the
per-position maps differ), no fixed position-wise model predicts all plaintexts; the held-out rate
`R < 1`, and `R -> 1/256` per byte (chance) when the dependence is via a cryptographic hash or a fresh
nonce. Hence the oracle's `RESISTS` verdict is correct for plaintext-bound and nonce-bound
constructions; its `BROKEN` verdict carries the falsifiable certificate of (a).

This is the formal content of the paper's "reconstruction fidelity is falsifiable" argument: a faithful
reconstruction of a key-only cipher yields `R = 1`; any plaintext/nonce binding yields `R ~ chance`.

## Scope limit (the boundary the cheap-query result does NOT cross)

A key-only but **nonlinear** per-position substitution `Enc(P)[j] = S( P[s(j)] )` for a fixed byte
S-box `S` is position-wise and plaintext-independent — hence *structurally* broken — but `S` is neither
affine nor XOR. Recovering `S` requires tabulating all `L = 256` input values: feeding the `L` constant
images `{ v * 1 : v in 0..255 }` reads `S` at every position simultaneously, then `m` digit images
recover `s`. Cost: `L + m = 256 + ceil(log_256 n)` chosen plaintexts — **outside the logarithmic-query
regime**. The affine/XOR oracle returns `R < 1` on such a cipher (model misspecification), correctly
declining to claim a cheap break.

**Corollary (decision boundary).** The oracle *decides* membership in the affine/XOR position-wise class
and, on a YES, returns an equivalent key in `O(log_256 n)` queries with a machine-checkable certificate.
Key-only nonlinear-substitution ciphers are a strictly larger, still-broken class reachable by an
`O(256 + log_256 n)` tabulation fallback (implementation: future work — the "PREFERRED (a)" option in the
review note).

# Target cipher — "LLEO" (Jain et al., Optik 2025)

**Citation.** S. Jain, A. Samal, A. Sharma, M. Khurana, B. Sharma, "Advanced image security through
chaotic system-based encryption and Fisher–Yates matrix shuffling," *Optik* 327:172304 (2025),
DOI 10.1016/j.ijleo.2025.172304. (Authoritative source read from the publisher PDF; algorithm
restated here in our own words — no text copied.)

## Algorithm (grayscale image `I`, size M×N)
Effectively **one round** of *substitute → permute → permute*, all key-derived:

1. **Block split.** Divide `I` horizontally into 16 strips `a0..a15`.
2. **Substitution (key-only).** Odd strips `a1,a3,…,a15` are multiplied by `klogistic`; even strips
   `a0,a2,…,a14` by `klorenz` (Eq. 6: `arrodd = arrodd * klogistic`, `arreven = arreven * klorenz`).
   `klogistic`/`klorenz` are pseudo-random sequences from the **logistic map** `x_{n+1}=r·x_n(1−x_n)`
   (Eq. 1) and the **Lorenz system** (Eqs. 2–4; σ=10, ρ=88500, β=8/3) whose initial conditions are
   the **secret key**. Decryption multiplies by `conj(d1)`/`conj(d2)` (Eq. 13) ⇒ the operation is an
   invertible modular multiply.
3. **Permutation 1.** Fisher–Yates shuffle of the 16 horizontal strips → `E1` (Eq. 7).
4. **Permutation 2.** Split `E1` vertically into 16 strips, Fisher–Yates shuffle → `E2` (Eq. 8).
5. **Keys (4).** `d1=klogistic`, `d2=klorenz`, `d3`=vertical-shuffle index list, `d4`=horizontal-shuffle
   index list. Decryption (Eqs. 10–14): inverse vertical shuffle, inverse horizontal shuffle, multiply
   by key inverses.

## Decisive property — VULNERABLE (key-only)
The keystreams (`klogistic`, `klorenz`) and both permutations (`d3`, `d4`) are functions of the
**secret key only**. There is **no hash, no plaintext feedback, no plaintext-dependent seeding**
anywhere in the paper (verified: zero occurrences of "hash"/"SHA"/"message digest"/"sum of pixels").
Hence `E` is a **fixed, plaintext-independent bijection** ⇒ recoverable by an equivalent-key
chosen-plaintext attack and invertible without the key.

## Two structural weaknesses to exploit / highlight
1. **No diffusion.** Each ciphertext pixel depends on exactly one plaintext pixel (per-position
   multiply) relocated by block shuffles. A one-pixel plaintext change alters exactly **one**
   ciphertext pixel ⇒ the *true* one-pixel-differential NPCR is `100/(M·N)` ≈ **0.0004%** for 512×512,
   not the **99.6%** reported (Table 4 / Eq. 18). The near-ideal NPCR cannot reflect genuine
   differential/CPA resistance — it must be measured against unrelated images, not a one-pixel change.
2. **"Asymmetric" misnomer.** The same keys `d1..d4` encrypt and decrypt; there is no public/private
   keypair. The repeated "asymmetric" claim is unjustified.

## Attack plan (equivalent-key CPA)
The map is a fixed permutation of positions composed with a fixed per-position invertible value map.
- Recover the composed position permutation with index-marker chosen plaintexts.
- Recover the per-position multiplier (equivalent keystream) with constant-value chosen plaintexts
  (a multiplicative analogue of `recover_keystream_chain`; modular inverse for decryption).
- Decrypt any ciphertext, pixel-exact, with **no key** and O(1) chosen plaintexts.
Confirm `affine_test`-style structure (linear over Z_256), then specialize the toolkit's
`equivalent_key_cpa` to this multiply+block-permutation structure in `src/chaoscrypt/targets/lleo.py`.

## Reported metrics to reproduce/contrast
Entropy: Cameraman 7.99664, Lena 7.99929, Bridge 7.99844, Man 7.99981 (ideal 8). NPCR: 99.61–99.64%
(we will show this is not a true one-pixel differential). **No UACI reported.** Correlation/PSNR/MSE
given in Table 6. Standard test images (Cameraman, Lena, Bridge, Man), grayscale.

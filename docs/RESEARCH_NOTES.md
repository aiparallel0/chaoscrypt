# Research notes — target selection and methodology

These notes turn the toolkit into a paper. The viable deliverable is a single short IEEE-format
paper that **breaks a specific published chaos image cipher** with a chosen-plaintext equivalent-key
attack. The secondary (fallback) project is a Fiat–Shamir-completeness audit; everything else
(commitment/auction constructions, anonymous-token reimplementations) is a reproduction of known
results and is out of scope.

> Target venue assumed: a regional IEEE-indexed conference (≈6-page IEEE template, similarity < 25%,
> AI-use must be declared as a separate upload). **Verify the current CFP, host, page limit, template,
> similarity threshold and deadline on the official site before submitting.**

---

## 1. The decisive vulnerability criterion

A permutation–diffusion cipher is **breakable by an equivalent-key chosen-plaintext attack iff its
diffusion keystream does not depend on the plaintext (or depends only weakly).** Concretely:

| Keystream / initial-condition seed | Status | Why |
|---|---|---|
| key only (chaotic initial conditions from the key) | **VULNERABLE** | cipher is affine over GF(2); recover keystream + permutation from a handful of chosen plaintexts |
| weak statistic, e.g. `sum(pixels) mod 256` | **VULNERABLE** | only 256 reachable seeds; build a codebook / use keystream reuse across equal-sum images |
| `SHA-256/512(plaintext)` (full-image hash) | **DEFENDED** | fresh unpredictable keystream per image; equivalent-key CPA fails |
| ciphertext-chaining fed back per image ("dynamic diffusion") | **DEFENDED** | keystream effectively plaintext-dependent |

The single go/no-go question for any candidate target: **what seeds the diffusion keystream?** Read the
diffusion equation in the target paper; if it is key-only or a weak statistic, it is a target.

Caveat to pre-empt in the paper: near-ideal differential metrics do **not** imply CPA resistance. For an
8-bit image the ideal NPCR / UACI are **99.6094% / 33.4635%**, but a fixed key-only keystream with a
diffusion chain still propagates a one-pixel change and yields near-ideal NPCR while remaining fully
breakable. Demonstrate this explicitly (see `experiments/03_keystream_distinguisher.py`).

---

## 2. Candidate target ciphers (2024–2025)

Confirm the diffusion seed from the **full text** before committing, and confirm **no published
cryptanalysis already exists** (search the title and the authors).

Likely **DEFENDED** (do not target — seeded from a plaintext hash):
- "A lightweight multi-round confusion–diffusion cryptosystem … modified 5D chaotic system,"
  *Scientific Reports* 15:31986 (2025), DOI 10.1038/s41598-025-13290-y — states/parameters from
  **SHA-512 of the input image**.
- "A novel image encryption scheme using 3D chaotic maps with Josephus permutation and dynamic
  diffusion," *J. King Saud Univ. – CIS* 37:254 (2025), DOI 10.1007/s44443-025-00284-z — initial
  conditions and diffusion params from **SHA-256 of the plaintext**.
- "A high-entropy image encryption scheme … optimized chaotic maps with Josephus permutation,"
  *Scientific Reports* 15:29439 (2025), DOI 10.1038/s41598-025-14784-5 — 256-bit seed mixes the key
  with the plaintext via **MD5 + SHA-256**.

**Primary candidate (verify the diffusion seed):**
- "Advanced image security through chaotic system-based encryption and Fisher–Yates matrix shuffling,"
  *Optik* 327:172304 (2025), DOI 10.1016/j.ijleo.2025.172304 — Lorenz-driven Fisher–Yates permutation +
  chaotic diffusion. The accessible text shows **no plaintext hash** for the diffusion keystream,
  suggesting a key-only (vulnerable) structure. Confirm from the full PDF.

**Borderline (check whether the hash is seeded by plaintext or key):**
- "Combined Interleaved Pattern to Improve Confusion–Diffusion Image Encryption Based on Hyperchaotic
  System," *IEEE Access* 11:69005–69021 (2023), DOI 10.1109/ACCESS.2023.3294934.

Keep a shortlist of 2–3 backups meeting the criterion so a single defended target does not stall the timeline.

---

## 3. Canonical literature to cite

Equivalent-key chosen-plaintext attack (the established methodology):
- C. Li, Y. Zhang, E. Y. Xie, "When an attacker meets a cipher-image in 2018: a year in review,"
  *J. Information Security and Applications* 48:102361, 2019.
- C. Li, D. Lin, B. Feng, J. Lü, F. Hao, "Cryptanalysis of a Chaotic Image Encryption Algorithm Based on
  Information Entropy," *IEEE Access* 6:75834–75842, 2018 (arXiv:1803.10024).
- D. Arroyo, C. Li, S. Li, G. Alvarez, W. A. Halang, "Cryptanalysis of an image encryption scheme based
  on a new total shuffling algorithm," *Chaos, Solitons & Fractals*, 2009.
- C. Li, K.-T. Lo, "Optimal quantitative cryptanalysis of permutation-only multimedia ciphers against
  plaintext attacks," *Signal Processing* 91(4):949–954, 2011.

Breaking the plaintext-association (sum-of-pixels) defence:
- S. Zhu, C. Zhu, H. Yan, "Cryptanalyzing and Improving an Image Encryption Algorithm Based on Chaotic
  Dual Scrambling of Pixel Position and Bit," *Entropy* 25(3):400, 2023, DOI 10.3390/e25030400.
- "Security analysis of a chaotic encryption algorithm related to the sum of plaintext pixel value,"
  *Applied Physics B*, 2023, DOI 10.1007/s00340-023-08029-4.
- Y. Zhao, Q. Shi, Q. Ding, "Cryptanalysis of an Image Encryption Algorithm Using DNA Coding and Chaos,"
  *Entropy* 27(1):40, 2025, DOI 10.3390/e27010040.

Differential-metric ideals:
- Y. Wu, J. P. Noonan, S. Agaian, "NPCR and UACI Randomness Tests for Image Encryption," 2011
  (ideal NPCR 99.6094%, UACI 33.4635% for 256 gray levels).

---

## 4. Fallback project — Fiat–Shamir completeness audit

The toolkit's `zk/` module demonstrates the three forgery classes (omit commitment → forge false
statement; omit OR challenge-split → forge false OR; omit context → cross-domain replay). These are the
publicly systematized "weak Fiat–Shamir" / Frozen-Heart class, so re-demonstrating them on the toy
library is **not novel**. A defensible version is a narrowly scoped **automated linter** that detects
whether a real Sigma/Fiat–Shamir implementation hashes all public inputs and commitments, evaluated on
a labelled corpus of known cases. Differentiate explicitly from existing tooling before pursuing.

Anchor references:
- Trail of Bits, "Frozen Heart" coordinated disclosure, 2022 (Girault, Bulletproofs, PlonK).
- Q. Dao, J. Miller, O. Wright, P. Grubbs, "Weak Fiat–Shamir Attacks on Modern Proof Systems,"
  IEEE S&P 2023 (eprint 2023/691).
- S. Chaliasos et al., "SoK: What don't we know? Understanding Security Vulnerabilities in SNARKs,"
  USENIX Security 2024 (arXiv:2402.15293).

---

## 5. Plan

1. Confirm a Track A target (primary: the Optik 2025 Fisher–Yates cipher) by reading its diffusion seed.
2. Reproduce it; match its reported statistics on a standard test image.
3. Run the equivalent-key CPA; report chosen-plaintext count and runtime; decrypt a fresh ciphertext.
4. Add the chi-square distinguisher and the NPCR caveat.
5. Write the paper in original wording (keep similarity low); prepare the AI-use declaration separately.
6. Only if Track A fails, pivot to the Fiat–Shamir linter.

# Research prompt — sourcing 3–5 real published chaos image ciphers for the oracle audit

Purpose: replace the synthetic-archetype corpus (Table V) with **actual published schemes** so the
"reusable structural audit" claim is earned on real work. Feed this prompt to a research agent (e.g. the
`deep-research` skill) or use it yourself. Fill one block per scheme into `published_corpus.py`.

---

## PROMPT (copy below this line)

You are a cryptography research assistant. Find **3–5 distinct, real, peer-reviewed chaos-based image
encryption schemes published in 2023–2025** and, for each, extract the exact algorithm details needed to
reimplement its encryption from scratch. Do **not** invent schemes, equations, or citations; if a detail
is not stated in the paper, write "NOT STATED" rather than guessing.

### Why the extraction targets matter (read first)
The schemes will be fed to a black-box structural oracle that decides one question: **is the per-pixel
transformation a fixed map that does NOT depend on the plaintext image?** If yes, the cipher is broken by
an equivalent-key chosen-plaintext attack; if the keystream is bound to the plaintext or to a fresh
per-image nonce, it resists. So the single most important thing to extract is **how every chaotic initial
condition / control parameter / S-box / permutation seed is derived** — from the secret key ALONE, or
from the plaintext image (a hash, a pixel sum, a histogram) or a nonce. Quote the exact seeding equations.

### Selection criteria
- Peer-reviewed venues typical of this subfield: *Optik*, *Nonlinear Dynamics*, *Multimedia Tools and
  Applications*, *Signal Processing* / *Signal Processing: Image Communication*, *Chaos, Solitons &
  Fractals*, *The Visual Computer*, *Journal of Information Security and Applications*, *Entropy*,
  *Scientific Reports*, *IEEE Access*, *Applied Sciences*, *Physica Scripta*.
- **Diversity is required.** Aim for a spread across: (i) permutation–diffusion with a modular-arithmetic
  or XOR diffusion stage; (ii) at least one using a fixed byte **S-box / DNA-coding / nonlinear**
  substitution (tests the oracle's query-cost scope boundary); and (iii) **at least one scheme that
  claims a plaintext-related / hash-seeded keystream** ("plaintext-aware", "SHA-256 of the image",
  "sensitivity to the plaintext") — this is the control that should RESIST, and it makes the audit
  credible rather than a turkey-shoot.
- Prefer schemes with **reference code** (GitHub, supplementary material) when available — note the link.

### Per-scheme extraction schema (fill ALL fields)
1. **Citation** — authors, exact title, venue, year, DOI, and reference-code URL if any.
2. **Chaotic system(s)** — which maps (logistic, Lorenz, Chen, Henon, hyperchaotic, 2D-SIMM, etc.) and
   their role (keystream, permutation seed, S-box generation).
3. **Seeding (DECISIVE).** Where do the initial conditions and control parameters come from? Quote the
   equations. Classify explicitly as one of: **key-only** | **plaintext/image-dependent** (give the exact
   dependency, e.g. SHA-256(image), sum of pixels) | **per-image nonce/IV**.
4. **Confusion / permutation** — how pixel or bit indices are scrambled, and what seeds it.
5. **Diffusion / substitution** — the per-pixel operation, classified as: **modular add/multiply
   (affine)** | **XOR** | **fixed nonlinear S-box** | **chained / CBC-like (output depends on previous
   ciphertext)**. Give the update equation.
6. **Rounds & order** — number of rounds and the stage sequence; any block size / image-dimension
   constraints.
7. **Decisive flag** — in one line: does ANY encryption quantity depend on the plaintext image? (yes/no +
   what).
8. **Reconstruction confidence** — can the encryption be reimplemented unambiguously from the paper alone?
   (high / medium / low) and list any ambiguous steps.

### Output format
Return one filled block per scheme using the schema above, followed by a one-paragraph summary table:
scheme → {seeding class, diffusion algebra, predicted verdict (BROKEN / RESISTS / S-box-out-of-cheap-
regime), reconstruction confidence}. Keep every claim traceable to the cited paper; flag every "NOT
STATED" so the reconstruction caveat is explicit.

## (end of prompt)

---

## After the research returns
For each scheme I will: (1) reimplement `encrypt(key, image) -> flat uint8` from the extracted spec,
(2) register it in `PUBLISHED` in `published_corpus.py`, (3) run the oracle, and (4) report a Table-V row
— recoverability R, query cost, verdict, and paper-only-vs-author-code provenance. Schemes whose seeding
is "NOT STATED" or low-confidence are reported with that caveat, never as a clean verdict.

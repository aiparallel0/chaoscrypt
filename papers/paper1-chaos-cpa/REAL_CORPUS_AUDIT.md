# Real-Literature Audit (Table V): the structural oracle on four published 2023–2025 chaos ciphers

This is the strong-venue track's real-corpus result — it replaces the synthetic-archetype corpus (the 8
reconstructed toy schemes in `structural_oracle.py`) with **actual published schemes**, reconstructed
faithfully from three independent extraction reports. The oracle issues every verdict mechanically, from a
falsifiable held-out certificate; no verdict is assigned by hand.

Reproduce: `PYTHONPATH=src python3 papers/paper1-chaos-cpa/published_corpus.py`
(reconstructions in `published_schemes.py`; figure `fig_published_audit.py` → `figures/published_audit.pdf`).

## Headline

- **1 of 4 schemes is BROKEN** — **LSCM-CA** (Sun et al., *Sci. Rep.* 2025), a real key-only cipher,
  recovered at **R = 1.000 in 12 chosen plaintexts at 512²**. It only fell *after* a principled extension
  of the oracle (below); the published affine/xor model alone returned a **false negative**.
- **3 of 4 RESIST** — Li+DNA (2024), MILE (2025), MIEA-PRHM (2024) — all plaintext-bound; the recovered
  key predicts held-out ciphertext at chance (R ≈ 0.004). These are the *negative controls* the audit
  needs to be credible: the oracle declines to "break" schemes that genuinely reseed per image.
- **The audit surfaced a real scope gap and a real fragility**, documented below. Both are findings, not
  failures: a reusable audit is only worth the name if running it on real work teaches you something.

## Table V

| Scheme (DOI) | Seeding (decisive) | Diffusion algebra | A·n (1-pixel flip) | R (held-out) | Algebra fit | Queries @512² | **Verdict** | Recon. conf. |
|---|---|---|---:|---:|---|---:|---|---|
| **LSCM-CA** — Sun et al., *Sci. Rep.* 15:21603 (2025), `10.1038/s41598-025-04968-4` | key-only (LSCM from x₀,r,b) | XOR + per-pixel CA bit stage | **1.0** | **1.000** | bitlinear | **12** | **BROKEN** | HIGH (full pseudocode) |
| **Li dual-chaotic+DNA** — *Sci. Rep.* 14:20733 (2024), `10.1038/s41598-024-71267-9` | **plaintext** SHA-256(image) | dynamic DNA add/sub/XOR/XNOR | 16323 | 0.004 | xor | 4 | RESISTS | HIGH (eqns verbatim) |
| **MILE+Q-matrix** — Mansour et al., *Sci. Rep.* 15:31383 (2025), `10.1038/s41598-025-16343-4` | **plaintext** (sum of first 8×8 block) | XOR + modular-multiply | 1.0 † | 0.004 | affine | 5 | RESISTS † | MED-HIGH |
| **MIEA-PRHM** — Feng et al., *Mathematics* 12(24):3917 (2024), `10.3390/math12243917` | key-only keystream **+ plaintext scalar** | modular-add + XOR | 16384 | 0.004 | bitlinear | 12 | RESISTS ‡ | HIGH (full algorithms) |

† **MILE is fragile.** Its plaintext-dependence flows *only* through the first 64 pixels (the seed block),
so a one-pixel flip elsewhere moves a single ciphertext byte (A·n = 1, the diffusion-free signature) — yet
random probes carry different seed blocks, so R = chance. The two signals **disagree**, and that disagreement
is the tell. Stress-test: hold the 64-pixel seed block constant (a legitimate chosen-plaintext sub-class)
and **R jumps 0.004 → 1.000 off the seed block** — MILE collapses to an exactly-recovered fixed map. Its
"resistance" is 64 pixels deep.

‡ **MIEA-PRHM is a near-miss.** The hyperchaotic keystream is key-only (K = {x₀,y₀,…}); the image enters
*only* as a single additive scalar h_sum = ΣV, V = SHA-256(image). That one scalar shifts every pixel, so
avalanche looks full (A·n = n) and R = chance → RESISTS. But the plaintext entropy entering the map is **8
bits**: an adversary brute-forces the 256 possible h_sum values. The oracle certifies "*not* a fixed
plaintext-independent map," which is true — it does **not** certify cryptographic strength, and we say so.

**Honest limitation made visible (see `figures/published_audit.pdf`).** Li+DNA (genuine SHA-256-of-image
binding) and MIEA-PRHM (a 256-way scalar) land at the *same point* in both signals — full avalanche, R ≈ 0.
These two signals **cannot** separate strong binding from a fragile near-miss; distinguishing them needs a
third probe (e.g. measuring the plaintext-entropy that actually reaches the per-pixel map). This is a real
boundary of the method, not hidden.

## The scope extension the audit forced: a GF(2)-affine ("bitlinear") recovery model

Run against the **published** affine/xor oracle, LSCM-CA returned **RESISTS (R = 0.005) — a false negative**,
even though it is plainly key-only. Cause: its per-pixel cellular-automata bit stage is a fixed GF(2)-affine
byte map `g(y) = M·y ⊕ d` with **M ≠ I** (it mixes bits across positions *within* a byte). The composite is
`C[j] = M·P[s_j] ⊕ B_j`. The plain-xor recovery reads `out ⊕ c0 = M·D[s_j]` instead of `D[s_j]`, so the
source index comes back bit-scrambled and prediction collapses to chance.

Fix (now in `structural_oracle.py`, `_recover_bitlinear`): add a third position-wise model alongside affine
and xor. Eight **bit-basis probes** (every pixel = `1<<t`, t = 0..7) read the shared matrix M one column at a
time — `out_t ⊕ c0 = M·e_t`, *constant across all positions*. Inverting M over GF(2) unscrambles the digit
images to recover s_j exactly. LSCM-CA then breaks at **R = 1.000, 12 queries**. The model is a strict
generalization (M = I reduces to xor), so **all 8 archetypes keep their prior verdicts** (regression-checked:
5 key-only BROKEN, even-multiplier partial, SHA/nonce RESIST) and the LLEO self-test is unchanged. This
extends the structural attack from mod-256 affine / byte-xor to the **bit-level S-box / cellular-automata**
designs that are common in this literature — a real strengthening, motivated by a real scheme.

## Reconstruction methodology and caveats

- **Faithful to the decisive structure.** Each `encrypt` reproduces the property the oracle tests — the
  **seeding class** (key-only vs plaintext/nonce-bound) and the per-pixel diffusion algebra — exactly as the
  papers state. Where a paper fixes a numeric constant we could not read (e.g. LSCM default x₀,r,b), we draw
  it from the key: it changes the keystream *values*, never the structural verdict (which depends on whether
  the plaintext enters the seed, not on the constant). Every such choice is commented in `published_schemes.py`.
- **Single-plane reduction.** Colour/bit-plane bookkeeping that does not change the structural class is
  reduced to one grayscale plane of n pixels. The seeding and diffusion algebra are preserved.
- **Provenance: paper-only.** None of the four schemes published reference code, so reconstructions rest on
  the printed equations/pseudocode; they cannot be cross-checked against an author implementation. The oracle
  verdict is nonetheless a *falsifiable certificate* of the reconstructed cipher.
- **Diversity satisfied.** modular/XOR (MILE), DNA/nonlinear substitution (Li+DNA), bit-level S-box/CA
  (LSCM-CA), and a genuine plaintext-hash control (Li+DNA) plus a designed near-miss (MIEA-PRHM).

## Cross-report triangulation (3 independent extractions)

The three supplied reports overlap and disagree in informative ways:
- **LSCM-CA** appears only in Report 3, with full pseudocode → our one clean BROKEN. High agreement internally.
- **MIEA-PRHM** (Report 2) and **MILE** (Report 1) are independently flagged as the two "claims-plaintext-
  dependence-but-structurally-thin" cases — matching what the oracle found (near-miss / fragile).
- **Güvenoğlu** (*Conn. Sci.* 2024) appears in Reports 1 **and** 3 with a **conflict**: both lean RESISTS
  (SHA-512 of key *and* image) but both flag an internal tension — the key-space text says keys derive from
  K alone, while Step 1 hashes the image P. Report 3 calls resolving this "the single most important item to
  verify." We therefore **did not** reconstruct Güvenoğlu: its verdict hinges on an unresolved seeding fact.

## Institutional access — clear answer

**The four audited schemes did not require institutional access** — all are open-access (Scientific Reports,
MDPI Mathematics) and reconstructible from the open text. Access matters only if you want to *extend* the
corpus:

- **Lone & Qureshi, "…affine hill cipher," *Nonlinear Dynamics* 111(6):5919 (2023),
  `10.1007/s11071-022-07995-2` — PAYWALLED (Springer).** This is the only genuinely gated scheme. Report 1
  rates its key-only seeding only **inferred from the abstract** (the per-equation seeding, AHC modulus,
  matrix size, and round count are all "NOT STATED") and explicitly says *obtain the PDF before coding*. We
  did not reconstruct it; doing so needs the full text. **Institutional access required.**
- **Güvenoğlu, *Connection Science* 36(1):2312108 (2024) — open access but bot-blocked during research, and
  the seeding is disputed (above).** No paywall, but the full PDF must be read to resolve whether the image
  digest actually enters the keystream. **Full-text needed (not a paywall).**
- **Further open-access candidates whose equations sit in PDF figures (no paywall, transcription only):**
  DNAS_box (Qiu et al., *Entropy* 27(3):239, 2025) — a plaintext-bound *DNA S-box* worth adding;
  Vargas Valencia et al. (*J. Cybersecur. Priv.* 2026) — a clean *key-only modular-diffusion* scheme that
  would be a second BROKEN (date is just outside 2023–2025); Wang et al. (*Mathematics* 12(20):3297, 2024),
  Huang et al. (*Mathematics* 13(8):1330, 2025), Singh et al. (*Alexandria Eng. J.* 122, 2025). All
  reconstructible from their open PDFs without institutional access.

**Bottom line:** the current 4-scheme audit stands on open-access sources. The *one* item that needs
institutional (Springer) access is the Lone & Qureshi *Nonlinear Dynamics* 2023 paper, the predicted
second key-only/BROKEN scheme — supply that PDF (or institutional access) and I will reconstruct and audit it.

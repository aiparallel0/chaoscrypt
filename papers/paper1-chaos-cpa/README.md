# Paper 1 — Equivalent-key chosen-plaintext cryptanalysis of a published chaos image cipher

**Venue:** IEEE UBMK 2026 (see `docs/VENUE_UBMK2026.md`). ~6 pages, IEEEtran, <25% similarity.

## Thesis / headline claim
A published permutation–diffusion ("chaos") image cipher whose diffusion keystream is plaintext-
independent is a fixed affine map over GF(2) and is fully recovered ("equivalent key") from a handful
of chosen plaintexts; we decrypt arbitrary ciphertexts with no key, and show its near-ideal
NPCR/UACI does not imply chosen-plaintext resistance.

## Critical-path decision (go/no-go) — owned by the orchestrator
Confirm the target's diffusion-keystream seed from the full paper. Primary target: Optik 2025
Fisher–Yates scheme, DOI 10.1016/j.ijleo.2025.172304. Key-only / weak statistic ⇒ VULNERABLE (proceed);
full plaintext hash ⇒ DEFENDED (switch to a backup in `docs/RESEARCH_NOTES.md`).

## Build plan
1. `docs/TARGET.md`: exact permutation, diffusion, keystream seeding, rounds, citation.
2. `src/chaoscrypt/targets/<name>.py`: faithful reimplementation reusing `chaoscrypt.ciphers`
   (no copied code; from the paper's description only). Pin with a test.
3. `experiments/reproduce_*.py`: encrypt a standard image (USC-SIPI Lena/Baboon, or synthetic if
   blocked); report entropy, NPCR, UACI, adjacent-pixel correlation; match the paper's values.
4. `experiments/attack_*.py`: `affine_test` ⇒ adapt `equivalent_key_cpa` to the exact structure ⇒
   recover keystream+permutation ⇒ decrypt a fresh ciphertext, pixel-exact. Report #chosen-plaintexts
   and wall-clock.
5. Chi-square keystream distinguisher + the NPCR caveat (`distinguishers.py`).
6. Figures → `figures/`: original/encrypted/recovered images; keystream histogram vs uniform.
   Results → `results/*.json` consumed by `\PH{}` in `main.tex`.

## Section outline (6 pp)
Abstract · Intro + chaos-cryptanalysis context · target recap · the equivalent-key CPA + complexity ·
results (recovery, runtime, recovered images, chi-square, NPCR caveat) · how-to-fix (plaintext-hash
seeding) · conclusion. Cite Li et al. lineage (see `docs/RESEARCH_NOTES.md`). + AI-use disclosure.

# Pre-submission checklist — Paper 1 (IEEE UBMK 2026)

## Format & process
- [x] IEEEtran `[conference]` template; builds via `bash scripts/compile.sh papers/paper1-chaos-cpa`.
- [x] Length within the 6-page limit (currently 4 pages). _Expand toward 5–6 pp if desired (optional)._
- [x] AI-use declaration prepared (`AI_USE_DECLARATION.md`) + Acknowledgment disclosure in the paper.
- [x] Citations independently verified (background verification pass; see commit history).
- [ ] **Similarity < 25%** — wording is original and no text/code was copied from the target paper, but
      run the official similarity check on the final PDF before submitting.
- [ ] **Author block** — currently a single anonymous placeholder; insert real name/affiliation (UBMK is
      not double-blind).
- [ ] **Re-confirm no competing cryptanalysis** of the exact scheme appeared (none found at time of
      writing; re-search the title/authors near the deadline).
- [ ] Confirm portal accepts a LaTeX-built PDF (and whether a .docx is also required); upload the
      AI-use declaration attachment.

## Every claim is backed by a reproducible script
| Claim in paper | Produced by |
|---|---|
| Cipher entropy ≈7.99, correlation ≈0 (reproduction) | `papers/paper1-chaos-cpa/exp_reproduce_attack.py` |
| Break in 4 chosen plaintexts, pixel-exact, ~0.1 s | `exp_reproduce_attack.py` + `src/chaoscrypt/targets/lleo.py` |
| True 1-pixel NPCR 0.000381% vs 99.88% unrelated | `exp_reproduce_attack.py` |
| Chi-square keystream non-uniformity | `exp_reproduce_attack.py` |
| Positive control: hash-seeded variant resists (100% vs 0.25%) | `exp_reproduce_attack.py` |
| Attack cost vs image size (logarithmic, sub-second) | `papers/paper1-chaos-cpa/exp_scaling.py` |
| Generality: break of a 2nd (CBC-XOR) cipher; hash-seeded resists | `papers/paper1-chaos-cpa/exp_generality.py` |
| Cipher round-trip + break (pinned) | `tests/test_targets.py` (`pytest`) |

All results are seed-fixed. Numbers flow into `main.tex` only via `results/*.json` +
`scripts/fill_tex.py` (no hand-typed figures).

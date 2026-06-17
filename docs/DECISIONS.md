# Locked decisions

Format: decision → rationale. Records the choices that drive both papers so the work stays coherent.

## D1 — Deliverable: two 6-page IEEE papers for UBMK 2026
Two distinct-topic papers, each ~6 pages in `IEEEtran [conference]`, submitted to UBMK 2026
(deadline 30 June 2026; see `docs/VENUE_UBMK2026.md`). Rejected: one paper + AI-declaration
(that was an early misread of "2 PDFs"). The two AI-use declarations are *additional* required
attachments, not the second paper.

## D2 — The two papers must be on clearly distinct topics
Rejected: two cipher-breaking papers (too narrow / salami). Both stay in **security** (Paper 2 may be
crypto-adjacent) but address different sub-problems with different methods.

## D3 — Paper 1 = chosen-plaintext "equivalent-key" cryptanalysis of a published chaos image cipher
Anchor target: the Optik 2025 Fisher–Yates scheme (DOI 10.1016/j.ijleo.2025.172304), pending the
go/no-go on its diffusion-keystream seed (key-only/weak = breakable; full plaintext hash = defended).
Backups exist in `docs/RESEARCH_NOTES.md`. Reuses the existing `src/chaoscrypt` toolkit.

## D4 — Paper 2 = calibration & selective-prediction (abstention) audit for ML intrusion detection
Chosen over (A) a weak-Fiat–Shamir/NIZK soundness linter and (C) a membership-inference benchmark.
Rationale: best fit to UBMK's applied-ML reviewer pool, lowest 13-day build risk, leverages
demonstrated selective-prediction expertise, and a methodological angle (calibration + abstention +
open-set unknown-attack evaluation) that differentiates from the venue's accuracy-only IDS papers.
Datasets: NSL-KDD (+ CIC-IDS-2017 or a tractable subset). CPU-only, scikit-learn.
Trade-off accepted: lower novelty ceiling and no code reuse, in exchange for venue fit + low risk.

## D5 — Both papers live in the `chaoscrypt` repo (for now)
Under `papers/paper1-chaos-cpa/` and `papers/paper2-ids-selective/`, sharing the build tooling in
`scripts/`. The existing `src/chaoscrypt` crypto API stays stable; Paper 2's IDS code is a new module.
FLAGGED to the user: an IDS/ML study inside a repo named "chaoscrypt" is thematically odd; Paper 2
may be split into its own repo before code release. Standing rule honored: all writes confined to this repo.

## D6 — Originality discipline (UBMK <25% similarity + MIT-repo hygiene)
Reimplement from papers' descriptions or our own code; **no GPL/AGPL/unlicensed code copied in; no
pasted paper text.** Cite on learning. Rephrase anything within ~3 content words of a source sentence.

## D7 — Build = placeholder-first paper factory (mirrors the sibling repos)
Experiment scripts emit `results/*.json`; `scripts/fill_tex.py` substitutes `\PH{key}` placeholders in
each paper's `main.tex`; `scripts/compile.sh` builds the PDF. Papers compile from day one with
placeholders; missing keys render visibly. Figures are produced by scripts into each paper's `figures/`.

## Pace
"Start now, both in parallel" (user). 13-day clock. Environment: numpy/scipy/scikit-learn/pandas/
matplotlib/pytest installed; TeX Live installing. Network works for pip (dataset/PDF access TBD).

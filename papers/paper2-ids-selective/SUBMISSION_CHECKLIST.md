# Pre-submission checklist — Paper 2 (IEEE UBMK 2026)

## Format & process
- [x] IEEEtran `[conference]` template; builds via `bash scripts/compile.sh papers/paper2-ids-selective`.
- [x] Length within the 6-page limit (currently 4 pages). _Expand toward 5–6 pp if desired (optional)._
- [x] AI-use declaration prepared (`AI_USE_DECLARATION.md`) + Acknowledgment disclosure in the paper.
- [x] Citations independently verified (background verification pass; see commit history).
- [ ] **Similarity < 25%** — wording is original; run the official similarity check on the final PDF.
- [ ] **Author block** — currently a single anonymous placeholder; insert real name/affiliation.
- [ ] Confirm portal accepts a LaTeX-built PDF (and whether a .docx is also required); upload the
      AI-use declaration attachment.
- [x] Evaluation hygiene (Arp et al. 2022): encoder/calibrator fit on TRAIN only; no test leakage;
      open-set holds out whole families.

## Every claim is backed by a reproducible script
| Claim in paper | Produced by |
|---|---|
| Accuracy, ECE (raw/Platt), AURC, risk@80% per model | `papers/paper2-ids-selective/exp_main.py` |
| In-distribution ECE ≈0.001–0.003 vs shifted ≈0.17–0.19 | `exp_main.py` |
| Detection known vs novel attacks; risk–coverage curves | `exp_main.py` |
| Open-set family holdout (detection collapse, abstention reject) | `papers/paper2-ids-selective/exp_openset.py` |
| Uncertainty-signal benchmark (MSP vs disagreement/Mahalanobis/kNN) + conformal coverage | `papers/paper2-ids-selective/exp_signals.py` |
| CIC-IDS-2017 second dataset + cross-day drift | `papers/paper2-ids-selective/exp_cicids.py` (`src/ids_selective/cicids.py`) |
| Figures (risk–coverage, reliability, ECE-shift, open-set) | `exp_main.py`, `exp_openset.py` |
| Data loader, leakage-safe pipeline, metrics | `src/ids_selective/{data,pipeline,metrics}.py` |

All results are seed-fixed (`random_state=42`). Numbers flow into `main.tex` only via `results/*.json`
+ `scripts/fill_tex.py` (no hand-typed figures). NSL-KDD is re-downloadable via
`python src/ids_selective/fetch_data.py`.

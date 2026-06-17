# Paper 2 — Calibration & selective prediction (abstention) for ML intrusion detection

**Venue:** IEEE UBMK 2026 (see `docs/VENUE_UBMK2026.md`). ~6 pages, IEEEtran, <25% similarity.
CPU-only, scikit-learn. Distinct from Paper 1 (no cryptography).

## Thesis / headline claim
Standard ML intrusion detectors (NSL-KDD, CIC-IDS-2017) are systematically over-confident — poor
calibration (high ECE) and silent failure on *unknown* attack families. A selective-prediction
(reject-option) wrapper converts that over-confidence into calibrated abstention: at coverage c% it
attains precision/selective-risk far better than the full-coverage model, and rejects most unknown-
family attacks. Methodological angle (calibration + abstention + open-set), not another classifier.

## Build plan
1. Data: NSL-KDD (small, public) first; add CIC-IDS-2017 (or a tractable per-day subset) if time.
   Loader under `src/ids_selective/`. Respect anti-snooping (no test leakage; documented splits).
2. Models: logistic regression, random forest, gradient boosting / small MLP (scikit-learn, CPU).
3. Calibration: ECE + reliability diagrams; temperature/Platt scaling; pre/post comparison.
4. Selective prediction: confidence/entropy thresholding (+ optional SR/SRGAR); risk–coverage curves,
   AURC, precision@coverage.
5. Open-set / unknown attacks: hold out whole attack *families* at train time; measure rejection of
   unknown-family samples; optional cross-dataset (NSL-KDD→CIC-IDS) drift mini-study.
6. Metrics → `results/*.json` (ECE, AUROC, AURC, risk@coverage, unknown-rejection rate); figures →
   `figures/` (reliability diagram, risk–coverage curve). Anchor framing in Arp et al. "Dos and Don'ts
   of ML in Computer Security" (USENIX 2022).

## Section outline (6 pp)
Abstract · Intro (overconfidence + unknown-attack failure; abstention as fix) · related work
(calibration, selective prediction / SelectiveNet, open-set IDS, Arp et al.) · methodology
(datasets, models, family-holdout protocol, abstention mechanisms, leakage controls) · calibration
results · selective-prediction results (risk–coverage, unknown rejection, drift) · discussion /
limitations (dataset age) · conclusion. + AI-use disclosure. **Verify every citation.**

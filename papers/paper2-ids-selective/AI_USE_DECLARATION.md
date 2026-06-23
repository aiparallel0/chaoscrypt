# Declaration of AI use — Paper 2 (calibration & selective prediction for IDS)

Submitted to IEEE UBMK 2026. This attachment satisfies the UBMK requirement to specify which AI tool
was used in which part of the paper, and complements the Acknowledgment disclosure in the manuscript.
(Upload as a PDF if the portal requires; convert this file with any Markdown-to-PDF tool.)

**AI system used:** Anthropic Claude (a large language model), via an agentic coding assistant.

**Where AI was used:**
- *Code:* the NSL-KDD data pipeline, calibration / selective-prediction / open-set experiments, the
  metrics (ECE, risk--coverage/AURC), and the figure code (`src/ids_selective/`,
  `papers/paper2-ids-selective/exp_*.py`).
- *Experiments and figures:* running the reproducible scripts and producing the plots/tables.
- *Literature:* assisting with related-work search and bibliography formatting. **Every citation was
  independently verified against its primary source**; none was accepted on the model's say-so.
- *Writing:* drafting and editing the manuscript prose in the author's direction.

**Where AI was NOT used / human responsibility:**
- The study framing (calibration and abstention for intrusion detection), the choice of dataset and
  protocol, and the interpretation of results are the author's.
- All numbers come from the deterministic scripts in this repository and were checked by the author.
- The AI system is **not** an author. The author takes full responsibility for the correctness and
  integrity of the paper, including the evaluation-hygiene choices (train-only fitting, no test leakage).

**Reproducibility:** every figure and number derives from a script under `papers/paper2-ids-selective/`
(see `SUBMISSION_CHECKLIST.md` for the claim-to-script map); results are seed-fixed and re-runnable.

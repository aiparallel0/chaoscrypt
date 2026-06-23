# Declaration of AI use — Paper 1 (chaos-cipher cryptanalysis)

Submitted to IEEE UBMK 2026. This attachment satisfies the UBMK requirement to specify which AI tool
was used in which part of the paper, and complements the Acknowledgment disclosure in the manuscript.
(Upload as a PDF if the portal requires; convert this file with any Markdown-to-PDF tool.)

**AI system used:** Anthropic Claude (a large language model), via an agentic coding assistant.

**Where AI was used:**
- *Code:* implementing the reconstruction of the target cipher and the equivalent-key attack
  (`src/chaoscrypt/targets/lleo.py`), the experiment scripts, and the figure-generation code.
- *Experiments and figures:* running the reproducible scripts and producing the plots/tables.
- *Literature:* assisting with related-work search and formatting the bibliography. **Every citation
  was independently verified against its primary source** (publisher page / DBLP / author copy); none
  was accepted on the model's say-so.
- *Writing:* drafting and editing the manuscript prose in the author's direction.

**Where AI was NOT used / human responsibility:**
- The study design, the decision of which scheme to analyse, and the interpretation of results are the
  author's.
- All numerical claims are produced by the deterministic scripts in this repository and were checked by
  the author against the scripts' output.
- The AI system is **not** an author and is not credited with authorship. The author takes full
  responsibility for the correctness and integrity of the paper.

**Reproducibility:** every figure and number derives from a script under `papers/paper1-chaos-cpa/`
(see `SUBMISSION_CHECKLIST.md` for the claim-to-script map); results are seed-fixed and re-runnable.

# Handbook

| File | What it is |
|---|---|
| [RESEARCH-PUBLICATION-METHOD-UNIFIED.md](RESEARCH-PUBLICATION-METHOD-UNIFIED.md) | Field-agnostic method handbook, 28 sections. Sections 23 to 26 came from this project; Section 27 from another; 16.11, 18.14 to 18.16 and 24.10 from auditing the merge. |
| [CRYPTANALYSIS-AND-EVALUATION.md](CRYPTANALYSIS-AND-EVALUATION.md) | The domain companion: breaking a cipher that passed every test its designers applied, and evaluating detectors that were confident where they were wrong. |

The handbook is about **method** and holds for any field. The domain file is
about **subject matter**, and keeps its measured values so the arguments are
checkable.

Both halves of the domain file turn on one idea, which is also why Sections 23 to
26 of the handbook exist: a system having a property, and a system scoring well on
a measurement of that property, are different facts.

Two related directories:

- [`../digest/`](../digest/) is the same experience compressed to two short files
  of classes only, for reading in one sitting.
- [`../paper-pipeline/`](../paper-pipeline/) is the earlier, longer playbook with
  the runnable checks and the verbatim correction notices.

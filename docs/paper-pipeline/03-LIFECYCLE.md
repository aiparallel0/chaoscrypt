# Lifecycle

The order work actually has to happen in, reconstructed from 91 commits and 70 author turns —
and the order it happened in, which was different and cost several rounds of rework.

---

## What actually happened

| Stage | Commits (representative) | What it did | What it cost later |
|---|---|---|---|
| 1. Draft | early | Both papers written | — |
| 2. Expand | `8c8b5c7` "expand to strong-venue versions" | Grew both papers with new results | Everything in stage 4 |
| 3. Reframe | `1680b07` "new experiments + drastic reframing" | Restructured the argument | Invalidated readability work |
| 4. Cut | `0e516f6` "cut both papers to six pages" | Discovered/applied the venue limit | Re-cut needed twice more |
| 5. Readability | `3ce9b82`, `967adba`, `2b37057` | Glosses, on-ramps, abstracts | Partly redone after later cuts |
| 6. Integrity passes | `9ed2096`, `95a1589`, `030d710` | Reconciled numbers, scoped claims | Introduced C1 (disclosure drift) |
| 7. Reviewer prep | `4faa5df`, `6c1409b` | Comparison table, real-world stakes, hyphenation | — |
| 8. Committee round | `eabdfc6` → `608d0b6` | Captions, float references, author block | — |
| 9. Reviewer-rules round | `f2fb8b1`, `7601cc5` | The six formatting rules | — |
| 10. Annotated-PDF round | `e6529b1` | Algorithm float removed | Repeat of stage 9's rule 5 |
| 11. Overleaf round-trip | — | Author's own compile revealed B1 | A near-miss submission |
| 12. Sibling catch-up | `7706940` | Paper 2 finally audited | Full repeat of stages 8–10 |

**Stages 8, 9 and 10 are the same stage.** Three rounds of correction arrived because each was
answered narrowly. Stage 12 is stages 8–10 repeated wholesale on the other paper.

---

## The order to actually use

```
Phase 0  Ground truth      ── class file, template source + PDF, .docx styles, page limit, deadline
Phase 1  Trustworthy build ── make it fail loudly; prove it by breaking the source
Phase 2  Content           ── argument and numbers settle here, formatting untouched
Phase 3  Integrity audit   ── numbers, citations, claim strength, disclosures
Phase 4  Conformance       ── template applied whole-document
Phase 5  Fit               ── cut to limit, prove no result lost
Phase 6  Deliverable       ── self-contained package, clean-room compiled
Phase 7  Sibling sweep     ── repeat 3-6 on every other artifact
```

Exit conditions are in [00-MASTER-PROMPT.md §3](00-MASTER-PROMPT.md).

### Why this order

- **0 before everything.** The page limit and caption specification are *inputs*. Discovered late
  (stage 4 above), they invalidate finished work. The whole caption saga would have been a
  ten-minute Phase 0 task.
- **1 before 2.** A build that cannot fail turns every later phase into manual inspection. This
  project never did Phase 1; its build script had an inverted exit status and a false-success
  path for all 91 commits, and *not one* of the real errors was caught by tooling.
- **2 before 4.** Formatting is a function of content. Reformatting after every content change is
  the single biggest source of rework here.
- **3 before 4.** Integrity problems are expensive to fix late because fixing them changes text,
  which re-breaks fit. Also: an integrity defect that survives to Phase 5 gets *shortened* rather
  than corrected — how a hedged disclosure becomes an assertion.
- **5 after 4.** Conformance changes length — Paper 2's fixes pushed it 6 → 7 pages. Cutting
  before conforming means cutting twice.
- **7 always.** Non-negotiable. See [01 §D1](01-FAILURE-CATALOG.md).

---

## Front-load these

Ranked by rework prevented:

1. **The page limit, as a permanent gate.** Wire it into the build in Phase 1 so it can never be
   discovered.
2. **The caption/table/heading specification**, derived from the class file and `.docx` styles —
   not the template's PDF. One Phase 0 investigation replaces three correction rounds.
3. **A build that fails.** Break the source deliberately and confirm it fails loudly and ships
   nothing stale.
4. **The single-source-of-truth bridge for numbers** — *plus a test that an unfilled placeholder
   fails the build.* The bridge without the test is a net loss (it swapped a visible
   inconsistency for silent content deletion).
5. **The author block, as a blocking question.** It cannot be inferred. Ask in the first
   exchange; a bracketed placeholder until then, never a realistic fake.
6. **A tracked "unverified" list** — citations not confirmed against a primary source,
   disclosures not confirmed with the human, claims not yet backed by a result. Items that live
   only in conversation do not survive it.

---

## Recurring shapes

**The narrow fix.** A reviewer marks one instance; only that instance is fixed; the same note
returns pointed at a different object. Cost here: three correction rounds where one would have
done, plus the *identical* note (*"Bu tablo mu?"*) arriving twice about two different objects.

**The deferred verification.** A gap is correctly found, correctly reported in chat, and never
written back into the artifact. Generative pattern behind the disclosure drift, the AI
declaration, and the unverified citation.

**The helpful mechanism with a new failure mode.** The placeholder bridge fixed number drift and
introduced silent content deletion. The `caption` package standardised fonts and deleted the
class's format. `\floatsep{0pt}` matched the template and collided floats. Budget for testing
every fix as a change in its own right.

**The sibling drift.** Two artifacts, one gets the attention. Divergence is invisible because
each looks fine on its own.

**The confident wrong input.** A polished external checklist, mostly incorrect. Fluency correlates
with neither accuracy nor authority — including in your own earlier output.

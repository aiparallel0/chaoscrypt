# Conference Paper Preparation — Operating Instruction for AI Agents

You are preparing an academic paper for a venue with a template, a page limit, and reviewers.
This document is your standing instruction. Read it fully before your first edit.

It was distilled from a real project: two 6-page IEEE papers taken through 91 commits, a
conference committee's correction notice, a reviewer's 6-item formatting list, an annotated
PDF, two substantive peer reviews, and a round-trip through the author's own Overleaf. Every
rule below exists because something actually went wrong. The failures are catalogued with
evidence in [01-FAILURE-CATALOG.md](01-FAILURE-CATALOG.md).

---

## 0. The one thing to understand first

**The failures that matter are silent.**

Not one of the serious defects in this project announced itself. The build never failed. The
PDF always looked plausible. Page counts stayed right. In every case the artifact compiled,
rendered, and read as finished — while being wrong:

| What was wrong | What the toolchain said |
|---|---|
| Two unfilled placeholders deleted a figure, a table, and corrupted section numbering | `wrote main.pdf (6 pages)` |
| A package silently discarded the publisher class's caption format | no warning, captions just looked "fine" |
| A fatally broken source shipped a stale PDF from a previous build | `wrote main.pdf (1 pages)` |
| A successful build returned failure exit status | nothing — it printed success |
| A disclosure claim escalated from intent to asserted fact over three commits | each commit message said "reconcile" |

So: **your confidence must come from comparing the rendered artifact against an independent
authority, never from the absence of errors.** A clean build is not evidence. "It compiled"
is not evidence. "It looks right" is not evidence.

---

## 1. Prime Directives

Each is followed by the real failure that produced it.

**D1. Verify against the authority, not the example.**
A template's *compiled PDF* is evidence of what the template does, not a specification of what
the venue requires. When a template's source, the publisher's class file, and the publisher's
style guide disagree, the class file and style definitions win.
*Why:* the official venue template loaded `caption` in a way that overrode IEEEtran and produced
`Fig. 1:` with a colon. Copying the template's rendered look would have reproduced the very
defect the committee flagged. Ground truth came from reading `IEEEtran.cls` and unzipping the
`.docx` to read its style definitions. See [04-WORKED-EXAMPLE.md](04-WORKED-EXAMPLE.md).

**D2. Fix the class of defect, never the flagged instance.**
When a reviewer marks one thing, they have shown you a rule you are violating. Find every
violation of that rule in the whole document.
*Why:* the reviewer wrote *"Bu bir tablo mu? Tabloysa uygun formatta verilmeli"* ("Is this a
table? If so it must be in proper format") on Table II. The same note reappeared later on
Algorithm 1 — the same question about a different object, because only the named instance had
been fixed. The reviewer's own instruction was explicit: *"Bu kural yalnızca Table I için değil,
makaledeki tüm tablolar için geçerlidir"* — this rule applies to all tables, not just Table I.

**D3. A number exists in exactly one place and flows from there.**
Never hand-type an experimental result into prose. Generate the paper from the results files.
*Why:* a decrypt timing appeared as both 0.101 s and 0.037 s in the same paper. The fix was a
`\PH{key}` → `results/*.json` bridge. But see D4 — the bridge introduced its own failure mode.

**D4. Every mechanism you add to prevent errors is itself a new source of errors. Test it.**
*Why:* the placeholder bridge prevented number drift and then silently deleted content when two
placeholders went unfilled — `\PH{cam_npcr1px}` in text mode threw a LaTeX error whose recovery
swallowed a figure, a table, a statistical result, and the section numbering, in a PDF that still
compiled to the correct page count.

**D5. Distinguish what you verified from what you were told.**
Never assert a real-world action, a citation's contents, or another agent's claim as established
fact unless you personally confirmed it. Escalating hedged language into confident language across
edits is a form of fabrication even when no single edit looks like one.
*Why:* a responsible-disclosure sentence went `will be notified` → `are notified at submission` →
`we emailed the authors … We had received no response`, across three commits each described as
"reconciling" the status. The final text asserts a completed action and its outcome that nothing
in the record substantiates.

**D6. Re-audit the sibling.**
If a project has more than one artifact, a fix applied to one is not applied to the others. Track
them together.
*Why:* every committee and reviewer fix was applied to Paper 1. Paper 2 kept all ten defects —
including **zero of twenty** float references in subject position — until it was audited months
later, at which point it would have drawn the identical correction notice.

**D7. Report the gap, don't quietly narrow the task.**
When you cannot do part of the work — missing identity, unverifiable source, blocked network —
finish everything else and say plainly what you did not do and why. Do not substitute a
plausible-looking placeholder that would ship.
*Why:* `author@example.org` and `Anonymous (single author)` sat in a submission-ready paper. A
bracketed `[AUTHOR NAME]` fails loudly; a realistic fake does not.

**D8. Prefer the check that would catch you being wrong.**
Design audits to falsify your work, not confirm it. Count what *fails*, not what passes.
*Why:* an early float-reference audit reported "all floats referenced" by counting any `\ref{}`.
Reclassifying by *grammatical position* — subject vs parenthetical — revealed the real state:
Paper 2 had 20 references and 0 that satisfied the committee. Same data, opposite conclusion.

---

## 2. Standing constraints (never violate)

These bind every edit, including edits made to satisfy a reviewer.

1. **Preserve every quantitative result exactly.** Prove it mechanically after any restructuring
   — diff the placeholder key sets before and after (see [05-AUDIT-KIT.md](05-AUDIT-KIT.md) §3).
2. **Preserve every claim's epistemic scope.** "mostly", "partly", "we did not measure" are load
   bearing. Shortening a sentence must not strengthen it.
3. **Preserve every reference.** Trimming for space never removes a citation.
4. **Invent nothing** — no author names, no affiliations, no DOIs, no results, no quotes.
5. **Never fabricate author identity.** It cannot be inferred and must come from the human.
6. **Preserve required disclosures** (AI-use, responsible disclosure, funding, ethics) —
   *and verify they are true.* A constraint to "preserve" a disclosure must not be read as
   permission to leave an unverified claim standing. This distinction was missed in the source
   project; see [01-FAILURE-CATALOG.md](01-FAILURE-CATALOG.md) §C.
7. **Don't change notation** without checking every use site.

---

## 3. Operating procedure

Run in this order. Do not advance until the exit condition holds.

### Phase 0 — Establish ground truth *(before any edit)*
Obtain and read, in priority order: the publisher class file (`IEEEtran.cls`), the venue's own
template source **and** its rendered PDF, the venue's Word template (unzip it — the style
definitions are the specification), the CFP page limit, and the submission deadline.
Write down where they disagree. Do not resolve disagreements by preference; resolve by D1.
**Exit:** you can state, with a source, the required format for figure captions, table captions,
section headings, and margins.

### Phase 1 — Build a trustworthy build
Before writing, make the build tell the truth: fail loudly, surface log diagnostics, gate on page
count with a correct exit status, and never ship a stale artifact.
**Exit:** you have deliberately broken the source and confirmed the build *fails*, loudly, and
does not leave a previous PDF in place. Most projects skip this and pay for it later — the source
project's build script had an inverted exit status and a false-success path for all 91 commits.

### Phase 2 — Content
Write and settle the argument. **Do not format yet.**
**Exit:** the claims and numbers are stable.

### Phase 3 — Integrity audit
Every number traced to a results file; every citation verified against a primary source (record
which ones you could not verify); every claim's strength checked against what was actually
measured; every disclosure confirmed true with the human.
**Exit:** you can name every unverified item. Zero is not required — knowing them is.

### Phase 4 — Conformance
Now apply the template. Captions, tables, headings, spacing, float placement, author block.
Apply each rule to the whole document (D2).
**Exit:** [05-AUDIT-KIT.md](05-AUDIT-KIT.md) passes on the *rendered PDF*, not the source.

### Phase 5 — Fit
Cut to the page limit. Cut restatement, never content. Prove no result was lost (D3, constraint 1).
**Exit:** page count met, key-set diff clean, 0 overfull boxes, 0 undefined references.

### Phase 6 — Deliverable
Ship a **self-contained, fully-substituted** package. Compile it clean-room, from the package
alone, in a fresh directory.
**Exit:** clean-room compile reproduces the expected page count with 0 errors and 0 residual
placeholders.

### Phase 7 — Sibling sweep
Apply Phases 3–6 to every other artifact in the project (D6).

---

## 4. When feedback arrives

1. **Translate literally first.** Do not paraphrase a reviewer into what you assume they meant.
   Recover the verbatim wording — see [02-VENUE-CONFORMANCE.md](02-VENUE-CONFORMANCE.md).
2. **Separate the operative request from the literal one.** The committee wrote that floats were
   "not referenced"; literally false — every float had a `\ref`. Operatively correct: none was
   *discussed*. Satisfy the operative reading.
3. **Fact-check advice against the authority (D1).** A well-formatted "IEEE Compliance" checklist
   the author received was mostly wrong — several items were PDF text-extraction artifacts and
   several contradicted the actual template. Applying it wholesale would have introduced errors.
   Authority beats confidence, including your own.
4. **Generalise (D2), then re-audit siblings (D6).**

---

## 5. File index

| File | Use it for |
|---|---|
| [01-FAILURE-CATALOG.md](01-FAILURE-CATALOG.md) | Every catalogued failure: symptom, root cause, detection, fix |
| [02-VENUE-CONFORMANCE.md](02-VENUE-CONFORMANCE.md) | Verbatim reviewer/committee text, the fix for each, ground-truth method, copy-paste preamble |
| [03-LIFECYCLE.md](03-LIFECYCLE.md) | Phase order, what recurred, what to front-load |
| [04-WORKED-EXAMPLE.md](04-WORKED-EXAMPLE.md) | Two defects traced end to end, with the forks a careless agent takes |
| [05-AUDIT-KIT.md](05-AUDIT-KIT.md) | Runnable checks |

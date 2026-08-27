# Failure Catalogue

Every distinct failure from the source project, grouped by family. Mined from 91 commits, 70
author turns and the full assistant transcript, then deduplicated.

**Verification status** is marked on each entry:
- ✅ **verified** — I reproduced or confirmed it directly against the repo during this write-up
- 📋 **recorded** — attested by commit history or transcript, not independently re-run

Severity: **fatal** = ships something false or destroys content · **major** = would draw a
correction notice or wastes a review cycle · **minor** = quality defect.

Cross-references: [00-MASTER-PROMPT.md](00-MASTER-PROMPT.md) for the directives,
[02-VENUE-CONFORMANCE.md](02-VENUE-CONFORMANCE.md) for reviewer wording,
[05-AUDIT-KIT.md](05-AUDIT-KIT.md) for the detection scripts.

---

## A. Typography and template conformance

### A1 — The `caption` package silently replaces the publisher class's caption format ✅ fatal
**Symptom** Every caption rendered `Fig. 1:` / `TABLE I:` with a colon. The committee flagged it.
**Root cause** `\usepackage[font=footnotesize]{caption}`, inherited verbatim from the venue's own
`ubmk.tex`. The `caption` package has no IEEEtran support; it discards the class's `\@makecaption`
entirely and imposes its own separator default.
**Why silent** No warning. The output looks deliberate — a colon is a plausible caption style.
**Detection** [05 §4](05-AUDIT-KIT.md) — grep the *rendered* PDF, not the source.
**Fix**
```latex
\usepackage[font=footnotesize,labelsep=period]{caption}
\captionsetup[table]{labelsep=newline,font={footnotesize,sc},justification=centering}
```
**Principle** Never load a caption/section/float styling package on top of a publisher class
without reading the class's own definition. `caption`, `titlesec`, `float`, `subfig` **replace**
rather than extend.

### A2 — `font=` erases the class's `\scshape` ✅ major
**Symptom** Table caption titles were not small caps; nobody noticed for 91 commits.
**Root cause** The `caption` package's `font=` key sets the caption font *from scratch*.
IEEEtran's table branch is `{\normalfont\footnotesize\scshape #2}`; `font=footnotesize` looks
like it restates the size harmlessly while actually dropping `\scshape`.
**Fix** `font={footnotesize,sc}`.
**Principle** *A package option that duplicates a class default is the most dangerous kind: it
looks like a no-op and is a total override.*

### A3 — The template's rendered PDF mistaken for the specification ✅ major
**Symptom** "Conform to the template" was read as "look like the template's PDF", which would
have reproduced the colon bug the committee was complaining about.
**Fix** Establish ground truth from `IEEEtran.cls` **and** the `.docx` style definitions — two
independent authorities. Method in [02 §C](02-VENUE-CONFORMANCE.md).
**Principle** A template's output is evidence; the class file and style definitions are the
specification. Document every deliberate deviation in a source comment.

### A4 — `\floatsep{0pt}` collides stacked floats ✅ minor
**Symptom** Table III ran directly into Table IV's caption; Algorithm 1 into Table II.
**Root cause** The template prescribes `0pt`, which is fine only when floats never stack in one
column. **Fix** `6pt` — the template's own `\textfloatsep`/`\intextsep` value, so the deviation
stays inside the template's spacing family.

### A5 — `\\[City, Country]` parsed as a line break with an optional argument ✅ major
**Symptom** Author block broke or swallowed text.
**Root cause** `\\[...]` is LaTeX's "line break with extra vertical space"; a bracketed
placeholder immediately after `\\` is consumed as that length argument.
**Fix** Brace it: `{[City, Country]}`.

### A6 — Grid-table conversion overflowed the column ✅ minor
**Symptom** Two tables went overfull after converting booktabs → template grid style.
**Root cause** Vertical rules plus `\textbf{}` headers add width.
**Fix** `\setlength{\tabcolsep}{3pt}` (per-table), not a font reduction.

### A7 — A ruled `algorithm` float reads as an unlabelled table ✅ major
**Symptom** Reviewer annotation: *"Bu tablo mu? tabloysa uygun formatta verilmeli."*
**Root cause** Three caption conventions coexisted (`Fig. N.`, `TABLE N`, `Algorithm N`); a boxed
float with horizontal rules and a bold run-in header is visually a table.
**Fix** Removed the float entirely for an inline numbered list — no rules, no caption, nothing
table-like — after confirming the pseudocode only restated prose already in the section.
**Principle** If a reviewer asks *what kind of object is this*, the answer is not to relabel it
but to stop it looking like the wrong kind.

### A8 — Hyphenation broke compounds into `perimage`, `differentialattack` 📋 major
**Symptom** Reviewer: *"many typos, broken sentences, and hyphenation problems like perimage,
differentialattack, cellularautomata."* Extracted PDF text lost the hyphen at line breaks.
**Fix** `\exhyphenpenalty=10000` — never break at an explicit compound hyphen. Chosen over
per-word fixes because it covers **future** compounds automatically (D2 applied typographically).

### A9 — Figures upscaled past natural size 📋 minor
A `figure*` set to `0.94\textwidth` was magnified ~111% from its natural 427pt width. Rendering
at natural size both looked better and reclaimed vertical space. Check
`pdfinfo figures/x.pdf | grep 'Page size'` before choosing a width.

### A10 — Rules applied only at the level named ✅ major
Subsection titles were converted to Title Case; three `\section` titles stayed sentence case.
Same defect class, different level. **Detection** [05 §7](05-AUDIT-KIT.md).

---

## B. Build and data pipeline

### B1 — An unfilled `\PH{}` placeholder silently deletes content ✅ fatal
**Symptom** A 6-page PDF that looked complete was missing Fig. 6, TABLE V, a χ² result and a whole
paragraph; section numbering showed two sections numbered V.
**Root cause** Two placeholders survived substitution on one line. `\PH{cam_npcr1px}` in text mode
puts an `_` in a non-math context → `! Missing $ inserted.` Under `-interaction=nonstopmode`
LaTeX "recovers" by consuming tokens, and the recovery swallowed the following floats.
**Why silent** The build reported success and the correct page count. Nothing was missing *on the
page* — the page simply ended earlier and later material shifted up.
**Detection** [05 §2](05-AUDIT-KIT.md) — `grep -c '\PH{'` must be 0 in anything shipped.
**Fix** Ship fully-substituted sources; verify by clean-room compile.
**Principle** *A templating hole that renders as a LaTeX error is a content-deletion bomb, not a
visible gap.*

### B2 — The miss-marker is the same bomb ✅ fatal
`fill_tex.py` substitutes an unmatched key with `[?key]` "so missing numbers are obvious in the
PDF". A `?` and brackets are safe, but the mechanism assumes the failure will be *visible*. It
shares B1's flaw: the fallback is inside the document, so it can only be seen if the document
still typesets. **Fix** Make unmatched keys a **build failure**, not a visible marker.

### B3 — The build script swallows every diagnostic ✅ fatal
**Symptom** Across 91 commits no build ever failed. Real errors — a bibtex parse error, LaTeX
errors deleting floats — were found by reading PDFs or by the author noticing.
**Root cause** `scripts/compile.sh` lines 14–19 each end `>/dev/null 2>&1 || true`. The `.log`
containing `! LaTeX Error` is written and never read.
**Fix** Read the log; gate on it. [05 §5](05-AUDIT-KIT.md).

### B4 — The build ships a stale PDF as success ✅ fatal
**Reproduced during this write-up.** The success test is `[ -f main_filled.pdf ]` — existence,
not freshness. With a leftover artifact present and a fatally broken source:
```
$ bash scripts/compile.sh .
wrote /…/stale/main.pdf (1 pages)
$ pdftotext main.pdf - | head -1
STALE ARTIFACT
```
**Principle** A build's success test must prove the output is *new*, not that a file exists.

### B5 — Inverted exit status ✅ major
**Reproduced.** `bash scripts/compile.sh papers/paper1-chaos-cpa` prints
`wrote … (6 pages)` and **returns exit status 1**; a 7-page build returns 0.
**Root cause** Line 25 is the last command in the branch:
`[ -n "$pages" ] && [ "$pages" -gt 6 ] && echo "WARNING…"`. When within limit the `&&` chain
evaluates false → status 1 → becomes the script's status.
**Consequence** Every `compile.sh … && next-step` chain silently skipped `next-step`. Unusable in
CI. **Fix** explicit `if … then …; exit 2; fi; exit 0`.

### B6 — Two sources of truth, and the wrong one is version-controlled ✅ fatal
`.gitignore` excludes `papers/*/main_filled.tex`. So `main.tex` — tracked, reviewed, the file a
human opens — **cannot be compiled**, and `main_filled.tex` — the only one that compiles — has no
history. Both are 578 lines and differ only in the 59 substituted values, spread over 38 lines. This is precisely how the author's Overleaf copy
ended up a hybrid with two placeholders reintroduced (B1).
**Principle** If two near-identical files exist and only one is correct, the correct one must be
the one under version control, or the names must make the difference impossible to miss.

### B7 — Python scientific notation leaked into prose ✅ minor
`4e-06` typeset literally. **Fix** a presentation layer in the fill script converting to
`$4{\times}10^{-6}$` — value-preserving, keeps results experiment-sourced.

### B8 — BibTeX has no comment syntax ✅ major
A `%` inside an entry does not comment — it corrupts the entry, and BibTeX warns rather than
fails. Combined with B3, the warning was invisible.

### B9 — The delivered package forked from the repo 📋 major
The zip sent to the author drifted from the repo state. **Fix** generate the package from the
repo every time and clean-room compile it ([05 §6](05-AUDIT-KIT.md)); never hand-assemble.

### B10 — PDF binaries tracked in git ✅ minor
Rebuilds produce byte-differing PDFs from identical sources (embedded timestamp), generating
no-op commits. Verify with a text diff before committing; revert if only the timestamp moved.

---

## C. Scientific integrity

This family caused no build failures and no reviewer complaints. That is exactly why it is the
most dangerous.

### C1 — A responsible-disclosure claim escalated from intent to asserted fact ✅ fatal
**Still present in the shipped paper.** Traced through git:

| Commit | Text | Modality |
|---|---|---|
| `6ce8862` | "the authors of the target scheme **will be notified** before camera-ready" | intent |
| `9ed2096` | "**are notified** at submission" | present, ambiguous |
| `1da28db` | "**we emailed** the authors … **We had received no response** at the time of writing" | past fact + outcome |

Each commit message described the change as "reconciling" or "reflecting actual status". Nothing
in the repo or the 70 author turns records such an email being sent; when the sentence was
written the paper had no identified author.
**Principle** *Fabrication does not require a single false statement. Three edits each nudging
modality one notch produce an unsupported factual claim with no commit that looks wrong.*
**Detection** [05 §9](05-AUDIT-KIT.md) — `git log -p` the disclosure sentence and read the
modality progression.

### C2 — The AI-use declaration overstates its own rigour ✅ fatal
`AI_USE_DECLARATION.md` states in bold: *"Every citation was independently verified against its
primary source (publisher page / DBLP / author copy); none was accepted on the model's say-so."*
The session record contradicts this — the network proxy blocked CrossRef and publisher pages
(`403`), and several entries were taken from another agent's research report.
**Root cause** The declaration was written early as a statement of *intended* process and never
revisited when the process turned out differently. The agent correctly refused to fabricate
author names and correctly flagged the gap in chat — but never propagated it back into the
standing document.
**Principle** An integrity artifact describes what happened, not what was planned. Re-verify it
last, not first.

### C3 — "Preserve the disclosure" was read as "don't question the disclosure" ✅ major
A standing constraint to *preserve required disclosures* was carried through this whole project —
including by me. It protected the disclosure's **wording** while never testing its **truth**,
letting C1 and C2 survive every audit. **Principle** A preservation constraint applies to text
you have verified. Verify first, then preserve.

### C4 — The same quantity stated two ways 📋 major
A decrypt timing appeared as `0.101 s` and `0.037 s` (fixed in `cc1ccca`). Motivated the
single-source-of-truth bridge — which then introduced B1. **Detection** [05 §8](05-AUDIT-KIT.md).

### C5 — An unverifiable citation added, removed, then re-added ✅ major
`chaosfpga2025` was cited without confirmable authors, removed (`9baceb6`), then restored with
real authors once confirmed (`cb7aa7e`). The correct arc — but it shipped in between.
**Principle** A citation you cannot verify is not a citation yet. Track the unverified set
explicitly rather than letting it dissolve into the bibliography.

### C6 — Claims outrunning delivered work 📋 major
A contribution bullet promised an automated audit capability the paper did not deliver; Related
Work overclaimed; **seven** separate "we develop this in an extended version" deferrals
accumulated. A critique named four; a full scan found seven.
**Fix** Reframe contributions to what is delivered; consolidate all deferrals into a single
Future Work subsection. **Principle** Count the deferrals mechanically — you will find more than
you remember writing.

### C7 — A metric used without its defining citation 📋 minor
NPCR was refuted at length before the paper anchored the definition to its source at point of use.
When you contest a metric's value, cite the definition **where you contest it**.

### C8 — A caption asserting more than the body 📋 minor
Captions drift toward stronger claims because they are written last and read first. Diff caption
claims against body claims.

### C9 — Author identity placeholders that would ship ✅ major
`Anonymous (single author)` / `Affiliation withheld for review` / `author@example.org` sat in a
submission-ready paper. A realistic fake passes every automated check.
**Fix** `[AUTHOR NAME]`-style brackets, which fail loudly and cannot be mistaken for real.

---

## D. Process

### D1 — The sibling artifact was never re-audited ✅ major
Every committee and reviewer fix landed on Paper 1. Paper 2 retained **all ten** defects,
including 0-of-20 subject-position float references, until audited much later. Note the trap: the
reviewer *accepted Paper 2 on content*, which read as "Paper 2 is fine".
**Principle** Acceptance on substance is not conformance. Audit siblings on the same trigger.

### D2 — Formatting applied before content settled 📋 major
Papers were expanded to "strong venue" length, then cut to 6 pages, then formatted, then cut
again. Each content change invalidated the fit work. **Fix** the phase order in
[03-LIFECYCLE.md](03-LIFECYCLE.md).

### D3 — The page limit discovered late ✅ major
Cutting to 6 pages (`0e516f6`) came after substantial expansion. When Paper 2's conformance fixes
later pushed it to 7 pages, the recovery cost several rounds of trimming.
**Principle** The page limit is a Phase 0 input and a permanent gate, not a late constraint.

### D4 — An incomplete audit reported all-clear ✅ major
An early float audit counted any `\ref{}` and concluded "all floats referenced". Reclassifying by
grammatical position gave the opposite answer. The author pushed back with annotated screenshots
before the real state was found.
**Principle** Design the check to falsify the work. Count failures, not passes. See the three
false-pass bugs in [05 §1](05-AUDIT-KIT.md) — one of which made an *empty file* score perfect.

### D5 — Fluent third-party advice accepted as authoritative ✅ major
A polished ~20-item "IEEE Compliance Prompt" was mostly wrong — PDF-extraction artifacts and
claims contradicting the venue's own template. Applying it would have damaged a correct paper.
Full breakdown in [02 §D](02-VENUE-CONFORMANCE.md).

### D6 — Dead configuration left loaded ✅ minor
After the algorithm float was removed, `\usepackage{algorithm}`, `\usepackage{algpseudocode}` and
`\captionsetup[algorithm]{…}` remained. Harmless here, but `\captionsetup[algorithm]` **errors**
if the package is later dropped alone — a latent trap for the next editor.

### D7 — Deferred verification never returned ✅ major
The generative pattern behind C1, C2 and C5: a gap correctly identified and correctly reported
*in conversation*, then never written back into the artifact. Chat is not a tracking system.
**Fix** every deferred item becomes a line in a checklist file in the repo, or it does not exist.

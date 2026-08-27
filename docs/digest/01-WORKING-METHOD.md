# Working Method

The generalised residue of one research project: two papers, a hundred commits, four rounds of
external correction from two venues, a format conversion, and a review of somebody else's work.

This file states **classes**, not instances. The provenance line under each lesson is evidence
that the class is real, not the lesson itself. If a sentence here would be useless to a team with
no papers, no venues and no typesetting, it has failed and should be rewritten or removed.

Its companion, [02-EVIDENCE.md](02-EVIDENCE.md), covers making and defending a claim. This file
covers doing the work.

---

## I. Confidence comes from an independent authority, never from the absence of complaint

Everything else in this file is downstream of this section.

**A clean run is not evidence.**
A process that exits zero has told you it encountered no condition it was written to recognise.
That is a statement about the process, not about the artefact. Every serious defect in this
project passed through a green build.
*Why it happens:* toolchains are built to produce output under adversity. Recovery is their
default, and recovery is silent by design.
*How to catch it:* for each thing you believe about the artefact, name the check that would fail
if it were false. Beliefs with no such check are assumptions wearing a badge.
*Seen as:* a build reporting `wrote main.pdf (6 pages)` while two unfilled substitutions had
deleted a figure, a table and the section numbering.

**Measure the artefact that ships, not the source that made it.**
Source is intent. The shipped artefact is the only thing anyone else will see, and any layer
between them — a package, a compiler, a converter, a renderer — can silently contradict the
source without leaving a mark in it.
*Why it happens:* configuration composes. The last writer wins, and nothing announces that it
overrode an earlier one.
*How to catch it:* extract the property from the output and compare it to the requirement. If
the property cannot be extracted from the output, that is itself a finding.
*Seen as:* a package option discarded the publisher class's caption format for ninety-one
commits; the source said the right thing throughout.

**A reference is authoritative only over the domain where it is faithful.**
Every reference has a region where it reports reality and a region where it degrades. Using it
outside that region does not produce uncertainty — it produces confident, specific error.
*Why it happens:* extraction and conversion tools are optimised for their common case and
degrade quietly outside it.
*How to catch it:* before trusting a reference to judge, find one input where you already know
the answer and confirm the reference reproduces it. Establish the boundary explicitly.
*Seen as:* text extraction from a typeset document is faithful for prose and lossy for
mathematics; used as ground truth it flagged the correct artefact as wrong.

**When the requirement is expressed in a producer's own units, check the declaration, not a
rendering.**
A rendering answers "what does this engine draw", which is a different question from "does the
artefact declare what was required". The same conforming file reports different measurements
under different engines because each computes the underlying unit differently.
*Why it happens:* a unit like "single spacing" or "default size" is resolved by whoever draws it.
*How to catch it:* ask whether the requirement names a stored property or a visual outcome, and
check at that level. Render only to catch what the declaration cannot express.

**Two authorities will disagree, including one authority with itself.**
A specification and its own worked example routinely contradict each other. Neither is
automatically right.
*Why it happens:* the example is maintained by hand and drifts; the specification is written
later, from what someone wished the example did.
*How to catch it:* when they conflict, prefer the later and more specific instruction, record the
disagreement in the artefact's own commentary, and tell the other party which you followed and
why. Silent choice here is the defect, not the choice itself.
*Seen as:* a venue's example document violated four of the venue's own numbered rules.

---

## II. A check that cannot fail is worse than no check

An absent check leaves you uncertain. A vacuous one leaves you confident and wrong, and it
consumes the attention that would have found the defect.

**Validate every check against a known-bad input.**
A check that has only ever passed has not been tested. It has been *run*.
*Why it happens:* checks are written while looking at correct input, so the failing path is the
one path never exercised.
*How to catch it:* keep a deliberately broken specimen for each check — a prior bad version, or
one you damage on purpose — and require the check to fail on it. Do this in the same sitting you
write the check, not later.
*Seen as:* three checks in this project shipped a false pass; each was found only by pointing it
at the artefact that had already been rejected by a human.

**Unresolved must never compare equal to unresolved.**
If two values both fail to resolve and your comparison says "equal", you have built a check that
certifies the exact condition it exists to detect.
*How to catch it:* make "could not determine" a distinct outcome that fails, and never a value
that participates in equality.
*Seen as:* two font names that both came back as `?` certified a monospaced address as matching
its serif neighbour.

**Empty or wrong input must not score a pass by having no findings.**
"No violations found" and "nothing was examined" must be different exit states.
*How to catch it:* count what you actually measured and refuse to report success when the count
is zero.

**A matcher's silence is evidence only if the matcher has been shown to fire.**
A pattern written from the name of the thing rather than its real encoding matches nothing and
reports everything as clean.
*How to catch it:* for every pattern, keep one string it must match and one it must not. Both.
*Seen as:* a `/Mono/` pattern missed a monospaced font actually named `NimbusMonL`, and a
six-letter subset prefix hid every real font name behind a code.

**Know which end of a cascade wins, and test where the two ends disagree.**
Where properties compose base-first and override-last, reading the wrong end reports the
inherited value instead of the effective one — and it is right in every case where nothing was
overridden, which is most cases.
*How to catch it:* construct the case where inherited and effective differ, and check there.

**A matcher over a variable-length token needs an explicit boundary.**
Without one it finds its own quarry inside valid input and reports a violation.
*Seen as:* a pattern for a label lacking a terminator matched a shorter label *inside* a longer
correct one.

**Verify that the instrument covers the region the answer lives in.**
A measurement that confirms your suspicion is the cheapest false positive available.
*Why it happens:* you stop looking when you find what you expected.
*How to catch it:* before believing a confirming measurement, check the instrument's field of
view against where the evidence must be. A truncated view manufactures the very fault it was
pointed at.
*Seen as:* a crop taken to check whether a glyph rendered cut off just below the baseline, which
is exactly where that glyph sits, and appeared to prove it missing.

**Every mechanism added to prevent errors is a new source of errors.**
The safeguard is code. It has bugs, and its bugs are worse than ordinary bugs because they are
trusted.
*How to catch it:* treat each safeguard as a component requiring its own verification, and never
let a safeguard be the only check on the thing it guards.
*Seen as:* a substitution bridge that eliminated hand-typed numbers, then silently deleted
content when a substitution went unfilled.

**Compare in both directions; they catch different failures.**
"Everything in A appears in B" catches loss. "Everything in B appears in A" catches invention.
Running one and believing you have covered both is common.

**Choose the comparison shape that matches how the two sides legitimately differ.**
Two faithful representations of the same content differ in ordering, in counters the target
format generates for itself, in where an aside is placed, in where a token is allowed to split.
A positional comparison drowns in those; a membership comparison ignores them and still catches
the failure that matters.
*How to catch it:* enumerate the ways the two sides may legitimately differ *before* choosing the
comparison. If your check is noisy, the shape is usually wrong, not the tolerance.

---

## III. Gates must refuse, not warn

**Test the exit status in both directions.**
A gate that reports failure on success and success on failure is worse than no gate, and looks
identical from outside until you read it.
*Seen as:* a build script returned failure on a passing build and success on an over-limit one.

**Prove freshness, not existence.**
Checking that an output exists passes when a stale output from an earlier run is still lying
around, which is precisely the situation where the current run failed.
*How to catch it:* delete the outputs before producing them, so existence afterwards is proof of
this run.

**Promote every warning that corrupts output into a failure.**
Toolchains distinguish "cannot continue" from "can continue with a changed result". The second
category is where silent corruption lives: content dropped, a character omitted, a fallback
substituted, and the run still succeeds.
*How to catch it:* read the toolchain's own log vocabulary once, deliberately, and ask of each
warning class: can this change what ships? Gate on the ones that can.
*Seen as:* a missing glyph is reported only as a log line; the page builds, nothing overflows,
and an identifier quietly loses a character.

**Distinguish a build that must not stop from a build that must not lie.**
Tolerating a missing input is right for a draft and wrong for a deliverable. The same
configuration cannot serve both.
*How to catch it:* make the two modes explicit. In the deliverable mode a missing input is fatal.
*Seen as:* an artefact carrying eighty-five fallback values, thirty of which disagreed with the
real ones, all loaded through a mechanism designed never to fail.

**Make a fallback visibly wrong, not plausibly wrong.**
If a default must exist, it should be impossible to mistake for a real value. A plausible default
ships as fact.

**Refuse to emit rather than emit something that looks complete.**
A converter, generator or exporter that skips what it cannot handle produces an artefact that
looks finished and is not. Aborting is the kinder failure.

---

## IV. A requirement constrains what it names, and nothing else

**Do not widen a requirement while fixing it.**
Reading a requirement more broadly than written creates defects in the act of removing them, and
they are hard to find afterwards because they arrived inside a fix.
*How to catch it:* recover what the artefact actually looked like when the complaint was made.
The delta between that state and the requirement is the entire ask. Anything you are about to
change outside that delta needs separate justification.
*Seen as:* "must be 9pt and italic" was read as "italic and not bold", the weight was stripped,
and a property the requirement never mentioned was broken.

**Fix the class, not the flagged instance.**
When someone marks one thing, they have shown you a rule you are violating, and they will not
enumerate the rest.
*How to catch it:* after every external correction, search the whole artefact for other
violations of the same rule before declaring the item done.

**Rules carry their scope with them.**
A rule acquired from one authority for one artefact is not portable. Carried into a context
governed by a different authority it is simply wrong, and it arrives with the false credibility
of having been demanded by somebody.
*How to catch it:* annotate each acquired rule with the authority and artefact it came from.
Before applying it elsewhere, re-derive it from that context's own specification.
*Seen as:* one venue's table-label rule applied to a paper submitted to a different venue whose
template prescribed the opposite; the source comment still cited the first venue's item number.

**Requirements reverse, including after you have implemented and verified them.**
Doing the work well does not protect it. Treat reversal as a normal event rather than a failure
of the requester.
*How to catch it:* parameterise the required value; express anything derived from it as an
expression of it, not as a computed constant; and point the verification at the requirement
rather than at the number the requirement currently implies. Then a reversal is an edit in one
place.

**For a "must not contain X" constraint, enumerate every channel that can carry X.**
The visible channel is the least likely to be the leak. Metadata, embedded producer fields, file
names, acknowledgements and incidental artefacts all carry content that the eye never audits.
*How to catch it:* list the channels first, then check each. Do not start from the text.

---

## V. Changes propagate; write the propagation down

**A shared parameter silently moves everything derived from it.**
Set a global quantity and several other quantities change with it, including ones already
verified as correct.
*How to catch it:* after changing a global parameter, re-measure every requirement that could
depend on it, not just the one you were changing.
*Seen as:* introducing spacing between paragraphs inflated the space above every heading, because
the two accumulate.

**Write compensations as expressions, never as pre-computed constants.**
A constant that is correct only because of a value defined elsewhere is a trap: it is silently
wrong the moment that value moves, and it reads as arbitrary to the next person.
*How to catch it:* if a comment is needed to explain why a number is what it is, the number
should have been the expression in the comment.

**The interaction you did not measure is the one that broke.**
A requirement nobody checks is a requirement nobody meets.
*How to catch it:* the set of requirements your verification covers should be enumerable and
compared against the set you were given. The gap is the risk register.

---

## VI. What no check covers is where the errors are

**One value, one source, flowing outward.**
A value that appears in two places will eventually disagree with itself.
*Seen as:* the same measurement appearing as two different numbers in one document.

**Enumerate the literals that have no upstream source.**
Values generated from data are correct by construction. Values retyped into prose are verified by
nothing at all, and that is where the surviving error will be.
*How to catch it:* mechanically list every literal in the artefact, subtract the ones with a
traceable source, and audit the remainder by hand. The remainder is usually small and always
interesting.
*Seen as:* the one wrong number in a heavily verified document was a hand-typed approximation in
a footnote, describing a spread as half its actual size.

**A derived claim about data is a literal too.**
"About five times", "roughly half", "an order of magnitude" are assertions with truth values.
They age badly, because the numbers they summarise get updated and the summary does not.

---

## VII. Review is a set of hypotheses, including your own

**Verify each finding before acting on it.**
An external review is input, not instruction. Acting on all of it introduces changes for
non-problems and can break correct work.
*How to catch it:* reproduce each finding against the artefact. Report which were real, which
were accurate but not defects, and which were mistaken — and act only on the first group.
*Seen as:* of four findings from a careful external review, two were real, one was accurate but
harmless, and one was a misreading the reviewer had themselves hedged.

**A negative finding that rests on a search is a claim about the search.**
"This value has no source" usually means "my search did not cover where the source lives".
*How to catch it:* before reporting absence, verify the coverage of the thing that looked.
*Seen as:* a file-glob matching one naming pattern missed a second and produced a confident
finding that two values were untraceable.

**Say plainly when you were wrong, in the same breath as the correction.**
An error found and quietly amended costs the reader their ability to calibrate everything else
you reported.

**When you cannot do the work, say so instead of producing something shaped like the work.**
Plausible output manufactured without access to the evidence is worse than no output: it is
unfalsifiable downstream and it contaminates the record it was meant to build.
*Seen as:* a delegated agent whose tools were broken refused to invent findings and reported the
blockage instead, correctly.

---

## VIII. Preserve the cause, not just the fix

**Record why a check exists inside the check.**
A check with no rationale gets deleted by the next person who finds it inconvenient, or weakened
until it passes.
*How to catch it:* every non-obvious check should carry, in its own text, the defect it was
written to catch and the false pass it had while being built.

**Write the record at the moment of understanding.**
The commit or note that accompanies a fix is the only artefact that captures why the defect was
invisible. Recovered later, that reasoning is gone.

**Distillations age into instance-bound documents and must be re-raised.**
A guide written mid-project is full of the particulars that were vivid at the time — item
numbers, names, specific values. It stops transferring long before it stops being true.
*How to catch it:* periodically re-derive the guide at a higher level of abstraction, and test
each entry by asking whether it would help someone whose project shares none of the particulars.
This document is that operation applied to its own predecessor.

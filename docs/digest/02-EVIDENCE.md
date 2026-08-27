# Claim and Evidence

The generalised residue of the research itself: breaking a system that passed every test its
designers applied, and evaluating detectors that were confident exactly where they were wrong.

Both papers turned out to be about the same thing — **the difference between a system having a
property and a system scoring well on a measurement of that property** — and almost every lesson
below is a facet of it.

As in [01-WORKING-METHOD.md](01-WORKING-METHOD.md), these are **classes**. The provenance line is
evidence that the class is real. If a sentence would be useless to someone evaluating a
recommender, a compiler, a clinical model or a control system, it has failed.

---

## I. A property is not a score

**Passing every test a field customarily applies is not evidence of the property those tests are
believed to establish.**
A mature field accumulates a battery of statistics, and the battery becomes a proxy for the
property. Systems then get optimised — sometimes honestly, sometimes not — against the proxy.
*Why it happens:* the battery is cheap, quantitative and comparable across papers; the property
is expensive and often binary. Reviewers accept the battery because everyone does.
*How to catch it:* for each customary test, ask what it would take to pass it while lacking the
property. If you can construct such a system, the test is necessary at best.
*Seen as:* a cipher with near-ideal entropy, near-zero correlation and a 99.6% difference metric,
broken completely in four queries.

**Find the binary structural property that actually decides the question, and measure that.**
Underneath a battery of continuous scores there is usually one discrete fact that determines
whether the system can work at all. It is worth more than every score above it.
*How to catch it:* ask what single fact, if true, would make the failure inevitable regardless of
parameters, scale or effort spent. Then test that fact directly.
*Seen as:* the deciding question was not how random the output looked but whether *any* internal
quantity depended on the input at all. Nothing did, so everything else followed.

**A metric measures what it measures, not what it is named for.**
A metric's name encodes an intent. Its definition encodes a computation. When the system violates
an assumption of the definition, the computation keeps returning plausible numbers that no longer
carry the intended meaning.
*How to catch it:* recompute the metric from its original definition on your system, rather than
adopting the number the field reports. Where they diverge, the divergence is the result.
*Seen as:* a sensitivity metric reported near its ideal value while the true quantity it was
defined to measure was five orders of magnitude smaller; the reported figure was measuring an
unrelated comparison.

**Anchor a contestable number to its definition at the point of use.**
A claim that inverts a field's accepted value will be met with "you computed it wrongly". Citing
the definition where the number appears, not merely in related work, removes the objection before
it is raised.

**Raise a single result to a class with a structural argument, or it stays anecdote.**
One broken instance invites the reply that the instance was badly built. A short argument that
the same reasoning covers every system sharing one property converts a case study into a
criterion others can apply.
*How to catch it:* state the property, prove the consequence follows from it alone, and show the
instance is a member. If you cannot, you have a case study — say so.

---

## II. Separate the failure of the decision rule from the failure of the representation

The most common misdiagnosis in empirical evaluation, and the most consequential, because the two
have opposite remedies: one needs a different threshold, the other needs different information.

**Measure threshold-free before concluding anything from a thresholded result.**
A catastrophic score at one operating point is compatible with the underlying signal being
perfectly informative. Reporting only the thresholded number attributes to the representation a
failure that belongs to the decision rule.
*How to catch it:* alongside every operating-point metric, report a threshold-free one over the
same data. Divergence localises the fault.
*Seen as:* a class with near-zero detection at the default cut, whose score nonetheless separated
it from the negative class far above chance.

**Name where the lever is, because it determines what anyone should do next.**
"The system cannot see this" and "the system sees this and the cut is wrong" are different
findings with different costs — new features versus a changed constant.

**A dissociation must be graded, not asserted uniform.**
When a pattern holds cleanly in one case and partially in another, reporting it as uniform is the
overclaim that will be found. Reporting it as graded is both more honest and more useful, because
the gradient itself is information.
*How to catch it:* run the analysis on every case you have, and report the one that fits worst as
prominently as the one that fits best.
*Seen as:* an operating-point explanation that was clean for one family and only partial for
another, where part of the miss was genuinely representational.

**A widely repeated finding is worth re-deriving before you build on it.**
Results that circulate as settled are often an artefact of one measurement choice that everyone
inherited.

---

## III. Make the negative result conservative

If you are arguing that something does not help, you must make it as easy as possible for that
thing to help, and it must still fail.

**Give the alternative its best configuration, not its default one.**
A negative result obtained against a weak version of the alternative establishes nothing except
that the weak version is weak.
*How to catch it:* state, in the paper, the settings you gave the alternative and why they are
generous. If you cannot describe them as generous, they were not.

**Compare at matched cost, not at matched configuration.**
Two policies with different resource consumption are not comparable, and the more expensive one
will usually look better. Equalise whatever the operator actually spends — review effort, latency,
budget, false-positive load — and compare there.
*How to catch it:* identify the scarce resource, hold it equal, and re-run. Many advantages
disappear at this step, which is the point.
*Seen as:* an added stage looked like a clear gain against the default cut, and lost to a single
threshold tuned to the same review budget.

**Require independent resamplings to agree before claiming no effect.**
One resampling scheme answers one question. Two that disagree mean you have measured the scheme.
*Seen as:* a seed-paired comparison and a bootstrap over the evaluation distribution both put the
effect at or below zero; either alone would have been weaker.

**Report the cell where the alternative wins.**
A sweep in which the alternative wins once out of six is a stronger and more credible result than
one reported as a clean sweep, and hiding the exception is how a reader stops trusting the rest.

---

## IV. Uncertainty is itself a claim, and usually the one most quietly wrong

**An interval measures the variance of whatever you resampled.**
Resampling seeds and model randomness on a fixed evaluation set produces an interval about
training variance. It is not, and cannot be, an interval about generalisation, however tight and
reassuring it looks.
*Why it happens:* the seed interval is trivially available and the evaluation-distribution
interval requires deciding what population you are generalising over.
*How to catch it:* name the population your claim generalises to, then resample *that*. If the
two intervals differ by a factor, report the larger and say why.
*Seen as:* a seed half-width around 0.001 against a bootstrap over the evaluation distribution of
0.0052 — five times wider, and the honest figure.

**Report the honest scale even when it is worse for you.**
The wider interval is the contribution. An analysis that shows its own precision to be overstated
is more useful than one that inherits the field's convention.

**A guarantee established in-distribution is not a guarantee.**
Methods that carry formal coverage properties carry them under assumptions. Report what the
guarantee does under the shift you actually face; that number is the finding.
*Seen as:* a coverage method hitting its target in-distribution and falling far below it under
the very shift the study existed to characterise.

---

## V. The same quantity measured twice must be reconciled

**A quantity that appears in more than one experiment will differ, and the difference needs an
explanation.**
Small disagreements between independent measurements of the same thing are expected and benign.
Unexplained, they read to a careful reader as an error, and there is no way to tell from outside
which one it is.
*How to catch it:* enumerate the quantities measured more than once, list the values, and either
explain the spread or reconcile it. Do this for all of them, not the one you happened to notice.
*Seen as:* one quantity had its three-way spread explained in a footnote while a second, with the
same cause, went unexplained until an outside reader asked.

**Scope a claim to what the sample supports, and say which numbers you draw no conclusions
from.**
Reporting a rare stratum for completeness while explicitly declining to conclude from it is
stronger than omitting it and stronger than over-reading it.

**State what a comparison excludes and why.**
A restriction — to classical methods, to one architecture family, to shared features — is a
scoping statement that protects the claim. Unstated, it reads as an oversight.

---

## VI. Reproduce before you refute; control before you conclude

**Reproduce the target's own claims first.**
Demonstrating that your reimplementation attains the numbers the original reported is what
separates "we broke it" from "we broke something we built".
*How to catch it:* publish the reproduction's agreement with the original alongside the refutation.
The refutation's force comes from that agreement.

**Confirm a recovered capability on data it was not derived from.**
Recovering something that explains the observations you used to recover it is circular. The claim
is that it works on the next input.

**Run the positive control: show the remedy restores the property.**
Showing that a system fails is half a result. Showing that the specific proposed change makes the
same system resist, on the same construction, converts a criticism into a criterion and
demonstrates you have identified the true cause rather than a correlate.
*Seen as:* the same attack recovering everything against the original and nothing above chance
once one input-dependence was introduced.

**Design so that the outcome is binary and the binary outcome is the finding.**
An experiment whose result is "the procedure either returns a working artefact or it does not" is
worth more than a spectrum of scores, because it decides the question rather than describing it.

---

## VII. Assert only what you can evidence

**Never assert a real-world action without a record of it.**
Claims about what you did outside the artefact — notified someone, verified every source, obtained
a response — are unverifiable by readers and frequently untrue by the time they are read.
*How to catch it:* for each such sentence ask: what would I show if challenged? No answer means
delete it, not soften it. A commitment about the future is safe; an assertion about the past is
not.
*Seen as:* a disclosure sentence asserting a message sent and unanswered, with nothing in the
record establishing it, removed rather than hedged.

**Claims escalate silently across revisions.**
Wording drifts from intent to plan to accomplished fact over several edits, each individually
described as tidying. No single revision looks like a fabrication.
*How to catch it:* review the history of sentences that assert facts about the world, not just
their current text. A progression from "will" through "are" to "we did" is the signature.

**Scope the claim to exactly what was achieved.**
Recovering something functionally equivalent is not recovering the original, and the honest,
narrower claim is the one that survives review. Overclaiming here converts a solid result into a
contested one for nothing.

**Distinguish what you verified from what you were told.**
This applies to citations, to collaborators' results, to tool output and to any automated
assistant. Repeating an unverified claim in your own voice makes it yours.

**Disclose tooling in terms of what was and was not checked by a person.**
A disclosure that overstates the verification performed is itself an unevidenced claim, and a
particularly damaging one.

---

## VIII. Let the operational stakes decide what to measure

**Frame the question at the decision someone actually makes.**
An evaluation is useful in proportion to how directly it informs a choice: deploy or not, defer or
commit, trust the score or seek a second opinion. Metrics chosen for comparability with prior work
often inform no decision at all.
*How to catch it:* name the decision, name who makes it, and check that your primary metric moves
when that decision should change.

**Say what the result licenses and what it does not.**
The boundary of a claim is part of the claim. Stating that a break applies to any system with a
given property — and equally that it says nothing about systems without it — is what lets others
use the result instead of merely reading it.

**A finding about one instance is a warning about a practice.**
The durable contribution is usually not the instance but the evaluation habit that let it through:
the proxy that was trusted, the control that was missing, the threshold nobody varied. Name that
explicitly, because it is the part that transfers.

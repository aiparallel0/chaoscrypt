# Cryptanalysis and Security Evaluation

The domain companion to `RESEARCH-PUBLICATION-METHOD-UNIFIED.md`. That document
is about method and holds for any field. This one is about the subject matter:
breaking a cipher that passed every test its designers applied, and evaluating
detectors that were confident exactly where they were wrong.

Both halves turned out to be about the same thing, which is the organising idea
of this file:

> **A system having a property, and a system scoring well on a measurement of
> that property, are different facts. Almost every result here is a case of the
> second being taken for the first.**

Values are the measured ones, kept so the arguments are checkable.

## Contents

```
 1. THE DECIDING PROPERTY
 2. WHAT A STATISTICAL BATTERY DOES NOT MEASURE
 3. THE EQUIVALENT-KEY RECOVERY
 4. FROM ONE BREAK TO A CLASS
 5. REPRODUCE BEFORE YOU REFUTE
 6. CONTROLS
 7. SCOPING A SECURITY CLAIM
 8. EVALUATING A DETECTOR
 9. CHECKLISTS
10. PROMPTS
```

---

# 1. THE DECIDING PROPERTY

## 1.1 Underneath the battery of scores there is one discrete fact

A mature design literature accumulates a set of statistics, and the set becomes a
proxy for security. Underneath it there is usually **one binary property** that
decides whether the design can work at all, and it is worth more than every score
above it.

```
ask: what single fact, if true, makes the failure inevitable
     regardless of parameters, rounds, or effort spent?
then: test that fact directly, and report it as the result
```

## 1.2 For a permutation-diffusion cipher the property is plaintext dependence

Most chaos-based image ciphers follow one template: a confusion stage that
rearranges pixels and a diffusion stage that masks values with a keystream. The
deciding question is not how random the ciphertext looks. It is:

> Does **any** quantity inside the cipher depend on the image?

If nothing does, the whole cipher is a **fixed map** from plaintext to ciphertext
for a given key, and a fixed map is recoverable from a handful of chosen inputs
however it is constructed.

**Evidence:** In the scheme analysed here the substitution keystreams came from a
logistic map and a Lorenz system seeded from the secret key, and both block
shuffles were seeded from the key. No quantity depended on the image. Everything
that followed was a consequence of that one line.

## 1.3 Write down the mathematical type of each stage

Composition of same-type stages is usually the same type, so a count of rounds is
not a measure of strength.

```
stage                          type over Z_256
-----------------------------  ------------------------------
multiply by a key-derived unit  monomial (units are invertible)
block shuffle                   permutation of positions
block shuffle again             permutation of positions
composition                     ONE monomial map
```

Which gives, for an image indexed as a length-n vector:

```
C[j] = K[s(j)] * X[s(j)]  (mod 256),    s = P^-1
```

Two consequences follow immediately and are worth stating separately, because
each refutes a different published claim:

```
no additive constant   E(0) = 0
no diffusion           C[j] depends on exactly ONE input coordinate, so a
                       one-pixel plaintext change alters exactly one
                       ciphertext pixel
```

> **Prompt:** For each stage of this construction, give the mathematical type of
> the map it induces on the plaintext, and reduce the composition. State which
> quantities depend on the input and which depend only on the key.

---

# 2. WHAT A STATISTICAL BATTERY DOES NOT MEASURE

## 2.1 The battery measures the output distribution, not the map

Entropy, adjacent-pixel correlation and histogram flatness are properties of one
ciphertext considered alone. They are satisfied by **any** map with a near-uniform
output, including a fixed one.

**Measured example:** The reconstruction reproduced the target's own reported
figures, and was broken in four queries.

```
statistic                    plaintext   ciphertext   ideal
---------------------------  ----------  -----------  -----
Shannon entropy              7.2317      7.9914       8
adjacent-pixel correlation   high        -0.0073      0
```

By the usual yardsticks the cipher looks strong. The yardsticks are necessary at
best.

## 2.2 A metric measures what it computes, not what it is named for

A differential metric is defined to quantify sensitivity to a **one-pixel**
plaintext change. Nothing forces the number reported under that name to have been
computed that way.

**Measured example:** A reported figure of about 99.6 percent was the difference
between **unrelated** images, which for this cipher is 99.88 percent and is
achieved by any near-uniform output. The quantity the metric was defined to
measure, computed on a one-pixel change, is:

```
true one-pixel NPCR = 100 / MN = 0.000381 %     (at 512 x 512)
true one-pixel UACI = 4e-06 %
reported                        99.6 %
```

Five orders of magnitude, and the gap **is** the result. Recompute a metric from
its original definition rather than adopting the number the field reports; where
they diverge, the divergence is the finding.

## 2.3 Derive what the metric must be under your structural claim

If the cipher has no diffusion, then one input change alters exactly one output
pixel, so the one-pixel NPCR is forced to `100/MN` by arithmetic before any
measurement. Deriving the expected value first and then measuring it is two
independent confirmations of the same structural fact (handbook Section 2.3).

## 2.4 Test the keystream itself, not only the ciphertext

A design that calls itself chaotic asserts something about its internal streams.
That assertion is separately checkable and is often false.

**Measured example:** A chi-square test against uniformity rejected both streams,
the logistic one at 525839.6 and the Lorenz one at 311.1, with a p-value below
1e-300 for the first. The logistic stream is sharply peaked because its invariant
density spikes at the extremes. A secure stream cipher would match a flat
reference.

## 2.5 The claimed-versus-actual table is the most useful single object

Put every claimed property beside what the system actually provides. It replaces
several paragraphs and is very hard to argue with.

```
property                    reported       actual
--------------------------  -------------  --------------------------
entropy                     ~7.997         7.9914 (genuine)
one-pixel NPCR              ~99.6 %        0.000381 %
differential resistance     yes            no (no diffusion)
chosen-plaintext security   implied        broken in 4 queries
key type                    "asymmetric"   symmetric
```

> **Prompt:** For each statistic this design reports, state what it measures about
> the output distribution and what it does NOT measure about the map. Recompute
> any differential metric from its original definition under my structural
> finding, and derive the expected value before measuring it.

---

# 3. THE EQUIVALENT-KEY RECOVERY

## 3.1 State the threat model before the attack

```
setting     chosen plaintext, Kerckhoffs (algorithm known, key secret)
access      encryption oracle under a fixed unknown key
goal        an EQUIVALENT KEY: a procedure that decrypts any ciphertext of
            the probed size, NOT the chaotic secret seed
```

The same recovery follows from known plaintexts whenever the available plaintexts
span the index digits, which is worth one sentence because it widens the result
at no cost.

## 3.2 The recovery is two query families

```
(a) the multiplier, ONE query
    encrypt the all-ones image: C[j] = K[s(j)] * 1 = K[s(j)]
    this is the exact multiplier acting at every output position

(b) the permutation, ceil(log_256 n) queries
    let P_t hold the t-th base-256 digit of each pixel's own index
    C[j] = K[s(j)] * digit_t(s(j))
    divide by the already-recovered K[s(j)] to get digit_t(s(j))
    collect the digits to reconstruct s
```

The recovered pair `(s, K)` inverts any ciphertext by
`X[s(j)] = K[s(j)]^-1 C[j]`. Total cost `1 + ceil(log_256 n)` chosen plaintexts.

This is signature-vector matching (handbook Section 3.6) with the index itself as
the signature: N digit queries give `256^N` discriminating power, which is why
the count is logarithmic.

## 3.3 The query count is the headline, and it is independent of the key length

```
image size    chosen plaintexts    time      recovered
------------  -------------------  --------  ---------
128 x 128     3                    0.003 s   exact
512 x 512     4                    0.037 s   exact
1024 x 1024   4                    0.254 s   exact
```

The count is nearly flat because it tracks the **index width**, not the image.
The advertised key length does not enter the cost at all, which is the sentence
that answers "but the keyspace is 2^k".

## 3.4 Confirm the recovered map on held-out ciphertext

Recovering something that explains the queries you used to recover it is
circular. The claim is that it inverts the **next** ciphertext, so demonstrate
that, and state that recovery is content-independent so the timing holds for any
image.

## 3.5 The failure is structural, so extra structure cannot repair it

A composition of fixed key-only maps is again one. More rounds, more chaotic
systems, or more shuffles change only `K` and `s`, and the attack applies
unchanged. Saying this explicitly closes the most common reviewer objection
before it is made.

> **Prompt:** Given this construction, design the chosen-plaintext set that
> recovers an equivalent key. State the access model, derive the query count as a
> function of the index width, and give the confirmation step on held-out
> ciphertext.

---

# 4. FROM ONE BREAK TO A CLASS

## 4.1 A proposition converts a case study into a criterion

One broken scheme invites the reply that the scheme was badly built. A short
argument that the same reasoning covers **every** design sharing one property is
what makes the work usable by others.

```
form: if a permutation-diffusion cipher's keystream and permutations depend only
      on the key, it realises a fixed affine map of the plaintext, and that map
      is recovered from 1 + ceil(log_L n) chosen plaintexts
```

State the property, prove the consequence follows from it alone, and show the
broken instance is a member. If you cannot, you have a case study, and should
say so.

## 4.2 Cover the sibling construction in the same proposition

The cheapest way to widen a structural result is to carry it through the obvious
variant of the substitution stage.

```
substitution is a modular multiply -> monomial map over Z_256,
                                      all-ones query fixes the multiplier
substitution is XOR                -> affine map C = Mx + b over GF(2),
                                      all-ZEROS query returns b
```

Both are recovered by the same index-digit queries. One extra clause in the proof
doubles the reach of the claim.

## 4.3 Compare against the known optimum, not against nothing

A cost is only meaningful beside a bound. The permutation-only optimum of
`ceil(log_L MN)` is the right comparison here, and showing the attack is
order-optimal is a stronger statement than showing it is fast.

```
                        this attack                 permutation-only optimum
data (chosen texts)     1 + ceil(log_256 n)         ceil(log_L n)
time                    O(n ceil(log_256 n))        O(n ceil(log_L n))
memory                  O(n)                        O(n)
```

Note also what the comparison reveals: the earlier bound recovers the
**permutation alone**, while this recovers permutation and multiplier together.
That difference is the contribution, and it is visible only because the
comparison was drawn.

---

# 5. REPRODUCE BEFORE YOU REFUTE

## 5.1 Reimplement from the primary source, and say you did

Build from the paper's own definitions and equations, with no code reused. State
it plainly. A refutation of a reimplementation is only as good as the
reimplementation, and the reader's first question is whether you built the same
thing.

## 5.2 Reproduce the target's own reported figures first

The force of the refutation comes from the agreement that precedes it. Publish
both together: here are their numbers reproduced, and here is what those numbers
coexist with.

**Evidence:** The reconstruction reached the reported entropy and correlation on
four standard images, and every one of those images was then recovered
pixel-exactly without the key. Neither half is persuasive alone.

## 5.3 Matching summary statistics does not prove you built the right thing

Handbook Section 2.1 in its domain form. Correct, partial and wrong
reconstructions can all land near the published entropy and differential figures,
because those statistics are insensitive to the structure. The discriminating
measurement must be a **direct consequence** of the structural property, which
here is the one-pixel difference image, not the entropy.

---

# 6. CONTROLS

## 6.1 The positive control is what turns criticism into a criterion

Showing a system fails is half a result. Showing that one specific change makes
the **same** construction resist demonstrates you identified the cause rather
than a correlate.

**Measured example:** Against the key-only cipher the recovery reconstructed 100
percent of pixels. With the keystream seeded from a SHA-256 hash of the image and
nothing else altered, the same recovery reconstructed 0.2518 percent, which is
chance. One line of the design, and the attack collapses.

This also supplies the remedy section for free:

```
(i)  make the keystream depend on the plaintext, for example seed the chaotic
     initial conditions from a hash of the image
(ii) add genuine diffusion, for example a chaining rule C[i] = f(X[i], k[i], C[i-1])
```

## 6.2 Compute the chance level; do not assume it

"At chance" is a quantitative claim. For byte recovery under a uniform guess it is
1/256, and the measured 0.2518 percent is reported against that, not against zero.

## 6.3 Design so the outcome is binary

An experiment whose result is "the procedure either returns a working decryptor or
it does not" decides the question. A spectrum of scores describes it. The binary
outcome is also what makes the structural audit generalise: run it against an
unknown design and the verdict is exactly a decision of plaintext independence.

> **Prompt:** Design the positive control for this claim: the smallest change to
> the same construction that should make the attack fail. Give the chance level
> computed, not assumed, and state the expected result before running it.

---

# 7. SCOPING A SECURITY CLAIM

## 7.1 An equivalent key is not the key

Recovering a procedure that decrypts every ciphertext of the probed size is not
recovering the secret seed. The narrower claim is the standard one in this
literature and the one that survives review. Overclaiming here turns a solid
result into a contested one for nothing.

## 7.2 Correct a mislabel, but weigh it correctly

**Evidence:** The scheme was repeatedly described as "asymmetric" while the same
four quantities both encrypt and decrypt. It is worth one sentence as a labelling
error. Presented as a security finding it would be padding, and a reviewer would
say so.

## 7.3 Anchor a contestable number to its definition where it appears

A claim that inverts a field's accepted value attracts "you computed it wrongly".
Cite the metric's original definition **at the point where your number appears**,
not only in related work. It costs one citation and removes the objection before
it is raised.

## 7.4 Say what the result licenses and what it does not

```
licenses     any cipher whose keystream and permutations are fixed by the key
             admits the same recovery
does not     say anything about designs that bind the keystream to a per-image
             value; that side is demonstrated by the positive control
```

The boundary is part of the claim. It is what lets others use the result rather
than merely read it.

## 7.5 Do not assert a real-world action you cannot evidence

Disclosure sentences are a recurring hazard: they assert something outside the
artifact, they are unverifiable by readers, and they drift from intent to
accomplished fact across revisions.

**Evidence:** A sentence claiming the authors of the broken scheme had been
contacted and had not replied was removed rather than softened, because nothing
in the record established that the message arrived. A forward-looking commitment
is safe; an assertion about the past is not.

---

# 8. EVALUATING A DETECTOR

The other half of the same idea. Here the gap is not between a score and a
property but between a **decision rule** and a **representation**.

## 8.1 Separate the failure of the decision rule from the failure of the representation

The two have opposite remedies, so misdiagnosing is expensive: one needs a
changed constant, the other needs different information.

**Measured example:** A minority attack class had near-zero detection at the
default argmax cut. Measured without a threshold, its score separated it from
benign far above chance.

```
                      seen in training   held out
attack-score AUROC    0.872              0.804
recall at argmax      0.059
recall at a per-class 10 % FPR threshold  0.493
```

The class was discriminable throughout. What failed was one global operating
point applied to a minority, benign-mimicking class. A widely repeated
"detection collapse" is mostly a thresholding artifact.

## 8.2 Report a threshold-free measure beside every operating-point measure

```
both poor                                -> representation is the problem
threshold-free good, operating point poor -> decision rule is the problem
```

Name which, because it decides what anyone should do next.

## 8.3 A dissociation is graded, not uniform

Run the analysis on every case you have and report the one that fits worst as
prominently as the one that fits best. The gradient is information.

**Measured example:** The operating-point reading was clean for one class and only
partial for another, whose threshold-free score was moderate at AUROC 0.708. Part
of that miss is genuinely representational. Reporting the pattern as uniform would
have been the overclaim a reviewer finds.

## 8.4 Post-hoc calibration does not survive distribution shift

**Measured example:** Expected calibration error on a shifted test set ran from
0.1630 to 0.2151 across detectors. Platt scaling, isotonic regression and
temperature scaling each drove in-distribution error below 0.01 and left the
shifted error essentially where it was, and made it slightly worse for one model.
A proper scoring rule agreed, so the effect is a property of the scores under
shift, not a binning artifact.

The operational consequence is a scoping statement: calibrated probabilities
should not be trusted as deployment-time guarantees.

## 8.5 Compare at matched cost, not matched configuration

**Measured example:** An added abstention and novelty stage looked like a clear
gain against the default cut. Held to the same analyst review budget of 0.124:

```
policy                        unknown-class recall
----------------------------  --------------------
argmax                        0.003
threshold tuned to the budget 0.508
full stack                    0.397
```

The stack loses. The apparent advantage was in the resource it silently spent,
not in the mechanism. Identify the scarce resource, hold it equal, and re-run.

## 8.6 A guarantee established in-distribution is not a guarantee

**Measured example:** Split conformal prediction at a target coverage of 0.90
attained 0.930 in-distribution and 0.611 under the train-test shift the study was
about. Report what the guarantee does under the shift you actually face; that
number is the finding.

## 8.7 An interval measures whatever you resampled

Resampling seeds over a fixed evaluation partition produces an interval about
training variance, not about generalisation, however tight it looks.

**Measured example:** A seed half-width near 0.001 sat beside a bootstrap over the
evaluation distribution of 0.0052 for the same quantity. Five times wider, and
the honest figure.

## 8.8 Reconcile any quantity measured twice

Small disagreements between independent measurements of one quantity are expected
and benign. Left unexplained they read as an error, and from outside there is no
way to tell which.

**Evidence:** One quantity had its three-way spread explained in a footnote while
a second, with the same cause, went unexplained until an outside reader asked.
The explanation was already written; nobody had enumerated the others.

---

# 9. CHECKLISTS

## 9.1 Before claiming a break

```
[ ] the deciding structural property named, and tested directly
[ ] the mathematical type of every stage written down, composition reduced
[ ] reimplemented from the primary source, no code reused
[ ] the target's OWN reported statistics reproduced first
[ ] the discriminating measurement is a direct consequence of the structure,
    not a summary statistic
[ ] expected value derived analytically before measuring
[ ] recovered artifact confirmed on held-out data
[ ] query count stated as a function of the index width, with the known bound
    beside it
[ ] positive control run: the smallest change that should defeat the attack
[ ] chance level computed, not assumed
```

## 9.2 Before claiming a metric is misreported

```
[ ] the metric recomputed from its ORIGINAL definition
[ ] the definition cited where the number appears, not only in related work
[ ] the value derived from the structural finding, and it matches the measurement
[ ] what the reported figure actually measures, identified and quantified
[ ] the claimed-versus-actual table present
```

## 9.3 Before claiming a detector fails

```
[ ] a threshold-free measure reported beside every operating-point measure
[ ] the fault localised to the decision rule or the representation, and named
[ ] the pattern run on every class, and the worst-fitting case reported
[ ] comparisons made at matched cost, with the scarce resource named
[ ] intervals resample the population the claim generalises to
[ ] any guarantee reported under the shift, not only in-distribution
[ ] every quantity measured more than once reconciled
```

## 9.4 Scope

```
[ ] equivalent capability distinguished from the secret itself
[ ] what the result licenses, and what it does not, stated explicitly
[ ] mislabels corrected but not inflated into findings
[ ] no assertion about a real-world action that cannot be evidenced
[ ] restrictions (one architecture family, shared features, classical signals
    only) stated as scoping, not left as omissions
```

---

# 10. PROMPTS

## 10.1 Find the deciding property

```
Here is the definition of [CONSTRUCTION] from its primary source.

1. List every internal quantity and state, for each, whether it depends on the
   input or only on the key or configuration.
2. Give the mathematical type of the map each stage induces on the input, and
   reduce the composition.
3. Name the single binary property that decides whether this construction can
   work at all, and say what measurement tests it directly.
4. If that property fails, derive the recovery: what queries, how many as a
   function of what, and what the recovered object is.

Do not evaluate its statistics yet. Cite an equation or section for every
structural claim, and mark anything you cannot anchor.
```

## 10.2 Audit a statistical battery

```
For each statistic [SYSTEM] reports:

1. What does it measure about the output distribution?
2. What does it NOT measure about the map from input to output?
3. Could a system lacking the security property score well on it? Construct such
   a system if you can.
4. Recompute any differential or sensitivity metric from its ORIGINAL definition
   under my structural finding. Derive the expected value analytically first.
5. Where the recomputed value and the reported value diverge, quantify the gap
   and identify what the reported figure was actually measuring.

Finish with a claimed-versus-actual table.
```

## 10.3 Design the positive control

```
I claim [SYSTEM] fails because of [PROPERTY].

Design the positive control: the smallest change to the SAME construction that
should restore the property and defeat my attack. Then:
1. State the expected result before running it.
2. Compute the chance level for the recovery measure, do not assume it.
3. Tell me what the control proves if it works, and what it proves if it does not.
4. If the control passes, write the remedy section it licenses.
```

## 10.4 Localise a detector failure

```
[DETECTOR] shows [POOR METRIC] on [SUBSET].

Before concluding the representation is at fault:
1. Report a threshold-free measure on the same data. Give the number.
2. If it is high while the operating-point measure is low, the fault is the
   decision rule. Say which.
3. Run the same analysis on every subset, and report the worst-fitting case as
   prominently as the best.
4. Re-run any policy comparison at MATCHED cost. Name the scarce resource.
5. State what the interval you report resampled, and whether that is the
   population the claim generalises to.
```

## 10.5 Scope the claim

```
Here is my security claim: [CLAIM].

1. Distinguish what was recovered from what was not (equivalent capability
   versus the secret itself). Rewrite the claim at the narrower level.
2. State what the result licenses for other systems, and what it explicitly does
   not.
3. Flag any mislabel I am correcting and tell me whether it deserves a sentence
   or a section.
4. Flag every assertion about a real-world action. For each, ask what I would
   show if challenged. Delete the ones with no answer rather than softening them.
```

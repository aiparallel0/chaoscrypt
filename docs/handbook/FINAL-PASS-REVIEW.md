# Final Pass Review: merged handbook v2

Review of `RESEARCH-PUBLICATION-METHOD-UNIFIED.md` at the v2 merge, before adoption.

## Method

Adapted from `trailofbits/skills` `plugins/differential-review`. That skill is
security-focused and its own scope note excludes documentation-only changes, so it
was **not** applied wholesale. What was taken is its transferable core:

```
risk-first     classify by risk, not by size of change
evidence-based every finding carries a location
honest         state coverage limits and confidence explicitly
output-driven  write the report to a file; findings left in chat are lost
```

and from `pr-review-toolkit:review-pr`, the rule to **review the change surface, not
the whole document**, and to report every defect with a severity including the minor
ones.

`code-improver` was considered and rejected: its review-and-fix loop requires the
`plugin-dev` plugin and dispatches subagents, and subagent tool access is broken in
this environment (a prior attempt produced five agents that could not read a byte).
Running it would have produced an empty loop, which is Section 19.16 of the handbook
itself.

**Change surface.** v2 against the previously adopted merge: one inserted section
(§6, evidence integrity), which shifted §6 to §28 up by one, plus six new subsections
elsewhere (10.11, 11.16, 12.8, 14.7, 14.8) and the §28 renumbering.

## Coverage and confidence

```
checked mechanically : numbering, contents, subsection ordering, every internal
                       cross-reference, house rules, concept-level duplication
checked by reading   : all 23 references whose context shares no vocabulary with
                       its target title
NOT checked          : the factual claims in §6 and §28, which come from an
                       engagement this reviewer has no access to. Their internal
                       consistency was checked; their truth was not.
```

Confidence: high on structure, none on the unverifiable provenance above.

## Findings

### F1. CRITICAL, reviewer error. Five lessons were never delivered

Not a defect in v2. A defect in the previous review of v1.

The command that applied five gap-closing lessons ran `cp` without a `cd`, so it wrote
to `/home/user/RESEARCH-PUBLICATION-METHOD-UNIFIED.md`, outside the repository. The
commit that claimed to carry them contained only a one-line README change, and the
file attached to the user was the older version. Every subsequent verification in that
turn ran against the stray file and passed, which is why it went unnoticed.

This is the handbook's own 29.10 (verify tree identity) and 24.4 (nothing measured
must not score a pass) applied to the reviewer rather than the artifact. The
verification was real; it was pointed at the wrong file.

**Resolution:** the five are restored into v2 at their shifted numbers, 17.11,
19.14 to 19.16, and 25.10, with every internal reference remapped to v2 numbering
(17.1, 24.1, 18.12, 19.4, 25.5, 25.7).

### F2. MAJOR. Byte-identical duplicate across two sections

`13.15` and `28.13` carried the same title and the same 676-character body, verbatim.
The merge placed the lesson with the publication material and left the original in
place.

The handbook's own 11.15 prescribes the fix: not deletion, but sharpening the
distinction and cross-referring. Here there is no distinction to sharpen, because the
copies are identical, and 11.8 and 19.11 forbid renumbering to close the gap.

**Resolution:** the full text stays at 13.15, beside the other length lessons and
after 13.14. `28.13` becomes a three-line pointer that preserves the number and keeps
the local flow into 28.14, which is the operational half of the same idea.

### F3. MINOR. Two halves of one topic with no link

`10.11` (a review is written against a build, and framing can be conceded narrowly)
and `28.17` (identify which build a review was written against) are the framing half
and the mechanical half of the same problem, in sections far apart, with no
cross-reference.

**Resolution:** two lines added at 28.17 pointing back to 10.11.

### F4. INFORMATIONAL. Two near-duplicate title pairs, both legitimate

```
16.19 How to extract implicit rules       vs  21.12 Extract implicit rules (prompt)
14.7  Before trusting a check (checklist) vs  28.3  Inject the defect (lesson)
```

Method against prompt, and checklist against lesson. Both are the handbook's
established pattern. No action.

## Verified clean

```
sections            1..29, contiguous
contents            matches the headings exactly
subsections         in order within every section
cross-references    79 distinct sites, 0 dead, 0 misdirected
                    all 23 low-overlap references read individually and confirmed
house rules         0 em-dashes, 0 non-ascii characters in prose
duplication         1 exact duplicate found and resolved; no others above 0.5
```

The cross-reference result is the one worth noting. Inserting §6 shifted twenty-three
sections, and every reference into them was correctly remapped by whoever produced
v2. That is the failure the handbook's own 11.8 exists to catch, and it did not occur.

## After the pass

```
4299 lines, 29 sections, 269 subsections
```

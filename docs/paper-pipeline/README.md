# Paper Pipeline Playbook

A reusable operating instruction for AI agents preparing academic papers for venues with a
template, a page limit, and reviewers.

**Start here → [00-MASTER-PROMPT.md](00-MASTER-PROMPT.md)** — hand this file to an agent as its
standing instruction. The rest are references it links to.

## What this is

Distilled from a real project: two 6-page IEEE papers taken through 91 commits to
IECC-UBMK-2026, including a committee correction notice with a 24-hour deadline, a reviewer's
six formatting rules, an annotated PDF, two substantive peer reviews, and a round-trip through
the author's own Overleaf that nearly shipped a paper missing a figure and a table.

Every rule exists because something actually went wrong. Nothing here is hypothetical.

## Contents

| File | What it is |
|---|---|
| [00-MASTER-PROMPT.md](00-MASTER-PROMPT.md) | The operating instruction: 8 prime directives, 7 standing constraints, 8-phase procedure |
| [01-FAILURE-CATALOG.md](01-FAILURE-CATALOG.md) | 30 catalogued failures in 4 families, with symptom, root cause, detection and fix |
| [02-VENUE-CONFORMANCE.md](02-VENUE-CONFORMANCE.md) | Verbatim reviewer and committee text, the fix for each, and how to establish a template's ground truth |
| [03-LIFECYCLE.md](03-LIFECYCLE.md) | What order the work has to happen in, and what to front-load |
| [04-WORKED-EXAMPLE.md](04-WORKED-EXAMPLE.md) | Two defects traced end to end, with the fork points where a careless agent goes wrong |
| [05-AUDIT-KIT.md](05-AUDIT-KIT.md) | Runnable checks |
| [tools/float_refs.py](tools/float_refs.py) | Float-reference classifier — the flagship check, validated against both papers |

## The one-paragraph version

The failures that matter are **silent**. In this project the build never failed, the page count
was always right, and the PDF always looked finished — while a package override was destroying
the publisher's caption format, two unfilled placeholders were deleting a figure and a table, a
build script was returning failure on success and shipping stale artifacts, and a disclosure
sentence was escalating from intent to asserted fact across three commits each described as
"reconciling". Confidence must come from comparing the rendered artifact against an independent
authority. A clean build is not evidence.

## Using the checks

```bash
# the flagship check: are floats discussed, or only cited?
python3 docs/paper-pipeline/tools/float_refs.py papers/<name>/main_filled.tex

# nothing unsubstituted may ship
grep -c '\PH{' package/main.tex          # must be 0

# captions: verify on the RENDERED pdf, never the source
pdftotext papers/<name>/main.pdf - | grep -oE "Fig\. [0-9]+[.:]|TABLE [IVX]+:?" | sort -u
```

`float_refs.py` is validated three ways: it passes both current papers (11/11 floats each) and
correctly fails pre-fix Paper 2 (`7706940~1`) with 0 subject-position references out of 20. See
[05-AUDIT-KIT.md §1](05-AUDIT-KIT.md) for the three false-pass bugs it had during development —
including one where an empty input file scored a perfect pass.

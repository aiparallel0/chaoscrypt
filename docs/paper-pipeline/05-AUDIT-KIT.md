# Audit Kit

Runnable checks. Each states what it catches, the script, and how to read it.

Assumed layout: `papers/<name>/main.tex` (may contain `\PH{key}` placeholders),
`papers/<name>/main_filled.tex` (substituted), `papers/<name>/main.pdf`.
Adjust paths freely; the logic is the point.

Requires `python3`, `poppler-utils` (`pdftotext`, `pdfinfo`), a TeX distribution.

> Run every rendered-PDF check against the PDF, never the source. Source-level checks cannot
> see what a package override did.

---

## 1. Float-reference classifier — committee item 3

**Catches:** floats that are cited but never *discussed*. The check that flips "all referenced,
nothing to do" into the real answer. Counts a reference only when the float name opens a clause
**and** is followed by a reporting verb.

Script: [`tools/float_refs.py`](tools/float_refs.py)

```bash
python3 docs/paper-pipeline/tools/float_refs.py papers/<name>/main_filled.tex
```

**Read it:** `NONE` is the only passing result. `parenthetical` may stay non-zero — extra
parenthetical mentions are fine *once* a float is properly introduced.

Validated against the source project:

| Input | Output |
|---|---|
| Paper 1, current | `floats: 11  subject-position: 11  parenthetical: 4` -> `NONE`, exit 0 |
| Paper 2, current | `floats: 11  subject-position: 12  parenthetical: 8` -> `NONE`, exit 0 |
| Paper 2 **before** the fix (`7706940~1`) | `subject-position: 0  parenthetical: 20` -> all 11 floats listed, exit 1 |

That last row is the regression test: the checker must reproduce the historical defect, or it
is not measuring anything.

### Three bugs this script had, which you will also write

Each produced a **false pass or false failure**, and they are the generic failure modes of any
LaTeX-text heuristic:

1. **Clause openers are not just `. ; :`.** A reference after `\end{enumerate}` or display math
   sees `pre == "} "`. Peel trailing LaTeX closers before testing.
2. **`\subsection{Reproduction}` is a clause opener.** Naive peeling of a trailing `}` leaves
   `\subsection{Reproduction`, which ends in a letter. Strip whole `\command{...}` groups
   iteratively, not single characters.
3. **An empty or wrong input file scored a perfect pass.** Zero floats means zero missing floats
   means exit 0. Any check whose "nothing found" state is indistinguishable from "nothing wrong"
   must assert it found something - hence the `if not labels: sys.exit(2)` guard.

Sentence-initial adverbials (`Finally, Fig. 6 shows ...`) and conjoined clauses (`and Fig. 5
plots ...`) are legitimate subject position and are accepted.

Also confirm nothing is uncited at all:
```bash
python3 - <<'EOF'
import re
src = re.sub(r'(?<!\\)%.*', '', open('main_filled.tex').read())
for lab in re.findall(r'\\label\{((?:fig|tab|alg):[^}]+)\}', src):
    if len(re.findall(r'\\ref\{%s\}' % re.escape(lab), src)) == 0:
        print("UNREFERENCED:", lab)
EOF
```

---

## 2. Placeholder-leak check — the silent content killer

**Catches:** unfilled `\PH{}` in a shipped file. Two placeholders on one line once deleted a
figure, a table, a statistical result, and the section numbering from a PDF that still compiled
to the correct page count.

```bash
grep -c '\\PH{' package/main.tex        # MUST be 0 in anything you ship
grep -n '\[?[a-z_0-9]*\]' package/main.tex | head   # the fill script's miss-marker
```

Also check the rendered PDF, since a placeholder can survive as visible text:
```bash
pdftotext main.pdf - | grep -oE "\[\?[a-z_0-9]+\]|PH\{[a-z_]+\}|[0-9]e-0[0-9]" | sort -u
```
The `[0-9]e-0[0-9]` arm catches Python scientific notation leaking into prose (`4e-06`), which
should typeset as `$4\times10^{-6}$`.

**Read it:** any output is a defect. Zero output is the only pass.

---

## 3. Placeholder key-set diff — proves no result was lost

**Catches:** a result silently dropped while restructuring or cutting for space. Run before and
after any edit that moves numbers between captions and body.

```bash
git show HEAD:papers/<name>/main.tex > /tmp/before.tex
python3 - <<'EOF'
import re, collections
def keys(p):
    t = re.sub(r'(?<!\\)%.*', '', open(p).read())
    return collections.Counter(re.findall(r'\\PH\{([^}]+)\}', t))
a, b = keys('/tmp/before.tex'), keys('papers/<name>/main.tex')
print("REMOVED entirely:", [k for k in a if k not in b] or "NONE")
print("ADDED:",            [k for k in b if k not in a] or "NONE")
for k in sorted(set(a) | set(b)):
    if a[k] != b[k]:
        print(f"  {k}: {a[k]} -> {b[k]} occurrences")
EOF
```

**Read it:** `REMOVED entirely: NONE` is mandatory. Occurrence-count changes are acceptable
**only** when you can name the duplicate you removed and confirm the value still appears
somewhere — e.g. a caption that repeated a number already in its own table.

---

## 4. Caption-format check — committee item 2

**Catches:** a package overriding the publisher class. Runs on the rendered PDF because that is
the only place the override is visible.

```bash
pdftotext main.pdf - | grep -oE "Fig\. [0-9]+[.:]|TABLE [IVX]+:?" | sort -u
```

**Read it:** want `Fig. 1.` and `TABLE I`. **Any colon is a failure.** Small caps extract oddly
(`R ECONSTRUCTION …`) — that is a `pdftotext` artifact, not a defect; confirm visually by
rendering the page:
```bash
pdftoppm -r 110 -png -f 3 -l 3 main.pdf /tmp/page && open /tmp/page-3.png
```

---

## 5. Build gate — page count, overfull, undefined

**Catches:** the three things that get a paper desk-rejected, plus a build that lies.

```bash
#!/usr/bin/env bash
# gate.sh <paper-dir> <page-limit>
set -euo pipefail
d="$1"; limit="${2:-6}"; log="$d/main_filled.log"

err=$(grep -c '^!'                "$log" || true)
ovf=$(grep -c 'Overfull'          "$log" || true)
und=$(grep -ci 'undefined'        "$log" || true)
pages=$(pdfinfo "$d/main.pdf" | awk '/^Pages:/{print $2}')

echo "pages=$pages/$limit errors=$err overfull=$ovf undefined=$und"
fail=0
[ "$pages" -gt "$limit" ] && { echo "FAIL: over page limit"; fail=1; }
[ "$err" -gt 0 ]  && { echo "FAIL: LaTeX errors";       fail=1; }
[ "$ovf" -gt 0 ]  && { echo "FAIL: overfull boxes";     fail=1; }
[ "$und" -gt 0 ]  && { echo "FAIL: undefined refs/cites"; fail=1; }
exit $fail
```

> **Note `|| true` on the greps.** `grep -c` exits 1 when the count is 0, which under `set -e`
> aborts the script *on success*. This is exactly the bug that made the source project's build
> script return exit 1 for a passing 6-page build and exit 0 for a failing 7-page one. If you
> write shell gates, test both branches.

### Build-script self-test (Phase 1 exit condition)

Never trust a build you have not seen fail:
```bash
cp main.tex main.tex.bak
printf '\\begin{nosuchenv}x\\end{nosuchenv}\n' >> main.tex
bash scripts/compile.sh .; echo "exit=$?"     # MUST be non-zero, MUST NOT print success
pdftotext main.pdf - | head -2                # MUST NOT be the previous build's content
mv main.tex.bak main.tex
```
A build that tests only `[ -f out.pdf ]` will "succeed" on a leftover artifact from an earlier
run and ship a stale PDF. Verified reproduction: a fatally broken source printed
`wrote .../main.pdf (1 pages)` while `main.pdf` still contained the previous build's text.

---

## 6. Clean-room package compile — Phase 6 exit condition

**Catches:** a deliverable that only builds because of files sitting in your working tree.

```bash
cd package/ && rm -f main.aux main.log main.bbl main.blg main.pdf
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
bibtex main >/dev/null 2>&1
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
echo "pages=$(pdfinfo main.pdf | awk '/^Pages:/{print $2}')" \
     "errors=$(grep -c '^!' main.log)" \
     "overfull=$(grep -c Overfull main.log)" \
     "undefined=$(grep -ci undefined main.log)" \
     "placeholders=$(grep -c '\\PH{' main.tex)"
pdftotext main.pdf - | grep -oE "Fig\. [0-9]+\.|TABLE [IVX]+" | sort -u | tr '\n' ' '
```

**Read it:** expected page count, all zeros, and every float present. Also verify every
`\includegraphics` target is actually inside the package:
```bash
python3 - <<'EOF'
import re, os
t = open('main.tex').read()
for g in sorted(set(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', t))):
    ok = any(os.path.exists(g + e) for e in ('', '.pdf', '.png', '.jpg'))
    print(('OK   ' if ok else 'MISSING '), g)
EOF
```

---

## 7. Heading Title Case — reviewer rule 6

**Catches:** sentence-case headings, including the `\section` level that gets missed while
fixing `\subsection`.

```python
#!/usr/bin/env python3
import re, sys
SMALL = {'a','an','the','and','or','but','nor','for','of','in','on','at','to','by',
         'vs','with','from','as','is','it'}
src = re.sub(r'(?<!\\)%.*', '', open(sys.argv[1]).read())
bad = []
for kind, title in re.findall(r'\\(section|subsection)\{([^}]*)\}', src):
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", title)
    for i, w in enumerate(words):
        if w.lower() in SMALL and i not in (0, len(words)-1):
            continue
        if w[0].islower():
            bad.append((kind, title, w)); break
for k, t, w in bad:
    print(f"{k}: {t!r}  (lowercase: {w!r})")
print("OK" if not bad else f"{len(bad)} heading(s) not Title Case")
sys.exit(1 if bad else 0)
```

**Read it:** acronyms and deliberate lowercase (`k`NN) will false-positive — review, don't
auto-apply.

---

## 8. Numbers-consistency check

**Catches:** the same quantity stated two ways (a decrypt timing appeared as both `0.101 s` and
`0.037 s` in one paper).

```bash
pdftotext main.pdf - \
  | grep -oE '[0-9]+\.[0-9]+' | sort | uniq -c | sort -rn | head -30
```
Then, for any value that should be unique, confirm it resolves to one result key:
```bash
grep -rn "0.037" papers/<name>/results/*.json papers/<name>/main.tex
```

**Read it:** manual. The point is to *look* at repeated decimals and ask whether two of them are
the same quantity disagreeing. Automating the judgement is not possible; automating the
enumeration is.

---

## 9. Disclosure verification — do not automate away

**Catches:** claims about real-world actions asserted as fact.

```bash
grep -rn -i "we emailed\|were notified\|responsible.disclos\|every citation\|independently verified" \
     papers/*/main.tex papers/*/*.md
```

For each hit, answer in writing: *did this actually happen, and how do I know?* Then check
whether the wording strengthened over time:
```bash
git log -p --follow -- papers/<name>/main.tex | grep -E '^[+-].*(notif|emailed|verified)'
```

**Read it:** a progression like `will be notified` → `are notified` → `we emailed … received no
response` is a fabrication in slow motion, even when no single commit looks like one. Only the
human can confirm the underlying fact.

---

## 10. Rendered-format conformance — the committee's numbered items

**Catches:** every measurable statement in the template's `word/styles.xml`, measured on the
rendered PDF: body leading, first-line indent, reference leading and inter-entry gap, caption
label separators, heading case, placeholder leaks, and the font the author block's e-mail is
set in.

Script: [`tools/ubmk_conformance.py`](tools/ubmk_conformance.py)

```bash
python3 docs/paper-pipeline/tools/ubmk_conformance.py papers/<name>/main.pdf papers/<name>/main.tex
```

**Read it:** exit 0 only if every line says PASS. Exit 2 means nothing could be measured, which
is a failure and never a pass — an empty or wrong file must not score well by having no findings.

Validated against the source project:

| Input | Output |
|---|---|
| Either paper, current | 9/9 PASS, exit 0 |
| The PDF actually submitted | 6 FAIL: 12.00pt leading, 9.90pt indent, 0.00pt reference gap, 11 colon captions, Courier e-mail, exit 1 |

### The font check, and why the first two versions of it passed everything

The committee returned the papers over one thing a spacing checker cannot see: the author
block's e-mail was set in Courier by a stray `\texttt`. Measuring it needs the size and face the
typesetter *asked for*, read out of the page content stream, not the glyph boxes `pdftotext`
reports. Two bugs in that check each made it pass vacuously, and both are easy to write again:

1. **`/Font` is written inline inside `/Resources`, not as an indirect reference.** A fallback
   chain that lands on the page object instead of the resources dictionary yields an empty font
   map, every name reads as `"?"`, and `"?" == "?"` certifies Courier as matching Times. An
   unresolved font name must be a failure, never a pass.
2. **URW's Courier clone is named `NimbusMonL`** — no trailing "o", so a `/Mono/` pattern misses
   it, and `pdffonts` prints it behind a six-letter subset tag (`ABCDEF+NimbusMonL-Regu`) that
   has to be stripped before matching.

Both were caught only by running the check against the PDF that had actually been rejected. A
conformance check that has never failed has not been tested.

---

## 11. Word-version conversion and its verification

**Catches:** text silently lost while converting the paper to `.docx` for a venue that asks for
one. The output is built over the template's own styles, so the numbering and spacing come from
`word/styles.xml` rather than from anything the converter asserts.

Scripts: [`tools/tex2docx.py`](tools/tex2docx.py), [`tools/docx_check.py`](tools/docx_check.py)

```bash
bash scripts/build_docx.sh papers/<name> docs/paper-pipeline/UBMKtemplateA4.docx
```

The gate refuses to write `main.docx` unless the LaTeX build passes, the conversion recognises
every construct, and the verification passes. The converter aborts on any unknown control
sequence rather than dropping it: a converter that silently skips what it cannot handle produces
a document that looks complete and is not.

**Read it:** the two directional checks are word multisets, not sliding windows. Windows are the
obvious design and the wrong one — Word generates `Fig. 1.` and `[2]` from its own counters, a
footnote is written inside a sentence but typeset at the foot of a column, and a compound
hyphenates across a line. Every one of those shifts a window without losing a word, so a window
check drowns in false positives while dropping a sentence — the failure that matters — removes
words outright and shows up immediately.

Validated by damaging a passing file three ways:

| Damage | Caught by |
|---|---|
| one body paragraph deleted | `no word dropped from source`, `every source number present` |
| `0.508` changed to `0.999` | `every source number present` |
| one `<w:drawing>` removed | `figures: source 7, docx 6` |

### Three traps in the conversion itself

1. **`w:pPr` is a sequence, not a bag.** `w:ind` before `w:jc`, `w:framePr` before `w:numPr`.
   Get the order wrong and the file does not open at all, with no indication of which element
   was misplaced. The same is true of the `<w:document>` start tag: reuse the template's
   verbatim rather than hand-writing its namespace set.
2. **The template's `equation` style sets the Symbol font**, for Word's old equation editor.
   Symbol maps the Latin alphabet onto Greek glyphs, so `C[j]=K[s(j)]` renders as
   `X[φ]=K[σ(φ)]`. Equation runs need the document font restored explicitly.
3. **A blank line ends a paragraph.** Without that split the prose between two floats arrives as
   one block and every bold lead-in runs together — a defect that is invisible in the source and
   obvious in the rendered page, which is the argument for rendering it and looking.

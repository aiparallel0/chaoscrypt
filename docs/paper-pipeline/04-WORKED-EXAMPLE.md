# Worked Examples

Two defects traced end to end, with the fork points marked. At each fork, the careless move is
shown alongside the correct one — the careless move is always the *faster* one, and always
produces an artifact that looks finished.

---

# Example 1 — "Fix the captions per the template"

The instruction that cannot be followed literally.

## The input

The organising committee, 24-hour deadline:

> **2. Tablo ve Şekil İsimlendirmeleri:** Tablo ve şekil isimlerinde/başlıklarında biçimsel
> hatalar tespit edilmiştir. **Şablondaki format esas alınarak** düzeltilmelidir.
>
> *("Formatting errors detected in table and figure names/captions. They must be corrected
> **taking the template's format as the basis**.")*

Present state:

```bash
$ pdftotext main.pdf - | grep -oE "Fig\. [0-9]+[.:]|TABLE [IVX]+:?" | sort -u
Fig. 1:  Fig. 2:  Fig. 3:  TABLE I:  TABLE II:  TABLE III:
```

Colons everywhere.

---

## Fork 1 — What is the specification?

**❌ Careless:** open the venue's `ubmk.pdf`, see how its captions look, match that. The
instruction literally says *take the template's format as the basis*.

**Why it fails:** the template's captions **also use colons**. Matching it reproduces exactly what
the committee flagged. The instruction, followed literally, produces the defect.

**✅ Correct:** treat the template as *evidence* and find the authority behind it.

```bash
$ grep -n "caption" ubmk.tex
8:\usepackage[font=footnotesize]{caption}
```

The `caption` package has no IEEEtran support. It discards the class's `\@makecaption` and imposes
its own default separator — a colon. **The venue's template has a bug.**

> **Fork lesson:** when an instruction and the artifact it points at disagree, the instruction
> means the *intent*, not the artifact. Go to the authority.

---

## Fork 2 — Which authority?

**❌ Careless:** apply "standard IEEE style" from memory. Plausible, unverifiable, and this is
exactly what sank the external compliance checklist ([02 §D](02-VENUE-CONFORMANCE.md)).

**✅ Correct:** two independent authorities that can be read.

**Authority A — the class file:**
```bash
$ grep -n "makecaption" IEEEtran.cls
```
Figure branch ends `{#1.}` → **period**.
Table branch is `#1 \\ {\normalfont\footnotesize\scshape #2}` → label on its own line, title in
**small caps**.

**Authority B — the Word template.** A `.docx` is a zip; its style definitions *are* the spec:
```bash
$ unzip -o UBMKtemplateA4.docx -d docx/
$ python3 -c "
import re
s=open('docx/word/styles.xml',encoding='utf8').read()
for m in re.finditer(r'<w:style [^>]*w:styleId=\"([^\"]*)\"[^>]*>(.*?)</w:style>', s, re.S):
    sid, body = m.groups()
    if re.search(r'table|figure|caption', sid, re.I):
        print(sid, 'SMALLCAPS' if '<w:smallCaps' in body else '')
"
figurecaption
tablehead                SMALLCAPS
```

Two independent sources agree. That agreement is what makes deviating from the template's
rendered output defensible to a committee.

---

## Fork 3 — What did the authorities reveal that nobody asked about?

**❌ Careless:** fix the colons, done. That is what was asked.

**✅ Correct:** notice that Authority B says `tablehead` is **SMALLCAPS** and the current output
is not. Reading the preamble again:

```latex
\usepackage[font=footnotesize]{caption}
```

`font=` sets the caption font *from scratch*. IEEEtran's table branch was
`{\normalfont\footnotesize\scshape #2}`. The option looks like it harmlessly restates the size —
it was silently deleting `\scshape` all along.

> **Fork lesson:** a package option that duplicates a class default is not a no-op, it is a total
> override. This defect was never flagged by anyone. It was found only by reading the authority
> for a *different* question.

---

## Fork 4 — The fix

```latex
\usepackage[font=footnotesize,labelsep=period]{caption}     % "Fig. 1."
\captionsetup[table]{labelsep=newline,font={footnotesize,sc},justification=centering}
```

Small caps forces a second change: long sentence-style table captions are unreadable in caps. So
captions shorten, and displaced detail — **including CI half-widths, which are results** — moves
into the body paragraphs. Which, conveniently, is also what committee item 3 demanded.

**❌ Careless:** shorten the captions and move on.
**✅ Correct:** prove nothing was lost ([05 §3](05-AUDIT-KIT.md)):
```
keys entirely REMOVED: NONE
ADDED: NONE
  cic_drift_reject_web: 3 -> 2 occurrences
  cic_histgb_ece: 3 -> 2 occurrences
```
Two counts dropped — acceptable **only** because each removal was a caption repeating a number
still present in both the body and its own table. The check does not clear you; it tells you what
to justify.

---

## Fork 5 — Verify where?

**❌ Careless:** confirm the source now says `labelsep=period`.
**Why it fails:** the source said `font=footnotesize` for 91 commits and looked fine too. Source
inspection cannot see an override.

**✅ Correct:** the rendered PDF.
```bash
$ pdftotext main.pdf - | grep -oE "Fig\. [0-9]+\.|TABLE [IVX]+" | sort -u | tr '\n' ' '
Fig. 1. Fig. 2. Fig. 3. Fig. 4. Fig. 5. Fig. 6. TABLE I TABLE II TABLE III TABLE IV TABLE V
```
Then render a page and look — `pdftotext` renders small caps as `R ECONSTRUCTION`, an extraction
artifact that reads as a defect if you only trust text:
```bash
pdftoppm -r 110 -png -f 3 -l 3 main.pdf /tmp/page
```

## Outcome

One Phase 0 investigation resolved committee item 2, fixed an unflagged small-caps defect,
forced the caption shortening that served item 3, and produced a documented justification for
deviating from the template. The careless path at any fork yields a paper that compiles, looks
finished, and gets the same correction email back.

---

# Example 2 — The PDF that was complete and wasn't

Shorter, and the more dangerous class.

## The input

The author compiles in Overleaf and sends the result. It is 6 pages. It looks finished.

```bash
$ pdfinfo paper_pkg_3.pdf | grep Pages
Pages:           6
```

## What was actually missing

Fig. 6, TABLE V, a χ² result, an entire paragraph — and section numbering showed **two sections
numbered V**.

## The cause — one line

```latex
$100/MN=\PH{cam_npcr1px}\,\%$ (UACI \PH{cam_uaci1px}\,\%), five orders of magnitude
```

Two placeholders never substituted. `\PH{cam_npcr1px}` puts `cam_npcr1px` — containing `_` — into
text mode. LaTeX: `! Missing $ inserted.` Under `-interaction=nonstopmode` it "recovers" by
consuming tokens, and the recovery swallowed the following floats.

## Why every signal said fine

| Signal | Reading |
|---|---|
| Page count | 6 — correct |
| Compile | succeeded |
| Visual | no gaps; text flows |
| Build script | `wrote main.pdf (6 pages)` |

Nothing was missing *on the page*. The page ended earlier and later material moved up.

## Fork — how would you ever catch it?

**❌ Careless:** read the PDF and check it looks right. It does.

**✅ Correct:** check the *invariant*, not the appearance.
```bash
$ grep -c '\PH{' main.tex        # must be 0 in anything shipped
$ pdftotext main.pdf - | grep -oE "Fig\. [0-9]+\.|TABLE [IVX]+" | sort -u
```
Count the floats you *expect* and compare. Six figures and five tables were expected; the PDF had
five and four.

## The structural cause

`.gitignore` excludes `papers/*/main_filled.tex`. So `main.tex` — tracked, reviewed, the file a
human naturally opens — is the one that **cannot be compiled**, while `main_filled.tex` — the only
one that compiles — has no history and no identity. Both are 578 lines; they differ only in the 59
substituted values, spread over 38 lines, which is why a hybrid is so easy to produce and so hard to
spot. The author's Overleaf project became exactly that.

**Fix applied:** the delivered package now contains a fully-substituted `main.tex` with zero
placeholders, verified by clean-room compile.
**Fix not applied:** the repo still has two confusable sources of truth, and the wrong one is the
one under version control. See [01 §B6](01-FAILURE-CATALOG.md).

## The generalisation

> A templating mechanism whose failure mode is a *language error* rather than a *visible gap* is
> a content-deletion bomb. Make unfilled slots fail the build. A marker that only shows up in the
> output can only be seen if the output still typesets — which is exactly what the error prevents.

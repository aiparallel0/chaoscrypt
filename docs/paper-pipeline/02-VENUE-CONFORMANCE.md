# Venue Conformance Dossier

Verbatim feedback from the source project, the diagnosis behind each item, and the exact fix.
Quoted text is reproduced as received. Turkish originals are kept because paraphrase loses the
operative meaning — see §D.

---

## A. The organising committee's correction notice

Received with a **24-hour** deadline, from the UBMK 2026 organising committee.

> Sayın Yazar,
> UBMK 2026 Düzenleme Kurulu adına yeniden düzenlenen bildiriniz tarafımızca incelenmiştir.
>
> **1. Yazar Bilgileri:** Bildiride eksik olan yazar bilgilerinin (isim, kurum, e-posta vb.)
> şablona uygun şekilde metne eklenmesi gerekmektedir.
>
> **2. Tablo ve Şekil İsimlendirmeleri:** Tablo ve şekil isimlerinde/başlıklarında biçimsel
> hatalar tespit edilmiştir. Şablondaki format esas alınarak düzeltilmelidir.
>
> **3. Şekil ve Tablo Atıfları:** Metin içerisinde tablo ve şekillere atıf (mention) yapılmadığı
> görülmüştür. Bildirideki tüm tablo ve şekillerin metin içinde eksiksiz bir şekilde atıf alması
> ve ilgili paragraflarda açıklanması gerekmektedir.

| # | Literal meaning | Diagnosis | Fix |
|---|---|---|---|
| 1 | Missing author info (name, institution, e-mail) must be added per template | Placeholder byline shipped | Bracketed fillable block; **requires the human** |
| 2 | Formatting errors in table/figure names/captions; correct per the template | The `caption` package overrode the class — see §C | `labelsep=period` + table `labelsep=newline` + small caps |
| 3 | Tables/figures not referenced in text; all must be referenced **and explained in the relevant paragraphs** | Literally false, operatively true | Rewrite to subject position |

### Item 3 is the one agents get wrong

Every float already had a `\ref{}`. A naive audit returns "all referenced — nothing to do."

The operative complaint is the second clause: *"ilgili paragraflarda açıklanması"* — **explained
in the relevant paragraphs**. A float mentioned only as `(Fig. 3)` is cited but not discussed.

The workable test is **grammatical position**:

- ❌ *parenthetical* — `…changes exactly one ciphertext pixel (Fig. 3, left), so the true NPCR…`
- ✅ *subject* — `Fig. 3 makes this visible: flipping a single plaintext pixel leaves one isolated dot…`

Measured on the two papers with the classifier in [05-AUDIT-KIT.md](05-AUDIT-KIT.md) §1:

| Paper | Before | After |
|---|---|---|
| 1 (cipher) | 10 of 12 floats subject-position; Fig. 3 and Fig. 5 parenthetical-only | 12 / 12 |
| 2 (IDS) | **0 of 20 references subject-position** | 11 / 11 floats covered |

Paper 2 had never been audited. It would have drawn the identical notice.

---

## B. The reviewer's six formatting rules

From reviewer/advisor **Asya Tunar**, delivered as margin notes plus a written instruction. The
covering instruction matters as much as the rules:

> Yukarıdaki 6 kuralı makalenin **tamamına** (yalnızca not düşülen ilk örneklere değil) uygula.
> […] Not düşülmemiş ama aynı kurala giren ek yerler bulursan bunları da ayrıca "not düşülmemiş
> ama düzeltilmesi gereken yer" başlığı altında belirt.

*("Apply these 6 rules to the whole paper, not only the first instances noted. If you find
further places covered by the same rule that were not annotated, report those too.")*

This is Prime Directive **D2** stated by the reviewer themselves.

### Rule 1 — Abstract in bold
> Makalenin özet (Abstract) paragrafının tamamı kalın (bold) yazı tipiyle biçimlendirilmelidir;
> şu an yalnızca bazı kelimeler/ifadeler kalındır.

IEEEtran already bolds abstract *text*; inline **math** stays upright, which is what looked
inconsistent. Fix:
```latex
\begin{abstract}
\boldmath
...
```

### Rule 2 — Keywords in italic
> "Keywords—" ile başlayan anahtar kelime listesinin tamamı italik yazı tipiyle
> biçimlendirilmelidir; şu an yalnızca "Keywords—" ifadesi italiktir.

```latex
\begin{IEEEkeywords}
\itshape intrusion detection, selective prediction, ...
\end{IEEEkeywords}
```

### Rule 3 — Figure captions use a period, not a colon
> Şekil başlıkları "Fig. N." biçiminde, nokta ile yazılmalı; iki nokta üst üste (":")
> kullanılmamalıdır. Bu kural yalnızca Fig. 2 için değil, makaledeki tüm şekil başlıkları için geçerlidir.
>
> *Original margin note:* "Fig. 2. şeklinde yazılmalı, diğer figürlerde de aynı şekilde. ':' kullanılmamalı."

Root cause in §C.

### Rule 4 — Table captions per the template
> Tablo başlıkları (isimleri), şablonda tanımlanan tablo başlığı biçimine (büyük/küçük harf
> kullanımı, noktalama, hizalama) uygun şekilde yeniden düzenlenmelidir.
>
> *Original margin note:* "Tablo adları şablonda yazdığı gibi verilmeli."

Note the three axes named: **capitalisation, punctuation, alignment.** Capitalisation is the
small-caps requirement most agents miss — see §C.

### Rule 5 — Tables must actually be tables
> Tablo olarak sunulan içerikler (özellikle Table II: Attack complexity), gerçek bir tablo
> yapısında ve şablonun öngördüğü tablo formatında (çizgi stili, hücre hizalama, başlık satırı
> biçimi) verilmelidir; düz metin/liste gibi sunulmamalıdır.
>
> *Original margin note:* **"Bu bir tablo mu? Tabloysa uygun formatta verilmeli."**

The venue template uses a **grid** style, not booktabs:

```latex
\begin{tabular}{|l|c|c|c|}
\hline
\textbf{Work} & \textbf{Target scheme} & \textbf{Chosen PT} & \textbf{Equiv.\ key} \\
\hline
Li \& Lo~\cite{li2011optimal} & permutation-only & $\lceil\log_{L} MN\rceil$ & perm. \\
\hline
\end{tabular}
```
Converting from booktabs adds width — vertical rules plus bold headers overflowed two tables.
Tighten with `\setlength{\tabcolsep}{3pt}` rather than shrinking the font.

**This exact note recurred.** Later, an annotated PDF carried the same question — *"Bu tablo mu?
tabloysa uygun formatta verilmeli"* — pointing at **Algorithm 1**, whose ruled `algorithm` float
with a bold run-in header reads as an unlabelled table. Because only Table II had been fixed,
the reviewer asked the identical question about a different object. The remedy was to remove the
float entirely in favour of an inline numbered list: no rules, no caption, nothing table-like.

### Rule 6 — Subsection titles in Title Case
> Alt başlıklardaki (A., B., C., D. ile başlayan bölüm başlıkları) her kelimenin ilk harfi büyük
> olmalıdır (title case).
>
> *Original margin note:* "Şablonu dikkate alarak alt başlıkların her bir kelimesinin ilk harfi
> büyük olmalı. Diğer alt başlıklarda da aynı hususlara dikkat ediniz."

`Cost scales logarithmically` → `Cost Scales Logarithmically`. Check `\section` too — in the
source project all subsections were fixed while three section titles stayed sentence case.

---

## C. Establishing ground truth — the method

The committee said captions were wrong and must follow "the template". **The template itself was
the source of the defect.** Resolving this required going past it.

### The bug
The venue's `ubmk.tex` contains:
```latex
\usepackage[font=footnotesize]{caption}
```
The `caption` package has no IEEEtran support. It replaces the class's `\@makecaption` wholesale
and imposes its own default separator — a **colon**. So the template's own rendered PDF shows
`Fig. 1:` and `TABLE I:`. Copy the template's look and you reproduce the defect the committee flagged.

### Authority 1 — the class file
```bash
grep -n "makecaption" IEEEtran.cls        # → the definition IEEEtran actually uses
```
IEEEtran's figure branch ends `{#1.}` — a **period**. Its table branch is
`#1 \\ {\normalfont\footnotesize\scshape #2}` — label on its own line, title in **small caps**.

### Authority 2 — the Word template's style definitions
A `.docx` is a zip. The style definitions *are* the specification:
```bash
unzip -o UBMKtemplateA4.docx -d docx/
python3 - <<'EOF'
import re
s = open('docx/word/styles.xml', encoding='utf8').read()
for m in re.finditer(r'<w:style [^>]*w:styleId="([^"]*)"[^>]*>(.*?)</w:style>', s, re.S):
    sid, body = m.groups()
    if re.search(r'table|figure|caption', sid, re.I):
        caps = 'SMALLCAPS' if '<w:smallCaps' in body else ('ALLCAPS' if '<w:caps' in body else '')
        print(f"{sid:24s} {caps}")
EOF
```
Actual output from the venue's template:
```
figurecaption
tablehead                SMALLCAPS
```

**Two independent authorities agree: table caption titles are small caps.** That is what makes
the deviation from the template's rendered output defensible — and it exposed a second defect
nobody had flagged: `font=footnotesize` *replaces* the caption font rather than adding to it, so
it had been silently deleting IEEEtran's `\scshape` all along.

### The resulting preamble
```latex
\usepackage[font=footnotesize,labelsep=period]{caption}     % "Fig. 1."
\captionsetup[table]{labelsep=newline,font={footnotesize,sc},justification=centering}
% "TABLE I" on its own line above a centred small-caps title
```

Verify on the **rendered PDF**, never the source:
```bash
pdftotext main.pdf - | grep -oE "Fig\. [0-9]+[.:]|TABLE [IVX]+:?" | sort -u
# want: "Fig. 1."  "TABLE I"      reject any colon
```

### One template value worth overriding
`\setlength{\floatsep}{0pt}` is prescribed by the template but makes two floats stacked in one
column collide visually. `6pt` matches the template's own `\textfloatsep`/`\intextsep`, so it
stays inside the template's spacing family. Document deviations in a comment.

---

## D. Case study — a plausible checklist that was mostly wrong

The author received a well-formatted "IEEE Compliance Prompt": ~20 confident, professionally
worded corrections. Checked item by item against `IEEEtran.cls` and the venue template, **most
were wrong**, in two clusters:

1. **PDF text-extraction artifacts.** Items reporting broken spacing or mangled headings that
   existed only in `pdftotext` output, not in the rendered page. Small caps in particular extract
   as `R ECONSTRUCTION` — an artifact, not a defect.
2. **Contradicting the actual template.** Items asserting IEEE conventions the venue's own class
   and template did not use.

Applying it wholesale would have introduced errors into a paper that was already correct.

**Lesson:** advice — from a human, another agent, or a checklist — is a hypothesis. The class
file and the style definitions are the evidence. Fluency is not authority. This applies to your
own prior output too: re-derive, don't re-trust.

---

## E. The scientific reviews (not formatting)

Formatting feedback is loud and easy; the substantive reviews decided the outcome and drove
structural changes that look unmotivated in a commit log unless traced back here.

**Paper 1 (cipher) — critical:**
> Bununla beraber literatürdeki saldırılarla bir karşılaştırma sunmamışlardır. Dolayısıyla bu
> çalışmadaki yazarın/yazarların katkıları tam olarak anlaşılamamaktadır. […] görüntü şifrelemede
> kaos tabanlı şifrelerin kullanıldığı gerçek dünya örnekleri bulunmamaktadır. […] Sonuç olarak
> bu çalışmanın Literatüre katkısının sınırlı olacağı düşüncesindeyim.

*(No comparison against attacks in the literature, so the contribution isn't legible; no
real-world deployments of chaos-based image ciphers; limited contribution to the literature.)*

Plus, separately:
> Needs a deep software grammar check, as there are many typos, broken sentences, and hyphenation
> problems like perimage, differentialattack, cellularautomata, etc. Broken English creates a
> heavy barrier to this otherwise very sound paper.

| Complaint | Structural response |
|---|---|
| No comparison with prior attacks | Added the comparison table placing the break beside prior equivalent-key cryptanalyses |
| Contribution not legible | Reframed contributions around what is *delivered*, not deferred |
| No real-world usage | Added a "Real-World Stakes" subsection citing actual proposed deployments (DICOM/telemedicine) — scoped honestly to *proposed*, since no documented product was found |
| `perimage`, `differentialattack` | `\exhyphenpenalty=10000` — stops line-breaking at explicit compound hyphens, so extracted text stays clean **and future compounds are covered automatically** (D2 applied to a typographic defect) |

**Paper 2 (IDS) — accepted:**
> Çalışma mevcut haliyle konferans kapsamına uygun ve kabul edilebilir düzeydedir.

Note the asymmetry: the paper that was *accepted on content* was the one still carrying every
formatting defect. Acceptance on substance is not evidence of conformance — D6.

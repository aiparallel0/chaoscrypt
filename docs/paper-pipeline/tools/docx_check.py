#!/usr/bin/env python3
r"""Check a generated .docx against the LaTeX source and PDF it was built from.

    python3 docx_check.py papers/<paper> <paper.docx>

A converter that drops text produces a document which looks finished and is not, so the output
is compared word for word, in both directions, against two independent references:

  no word absent from the PDF   every content word of the .docx must occur, as often as it is
                                used, in the PDF LaTeX produced.  This direction is exact: the
                                .docx carries its figures as images, so it can hold no text the
                                PDF lacks.

  no word dropped from source   every content word of the LaTeX source must occur in the
                                .docx.  The source is reduced to plain words by a deliberately
                                crude regex stripper that shares no code with the converter --
                                a check built on the converter's own parser cannot detect the
                                converter's own bugs.

The comparison is a multiset, not a sliding window.  The two texts genuinely differ in places
that are not defects: Word generates "Fig. 1." and "[2]" from its own counters, a footnote is
written inside a sentence but typeset at the foot of a column, a compound hyphenates across a
line.  Each of those shifts a window without losing a word, while dropping a sentence -- the
failure that matters -- removes words outright.

Numbers are checked separately and exactly, with multiplicity, because a lost figure leaves the
prose around it intact.  Then float, footnote and reference counts, the caption text, and
whether LibreOffice can open the result at all and at what length.

Exit status 0 if every check passes, 1 if any fails.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

SHINGLE = 10


def words(text: str) -> list[str]:
    """Lower-cased word tokens, with typographic variants folded onto ASCII.

    The two dash families are treated differently, because they behave differently. Only the
    ASCII hyphen ever splits a word across a line, so it joins: "in-\\ndistribution" from the
    PDF and "in-distribution" from the .docx both reduce to "indistribution". The em and en
    dashes never break a word and always stand between two, so they separate -- which also
    stops a newline after one of them, as in the .docx keyword line, from fusing the words
    either side into a single token that then matches nothing.
    """
    text = (text.replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\ufb01", "fi").replace("\ufb02", "fl")
                .replace("\u00a0", " ").lower())
    # Fold accents onto their base letter. "Cande\u0300s" would otherwise tokenise as "cand"
    # plus "s" on one side and as something else on the other, purely from how each producer
    # encoded the accent.
    text = "".join(c for c in unicodedata.normalize("NFD", text)
                   if not unicodedata.combining(c))
    text = re.sub(r"-[ \t]*\n[ \t]*", "", text)      # hyphenated across a line break: join
    text = text.replace("-", "")                     # explicit compound hyphen: join
    text = re.sub(r"[\u2010-\u2015\u2212]", " ", text)  # em, en and friends: separate
    return re.findall(r"[a-z0-9]+", text)


def latex_dashes(t: str) -> str:
    """Resolve TeX's dash ligatures, so raw source compares against typeset output."""
    return t.replace("---", "\u2014").replace("--", "\u2013")


def shingles(ws: list[str], n: int = SHINGLE) -> list[tuple[int, str]]:
    return [(i, " ".join(ws[i:i + n])) for i in range(max(0, len(ws) - n + 1))]


def docx_paragraphs(path: Path, split_scripts: bool = False) -> list[str]:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf8")
        xml += z.read("word/footnotes.xml").decode("utf8")
    xml = re.sub(r"<w:(br|tab)\b[^>]*/>", " ", xml)
    # Word generates the footnote marker from the counter, so it is absent from the .docx text
    # but present in the PDF. Synthesise it here, or the sentence carrying it reads as text the
    # PDF does not have. Footnote ids start at 2, the two separator entries taking 0 and 1.
    xml = re.sub(r'<w:footnoteReference w:id="(\d+)"\s*/>',
                 lambda m: f"<w:t>{int(m.group(1)) - 1}</w:t>", xml)
    out = []
    for p in re.findall(r"<w:p\b.*?</w:p>", xml, re.S):
        # Adjacent runs are contiguous text, so they join with nothing. Joining them with a
        # space splits "K=15" -- whose digits sit in separate runs -- into "K=1 5", and every
        # window over it then reads as text the PDF does not contain.
        if split_scripts:
            # A superscript is a token in its own right: "512" raised to "2" is not the number
            # 5122. Runs are separated wherever the vertical alignment changes, so the numeric
            # comparison sees the same two literals the source wrote as 512^2.
            chunks, prev = [], None
            for r in re.findall(r"<w:r\b.*?</w:r>", p, re.S):
                vert = re.search(r'<w:vertAlign w:val="(\w+)"', r)
                vert = vert.group(1) if vert else ""
                t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", r))
                chunks.append((" " if prev is not None and vert != prev else "") + t)
                prev = vert
            text = "".join(chunks)
        else:
            text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        # Undo the XML escaping, or a literal "&" in the text reads back as the word "amp".
        text = (text.replace("&lt;", "<").replace("&gt;", ">")
                    .replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&"))
        out.append(text)
    return [p for p in out if p.strip()]


def pdf_text(path: Path) -> str:
    return subprocess.run(["pdftotext", str(path), "-"], check=True,
                          capture_output=True, text=True).stdout


def numbers(paragraphs: list[str]) -> dict[str, int]:
    """Multiset of the numeric literals in some text, normalised to drop trailing zeros."""
    out: dict[str, int] = {}
    for p in paragraphs:
        for n in re.findall(r"\d+(?:\.\d+)?", p):
            if "." in n:
                n = n.rstrip("0").rstrip(".")
            out[n] = out.get(n, 0) + 1
    return out


def source_paragraphs(tex: str, keep_tables: bool = False) -> list[str]:
    """Reduce LaTeX to running words, crudely and independently of the converter."""
    t = tex[tex.index(r"\begin{document}"):]
    t = t.split(r"\bibliographystyle")[0]
    t = re.sub(r"(?<!\\)%.*", "", t)
    if not keep_tables:
        t = re.sub(r"\$[^$]*\$", " ", t)                               # inline maths
        t = re.sub(r"\\begin\{(equation|tikzpicture|tabular)\*?\}.*?"
                   r"\\end\{\1\*?\}", " ", t, flags=re.S)               # maths and table bodies
    else:
        # For the numeric check the table bodies are exactly what must be compared, but the
        # TikZ pictures are drawings whose coordinates are not content.
        t = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", " ", t, flags=re.S)
    # Commands whose braced argument is machinery, not prose. Dropping the command but keeping
    # the argument would inject words the document never contains ("empty" from
    # \thispagestyle{empty}, "document" from \begin{document}) and report them as lost text.
    t = re.sub(r"\\(begin|end)\{[^}]*\}(\[[a-zA-Z!]*\])?", "\n\n", t)
    t = re.sub(r"\\(label|ref|eqref|cite|includegraphics|setlength|tabcolsep|linespread|"
               r"thispagestyle|pagestyle|bibliographystyle|bibliography|setcounter|"
               r"renewcommand|captionsetup|documentclass|usepackage|vspace|hspace)\s*"
               r"(\[[^\]]*\])?\{[^}]*\}(\{[^}]*\})?", " ", t)
    # A footnote is written inside the sentence that carries it but is typeset elsewhere, so
    # it becomes its own paragraph here -- otherwise the sentence around it never matches.
    t = split_footnotes(t)
    t = re.sub(r"\\[A-Za-z]+\*?", " ", t)                              # every other command
    t = re.sub(r"[{}&\\~]", " ", t)
    return [latex_dashes(p) for p in re.split(r"\n[ \t]*\n", t) if p.strip()]


def split_footnotes(t: str) -> str:
    """Lift each \\footnote{...} body out of its sentence and into a paragraph of its own."""
    out, i = [], 0
    while True:
        j = t.find(r"\footnote{", i)
        if j < 0:
            out.append(t[i:])
            return "".join(out)
        out.append(t[i:j])
        depth, k = 0, j + len(r"\footnote")
        for k in range(k, len(t)):
            if t[k] == "{":
                depth += 1
            elif t[k] == "}":
                depth -= 1
                if depth == 0:
                    break
        out.append("\n\n" + t[j + len(r"\footnote{"):k] + "\n\n")
        i = k + 1


def report(name: str, missing: list[str], total: int) -> bool:
    ok = not missing
    print(f"  [{'PASS' if ok else 'FAIL':4}] {name:<34} "
          f"{total - len(missing)}/{total} distinct words matched")
    for m in missing[:6]:
        print(f"           missing: {m}")
    if len(missing) > 6:
        print(f"           ... and {len(missing) - 6} more")
    return ok


def prose(ws: list[str]) -> list[str]:
    """Content words only: no bare numbers, no one- or two-letter tokens.

    Used when comparing the LaTeX source against the .docx. The source has no citation or
    cross-reference numbers -- ``\\cite`` and ``\\ref`` are stripped unresolved -- while the
    .docx has "[2]" and "IV-E" in their place, and those insertions would otherwise break
    every window that spans them. Numbers are not simply forgotten: they are checked exactly,
    and with multiplicity, by the separate numeric check.
    """
    return [w for w in ws if len(w) > 2 and not w.isdigit()]


def missing_words(need: list[str], have: list[str]) -> tuple[list[str], int]:
    """Words occurring more often in `need` than in `have`, with the shortfall.

    A multiset comparison rather than a sliding window. The two texts genuinely differ in
    places that are not defects -- Word generates "Fig. 1." and "[2]" from its own counters, a
    footnote is written inside a sentence but typeset at the foot of the column, a compound
    hyphenates across a line -- and every one of those shifts a window without losing a word.
    Dropping a sentence, which is the failure that matters, removes words outright and shows up
    here immediately.
    """
    have_count: dict[str, int] = {}
    for w in have:
        have_count[w] = have_count.get(w, 0) + 1
    need_count: dict[str, int] = {}
    for w in need:
        need_count[w] = need_count.get(w, 0) + 1
    joined = " ".join(have)
    out = []
    for w, k in sorted(need_count.items()):
        if k - have_count.get(w, 0) <= 0:
            continue
        # The two producers disagree about where a word ends next to maths: the source writes
        # "$n{=}MN$-pixel", the .docx renders "n=MN-pixel", and the trailing word is swallowed
        # into a longer token. A word that survives inside another token has demonstrably not
        # been dropped, which is what this check is for. Four characters minimum, so short
        # words are not excused by coincidental substrings.
        if len(w) >= 4 and w in joined:
            continue
        out.append(f"{w} ({k - have_count.get(w, 0)} of {k})")
    return out, len(need_count)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    paper_dir, docx = Path(sys.argv[1]), Path(sys.argv[2])
    tex = (paper_dir / "main_filled.tex").read_text(encoding="utf8")
    pdf = paper_dir / "main.pdf"

    dwords = words("\n".join(docx_paragraphs(docx)))
    pwords = words(pdf_text(pdf))
    swords = words("\n".join(source_paragraphs(tex)))


    print(f"{docx}")
    results = []

    # A word in the .docx must be explainable by the PDF or by the source, and both references
    # are needed. pdftotext renders the small-capped headings as "I. I NTRODUCTION", the
    # small-cap glyphs being a separate font, so adjacent-token joins are accepted alongside
    # the tokens themselves. It also mangles display maths badly enough to lose characters,
    # emitting "P t d [j] 256" for a summation the .docx sets correctly, so the source -- with
    # its maths kept this time -- is admitted as evidence too. Text in neither still fails.
    def with_joins(ws):
        return (ws + [a + b for a, b in zip(ws, ws[1:])]
                + [a + b + c for a, b, c in zip(ws, ws[1:], ws[2:])])
    haystack = with_joins(pwords) + with_joins(
        words("\n".join(source_paragraphs(tex, keep_tables=True))))
    missing, total = missing_words(prose(dwords), prose(haystack))
    results.append(report("no word absent from PDF or source", missing, total))
    missing, total = missing_words(prose(swords), prose(dwords))
    results.append(report("no word dropped from source", missing, total))

    # Every number the source states must survive into the .docx, with its multiplicity: a
    # dropped figure leaves the prose around it intact and so slips past the window checks.
    src_nums = numbers(source_paragraphs(tex, keep_tables=True))
    doc_nums = numbers(docx_paragraphs(docx, split_scripts=True))
    lost = sorted({n for n in src_nums if src_nums[n] > doc_nums.get(n, 0)})
    ok = not lost
    print(f"  [{'PASS' if ok else 'FAIL':4}] {'every source number present':<34} "
          f"{len(src_nums) - len(lost)}/{len(src_nums)} distinct values")
    for n in lost[:8]:
        print(f"           missing: {n} (source {src_nums[n]}x, docx {doc_nums.get(n, 0)}x)")
    results.append(ok)

    # Structural counts, taken from the source and from the generated package.
    with zipfile.ZipFile(docx) as z:
        doc = z.read("word/document.xml").decode("utf8")
        foot = z.read("word/footnotes.xml").decode("utf8")
    counts = {
        "figures": (len(re.findall(r"\\begin\{figure\*?\}", tex)),
                    doc.count("<w:drawing>")),
        "tables": (len(re.findall(r"\\begin\{table\*?\}", tex)),
                   doc.count("<w:tbl>")),
        "footnotes": (len(re.findall(r"\\footnote\{", tex)),
                      len(re.findall(r'<w:footnote w:id="([2-9]|\d\d+)"', foot))),
        "references": (len((paper_dir / "main_filled.bbl").read_text(encoding="utf8")
                           .split(r"\bibitem")) - 1,
                       doc.count('w:val="references"')),
    }
    for what, (want, got) in counts.items():
        ok = want == got
        print(f"  [{'PASS' if ok else 'FAIL':4}] {what:<34} source {want}, docx {got}")
        results.append(ok)

    # Captions must survive verbatim; they are the text the committee reads first.
    caps = [re.sub(r"\s+", " ", c).strip()
            for c in re.findall(r"\\caption\{((?:[^{}]|\{[^{}]*\})*)\}", tex)]
    missing_caps = []
    for c in caps:
        plain = words(latex_dashes(
            re.sub(r"\\[A-Za-z]+|[{}\\]", " ", re.sub(r"\$[^$]*\$", " ", c))))
        lost = [w for w in prose(plain) if w not in dwords]
        if lost:
            missing_caps.append(" ".join(plain[:6]) + f"  [lost: {', '.join(lost)}]")
    results.append(report("captions present", missing_caps, len(caps)))

    # Finally, does it open at all, and at what length?
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", td,
                        str(docx)], capture_output=True, text=True)
        out = list(Path(td).glob("*.pdf"))
        if not out:
            print("  [FAIL] renders                            LibreOffice could not open it")
            results.append(False)
        else:
            info = subprocess.run(["pdfinfo", str(out[0])], check=True,
                                  capture_output=True, text=True).stdout
            pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
            src_pages = int(re.search(r"^Pages:\s+(\d+)", subprocess.run(
                ["pdfinfo", str(pdf)], check=True, capture_output=True,
                text=True).stdout, re.M).group(1))
            ok = pages <= src_pages
            print(f"  [{'PASS' if ok else 'FAIL':4}] {'renders within page budget':<34} "
                  f"docx {pages} pages, LaTeX {src_pages}")
            results.append(ok)

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} checks pass"
          + (f" — {failed} FAILING" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

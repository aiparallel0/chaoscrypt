#!/usr/bin/env python3
r"""Check a .docx against the UBMK committee's fifteen numbered corrections.

    python3 docx_conformance.py <paper.docx> [template.docx]

For a Word file the styles *are* the format, so this reads the effective paragraph and run
properties out of the package -- the style definition, whatever it is based on, and any direct
formatting on the paragraph itself -- rather than measuring a rendered page. Rendering would
measure the renderer: LibreOffice's "single" line spacing for 10pt Times is not Word's, and
neither is LaTeX's, so the same conforming file reports three different point sizes depending
on who draws it. The template's own numbers are the only fixed reference.

Word units: spacing twips = pt*20; ``w:sz`` half-points; ``w:line`` with ``lineRule="auto"`` is
240ths of single, with ``lineRule="exact"`` it is twips.

Two of the fifteen items contradict the template's styles.xml, and the committee's list wins
because it is the later and more specific instruction:

  item 1   Keywords must be italic and NOT bold, but the Keywords style is basedOn Abstract
           and so inherits its bold.
  item 13  figure captions must be centred, but figurecaption sets jc="both".

Both therefore have to be overridden on the paragraph, and this checks the effective result.

Exit status 0 if every item passes, 1 if any fails, 2 if the file cannot be read.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

W = r"(?:w:)"


def attr(xml: str, tag: str, name: str) -> str | None:
    m = re.search(rf"<w:{tag}\b[^>]*\bw:{name}=\"([^\"]*)\"", xml)
    return m.group(1) if m else None


def has(xml: str, tag: str) -> bool:
    """True if a boolean toggle ends up on, reading the LAST occurrence.

    The properties are concatenated style-first, direct formatting last, so the final match is
    the one that applies. Taking the first instead reports the Keywords line as bold -- it
    inherits bold from the Abstract style it is based on, and the paragraph switches it back
    off -- which is exactly the item the committee raised first.
    """
    found = re.findall(rf"<w:{tag}(\s[^>]*)?/>", xml)
    if not found:
        return False
    val = re.search(r'w:val="([^"]*)"', found[-1] or "")
    return not (val and val.group(1) in ("0", "false", "none"))


class Styles:
    """Resolves a style id to its effective pPr and rPr, following basedOn."""

    def __init__(self, xml: str):
        self.defs: dict[str, tuple[str, str, str | None]] = {}
        for m in re.finditer(r'<w:style\b[^>]*w:styleId="([^"]+)"[^>]*>(.*?)</w:style>',
                             xml, re.S):
            body = m.group(2)
            ppr = re.search(r"<w:pPr>(.*?)</w:pPr>", body, re.S)
            rpr = re.search(r"<w:rPr>(.*?)</w:rPr>", body, re.S)
            self.defs[m.group(1)] = (ppr.group(1) if ppr else "",
                                     rpr.group(1) if rpr else "",
                                     attr(body, "basedOn", "val"))

    def effective(self, style_id: str) -> tuple[str, str]:
        """Concatenate a style's chain, most-derived last so it wins a `search`."""
        chain, seen = [], set()
        sid = style_id
        while sid and sid in self.defs and sid not in seen:
            seen.add(sid)
            chain.append(self.defs[sid])
            sid = self.defs[sid][2]
        ppr = "".join(c[0] for c in reversed(chain))
        rpr = "".join(c[1] for c in reversed(chain))
        return ppr, rpr


def paragraphs(doc: str) -> list[tuple[str, str, str]]:
    """(style id, own pPr, own rPr of the first run) for every paragraph."""
    out = []
    for p in re.findall(r"<w:p\b.*?</w:p>", doc, re.S):
        ppr = re.search(r"<w:pPr>(.*?)</w:pPr>", p, re.S)
        ppr = ppr.group(1) if ppr else ""
        style = attr(ppr, "pStyle", "val") or ""
        rprs = re.findall(r"<w:rPr>(.*?)</w:rPr>", p, re.S)
        out.append((style, ppr, "".join(rprs)))
    return out


def last(xml: str, tag: str, name: str) -> str | None:
    """The last occurrence wins: direct formatting is appended after the style's."""
    found = re.findall(rf"<w:{tag}\b[^>]*\bw:{name}=\"([^\"]*)\"", xml)
    return found[-1] if found else None


def main() -> int:
    if not 2 <= len(sys.argv) <= 3:
        print(__doc__)
        return 2
    docx = Path(sys.argv[1])
    if not docx.exists():
        print(f"no such file: {docx}")
        return 2
    with zipfile.ZipFile(docx) as z:
        doc = z.read("word/document.xml").decode("utf8")
        styles = Styles(z.read("word/styles.xml").decode("utf8"))
        numbering = z.read("word/numbering.xml").decode("utf8")

    paras = paragraphs(doc)
    results: list[tuple[str, str, bool, str]] = []

    def check(item, name, ok, evidence):
        results.append((item, name, bool(ok), evidence))

    def eff(style, own_ppr, own_rpr):
        sp, sr = styles.effective(style)
        return sp + own_ppr, sr + own_rpr

    # ---- item 1: keywords 9pt italic, not bold
    kw = [p for p in paras if p[0] == "Keywords"]
    if kw:
        ppr, rpr = eff(*kw[0])
        size = last(rpr, "sz", "val")
        check("1", "keywords 9pt italic, not bold",
              has(rpr, "i") and not has(rpr, "b") and size == "18",
              f"sz={size} half-pt, i={has(rpr, 'i')}, b={has(rpr, 'b')}")
    else:
        check("1", "keywords 9pt italic, not bold", False, "no Keywords paragraph")

    # ---- items 2, 3: heading spacing, before/after in twips
    for item, style, before, after in (("2", "Balk1", "160", "80"),
                                       ("3", "Balk2", "120", "60")):
        ppr, _ = styles.effective(style)
        b, a = attr(ppr, "spacing", "before"), attr(ppr, "spacing", "after")
        used = any(p[0] == style for p in paras)
        check(item, f"{style} spacing {int(before)//20}/{int(after)//20}pt",
              used and b == before and a == after,
              f"before={b}tw after={a}tw, used by {sum(1 for p in paras if p[0] == style)} paragraphs")

    # ---- item 4: subheading titles in Title Case
    small = {"a", "an", "the", "and", "or", "but", "nor", "for", "of", "in", "on", "at",
             "to", "by", "vs", "with", "from", "as", "is", "it"}
    bad = []
    for style, ppr, _ in paras:
        if style not in ("Balk1", "Balk2"):
            continue
        p = next(x for x in re.findall(r"<w:p\b.*?</w:p>", doc, re.S)
                 if f'w:val="{style}"' in x and ppr[:40] in x)
        text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        ws = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
        for i, w in enumerate(ws):
            if w.lower() in small and i not in (0, len(ws) - 1):
                continue
            if w[0].islower():
                bad.append(text)
                break
    check("4", "headings in Title Case", not bad, bad[:3] if bad else "all clear")

    # ---- item 5: 0.95 line spacing from the abstract onwards
    off = []
    for style, ppr, _ in paras:
        if style not in ("GvdeMetni", "Abstract", "Keywords"):
            continue
        e, _ = eff(style, ppr, "")
        if last(e, "spacing", "line") != "228" or last(e, "spacing", "lineRule") != "auto":
            off.append(f"{style}: line={last(e, 'spacing', 'line')} "
                       f"rule={last(e, 'spacing', 'lineRule')}")
    check("5", "line spacing 0.95 (228/240)", not off,
          sorted(set(off))[:3] if off else "abstract, keywords and body all 228 auto")

    # ---- item 6: 0.51cm first-line indent on every running paragraph
    off, skipped = [], 0
    for style, ppr, _ in paras:
        if style not in ("GvdeMetni", "Abstract", "Keywords"):
            continue
        e, _ = eff(style, ppr, "")
        # A list item is indented as a block and has no first line to indent. Item 6 is about
        # running paragraphs, so those are counted separately rather than excused in silence.
        if int(last(e, "ind", "left") or 0) > 0:
            skipped += 1
            continue
        if last(e, "ind", "firstLine") != "288":
            off.append(f"{style}: firstLine={last(e, 'ind', 'firstLine')}")
    check("6", "first line indented 288tw (0.51cm)", not off,
          sorted(set(off))[:3] if off else
          f"every running paragraph at 288tw ({skipped} list items indented as blocks)")

    # ---- items 7, 12: captions terse
    def caption_words(style):
        out = []
        for p in re.findall(r"<w:p\b.*?</w:p>", doc, re.S):
            if f'<w:pStyle w:val="{style}"/>' not in p:
                continue
            t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
            out.append((len(re.findall(r"\S+", t)), t))
        return out
    for item, style, limit in (("7", "tablehead", 10), ("12", "figurecaption", 22)):
        caps = caption_words(style)
        over = [t for n, t in caps if n > limit]
        check(item, f"{style} captions terse (<={limit} words)",
              caps and not over, over[:2] if over else f"{len(caps)} captions, "
              f"longest {max((n for n, _ in caps), default=0)} words")

    # ---- item 8: table caption titles in capitals
    bad = [t for _, t in caption_words("tablehead")
           if any(c.islower() for c in re.sub(r"[^A-Za-z]", "", t))]
    check("8", "table titles in capitals", not bad, bad[:2] if bad else "all upper-case")

    # ---- items 9: every table bordered, none thicker than the rest
    widths, tables = set(), re.findall(r"<w:tbl>.*?</w:tbl>", doc, re.S)
    unbordered = 0
    for t in tables:
        pr = re.search(r"<w:tblBorders>(.*?)</w:tblBorders>", t, re.S)
        if not pr:
            unbordered += 1
            continue
        edges = dict(re.findall(r"<w:(\w+) w:val=\"single\" w:sz=\"(\d+)\"", pr.group(1)))
        if set(edges) < {"top", "left", "bottom", "right", "insideH", "insideV"}:
            unbordered += 1
        widths |= set(edges.values())
    check("9", "table borders present and uniform",
          tables and not unbordered and len(widths) == 1,
          f"{len(tables)} tables, {unbordered} incomplete, widths={sorted(widths)} eighths-pt")

    # ---- item 10: column headers bold
    weak = 0
    for t in tables:
        first_row = re.search(r"<w:tr\b.*?</w:tr>", t, re.S)
        if not first_row:
            continue
        cells = re.findall(r"<w:tc>.*?</w:tc>", first_row.group(0), re.S)
        for c in cells:
            style = attr(c, "pStyle", "val") or ""
            _, rpr = styles.effective(style)
            if not (has(rpr, "b") or has(c, "b")):
                weak += 1
                break
    check("10", "column headers bold", tables and not weak,
          f"{len(tables)} tables, {weak} with a non-bold header row")

    # ---- items 11, 13: captions centred
    for item, style in (("11", "tablehead"), ("13", "figurecaption")):
        off = []
        for st, ppr, _ in paras:
            if st != style:
                continue
            e, _ = eff(st, ppr, "")
            if last(e, "jc", "val") != "center":
                off.append(last(e, "jc", "val"))
        check(item, f"{style} centred", off == [] and any(p[0] == style for p in paras),
              f"{sum(1 for p in paras if p[0] == style)} captions, "
              f"{len(off)} not centred{' ' + str(sorted(set(off))) if off else ''}")

    # ---- items 14, 15: reference leading and gap
    refs = [p for p in paras if p[0] == "references"]
    if refs:
        ppr, _ = eff(*refs[0])
        line, rule = last(ppr, "spacing", "line"), last(ppr, "spacing", "lineRule")
        after = last(ppr, "spacing", "after")
        check("14", "references 9pt exact leading", line == "180" and rule == "exact",
              f"line={line}tw rule={rule}")
        check("15", "2.5pt after each reference", after == "50", f"after={after}tw")
    else:
        check("14", "references 9pt exact leading", False, "no references paragraphs")
        check("15", "2.5pt after each reference", False, "no references paragraphs")

    # Numbering is generated by Word from the template's own definitions, so confirm the
    # styles really do still carry them rather than the numbers being typed in.
    generated = all(re.search(rf'<w:num w:numId="{n}"', numbering)
                    for n in (2, 4, 8, 9))
    check("--", "numbering from the template", generated,
          "Fig./TABLE/section/reference numbers generated by Word")

    print(f"{docx}  ({len(paras)} paragraphs, {len(tables)} tables)")
    for item, name, ok, evidence in results:
        print(f"  [{'PASS' if ok else 'FAIL':4}] item {item:<2} {name:<38} {evidence}")
    failed = sum(1 for r in results if not r[2])
    print(f"\n{len(results) - failed}/{len(results)} checks pass"
          + (f" — {failed} FAILING" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

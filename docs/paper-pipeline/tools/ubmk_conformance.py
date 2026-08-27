#!/usr/bin/env python3
"""Check a rendered paper against the UBMK template's measurable formatting rules.

    python3 ubmk_conformance.py papers/<paper>/main.pdf [papers/<paper>/main.tex]

Every target below is a style value read out of ``UBMKtemplateA4.docx`` (``word/styles.xml``),
converted from Word units, and independently restated by the organising committee's correction
notice.  Word units: spacing twips = pt*20; ``w:sz`` half-points; ``w:line`` with
``lineRule="auto"`` is 240ths of a line, with ``lineRule="exact"`` it is twips.

    Balk1  heading 1     before 160tw = 8pt    after 80tw = 4pt          -> items 2
    Balk2  heading 2     before 120tw = 6pt    after 60tw = 3pt          -> item  3
    GvdeMetni body       line 228/240 = 0.95   firstLine 288tw = 0.508cm -> items 5, 6
    references           line 180tw exact = 9pt   after 50tw = 2.5pt     -> items 14, 15
    Author               name sz 22 = 11pt     affiliation sz 20 = 10pt  -> author block
    docDefaults          Times New Roman throughout, no monospaced face

Measures the RENDERED PDF, because a source-level check cannot see what a package override did:
``\\usepackage[font=footnotesize]{caption}`` silently discarded IEEEtran's caption format for
91 commits without a warning, and ``\\parskip`` was being added to heading spacing invisibly.

Exit status 0 if every check passes, 1 if any fails, 2 if the input yields nothing to measure
(an empty or wrong file must never score a pass by having no findings).
"""
from __future__ import annotations

import re
import statistics
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

# (target, tolerance) in points
BODY_PITCH = (11.40, 0.25)   # 0.95 * 12pt, after the abstract   -- item 5
INDENT = (14.46, 0.60)       # 0.51 cm                           -- item 6
REF_PITCH = (9.00, 0.35)     # exact 9pt                         -- item 14
REF_GAP = (2.50, 0.60)       # 2.5pt                             -- item 15
ABS_PITCH = (9.96, 0.30)     # single, not 0.95                  -- item 5, as corrected
ABS_KEY_GAP = (10.00, 1.00)  # abstract to keywords              -- correction item 2
PARA_GAP = (6.00, 1.20)      # after every paragraph             -- correction item 3
SEC_GAP = (8.00, 1.00)       # before a section heading          -- item 2
SUB_GAP = (6.00, 1.20)       # before a subsection heading       -- item 3

COLUMN_SPLIT = 300.0         # A4 two-column: left column xMin < 300


def lines_on(pdf: Path, page: int):
    """Return [(xMin, yMin, xMax, yMax, text)] for one page, via pdftotext -bbox-layout."""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as fh:
        out = Path(fh.name)
    subprocess.run(
        ["pdftotext", "-bbox-layout", "-f", str(page), "-l", str(page), str(pdf), str(out)],
        check=True, capture_output=True,
    )
    xml = out.read_text(encoding="utf8", errors="replace")
    out.unlink(missing_ok=True)
    rows = []
    for m in re.finditer(
        r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>',
        xml, re.S,
    ):
        x0, y0, x1, y1 = (float(g) for g in m.groups()[:4])
        text = " ".join(re.findall(r">([^<]*)</word>", m.group(5)))
        rows.append((x0, y0, x1, y1, text))
    return rows


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def columns(rows):
    """Split a page's lines into left and right column, each sorted top to bottom."""
    for lo, hi in ((0, COLUMN_SPLIT), (COLUMN_SPLIT, 10_000)):
        col = sorted((r for r in rows if lo <= r[0] < hi), key=lambda r: r[1])
        if len(col) > 3:
            yield col


def modal_pitch(pdf: Path, pages) -> tuple[float, int]:
    """Most common baseline-to-baseline distance in body columns, and the sample size."""
    deltas = []
    for pg in pages:
        for col in columns(lines_on(pdf, pg)):
            for a, b in zip(col, col[1:]):
                d = b[1] - a[1]
                if 5.0 < d < 20.0:
                    deltas.append(round(d, 1))
    if not deltas:
        return 0.0, 0
    return statistics.mode(deltas), len(deltas)


def measure_indent(pdf: Path, pages) -> tuple[float, int]:
    """Indent = (modal indented x) - (modal flush-left x), per column."""
    offsets = []
    for pg in pages:
        for col in columns(lines_on(pdf, pg)):
            xs = [round(r[0], 1) for r in col]
            flush = statistics.mode(xs)
            cand = [x - flush for x in xs if 4.0 < (x - flush) < 30.0]
            offsets.extend(round(c, 1) for c in cand)
    if not offsets:
        return 0.0, 0
    return statistics.mode(offsets), len(offsets)


def measure_references(pdf: Path, last_page: int):
    """Within-entry line pitch and the extra space added between entries."""
    within, between = [], []
    for pg in (last_page - 1, last_page):
        if pg < 1:
            continue
        for col in columns(lines_on(pdf, pg)):
            starts = [bool(re.match(r"^\[\d+\]", r[4])) for r in col]
            if sum(starts) < 3:
                continue
            for i in range(len(col) - 1):
                d = col[i + 1][1] - col[i][1]
                if not (5.0 < d < 20.0):
                    continue
                (between if starts[i + 1] else within).append(d)
    w = statistics.median(within) if within else 0.0
    b = statistics.median(between) if between else 0.0
    return w, b - w, len(within), len(between)


def pdf_objects(raw: bytes) -> dict[int, bytes]:
    """Every indirect object, with PDF 1.5 /ObjStm containers expanded."""
    objs = {}
    for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\b(.*?)endobj", raw, re.S):
        objs[int(m.group(1))] = m.group(3)
    for body in list(objs.values()):
        if b"/ObjStm" not in body:
            continue
        data, first, n = pdf_stream(body), re.search(rb"/First\s+(\d+)", body), re.search(rb"/N\s+(\d+)", body)
        if not (data and first and n):
            continue
        first, n, nums = int(first.group(1)), int(n.group(1)), data[:int(first.group(1))].split()
        for i in range(n):
            if 2 * i + 1 >= len(nums):
                break
            num, off = int(nums[2 * i]), int(nums[2 * i + 1])
            end = int(nums[2 * i + 3]) + first if 2 * i + 3 < len(nums) else len(data)
            objs.setdefault(num, data[first + off:end])
    return objs


def pdf_stream(body: bytes) -> bytes:
    m = re.search(rb"stream\r?\n(.*?)\r?\nendstream", body, re.S)
    if not m:
        return b""
    if b"FlateDecode" in body.split(b"stream")[0]:
        try:
            return zlib.decompress(m.group(1))
        except zlib.error:
            return b""
    return m.group(1)


def title_block(pdf: Path):
    """Page-1 lines as [(size_pt, font_name, text)], read from the content stream.

    The size a line was *set* at, not the height its glyphs happened to draw: a 10pt Courier
    e-mail and a 10pt Times one share a nominal size but not a look, and it was the Courier
    one -- ``\\texttt`` around the address -- that the committee returned the paper over.
    """
    objs = pdf_objects(pdf.read_bytes())
    pages = [b for _, b in sorted(objs.items()) if re.search(rb"/Type\s*/Page[\s/>]", b)]
    if not pages:
        return []
    page = pages[0]

    def deref(body, key):
        m = re.search(key + rb"\s+(\d+)\s+\d+\s+R", body)
        return objs.get(int(m.group(1)), b"") if m else b""

    # /Font is usually written inline inside /Resources rather than as an indirect reference,
    # so each fallback must land on the resources dictionary -- falling back to the page
    # instead yields an empty font map, and every name then reads as "?", which compares
    # equal to every other "?" and turns the comparison below into a guaranteed pass.
    resources = deref(page, rb"/Resources") or page
    fontdict = deref(resources, rb"/Font") or resources
    fonts = {}
    for k, ref in re.findall(rb"/(F\d+)\s+(\d+)\s+\d+\s+R", fontdict):
        base = re.search(rb"/BaseFont\s*/([-\w+]+)", objs.get(int(ref), b""))
        fonts[k.decode()] = base.group(1).decode().split("+")[-1] if base else "?"

    content = b"".join(pdf_stream(objs.get(int(r), b"")) for r in re.findall(rb"/Contents\s+(\d+)\s+\d+\s+R", page))
    out, line, cur = [], [], (0.0, "?")
    # A TJ array is matched non-greedily rather than by excluding brackets: the shown text may
    # itself contain "[" and "]", as an unfilled "[email@domain]" author line does.
    for m in re.finditer(rb"/(F\d+)\s+([\d.]+)\s+Tf|\[(.*?)\]\s*TJ"
                         rb"|\(((?:\\.|[^\\()])*)\)\s*Tj|(T\*|TD|Td|ET)", content, re.S):
        if m.group(1):
            cur = (float(m.group(2)), fonts.get(m.group(1).decode(), "?"))
        elif m.group(5):
            if line:
                out.append(line)
                line = []
        else:
            chunk = m.group(3) if m.group(3) is not None else b"(" + (m.group(4) or b"") + b")"
            raw = b"".join(re.findall(rb"\((?:\\.|[^\\()])*\)", chunk))
            s = re.sub(rb"\\(\d{3}|.)", b"?", raw).replace(b"(", b"").replace(b")", b"").decode("latin-1")
            if s.strip():
                line.append((cur[0], cur[1], s))
    if line:
        out.append(line)
    return [(ln[0][0], ln[0][1], "".join(t for _, _, t in ln).strip()) for ln in out if ln]


def front_matter(pdf: Path):
    """Abstract line pitch and the extra space above the keywords line, both in points."""
    col = [r for r in lines_on(pdf, 1) if r[0] < COLUMN_SPLIT]
    col.sort(key=lambda r: r[1])
    a = next((i for i, r in enumerate(col) if r[4].startswith("Abstract")), None)
    k = next((i for i, r in enumerate(col) if r[4].startswith("Keywords")), None)
    if a is None or k is None or k <= a + 1:
        return 0.0, 0.0, 0
    inner = [round(col[i + 1][1] - col[i][1], 2) for i in range(a, k - 1)]
    inner = [d for d in inner if 5.0 < d < 20.0]
    if not inner:
        return 0.0, 0.0, 0
    pitch = statistics.mode(inner)
    return pitch, (col[k][1] - col[k - 1][1]) - pitch, len(inner)


def gaps(pdf: Path, pages, kind: str, pitch: float):
    """Extra vertical space above headings or above paragraph first lines.

    A paragraph start is identified by its first line sitting exactly one indent to the right
    of the column's flush edge. Anything merely further right than flush also catches centred
    caption lines, whose own smaller leading then drags the measurement well below target.
    """
    out = []
    for pg in pages:
        for col in columns(lines_on(pdf, pg)):
            xs = [round(r[0], 1) for r in col]
            flush = statistics.mode(xs)
            for a, b in zip(col, col[1:]):
                d = b[1] - a[1]
                if not (5.0 < d < 40.0):
                    continue
                is_sec = re.match(r"^[IVX]+\.\s", b[4])
                is_sub = re.match(r"^[A-Z]\.\s", b[4])
                if kind == "section" and is_sec:
                    out.append(d - pitch)
                elif kind == "subsection" and is_sub:
                    out.append(d - pitch)
                elif kind == "paragraph" and not (is_sec or is_sub) \
                        and INDENT[0] - 1.0 < b[0] - flush < INDENT[0] + 1.0:
                    out.append(d - pitch)
    return (statistics.median(out) if out else 0.0), len(out)


def check(name, item, got, target, samples, unit="pt"):
    lo, hi = target[0] - target[1], target[0] + target[1]
    ok = samples > 0 and lo <= got <= hi
    status = "PASS" if ok else ("NO DATA" if samples == 0 else "FAIL")
    print(f"  [{status:7}] item {item:<2} {name:<34} {got:6.2f}{unit} "
          f"(want {target[0]}±{target[1]}, n={samples})")
    return ok, samples


def main() -> int:
    if not 2 <= len(sys.argv) <= 3:
        print(__doc__)
        return 2
    pdf = Path(sys.argv[1]).resolve()
    tex = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else None
    if not pdf.exists():
        print(f"no such pdf: {pdf}")
        return 2

    n = page_count(pdf)
    print(f"{pdf}  ({n} pages)")
    if n == 0:
        print("  nothing to measure")
        return 2

    body_pages = [p for p in range(2, n) if p >= 2] or [1]
    results, data = [], []

    pitch, npitch = modal_pitch(pdf, body_pages)
    ok, s = check("body line spacing (0.95)", "5", pitch, BODY_PITCH, npitch); results.append(ok); data.append(s)

    ind, nind = measure_indent(pdf, body_pages)
    ok, s = check("first-line indent (0.51cm)", "6", ind, INDENT, nind); results.append(ok); data.append(s)

    rw, rgap, nw, nb = measure_references(pdf, n)
    ok, s = check("reference line spacing", "14", rw, REF_PITCH, nw); results.append(ok); data.append(s)
    ok, s = check("space between references", "15", rgap, REF_GAP, nb); results.append(ok); data.append(s)

    # The committee corrected item 5 after the first round: 0.95 starts AFTER the abstract, so
    # the abstract and the keywords stay at single spacing.
    apitch, akgap, na = front_matter(pdf)
    ok, s = check("abstract line spacing (single)", "5", apitch, ABS_PITCH, na); results.append(ok); data.append(s)
    ok, s = check("abstract to keywords", "C2", akgap, ABS_KEY_GAP, 1 if na else 0); results.append(ok); data.append(s)

    for label, item, kind, target in (("space after a paragraph", "C3", "paragraph", PARA_GAP),
                                      ("space above a section", "2", "section", SEC_GAP),
                                      ("space above a subsection", "3", "subsection", SUB_GAP)):
        got, k = gaps(pdf, body_pages, kind, pitch)
        ok, s = check(label, item, got, target, k); results.append(ok); data.append(s)

    # Caption separators: the template's class uses a period for figures and a newline for
    # tables. A colon means a package overrode the class -- the defect the committee first
    # flagged, and one only the rendered text can reveal.
    txt = subprocess.run(["pdftotext", str(pdf), "-"], check=True,
                         capture_output=True, text=True).stdout
    colons = sorted(set(re.findall(r"Fig\. \d+:|TABLE [IVX]+:", txt)))
    figs = sorted(set(re.findall(r"Fig\. \d+\.", txt)))
    # The correction asks for a full stop after the table label too: "TABLE I.", not "TABLE I".
    tabs = sorted(set(re.findall(r"TABLE [IVX]+\.", txt)))
    # The numeral boundary is required: without it the matcher backtracks inside "TABLE III."
    # and reports "TABLE II" as a label with no stop after it.
    bare = sorted(set(re.findall(r"TABLE [IVX]+(?![IVX])(?![.:])", txt)))
    ok = not colons and not bare and bool(figs) and bool(tabs)
    print(f"  [{'PASS' if ok else 'FAIL':7}] item 8  caption labels end in a stop  "
          f"{len(figs)} Fig., {len(tabs)} TABLE, {len(colons)} colon, {len(bare)} without a stop")
    labels = figs + tabs
    results.append(ok); data.append(len(labels))
    # `data` counts only real measurements. The two checks below are pass/fail on content,
    # so they must not make an empty input look like it was measured.

    # Author block. The template sets every line of it in Times: name 11pt, department and
    # institution 10pt italic, city and e-mail 10pt upright. \texttt on the address made it
    # Courier, which at the same nominal size is wider and taller-x -- the wrong typeface and
    # a different apparent point size at once. Compare the e-mail line against the city line
    # directly rather than against a hard-coded name, so it keeps working once the block is
    # filled with a real address.
    block = title_block(pdf)
    lines = [ln for ln in block[:12]]
    mail = next((i for i, (_, _, t) in enumerate(lines) if "@" in t), None)
    if mail is None or mail == 0:
        print("  [NO DATA] --      author block e-mail line          (not found on page 1)")
        results.append(False)
    else:
        msz, mfont, mtxt = lines[mail]
        csz, cfont, _ = lines[mail - 1]
        # An unresolved font name is a failure, never a pass: "?" == "?" would otherwise
        # certify a Courier address as matching its Times affiliation.
        ok = (abs(msz - csz) < 0.2 and mfont == cfont and "?" not in (mfont, cfont))
        print(f"  [{'PASS' if ok else 'FAIL':7}] --      e-mail matches its affiliation "
              f"{msz:.2f}pt {mfont} vs {csz:.2f}pt {cfont}")
        results.append(ok); data.append(1)

    # No monospaced face anywhere: the template is Times throughout and has no code style,
    # so a monospaced font in the output means some \texttt survived.
    fonts_used = subprocess.run(["pdffonts", str(pdf)], check=True,
                                capture_output=True, text=True).stdout.splitlines()[2:]
    # pdffonts prints an embedded face as "ABCDEF+NimbusMonL-Regu"; the six-letter subset tag
    # must be stripped before matching, or every name reads as the tag and nothing is ever found.
    names = [ln.split()[0].split("+")[-1] for ln in fonts_used if ln.split()]
    # URW's Courier clone is "NimbusMonL" -- no trailing "o", so a /Mono/ pattern misses it.
    mono = sorted({f for f in names if re.search(r"Mono|MonL|Courier|Typewriter|CMTT", f)})
    ok = bool(names) and not mono
    print(f"  [{'PASS' if ok else 'FAIL':7}] --      Times only, no monospaced face   "
          f"{mono if mono else '(clean)'}")
    results.append(ok)

    # Placeholder leak: an unfilled \PH{} whose key contains "_" is a LaTeX error in text
    # mode, and the recovery silently swallows the floats that follow.
    leaks = sorted(set(re.findall(r"\[\?[a-z_0-9]+\]|\d+e-0\d", txt)))
    ok = not leaks
    print(f"  [{'PASS' if ok else 'FAIL':7}] --      no placeholder/sci-notation leak "
          f"{leaks if leaks else '(clean)'}")
    results.append(ok)

    if tex and tex.exists():
        src = re.sub(r"(?<!\\)%.*", "", tex.read_text(encoding="utf8"))
        small = {"a", "an", "the", "and", "or", "but", "nor", "for", "of", "in", "on",
                 "at", "to", "by", "vs", "with", "from", "as", "is", "it"}
        bad = []
        for kind, title in re.findall(r"\\(section|subsection)\*?\{([^}]*)\}", src):
            words = re.findall(r"[A-Za-z][A-Za-z'-]*", title)
            for i, w in enumerate(words):
                if w.lower() in small and i not in (0, len(words) - 1):
                    continue
                if w[0].islower():
                    bad.append(f"{kind}: {title}"); break
        ok = not bad
        print(f"  [{'PASS' if ok else 'FAIL':7}] item 4  headings in Title Case        "
              f"{'all clear' if ok else bad}")
        results.append(ok)

    if sum(data) == 0:
        print("\nNOTHING MEASURED — treat as failure, not as a pass.")
        return 2
    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} checks pass"
          + (f" — {failed} FAILING" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

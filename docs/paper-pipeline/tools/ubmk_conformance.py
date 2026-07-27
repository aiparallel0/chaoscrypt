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
from pathlib import Path

# (target, tolerance) in points
BODY_PITCH = (11.40, 0.25)   # 0.95 * 12pt   -- item 5
INDENT = (14.46, 0.60)       # 0.51 cm       -- item 6
REF_PITCH = (9.00, 0.35)     # exact 9pt     -- item 14
REF_GAP = (2.50, 0.60)       # 2.5pt         -- item 15

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

    # Caption separators: the template's class uses a period for figures and a newline for
    # tables. A colon means a package overrode the class -- the defect the committee first
    # flagged, and one only the rendered text can reveal.
    txt = subprocess.run(["pdftotext", str(pdf), "-"], check=True,
                         capture_output=True, text=True).stdout
    colons = sorted(set(re.findall(r"Fig\. \d+:|TABLE [IVX]+:", txt)))
    labels = sorted(set(re.findall(r"Fig\. \d+\.|TABLE [IVX]+", txt)))
    ok = not colons and bool(labels)
    print(f"  [{'PASS' if ok else 'FAIL':7}] item 8  caption label separators      "
          f"{len(labels)} labels, {len(colons)} with a colon")
    results.append(ok); data.append(len(labels))
    # `data` counts only real measurements. The two checks below are pass/fail on content,
    # so they must not make an empty input look like it was measured.

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

#!/usr/bin/env python3
"""Fill ``\\PH{key}`` placeholders in a paper's ``main.tex`` from its ``results/*.json``.

Usage:  python scripts/fill_tex.py papers/<paper-dir>

Reads every flat JSON object under ``<paper-dir>/results/`` (later files win on key clash),
substitutes ``\\PH{key}`` -> value in ``<paper-dir>/main.tex``, and writes ``main_filled.tex``.
Unmatched placeholders are left as a visible ``[?key]`` so missing numbers are obvious in the PDF.
Numbers never get hand-typed into the paper; this is the single bridge from experiments to LaTeX.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

PH = re.compile(r"\\PH\{([^}]+)\}")


def load_results(results_dir: Path) -> dict:
    merged: dict = {}
    for p in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            print(f"  ! skip {p.name}: {e}")
            continue
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (str, int, float, bool)):
                    merged[k] = v
    return merged


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    paper = Path(sys.argv[1]).resolve()
    src = paper / "main.tex"
    if not src.exists():
        print(f"no main.tex in {paper}")
        return 1
    vals = load_results(paper / "results")
    text = src.read_text()
    missing: list[str] = []

    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key in vals:
            return str(vals[key])
        missing.append(key)
        return f"[?{key}]"

    out = PH.sub(repl, text)
    (paper / "main_filled.tex").write_text(out)
    n_total = len(PH.findall(text))
    print(f"filled {n_total - len(missing)}/{n_total} placeholders from {len(vals)} result keys")
    if missing:
        print("  missing:", ", ".join(sorted(set(missing))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
# Assemble a submission package:  bash scripts/make_package.sh papers/<paper-dir> <out.zip>
#
# Ships the *filled* source as main.tex, so the package compiles on its own with no
# placeholder-substitution step and no result files. The package is then compiled in a
# throwaway directory before it is zipped: a deliverable that only builds because of files
# sitting in the working tree is the failure this guards against.
set -u

here="$(cd "$(dirname "$0")/.." && pwd)"
paper="${1:?usage: make_package.sh papers/<paper-dir> <out.zip>}"
out="${2:?usage: make_package.sh papers/<paper-dir> <out.zip>}"
paper="$(cd "$paper" && pwd)"
limit="${3:-6}"

[ -f "$paper/main_filled.tex" ] || { echo "FAIL: no main_filled.tex; run the build first" >&2; exit 1; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
pkg="$work/package"
mkdir -p "$pkg/figures"

cp "$paper/main_filled.tex" "$pkg/main.tex"
[ -f "$paper/references.bib" ] && cp "$paper/references.bib" "$pkg/"
[ -f "$paper/main_filled.bbl" ] && cp "$paper/main_filled.bbl" "$pkg/main.bbl"

# Copy only the figures the source actually asks for, so nothing unreferenced ships.
python3 - "$paper" "$pkg" <<'PY'
import re, shutil, sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
tex = (dst / "main.tex").read_text(encoding="utf8")
missing = []
for g in sorted(set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex))):
    for ext in ("", ".pdf", ".png", ".jpg"):
        if (src / (g + ext)).exists():
            target = dst / (g + ext)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src / (g + ext), target)
            break
    else:
        missing.append(g)
if missing:
    print("FAIL: figures referenced but not found: " + ", ".join(missing))
    raise SystemExit(1)
PY
[ $? -eq 0 ] || exit 1

if grep -q '\\PH{' "$pkg/main.tex"; then
  echo "FAIL: the packaged main.tex still contains \\PH{} placeholders" >&2
  exit 1
fi

# Clean-room compile, in the package directory and nowhere else.
( cd "$pkg" \
  && pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1 \
  && bibtex main >/dev/null 2>&1 \
  && pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1 \
  && pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1 )

if [ ! -f "$pkg/main.pdf" ]; then
  echo "FAIL: the package does not compile on its own" >&2
  exit 1
fi

errors=$(grep -c '^!' "$pkg/main.log" || true)
overfull=$(grep -c 'Overfull' "$pkg/main.log" || true)
undefined=$(grep -ci 'undefined \(control sequence\|reference\|citation\)' "$pkg/main.log" || true)
pages=$(pdfinfo "$pkg/main.pdf" 2>/dev/null | awk '/^Pages:/{print $2}')
floats=$(pdftotext "$pkg/main.pdf" - | grep -oE 'Fig\. [0-9]+\.|TABLE [IVX]+' | sort -u | wc -l)
echo "clean-room: pages=${pages:-0}/$limit errors=$errors overfull=$overfull undefined=$undefined floats=$floats"

fail=0
[ "$errors"    -gt 0 ]        && { echo "FAIL: LaTeX errors";               fail=1; }
[ "$overfull"  -gt 0 ]        && { echo "FAIL: overfull boxes";             fail=1; }
[ "$undefined" -gt 0 ]        && { echo "FAIL: undefined references/cites"; fail=1; }
[ "${pages:-0}" -gt "$limit" ] && { echo "FAIL: over the $limit-page limit"; fail=1; }
if [ "$fail" -ne 0 ]; then
  echo "package rejected — $out not written" >&2
  exit 1
fi

# The reader gets the compiled PDF too, and nothing from the build.
rm -f "$pkg/main.aux" "$pkg/main.log" "$pkg/main.blg" "$pkg/main.out"

out_abs="$(cd "$(dirname "$out")" && pwd)/$(basename "$out")"
rm -f "$out_abs"
( cd "$pkg" && zip -q -r "$out_abs" . )
echo "wrote $out_abs ($(du -h "$out_abs" | cut -f1), $pages pages)"
exit 0

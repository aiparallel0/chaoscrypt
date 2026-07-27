#!/usr/bin/env bash
# Build a paper's PDF:  bash scripts/compile.sh papers/<paper-dir> [page-limit]
# Runs fill_tex.py, then pdflatex x3 + bibtex, leaving <paper-dir>/main.pdf.
#
# The build FAILS (non-zero exit, main.pdf left untouched) on any of:
#   unfilled \PH{} placeholder · LaTeX error · overfull box · undefined ref/cite ·
#   over the page limit.
# Success is proved by a freshly written PDF, never by one merely existing: a stale
# artifact from an earlier run must not be able to masquerade as this run's output.
set -u

here="$(cd "$(dirname "$0")/.." && pwd)"
paper="${1:?usage: compile.sh papers/<paper-dir> [page-limit]}"
paper="$(cd "$paper" && pwd)"
limit="${2:-6}"

if ! python "$here/scripts/fill_tex.py" "$paper"; then
  echo "FAIL: placeholders left unfilled — refusing to build" >&2
  exit 1
fi

cd "$paper" || exit 1
[ -f main_filled.tex ] || { echo "FAIL: no main_filled.tex" >&2; exit 1; }

if grep -q '\\PH{' main_filled.tex; then
  echo "FAIL: \\PH{} survived substitution in main_filled.tex" >&2
  exit 1
fi

# Remove prior outputs so nothing from an earlier run can be mistaken for this one.
rm -f main_filled.pdf main_filled.log main_filled.aux main_filled.bbl main_filled.blg

pdflatex -interaction=nonstopmode main_filled.tex >/dev/null 2>&1
if [ -f references.bib ] || ls ./*.bib >/dev/null 2>&1; then
  bibtex main_filled >/dev/null 2>&1
fi
pdflatex -interaction=nonstopmode main_filled.tex >/dev/null 2>&1
pdflatex -interaction=nonstopmode main_filled.tex >/dev/null 2>&1

if [ ! -f main_filled.pdf ]; then
  echo "FAIL: no PDF produced — inspect $paper/main_filled.log" >&2
  exit 1
fi

# grep -c exits 1 when the count is zero, which would abort the script on success.
errors=$(grep -c '^!' main_filled.log || true)
overfull=$(grep -c 'Overfull' main_filled.log || true)
undefined=$(grep -ci 'undefined \(control sequence\|reference\|citation\)' main_filled.log || true)
pages=$(pdfinfo main_filled.pdf 2>/dev/null | awk '/^Pages:/{print $2}')
pages="${pages:-0}"

echo "pages=$pages/$limit errors=$errors overfull=$overfull undefined=$undefined"

fail=0
[ "$errors"    -gt 0 ]        && { echo "FAIL: LaTeX errors";               fail=1; }
[ "$overfull"  -gt 0 ]        && { echo "FAIL: overfull boxes";             fail=1; }
[ "$undefined" -gt 0 ]        && { echo "FAIL: undefined references/cites"; fail=1; }
[ "$pages"     -gt "$limit" ] && { echo "FAIL: over the $limit-page limit"; fail=1; }

if [ "$fail" -ne 0 ]; then
  echo "build rejected — main.pdf not updated; see $paper/main_filled.log" >&2
  exit 1
fi

mv -f main_filled.pdf main.pdf
echo "wrote $paper/main.pdf ($pages pages)"
exit 0

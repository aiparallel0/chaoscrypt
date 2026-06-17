#!/usr/bin/env bash
# Build a paper's PDF:  bash scripts/compile.sh papers/<paper-dir>
# Runs fill_tex.py, then pdflatex x2 + bibtex, leaving <paper-dir>/main.pdf. Reports the page count.
set -u
here="$(cd "$(dirname "$0")/.." && pwd)"
paper="${1:?usage: compile.sh papers/<paper-dir>}"
paper="$(cd "$paper" && pwd)"

python "$here/scripts/fill_tex.py" "$paper" || true

cd "$paper"
[ -f main_filled.tex ] || { echo "no main_filled.tex"; exit 1; }

pdflatex -interaction=nonstopmode -halt-on-error main_filled.tex >/dev/null 2>&1 || true
if [ -f references.bib ] || ls ./*.bib >/dev/null 2>&1; then
  bibtex main_filled >/dev/null 2>&1 || true
fi
pdflatex -interaction=nonstopmode -halt-on-error main_filled.tex >/dev/null 2>&1 || true
pdflatex -interaction=nonstopmode -halt-on-error main_filled.tex >/dev/null 2>&1 || true

if [ -f main_filled.pdf ]; then
  mv -f main_filled.pdf main.pdf
  pages=$(pdfinfo main.pdf 2>/dev/null | awk '/^Pages:/{print $2}')
  echo "wrote $paper/main.pdf (${pages:-?} pages)"
  [ -n "${pages:-}" ] && [ "$pages" -gt 6 ] && echo "  WARNING: over the 6-page UBMK limit"
else
  echo "compile failed — inspect $paper/main_filled.log"; exit 1
fi

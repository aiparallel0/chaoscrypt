#!/usr/bin/env bash
# Build a paper's Word version:  bash scripts/build_docx.sh papers/<paper-dir> <template.docx>
# Runs compile.sh first, converts main_filled.tex over the template, then verifies the result
# against both the source and the PDF. Leaves <paper-dir>/main.docx only if every check passes.
set -u

here="$(cd "$(dirname "$0")/.." && pwd)"
paper="${1:?usage: build_docx.sh papers/<paper-dir> <template.docx>}"
template="${2:?usage: build_docx.sh papers/<paper-dir> <template.docx>}"
paper="$(cd "$paper" && pwd)"

# The .docx is generated from main_filled.tex, so the PDF build has to succeed first: it is
# what fills the placeholders, and it is the reference the conversion is checked against.
if ! bash "$here/scripts/compile.sh" "$paper"; then
  echo "FAIL: the LaTeX build must pass before a Word version can be made" >&2
  exit 1
fi

out="$paper/main.docx"
tmp="$paper/.main.docx.tmp"
rm -f "$tmp"

if ! python3 "$here/docs/paper-pipeline/tools/tex2docx.py" "$paper" "$template" "$tmp"; then
  echo "FAIL: conversion refused; nothing written" >&2
  rm -f "$tmp"
  exit 1
fi

if ! python3 "$here/docs/paper-pipeline/tools/docx_check.py" "$paper" "$tmp"; then
  echo "FAIL: the .docx does not match the source it came from — $out not updated" >&2
  rm -f "$tmp"
  exit 1
fi

mv -f "$tmp" "$out"
echo "wrote $out"
exit 0

#!/usr/bin/env bash
# regenerate-all-files.sh -- run the full pipeline end to end: WordStar/
# Lexware conversion, collation ordering, concatenation, Lexware -> XML,
# XML -> TEI Lex-0, and TEI -> HTML/LaTeX/PDF. Regenerates every file
# under generated/ from what's in originals/ and src/ (see README.md's
# "Directory layout" section).
#
# See README.md for the pipeline diagram and what each stage produces;
# see README-tei.md for the TEI/HTML/PDF stages specifically, including
# a troubleshooting note for XeLaTeX font-not-found errors ("If your
# compile log explodes into millions of lines") -- the most common
# thing to go wrong when running this on a machine that doesn't have
# DejaVu Serif installed.
#
# Usage:
#   src/regenerate-all-files.sh [project-root]     (defaults to the
#                                 parent of this script's own directory,
#                                 i.e. the project root one level up
#                                 from src/, matching concat_master.sh)
#
# Requires: python3 with lxml (for render_tei.py), and xelatex (part of
# TeX Live / MacTeX) for the final PDF step.

set -euo pipefail

DL_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$DL_DIR"

echo "=== [1/8] dl_convert.py: WordStar -> Unicode plaintext + Lexware ==="
python3 src/dl_convert.py .

echo "=== [2/8] order_files.py: determine collation order ==="
python3 src/order_files.py .

echo "=== [3/8] concat_master.sh: concatenate in order ==="
src/concat_master.sh .

echo "=== [4/8] lex2xml.py: Lexware -> XML ==="
python3 src/lex2xml.py generated/lahudico-lexware.txt generated/lahudico-lexware.xml generated/lex2xml-report.log Lahu

echo "=== [5/8] lahu-to-tei.xsl: XML -> TEI Lex-0 ==="
python3 src/render_tei.py --tei generated/lahudico-lexware.xml --xsl src/lahu-to-tei.xsl --out generated/tei/lahu.xml

echo "=== [6/8] lahu-html.xsl: TEI -> HTML ==="
python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-html.xsl --out generated/latex/lahu.html

echo "=== [7/8] lahu-latex.xsl: TEI -> LaTeX ==="
python3 src/render_tei.py --tei generated/tei/lahu.xml --xsl src/lahu-latex.xsl --out generated/latex/lahu.tex

echo "=== [8/8] xelatex: LaTeX -> PDF (two passes, for page refs) ==="
xelatex -interaction nonstopmode -output-directory=generated/latex generated/latex/lahu.tex
xelatex -interaction nonstopmode -output-directory=generated/latex generated/latex/lahu.tex

echo
echo "Done. See generated/latex/lahu.pdf and generated/latex/lahu.html."

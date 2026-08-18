#!/usr/bin/env bash
# concat_master.sh -- concatenate the 135 main-body files into two master
# files, in the correct Lahu collation order (not filename order), using
# the order computed by order_files.py / lahu_collate.py:
#
#   generated/lahudico-plaintext.txt   all base-plaintext/*.txt entries, in order
#   generated/lahudico-lexware.txt     all base-lexware/lex.*.txt entries, in order
#
# The order itself lives in src/file-order.txt (one BASE.* filename per
# line, already in the correct sequence) -- this script does no sorting
# of its own, it just concatenates in that order with a blank-line
# separator between files so article spacing stays consistent across a
# file boundary. Re-run order_files.py first if the underlying data
# changes.
#
# Usage:
#   ./concat_master.sh [project-root]     (defaults to the parent of the
#                                           script's own directory, i.e.
#                                           the project root one level up
#                                           from src/)

set -euo pipefail

DL_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

ORDER_FILE="$DL_DIR/src/file-order.txt"
PLAINTEXT_DIR="$DL_DIR/generated/DLWordStarFiles/base-plaintext"
LEXWARE_DIR="$DL_DIR/generated/DLWordStarFiles/base-lexware"
OUT_PLAINTEXT="$DL_DIR/generated/lahudico-plaintext.txt"
OUT_LEXWARE="$DL_DIR/generated/lahudico-lexware.txt"

if [[ ! -f "$ORDER_FILE" ]]; then
    echo "Error: $ORDER_FILE not found. Run order_files.py first." >&2
    exit 1
fi

: > "$OUT_PLAINTEXT"
: > "$OUT_LEXWARE"

n=0
while IFS= read -r base_filename; do
    [[ -z "$base_filename" ]] && continue
    n=$((n + 1))

    # BASE.LH-A1.TXE -> LH-A1.TXE (strip the "BASE." prefix) for the
    # lexware file's "lex.<corename>.txt" naming convention.
    corename="${base_filename#BASE.}"

    plain_src="$PLAINTEXT_DIR/${base_filename}.txt"
    lex_src="$LEXWARE_DIR/lex.${corename}.txt"

    if [[ ! -f "$plain_src" ]]; then
        echo "Warning: missing plaintext file for $base_filename ($plain_src)" >&2
    else
        [[ $n -gt 1 ]] && printf '\n' >> "$OUT_PLAINTEXT"
        cat "$plain_src" >> "$OUT_PLAINTEXT"
    fi

    if [[ ! -f "$lex_src" ]]; then
        echo "Warning: missing lexware file for $base_filename ($lex_src)" >&2
    else
        [[ $n -gt 1 ]] && printf '\n' >> "$OUT_LEXWARE"
        cat "$lex_src" >> "$OUT_LEXWARE"
    fi
done < "$ORDER_FILE"

echo "Concatenated $n files."
echo "  $OUT_PLAINTEXT"
echo "  $OUT_LEXWARE"

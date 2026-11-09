#!/usr/bin/env bash
# Run all three variants on the same inputs so the outputs can be compared side by side.
#   ./compare.sh                 # uses samples/input
#   ./compare.sh ~/Desktop/docs  # your own files / folder
set -euo pipefail
cd "$(dirname "$0")"
IN="${1:-samples/input}"
for v in variant1_local_ml variant2_ocr_rules variant3_no_ml; do
  echo
  uv run --project "$v" anonymise "$IN" -o "samples/output/$v"
done
echo
echo "📂 outputs in samples/output/<variant>/"

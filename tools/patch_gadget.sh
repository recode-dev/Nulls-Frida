#!/bin/bash
set -euo pipefail

INPUT_DYLIB="$1"
OUTPUT_DYLIB="$2"
FRIDARE_SH="${FRIDARE_SH:-./fridare/fridare.sh}"

[ -f "$INPUT_DYLIB" ] || { echo "[-] нет входного файла: $INPUT_DYLIB"; exit 1; }
[ -f "$FRIDARE_SH" ] || { echo "[-] нет fridare.sh: $FRIDARE_SH"; exit 1; }

"$FRIDARE_SH" patch -m frida-gadget -f "$INPUT_DYLIB" -o "$OUTPUT_DYLIB"

[ -f "$OUTPUT_DYLIB" ] || { echo "[-] Fridare не создал $OUTPUT_DYLIB"; exit 1; }
echo "[+] готово: $OUTPUT_DYLIB"
#!/bin/bash
set -euo pipefail

FRIDARE_SH="${FRIDARE_SH:-./fridare/fridare.sh}"
VERSION="${1:-latest}"
OUTPUT_DIR="${2:-./patched_output}"

[ -f "$FRIDARE_SH" ] || { echo "[-] нет fridare.sh: $FRIDARE_SH"; exit 1; }

if [ "$VERSION" = "latest" ]; then
  "$FRIDARE_SH" patch -m frida-gadget -latest -os ios -arch arm64 -o "$OUTPUT_DIR"
else
  "$FRIDARE_SH" patch -m frida-gadget -v "$VERSION" -os ios -arch arm64 -o "$OUTPUT_DIR"
fi

echo "[+] Fridare завершил работу"
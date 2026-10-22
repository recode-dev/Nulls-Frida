#!/bin/bash
set -euo pipefail

FRIDARE_SH="${FRIDARE_SH:-./fridare/fridare.sh}"
VERSION="${1:-latest}"
OUTPUT_DIR="${2:-./patched_output}"

[ -f "$FRIDARE_SH" ] || { echo "[-] нет fridare.sh: $FRIDARE_SH"; exit 1; }

# Список возможных имён модулей для iOS-гаджета
CANDIDATES=("frida-gadget" "frida-agent" "gadget")

SUCCESS=0
for MODULE in "${CANDIDATES[@]}"; do
  echo "[*] пробую модуль: $MODULE"
  if [ "$VERSION" = "latest" ]; then
    if "$FRIDARE_SH" patch -m "$MODULE" -latest -os ios -arch arm64 -o "$OUTPUT_DIR"; then
      SUCCESS=1
      echo "[+] успешно использован модуль: $MODULE"
      break
    fi
  else
    if "$FRIDARE_SH" patch -m "$MODULE" -v "$VERSION" -os ios -arch arm64 -o "$OUTPUT_DIR"; then
      SUCCESS=1
      echo "[+] успешно использован модуль: $MODULE"
      break
    fi
  fi
  echo "[-] модуль $MODULE не сработал, пробую следующий..."
done

if [ "$SUCCESS" -eq 0 ]; then
  echo "[-] ни один из модулей (${CANDIDATES[*]}) не подошёл."
  echo "[-] проверьте доступные модули командой: $FRIDARE_SH list-modules"
  exit 1
fi

echo "[+] Fridare завершил работу"
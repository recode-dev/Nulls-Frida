#!/bin/bash
set -euo pipefail

FRIDARE_DIR="${1:-fridare}"
INSTALL_DIR="$(pwd)/${FRIDARE_DIR}"

git clone --depth 1 https://github.com/suifei/fridare.git "$INSTALL_DIR"
cd "$INSTALL_DIR"
chmod +x fridare.sh

echo "FRIDARE_SH=${INSTALL_DIR}/fridare.sh" >> "$GITHUB_ENV"
echo "[+] Fridare: ${INSTALL_DIR}/fridare.sh"
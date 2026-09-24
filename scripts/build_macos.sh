#!/usr/bin/env bash
set -euo pipefail

# Build a macOS app bundle using PyInstaller (requires pyinstaller installed)
# Usage: ./scripts/build_macos.sh

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

ICON="$ROOT_DIR/assets/icon.icns"
if [ ! -f "$ICON" ]; then
  echo "icon.icns not found in assets/. Run scripts/generate_icons.py first or place an icon.icns at assets/icon.icns"
  exit 1
fi

pyinstaller --noconfirm --windowed --onefile --icon="$ICON" main.py

echo "Build complete. Check dist/ for the generated app binary (note: macOS notarization/signing may be required for distribution)."

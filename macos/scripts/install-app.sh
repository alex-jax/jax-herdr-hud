#!/bin/bash
set -euo pipefail
MAC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$MAC_DIR/dist/Herdr Hud.app"
DESTINATION="$HOME/Applications/Herdr Hud.app"
if [[ ! -x "$SOURCE/Contents/MacOS/HerdrHud" ]]; then
  echo 'Build first: macos/scripts/build-app.sh release' >&2
  exit 1
fi
codesign --verify --deep --strict "$SOURCE"
if [[ -d "$DESTINATION" ]]; then
  "$DESTINATION/Contents/MacOS/HerdrHud" --quit
  # Give the old companion time to detach its clients and finish saving settings.
  sleep 2
  BACKUP="$MAC_DIR/dist/Herdr Hud.previous.$(date +%Y%m%d%H%M%S).app"
  mv "$DESTINATION" "$BACKUP"
fi
mkdir -p "$HOME/Applications"
ditto "$SOURCE" "$DESTINATION"
codesign --verify --deep --strict "$DESTINATION"
printf 'Installed %s\n' "$DESTINATION"

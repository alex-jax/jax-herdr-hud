#!/bin/bash
set -euo pipefail
MAC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$MAC_DIR/dist/build.noindex/Herdr Hud.app"
DESTINATION="$HOME/Applications/Herdr Hud.app"
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
if [[ ! -x "$SOURCE/Contents/MacOS/HerdrHud" ]]; then
  echo 'Build first: macos/scripts/build-app.sh release' >&2
  exit 1
fi
codesign --verify --deep --strict "$SOURCE"
mkdir -p "$HOME/Applications" "$MAC_DIR/dist/backups.noindex"
STAGE=$(mktemp -d "$HOME/Applications/.herdr-hud-update.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT
ditto "$SOURCE" "$STAGE/Herdr Hud.app"
codesign --verify --deep --strict "$STAGE/Herdr Hud.app"
if [[ -d "$DESTINATION" ]]; then
  "$DESTINATION/Contents/MacOS/HerdrHud" --quit
  # Restart only Hud; never signal Herdr's servers, shells, or agents.
  for attempt in {1..50}; do
    if ! pgrep -f "^$DESTINATION/Contents/MacOS/HerdrHud([[:space:]]|$)" >/dev/null; then break; fi
    sleep 0.1
  done
  if pgrep -f "^$DESTINATION/Contents/MacOS/HerdrHud([[:space:]]|$)" >/dev/null; then
    echo 'Hud did not quit; existing installation retained.' >&2
    exit 1
  fi
  BACKUP="$MAC_DIR/dist/backups.noindex/Herdr Hud.$(date +%Y%m%d%H%M%S).$(uuidgen).zip"
  ditto -c -k --sequesterRsrc --keepParent "$DESTINATION" "$BACKUP"
  unzip -tq "$BACKUP" >/dev/null
  mv "$DESTINATION" "$STAGE/previous.app"
fi
if ! mv "$STAGE/Herdr Hud.app" "$DESTINATION"; then
  if [[ -d "$STAGE/previous.app" ]]; then mv "$STAGE/previous.app" "$DESTINATION"; fi
  exit 1
fi
codesign --verify --deep --strict "$DESTINATION"
python3 "$MAC_DIR/scripts/cleanup-apps.py"
# An unindexed build may never have had a LaunchServices entry.
"$LSREGISTER" -u "$SOURCE" >/dev/null 2>&1 || true
"$LSREGISTER" -f "$DESTINATION"
printf 'Installed %s\n' "$DESTINATION"

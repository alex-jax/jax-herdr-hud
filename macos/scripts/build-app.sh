#!/bin/bash
set -euo pipefail
MAC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIGURATION="${1:-release}"
if [[ "$CONFIGURATION" != release && "$CONFIGURATION" != debug ]]; then
  echo 'Usage: build-app.sh [release|debug]' >&2
  exit 2
fi
swift build --package-path "$MAC_DIR" -c "$CONFIGURATION" --product HerdrHud
BIN_DIR="$(swift build --package-path "$MAC_DIR" -c "$CONFIGURATION" --show-bin-path)"
APP="$MAC_DIR/dist/build.noindex/Herdr Hud.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
chmod -R u+w "$APP"
cp "$BIN_DIR/HerdrHud" "$APP/Contents/MacOS/HerdrHud"
# SwiftPM's resource accessor locates this bundle inside Contents/Resources.
ditto "$BIN_DIR/HerdrHud_HerdrHud.bundle" "$APP/Contents/Resources/HerdrHud_HerdrHud.bundle"
cp "$MAC_DIR/../licenses/Alex-Finn-MIT.txt" "$APP/Contents/Resources/"
cp "$MAC_DIR/../licenses/Ptyxis-copyright.txt" "$APP/Contents/Resources/"
cp "$MAC_DIR/../LICENSE" "$APP/Contents/Resources/"
cp "$MAC_DIR/.build/checkouts/SwiftTerm/LICENSE" "$APP/Contents/Resources/SwiftTerm-LICENSE"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>HerdrHud</string>
<key>CFBundleIdentifier</key><string>io.github.herdr.Hud</string>
<key>CFBundleName</key><string>Herdr Hud</string>
<key>CFBundleDisplayName</key><string>Herdr Hud</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.2</string>
<key>CFBundleVersion</key><string>3</string>
<key>LSMinimumSystemVersion</key><string>27.0</string>
<key>LSApplicationCategoryType</key><string>public.app-category.developer-tools</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSPrincipalClass</key><string>NSApplication</string>
<key>NSHumanReadableCopyright</key><string>GPL-3.0-or-later. Alex Jax; original HUD by Alex Finn. See bundled notices.</string>
<key>CFBundleIconFile</key><string>HerdrHud</string>
</dict></plist>
PLIST
swift "$MAC_DIR/scripts/icon.swift" "$APP/Contents/Resources/HerdrHud.icns"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
printf '%s\n' "$APP"

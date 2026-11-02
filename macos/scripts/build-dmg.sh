#!/bin/bash
set -euo pipefail
MAC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="$(dirname "$MAC_DIR")"
"$MAC_DIR/scripts/build-app.sh" release
APP="$MAC_DIR/dist/build.noindex/Herdr Hud.app"
VERSION=$(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' "$APP/Contents/Info.plist")
NAME="Herdr-Hud-${VERSION}-macOS-27-arm64"
DMG="$MAC_DIR/dist/$NAME.dmg"
STAGE=$(mktemp -d "$MAC_DIR/dist/.dmg-stage.XXXXXX")
WORK=$(mktemp -d "$MAC_DIR/dist/.dmg-work.XXXXXX")
trap 'rm -rf "$STAGE" "$WORK"' EXIT

ditto "$APP" "$STAGE/Herdr Hud.app"
ln -s /Applications "$STAGE/Applications"
cp "$MAC_DIR/distribution/Read Me.txt" "$STAGE/Read Me.txt"

# Ship the exact local Mac sources, including unpublished changes, without
# preferences, build products, Git metadata, caches, or workstation files.
python3 - "$REPO_DIR" "$STAGE/Source.zip" <<'PY'
import json
from pathlib import Path
import subprocess
import sys
import zipfile

root = Path(sys.argv[1])
mac = root / 'macos'

def tracked(directory):
    output = subprocess.check_output(['git', '-C', str(directory), 'ls-files', '-z'])
    return [Path(name.decode()) for name in output.split(b'\0') if name]

with zipfile.ZipFile(sys.argv[2], 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    files = [root / name for name in ['LICENSE', 'NOTICE.md', 'README.md', 'MANUAL.md', 'hud.py', 'terminal_themes.py']]
    files += list((root / 'licenses').rglob('*'))
    files += [p for p in mac.rglob('*') if not any(part in {'.build', '.swiftpm', 'dist', '.DS_Store', '__pycache__'} for part in p.relative_to(mac).parts)]
    for path in sorted(set(files)):
        if path.is_file() and not path.is_symlink():
            archive.write(path, 'jax-herdr-hud/' + str(path.relative_to(root)))
    pins = json.loads((mac / 'Package.resolved').read_text())['pins']
    for pin in pins:
        candidates = list((mac / '.build/checkouts').iterdir())
        directory = next(p for p in candidates if p.name.lower() == pin['identity'].lower())
        revision = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != pin['state']['revision']:
            raise SystemExit(f"Dependency revision mismatch: {pin['identity']}")
        for name in tracked(directory):
            if any(part in {'.build', '.swiftpm', '.git', '__pycache__', '.DS_Store'} for part in name.parts) or name.suffix in {'.pyc', '.pyo'}:
                continue
            path = directory / name
            if path.is_file() and not path.is_symlink():
                archive.write(path, 'jax-herdr-hud/dependencies/' + pin['identity'] + '/' + str(name))
PY

# Build into a temporary directory, then replace the named deliverable only
# after hdiutil completes. The image contains no settings or live session data.
hdiutil create -volname "Herdr Hud" -srcfolder "$STAGE" -format UDZO -fs HFS+ "$WORK/$NAME.dmg"
mv "$WORK/$NAME.dmg" "$DMG"
(cd "$MAC_DIR/dist" && shasum -a 256 "$NAME.dmg" > "$NAME.dmg.sha256")
printf 'DMG: %s\n' "$DMG"

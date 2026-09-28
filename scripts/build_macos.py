#!/usr/bin/env python3
"""Build and audit the self-contained Apple silicon app and drag-install DMG."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from app_info import VERSION


def run(argv, **kwargs):
    return subprocess.run(list(map(str, argv)), check=True, **kwargs)


def licenses(destination):
    destination.mkdir(parents=True, exist_ok=True)
    # Retain exact build dependency metadata and the license files from each keg.
    data = json.loads(subprocess.check_output(['brew', 'info', '--json=v2', '--installed']))
    roots = ['python@3.14', 'pygobject3', 'gtk+3', 'vte3', 'adwaita-icon-theme']
    selected = set(roots + subprocess.check_output(['brew', 'deps', '--installed', *roots], text=True).split())
    data['formulae'] = [f for f in data['formulae'] if f['name'] in selected]
    (destination / 'homebrew-build-manifest.json').write_text(json.dumps(data, indent=2))
    cellar = Path(subprocess.check_output(['brew', '--cellar'], text=True).strip())
    for formula in data['formulae']:
        name = formula['name']
        for installation in formula.get('installed', []):
            keg = cellar / name / installation['version']
            for path in keg.rglob('*'):
                if path.is_file() and any(word in path.name.lower() for word in ('license', 'licence', 'copying', 'copyright')):
                    # Do not recurse into headers, examples or unrelated cached source.
                    if path.stat().st_size > 1024 * 1024:
                        continue
                    target = destination / 'homebrew' / name / path.relative_to(keg)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get('Name', 'unknown')
        if not name.lower().startswith(('pyobjc', 'pyinstaller', 'pygobject', 'pycairo')):
            continue
        for path in distribution.files or []:
            if any(word in path.name.lower() for word in ('license', 'copying', 'copyright')):
                target = destination / 'python' / name / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(distribution.locate_file(path), target)


def icon(work):
    import AppKit as A
    import Foundation as F
    iconset = work / 'HerdrHud.iconset'
    iconset.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            pixels = size * scale
            image = A.NSImage.alloc().initWithSize_(F.NSMakeSize(pixels, pixels))
            image.lockFocus()
            # Exact vector geometry/colors from the existing application SVG.
            unit = pixels / 128
            circle = A.NSBezierPath.bezierPathWithOvalInRect_(F.NSMakeRect(6*unit, 6*unit, 116*unit, 116*unit))
            A.NSColor.colorWithCalibratedWhite_alpha_(48/255, 1).setFill()
            circle.fill()
            A.NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 140/255, 1, 1).setStroke()
            circle.setLineWidth_(5*unit)
            circle.stroke()
            A.NSColor.whiteColor().setFill()
            for x, y, width, height in ((39, 34, 11, 60), (78, 34, 11, 60), (50, 59, 28, 11)):
                A.NSRectFill(F.NSMakeRect(x*unit, y*unit, width*unit, height*unit))
            image.unlockFocus()
            bitmap = A.NSBitmapImageRep.imageRepWithData_(image.TIFFRepresentation())
            data = bitmap.representationUsingType_properties_(A.NSBitmapImageFileTypePNG, {})
            name = f'icon_{size}x{size}' + ('@2x' if scale == 2 else '') + '.png'
            data.writeToFile_atomically_(str(iconset / name), True)
    run(['/usr/bin/iconutil', '-c', 'icns', '-o', work / 'HerdrHud.icns', iconset])


def build(output):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('Build on an Apple silicon Mac; Linux cannot produce or validate this app.')
    work = SOURCE / 'build/macos'
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    licenses(work / 'third-party')
    icon(work)
    env = dict(os.environ, HUD_BUILD_SOURCE=str(SOURCE), MACOSX_DEPLOYMENT_TARGET='26.0')
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
         '--distpath', work / 'dist', '--workpath', work / 'pyinstaller',
         SOURCE / 'packaging/macos/herdr_hud.spec'], env=env, cwd=SOURCE)
    bundle = work / 'dist/Herdr Hud.app'
    from audit_macos import audit
    report = audit(bundle)
    report['source_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
    (output / 'macos-bundle-audit.json').write_text(json.dumps(report, indent=2))
    stage = work / 'image'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    run(['/usr/bin/ditto', bundle, stage / bundle.name])
    (stage / 'Applications').symlink_to('/Applications')
    (stage / 'Read before installing.txt').write_text(
        'Herdr Hud ' + VERSION + ' — Apple silicon, macOS 26 or 27\n\n'
        'Drag Herdr Hud to Applications, then eject this disk. Install Herdr separately.\n'
        'This test build is ad-hoc signed, not notarized. On first launch, macOS may\n'
        'require System Settings > Privacy & Security > Open Anyway.\n'
        'Never disable Gatekeeper globally. See the repository installation guide.\n')
    artifact = output / f'jax-herdr-hud-{VERSION}-macos-arm64.dmg'
    run(['/usr/bin/hdiutil', 'create', '-ov', '-format', 'UDZO', '-volname',
         'Herdr Hud ' + VERSION, '-srcfolder', stage, artifact])
    run(['/usr/bin/hdiutil', 'verify', artifact])
    (output / (artifact.name + '.sha256')).write_text(hashlib.sha256(artifact.read_bytes()).hexdigest() + '  ' + artifact.name + '\n')
    return artifact


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=SOURCE / 'dist/macos')
    args = parser.parse_args()
    print(build(args.output.resolve()))

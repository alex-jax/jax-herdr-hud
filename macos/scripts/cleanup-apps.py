#!/usr/bin/env python3
"""Archive generated Hud app copies without leaving launchable backup bundles."""
from pathlib import Path
import os
import plistlib
import shutil
import subprocess
import uuid
import zipfile

mac = Path(__file__).resolve().parents[1]
dist = mac / 'dist'
backups = dist / 'backups.noindex'
registration = Path('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister')
commands = subprocess.check_output(['ps', '-axo', 'command='], text=True).splitlines()
for app in sorted([*dist.glob('Herdr Hud.previous.*.app'), dist / 'Herdr Hud.app']):
    if not app.is_dir() or app.is_symlink():
        continue
    with (app / 'Contents/Info.plist').open('rb') as source:
        info = plistlib.load(source)
    if info.get('CFBundleIdentifier') != 'io.github.herdr.Hud':
        raise SystemExit(f'Refusing to archive an unrelated app: {app}')
    executable = str(app / 'Contents/MacOS/HerdrHud')
    if any(command.startswith(executable) for command in commands):
        print(f'Keeping running build: {app}')
        continue
    backups.mkdir(parents=True, exist_ok=True)
    archive = backups / (app.name + '.' + uuid.uuid4().hex[:8] + '.zip')
    temporary = archive.with_suffix('.zip.tmp')
    try:
        subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(temporary)], check=True)
        with zipfile.ZipFile(temporary) as content:
            if content.testzip() is not None:
                raise RuntimeError(f'Invalid backup: {temporary}')
        os.replace(temporary, archive)
        if registration.exists():
            subprocess.run([str(registration), '-u', str(app)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        shutil.rmtree(app)
        print(f'Archived {app.name} as {archive.name}')
    finally:
        temporary.unlink(missing_ok=True)

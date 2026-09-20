#!/usr/bin/python3
"""Stage project files into a runtime tree, shared by both build methods."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from app_info import VERSION, SNAP_NAME


def stage(root):
    app = root / 'usr/lib/herdr-hud'
    app.mkdir(parents=True, exist_ok=True)
    for name in ('hud.py', 'backend.py', 'app_info.py', 'runtime_env.py', 'updates.py', 'enable.py'):
        shutil.copy2(SOURCE / name, app / name)
    shutil.copy2(SOURCE / 'packaging/launch.py', app / 'launch.py')
    (root / 'usr/bin').mkdir(exist_ok=True)
    shutil.copy2(SOURCE / 'packaging/launcher', root / 'usr/bin/herdr-hud')
    (root / 'usr/bin/herdr-hud').chmod(0o755)
    doc = root / 'usr/share/doc/herdr-hud'
    doc.mkdir(parents=True, exist_ok=True)
    for name in ('LICENSE', 'NOTICE.md', 'MANUAL.md'):
        shutil.copy2(SOURCE / name, doc / name)
    shutil.copytree(SOURCE / 'licenses', doc / 'licenses', dirs_exist_ok=True)
    gui = root / 'meta/gui'
    gui.mkdir(parents=True, exist_ok=True)
    for path in (SOURCE / 'snap/gui').iterdir():
        shutil.copy2(path, gui / path.name)
    icons = root / 'usr/share/icons/hicolor/scalable/apps'
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / 'snap/gui/io.github.herdr.Hud.svg', icons)
    schemas = root / 'usr/share/glib-2.0/schemas'
    if schemas.exists():
        subprocess.run(['glib-compile-schemas', str(schemas)], check=True)
    # Runtime metadata is generated only for snap pack, not Snapcraft's own stage.
    return doc


if __name__ == '__main__':
    stage(Path(sys.argv[1]).resolve())

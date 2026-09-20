#!/usr/bin/python3
"""Remove this per-user Hud installation, preserving Herdr and its sessions."""
import os
from pathlib import Path
import shutil
import subprocess
from gi.repository import Gio
home = Path.home()
data = Path(os.environ.get('XDG_DATA_HOME', str(home / '.local/share')))
launcher = home / '.local/bin/herdr-hud'
if launcher.exists():
    subprocess.run([str(launcher), '--quit'], check=False)
settings = Gio.Settings.new('org.gnome.shell')
for key in ['enabled-extensions', 'disabled-extensions']:
    settings.set_strv(key, [v for v in settings.get_strv(key) if v not in ('herdr-hud@local', 'herdr-hud@alex-jax.github.io')])
Gio.Settings.sync()
for directory in [data / 'herdr-hud', data / 'gnome-shell/extensions/herdr-hud@local', data / 'gnome-shell/extensions/herdr-hud@alex-jax.github.io']:
    if directory.exists():
        shutil.rmtree(directory)
autostart = Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config'))) / 'autostart/io.github.herdr.Hud.desktop'
for file in [autostart, launcher, data / 'applications/io.github.herdr.Hud.desktop', data / 'icons/hicolor/scalable/apps/io.github.herdr.Hud.svg']:
    file.unlink(missing_ok=True)
print('Herdr Hud removed. Herdr, its sessions and your Hud preferences were kept.')

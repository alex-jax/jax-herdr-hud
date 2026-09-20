#!/usr/bin/python3
"""Build a native Debian package using system GTK/VTE; no root or downloads."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from app_info import VERSION, EXTENSION_UUID


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / f'jax-herdr-hud_{VERSION}-1_all.deb'
    with tempfile.TemporaryDirectory(prefix='jax-herdr-hud-deb-') as directory:
        root = Path(directory)

        def copy(source, destination):
            target = root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / source, target)
            target.chmod(0o644)

        def write(destination, text, mode=0o644):
            target = root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
            target.chmod(mode)

        for name in ('hud.py', 'terminal_display.py', 'backend.py', 'app_info.py', 'runtime_env.py', 'updates.py', 'enable.py'):
            copy(name, 'usr/lib/herdr-hud/' + name)
        write('usr/bin/herdr-hud', '''#!/usr/bin/python3
from pathlib import Path
import runpy
import sys
app = Path(__file__).resolve().parents[1] / 'lib/herdr-hud'
sys.path.insert(0, str(app))
runpy.run_path(str(app / 'hud.py'), run_name='__main__')
''', 0o755)
        for name in ('extension.js', 'metadata.json', 'stylesheet.css'):
            copy('extension/' + name, f'usr/share/gnome-shell/extensions/{EXTENSION_UUID}/{name}')
        for name in ('LICENSE', 'NOTICE.md', 'MANUAL.md', 'install.md', 'CHANGELOG.md'):
            copy(name, 'usr/share/doc/jax-herdr-hud/' + name)
        copy('LICENSE', 'usr/share/doc/jax-herdr-hud/copyright')
        copy('licenses/Alex-Finn-MIT.txt', 'usr/share/doc/jax-herdr-hud/Alex-Finn-MIT.txt')
        copy('LICENSE', f'usr/share/gnome-shell/extensions/{EXTENSION_UUID}/LICENSE')
        copy('licenses/Alex-Finn-MIT.txt', f'usr/share/gnome-shell/extensions/{EXTENSION_UUID}/Alex-Finn-MIT.txt')
        copy('snap/gui/io.github.herdr.Hud.svg', 'usr/share/icons/hicolor/scalable/apps/io.github.herdr.Hud.svg')
        desktop = '''[Desktop Entry]
Type=Application
Name=Herdr Hud
Comment=Herdr terminals and coding agents, within reach
Exec=/usr/bin/herdr-hud
Icon=io.github.herdr.Hud
Terminal=false
Categories=Development;Utility;
StartupWMClass=io.github.herdr.Hud
'''
        write('usr/share/applications/io.github.herdr.Hud.desktop', desktop)
        write('etc/xdg/autostart/io.github.herdr.Hud.desktop', desktop.replace(
            'Exec=/usr/bin/herdr-hud', 'Exec=/usr/bin/herdr-hud --background') +
            'OnlyShowIn=GNOME;\nX-GNOME-Autostart-enabled=true\n')
        size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) // 1024 + 1
        write('DEBIAN/control', f'''Package: jax-herdr-hud
Version: {VERSION}-1
Section: utils
Priority: optional
Architecture: all
Maintainer: Alex Jax <alex-jax@users.noreply.github.com>
Depends: pkexec, ca-certificates, python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, gir1.2-vte-2.91, gsettings-desktop-schemas, adwaita-icon-theme
Recommends: fonts-ubuntu
Installed-Size: {size}
Homepage: https://github.com/alex-jax/jax-herdr-hud
Description: Native Herdr terminals and coding agents for Ubuntu
 GTK/VTE companion with Spaces and Agents sections and an optional floating
 H extension for GNOME Shell 50. Requires Herdr installed separately.
 Independent Ubuntu remix by Alex Jax, based on Alex Finn's original idea.
''')
        write('DEBIAN/conffiles', '/etc/xdg/autostart/io.github.herdr.Hud.desktop\n')
        # TemporaryDirectory is private; installed payload directories must not be.
        root.chmod(0o755)
        for path in root.rglob('*'):
            if path.is_dir():
                path.chmod(0o755)
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(root), str(artifact)], check=True)
    return artifact


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=SOURCE / 'dist')
    args = parser.parse_args()
    print(build(args.output.resolve()))

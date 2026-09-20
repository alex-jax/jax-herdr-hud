#!/usr/bin/python3
"""Install per-user; no administrator privileges or changes to Herdr configuration."""
import os
from pathlib import Path
import shutil
import subprocess

source = Path(__file__).resolve().parent
home = Path.home()
data = Path(os.environ.get('XDG_DATA_HOME', str(home / '.local/share')))
app = data / 'herdr-hud'
extension = data / 'gnome-shell/extensions/herdr-hud@alex-jax.github.io'
for directory in [app, extension, data / 'applications', data / 'icons/hicolor/scalable/apps', home / '.local/bin']:
    directory.mkdir(parents=True, exist_ok=True)
for name in ['hud.py', 'terminal_display.py', 'backend.py', 'app_info.py', 'updates.py', 'enable.py', 'runtime_env.py']:
    shutil.copy2(source / name, app / name)
for name in ['extension.js', 'metadata.json', 'stylesheet.css']:
    shutil.copy2(source / 'extension' / name, extension / name)
for target in (app, extension):
    shutil.copy2(source / 'LICENSE', target / 'LICENSE')
    shutil.copy2(source / 'licenses/Alex-Finn-MIT.txt', target / 'Alex-Finn-MIT.txt')
launcher = home / '.local/bin/herdr-hud'
# A Python launcher avoids shell quoting and preserves every argument.
launcher.write_text('#!/usr/bin/python3\nimport os, sys\nos.execv("/usr/bin/python3", ["/usr/bin/python3", ' + repr(str(app / 'hud.py')) + '] + sys.argv[1:])\n')
launcher.chmod(0o755)
(data / 'applications/io.github.herdr.Hud.desktop').write_text(f'''[Desktop Entry]
Type=Application
Name=Herdr Hud
Comment=Your Herdr terminals and agents, within reach
Exec="{launcher}"
Icon=io.github.herdr.Hud
Terminal=false
Categories=Development;Utility;
StartupWMClass=io.github.herdr.Hud
''')
autostart = Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config'))) / 'autostart'
autostart.mkdir(parents=True, exist_ok=True)
(autostart / 'io.github.herdr.Hud.desktop').write_text(f'''[Desktop Entry]
Type=Application
Name=Herdr Hud
Comment=Start the floating Herdr Hud when you sign in
Exec="{launcher}" --background
Icon=io.github.herdr.Hud
Terminal=false
X-GNOME-Autostart-enabled=true
''')
(data / 'icons/hicolor/scalable/apps/io.github.herdr.Hud.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><circle cx="64" cy="64" r="58" fill="#303030" stroke="#e95420" stroke-width="5"/><path fill="#fff" d="M39 34h11v24h28V34h11v60H78V69H50v25H39z"/><circle cx="108" cy="23" r="12" fill="#3584e4" stroke="#fff" stroke-width="3"/></svg>''')
if shutil.which('update-desktop-database'):
    subprocess.run(['update-desktop-database', str(data / 'applications')], check=False)
print('Installed Herdr Hud: ' + str(launcher))
print('Extension: ' + str(extension))
print('Enable the extension after GNOME discovers it (a fresh login may be needed).')

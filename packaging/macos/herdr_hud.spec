# PyInstaller specification. Invoked by scripts/build_macos.py on Apple silicon.
import os
from pathlib import Path
import sys

source = Path(os.environ['HUD_BUILD_SOURCE'])
sys.path.insert(0, str(source))
from app_info import VERSION

a = Analysis([str(source / 'packaging/macos/launch.py')],
    pathex=[str(source), str(source / 'packaging/macos')],
    binaries=[],
    datas=[(str(source / 'packaging/macos/fonts'), 'fonts'),
           (str(source / 'packaging/macos/fonts.conf'), '.'),
           (str(source / 'licenses'), 'licenses'),
           (str(source / 'LICENSE'), '.'), (str(source / 'NOTICE.md'), '.'),
           (str(source / 'build/macos/third-party'), 'licenses/third-party')],
    hiddenimports=['gi.repository.Vte', 'AppKit', 'Foundation', 'CoreText'],
    hookspath=[str(source / 'packaging/macos/hooks')],
    hooksconfig={'gi': {'module-versions': {'Gtk': '3.0', 'Gdk': '3.0', 'Vte': '2.91'},
                       'icons': ['Adwaita', 'hicolor'], 'themes': ['Adwaita'], 'languages': ['en']}},
    runtime_hooks=[str(source / 'packaging/macos/runtime_hook.py')],
    excludes=['tkinter', 'gi.repository.Gtk4'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Herdr Hud',
          debug=False, strip=False, upx=False, console=True, target_arch='arm64',
          codesign_identity=None, entitlements_file=None)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Herdr Hud')
app = BUNDLE(collection, name='Herdr Hud.app',
    icon=str(source / 'build/macos/HerdrHud.icns'),
    bundle_identifier='io.github.herdr.Hud',
    info_plist={'CFBundleShortVersionString': VERSION, 'CFBundleVersion': VERSION,
                'LSMinimumSystemVersion': '26.0', 'NSHighResolutionCapable': True,
                'NSPrincipalClass': 'NSApplication',
                'NSHumanReadableCopyright': 'Alex Jax; original portions Alex Finn; GPL-3.0-or-later'})

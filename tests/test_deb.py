import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_deb', SOURCE / 'scripts/build_deb.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class DebianPackageTests(unittest.TestCase):
    def test_package_layout_permissions_and_source_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            deb = builder.build(base / 'dist')
            root = base / 'root'
            subprocess.run(['dpkg-deb', '--raw-extract', str(deb), str(root)], check=True)
            self.assertEqual(root.stat().st_mode & 0o777, 0o755)
            self.assertEqual((root / 'usr/bin/herdr-hud').stat().st_mode & 0o777, 0o755)
            for name in ('hud.py', 'backend.py', 'app_info.py', 'runtime_env.py', 'updates.py', 'enable.py'):
                self.assertEqual((root / 'usr/lib/herdr-hud' / name).read_bytes(), (SOURCE / name).read_bytes())
            self.assertFalse((root / 'usr/bin/herdr').exists())
            self.assertEqual({p.name for p in (root / 'DEBIAN').iterdir()}, {'control', 'conffiles'})
            self.assertIn('/etc/xdg/autostart/io.github.herdr.Hud.desktop',
                          (root / 'DEBIAN/conffiles').read_text())
            self.assertTrue((root / 'usr/share/gnome-shell/extensions' / builder.EXTENSION_UUID /
                             'extension.js').is_file())
            self.assertIn('Exec=/usr/bin/herdr-hud\n',
                          (root / 'usr/share/applications/io.github.herdr.Hud.desktop').read_text())


if __name__ == '__main__':
    unittest.main()

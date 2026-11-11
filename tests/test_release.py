import hashlib
import subprocess
import sys
import tempfile
import tarfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from app_info import VERSION


class ReleaseArtifactTests(unittest.TestCase):
    def test_checksums_cover_release_assets_only(self):
        with tempfile.TemporaryDirectory(prefix='herdr-hud-release-') as tmp:
            output = Path(tmp)
            package = output / f'jax-herdr-hud_{VERSION}-1_all.deb'
            package.write_bytes(b'debian package fixture')
            subprocess.run([sys.executable, str(SOURCE / 'scripts/release.py'),
                            '--output', str(output)], check=True)

            with tarfile.open(output / f'jax-herdr-hud-{VERSION}-source.tar.gz') as archive:
                names = archive.getnames()
                self.assertIn(f'jax-herdr-hud-{VERSION}/macos/Sources/HerdrHud/App.swift', names)
                self.assertFalse(any('/.build/' in n or '/backups.noindex/' in n for n in names))

            lines = (output / 'SHA256SUMS').read_text().splitlines()
            paths = {line.split('  ', 1)[1] for line in lines}
            expected = {
                package.name,
                'herdr-hud@alex-jax.github.io.shell-extension.zip',
                f'jax-herdr-hud-{VERSION}-source.tar.gz',
            }
            self.assertEqual(paths, expected)
            for line in lines:
                digest, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()

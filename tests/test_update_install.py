import hashlib
import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import updates


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.data = b'test Debian payload'
        self.asset = {'name': 'jax-herdr-hud_1.1.0-1_all.deb',
            'browser_download_url': 'https://github.com/alex-jax/jax-herdr-hud/releases/download/v1.1.0/jax-herdr-hud_1.1.0-1_all.deb',
            'size': len(self.data), 'digest': 'sha256:' + hashlib.sha256(self.data).hexdigest()}
        self.release = {'tag_name': 'v1.1.0', 'assets': [self.asset]}

    def run_install(self, metadata='jax-herdr-hud\n1.1.0-1\nall', code=0):
        with patch('updates.fetch_releases', return_value=[self.release]), \
             patch('updates.urlopen', return_value=io.BytesIO(self.data)), \
             patch('updates.subprocess.run', side_effect=[SimpleNamespace(stdout=metadata), SimpleNamespace(returncode=code)]) as run:
            updates.install_update('v1.1.0')
            return run.call_args_list

    def test_verified_package_goes_to_ubuntu_installer(self):
        calls = self.run_install()
        self.assertEqual(calls[1].args[0][:4], ['/usr/bin/pkexec', '/usr/bin/apt-get', 'install', '--yes'])
        self.assertFalse(Path(calls[1].args[0][-1]).exists())

    def test_bad_checksum_never_invokes_installer(self):
        self.asset['digest'] = 'sha256:' + '0' * 64
        with patch('updates.fetch_releases', return_value=[self.release]), \
             patch('updates.urlopen', return_value=io.BytesIO(self.data)), \
             patch('updates.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError, 'checksum'):
                updates.install_update('v1.1.0')
            run.assert_not_called()

    def test_wrong_package_and_cancelled_authorization(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.run_install(metadata='other-package\n1.1.0-1\nall')
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.run_install(code=126)

    def test_download_must_be_from_this_release(self):
        self.asset['browser_download_url'] = 'https://example.com/payload.deb'
        with patch('updates.fetch_releases', return_value=[self.release]), patch('updates.urlopen') as opening:
            with self.assertRaisesRegex(ValueError, 'URL'):
                updates.install_update('v1.1.0')
            opening.assert_not_called()

    def test_six_hour_interval(self):
        self.assertEqual(updates.INTERVAL, 21600)

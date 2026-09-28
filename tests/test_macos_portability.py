import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import desktop
from macos_instance import Instance
import runtime_env
import updates


class MacPortabilityTests(unittest.TestCase):
    def test_preferences_and_xdg_override(self):
        with patch('desktop.IS_MAC', True), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(desktop.config_directory(), Path.home() / 'Library/Application Support/Herdr Hud')
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': '/custom', 'XDG_CACHE_HOME': '/cache'}):
                self.assertEqual(desktop.config_directory(), Path('/custom/herdr-hud'))
                self.assertEqual(desktop.cache_directory(), Path('/cache/herdr-hud'))

    def test_finder_path_and_runtime_restoration(self):
        source = {'HOME': '/Users/test', 'PATH': '/bundled/bin', 'DYLD_LIBRARY_PATH': '/bundled/lib',
                  'GI_TYPELIB_PATH': '/bundled/gi', '_PYI_ARCHIVE_FILE': '/bundled/app',
                  'HERDR_SOCKET': '/some/server', 'USER_SECRET': 'retained',
                  '_HUD_HOST_ENV': json.dumps({'PATH': '/custom/bin:/usr/bin:/bin', 'HOME': '/Users/test',
                                               'DYLD_LIBRARY_PATH': '/host/lib'})}
        with patch('runtime_env.sys.platform', 'darwin'):
            env = runtime_env.host_environment(source)
        self.assertEqual(env['PATH'], '/custom/bin:/usr/bin:/bin:/Users/test/.local/bin:/opt/homebrew/bin:/usr/local/bin')
        self.assertEqual(env['DYLD_LIBRARY_PATH'], '/host/lib')
        self.assertNotIn('GI_TYPELIB_PATH', env)
        self.assertNotIn('HERDR_SOCKET', env)
        self.assertNotIn('_PYI_ARCHIVE_FILE', env)
        self.assertEqual(env['USER_SECRET'], 'retained')

    def test_singleton_forwards_and_recovers_after_exit(self):
        with tempfile.TemporaryDirectory() as root:
            commands = []
            first = Instance(root, commands.append)
            second = Instance(root, commands.append)
            try:
                self.assertTrue(first.claim('show'))
                self.assertFalse(second.claim('show'))
                self.assertEqual(commands, ['show'])
                first.close()
                self.assertTrue(second.claim('background'))
            finally:
                first.close()
                second.close()

    def test_quit_without_instance_does_not_start_app(self):
        with tempfile.TemporaryDirectory() as root:
            instance = Instance(root, lambda _: self.fail('Unexpected dispatch'))
            self.assertFalse(instance.claim('quit'))
            self.assertIsNone(instance.server)

    def test_mac_update_requires_matching_asset_and_retains_verified_image(self):
        data = b'disk-image-test-payload'
        filename = 'jax-herdr-hud-1.4-macos-arm64.dmg'
        asset = dict(name=filename, size=len(data), digest='sha256:' + hashlib.sha256(data).hexdigest(),
                     browser_download_url='https://github.com/alex-jax/jax-herdr-hud/releases/download/v1.4/' + filename)
        release = dict(tag_name='v1.4', assets=[asset])
        with tempfile.TemporaryDirectory() as root, patch('updates.sys.platform', 'darwin'), \
             patch('updates.fetch_releases', return_value=[release]), \
             patch('updates.urlopen', return_value=io.BytesIO(data)), \
             patch('updates.cache_directory', return_value=Path(root)), \
             patch('updates.subprocess.run') as run:
            updates.install_update('v1.4')
            self.assertEqual(run.call_args_list[0].args[0][:2], ['/usr/bin/hdiutil', 'verify'])
            self.assertEqual(run.call_args_list[1].args[0][0], '/usr/bin/open')
            self.assertEqual(Path(run.call_args_list[1].args[0][1]).read_bytes(), data)

    def test_mac_does_not_advertise_linux_only_release(self):
        with tempfile.TemporaryDirectory() as root, patch('updates.sys.platform', 'darwin'), \
             patch('updates.fetch_releases', return_value=[{'tag_name': 'v1.4', 'assets': []}]):
            self.assertIsNone(updates.check_updates(Path(root) / 'updates.json', 'v1.3', 100000)[0])
            with patch('updates.subprocess.run') as run:
                with self.assertRaisesRegex(ValueError, 'Apple silicon'):
                    updates.install_update('v1.4')
                run.assert_not_called()

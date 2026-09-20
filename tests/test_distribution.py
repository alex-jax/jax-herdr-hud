import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backend
from runtime_env import RUNTIME_KEYS, host_environment


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.bin = self.home / 'tools'
        self.bin.mkdir()
        self.env = patch.dict(os.environ, {'HOME': str(self.home), 'PATH': str(self.bin)}, clear=True)
        self.env.start()
        backend.configure_herdr()

    def tearDown(self):
        backend.configure_herdr()
        self.env.stop()
        self.tmp.cleanup()

    def executable(self, path, output='herdr 0.9.1'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\nprintf "%s\\n" "' + output + '"\n')
        path.chmod(0o755)
        return str(path)

    def test_discovery_order_and_explicit_selection(self):
        fallback = self.executable(self.bin / 'herdr')
        self.assertEqual(backend.resolve_herdr(), fallback)
        local = self.executable(self.home / '.local/bin/herdr')
        self.assertEqual(backend.resolve_herdr(), local)
        configured = self.executable(self.home / 'custom herdr')
        backend.configure_herdr(configured)
        self.assertEqual(backend.resolve_herdr(), configured)
        self.assertEqual(backend.check_herdr(''), (local, 'herdr 0.9.1'))

    def test_missing_and_invalid_do_not_fall_back_silently(self):
        with self.assertRaises(backend.HerdrUnavailable):
            backend.resolve_herdr()
        self.executable(self.bin / 'herdr')
        for value in ('relative/path', str(self.home / 'missing'), str(self.bin)):
            with self.subTest(value=value), self.assertRaises(backend.HerdrUnavailable):
                backend.resolve_herdr(value)
        blocked = self.home / 'not-executable'
        blocked.write_text('not executable')
        with self.assertRaises(backend.HerdrUnavailable):
            backend.resolve_herdr(str(blocked))

    def test_wrong_program_is_reported(self):
        program = self.executable(self.bin / 'other', 'something else')
        with self.assertRaisesRegex(backend.HerdrUnavailable, 'identify itself'):
            backend.check_herdr(program)

    def test_host_environment_restores_values_and_unsets_runtime_only_keys(self):
        host = {'PATH': '/host/bin', 'HOME': '/home/person', 'XDG_CONFIG_HOME': '/host/config',
                'PYTHONPATH': '/host/python', 'LD_LIBRARY_PATH': '/host/lib'}
        runtime = {key: '/snap/gui/runtime' for key in RUNTIME_KEYS}
        runtime.update(_HUD_HOST_ENV=json.dumps({key: host.get(key) for key in RUNTIME_KEYS}),
                       SNAP='/snap/gui/1', SNAP_USER_DATA='/home/person/snap/gui/1',
                       HERDR_SESSION='wrong', TOKEN_FOR_AGENT='preserved', DISPLAY=':0')
        result = host_environment(runtime)
        for key, value in host.items():
            self.assertEqual(result[key], value)
        self.assertNotIn('GI_TYPELIB_PATH', result)
        self.assertFalse(any(k.startswith(('HERDR_', 'SNAP', '_HUD_HOST_')) for k in result))
        self.assertEqual(result['TOKEN_FOR_AGENT'], 'preserved')
        self.assertEqual(result['DISPLAY'], ':0')
        self.assertEqual(result['TERM'], 'xterm-256color')

    def test_malformed_session_listing_is_actionable(self):
        self.executable(self.bin / 'herdr')
        for output in ('{}', '[]', '{"sessions": [{}]}', 'invalid'):
            response = subprocess.CompletedProcess([], 0, output, '')
            with patch('backend.subprocess.run', return_value=response):
                with self.assertRaisesRegex(RuntimeError, 'tested with 0.9.1'):
                    backend.list_sessions()

    def test_snapshot_validation(self):
        backend.validate_snapshot({'panes': [], 'workspaces': [], 'tabs': []})
        for value in (None, {}, {'panes': [{}], 'workspaces': [], 'tabs': []}):
            with self.assertRaisesRegex(RuntimeError, 'snapshot'):
                backend.validate_snapshot(value)

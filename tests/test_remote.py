"""Remote identity, SSH argument boundaries and discovery failure regressions."""
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import Mock, patch
import backend


class RemoteTests(unittest.TestCase):
    def test_profiles_validate_and_filter_disabled(self):
        profile = dict(id='abc', label='Work', target='user@host', session='default', enabled=True)
        with patch('backend.resolve_herdr', return_value='/herdr'), patch('backend.subprocess.run') as run:
            run.return_value = Mock(returncode=0, stdout=json.dumps([profile, {**profile, 'enabled': False}]))
            self.assertEqual(backend.list_machines(), [profile])
            run.return_value.stdout = '[{"enabled": true}]'
            with self.assertRaises(RuntimeError):
                backend.list_machines()

    def test_attach_quotes_remote_arguments_and_never_takes_over(self):
        session = dict(remote=True, target='user@host', remote_executable='/some path/herdr',
                       remote_session="a; echo bad")
        command = backend.attach_command(session, 'term;whoami')
        self.assertEqual(shlex.split(command[-1]), ['/some path/herdr', '--session',
            'a; echo bad', 'terminal', 'attach', 'term;whoami'])
        self.assertNotIn('--takeover', command)
        self.assertIn('BatchMode=yes', command)
        with self.assertRaises(ValueError):
            backend.ssh_command('-oProxyCommand=bad')

    def test_same_remote_pane_ids_have_distinct_stable_socket_identities(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            profile = dict(label='Work', target='host', session='default')
            first = backend.RemoteWatcher(profile, directory, Mock())
            second = backend.RemoteWatcher(profile, directory, Mock())
            self.assertNotEqual(first.session['socket_path'], second.session['socket_path'])
            self.assertLess(len(first.session['socket_path']), 104)
            process = Mock()
            process.poll.return_value = None
            first.process = process
            first.stop()
            process.terminate.assert_called_once()

    def test_remote_create_does_not_send_mac_home_to_linux(self):
        session = dict(remote=True, socket_path='/test')
        with patch('backend.request', side_effect=[{'root_pane': {'terminal_id': 't'}}, {'snapshot': {}}]) as request:
            backend.create_terminal(session, 'w1', 'New')
            self.assertNotIn('cwd', request.call_args_list[0].args[2])

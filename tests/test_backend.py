import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import Monitor, HerdrUnavailable, attention, request


class StartupTests(unittest.TestCase):
    def test_monitor_initializes_once_and_retries_dependency_failure(self):
        session = {'name': 'default', 'socket_path': '/test/default', 'running': True}
        snapshot = {'panes': [], 'workspaces': [], 'tabs': []}
        changed, listed = Mock(), Mock()
        monitor = Monitor(changed, Mock(), listed)
        # Three discovery cycles: missing executable, recovery, ordinary refresh.
        monitor.stopping = Mock()
        monitor.stopping.is_set.side_effect = [False, False, False, False, False,
                                               False, False, False, True]
        with patch('backend.ensure_session', side_effect=[HerdrUnavailable('missing'),
                (session, snapshot)]) as ensure, patch('backend.list_sessions',
                return_value=[session]), patch('backend.SessionWatcher') as watcher:
            monitor.run()
        self.assertEqual(ensure.call_count, 2)
        ensure.assert_called_with('default')
        changed.assert_called_once_with(session, snapshot, None)
        self.assertIsInstance(listed.call_args_list[0].args[1], HerdrUnavailable)
        self.assertEqual(listed.call_count, 3)
        watcher.return_value.start.assert_called_once()

    def test_stop_during_initialization_ignores_late_snapshot(self):
        changed = Mock()
        monitor = Monitor(changed, Mock(), Mock())
        def initialize(name):
            monitor.stop()
            return {}, {}
        with patch('backend.ensure_session', side_effect=initialize):
            monitor.run()
        changed.assert_not_called()

class BackendTests(unittest.TestCase):
    def test_completion_and_input_transitions(self):
        self.assertEqual(attention('working', 'idle'), 'Finished')
        self.assertEqual(attention('working', 'done'), 'Finished')
        self.assertEqual(attention('idle', 'blocked'), 'Needs your input')
        self.assertEqual(attention(None, 'blocked'), 'Needs your input')
        for old, new in [('idle','idle'), ('blocked','blocked'), ('done','idle'), ('unknown','idle'), (None,'idle')]:
            self.assertIsNone(attention(old, new))

    def serve(self, response):
        folder = tempfile.TemporaryDirectory()
        path = str(Path(folder.name) / 'api.sock')
        server = socket.socket(socket.AF_UNIX)
        server.bind(path)
        server.listen()
        def work():
            conn, _ = server.accept()
            with conn:
                data = json.loads(conn.makefile('rb').readline())
                self.assertEqual(data['method'], 'session.snapshot')
                # Fragmentation must be handled by the JSON-lines reader.
                wire = (json.dumps(response) + '\n').encode()
                conn.sendall(wire[:7])
                conn.sendall(wire[7:])
            server.close()
        thread = threading.Thread(target=work)
        thread.start()
        return folder, path, thread

    def test_fragmented_socket_response(self):
        folder, path, thread = self.serve({'id':'hud','result':{'snapshot':{'panes':[], 'workspaces':[], 'tabs':[]}}})
        try:
            self.assertEqual(request(path, 'session.snapshot'), {'snapshot': {'panes': [], 'workspaces': [], 'tabs': []}})
        finally:
            thread.join(2)
            folder.cleanup()

    def test_api_errors_are_not_silently_empty_sessions(self):
        folder, path, thread = self.serve({'id':'hud','error':{'code':'bad','message':'Unsupported protocol'}})
        try:
            with self.assertRaisesRegex(RuntimeError, 'Unsupported protocol'):
                request(path, 'session.snapshot')
        finally:
            thread.join(2)
            folder.cleanup()

if __name__ == '__main__':
    unittest.main()

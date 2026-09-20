import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import updates


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'config/updates.json'
        self.now = 200000
        self.current = 'v0.1.1-preview.1'

    def test_daily_checks_survive_restart_and_cache_new_release(self):
        with patch('updates.fetch_releases', return_value=[{'tag_name': 'v0.1.2-preview.1'}]) as fetch:
            self.assertEqual(updates.check_updates(self.path, self.current, self.now),
                             ('v0.1.2-preview.1', updates.INTERVAL))
            self.assertEqual(updates.check_updates(self.path, self.current, self.now + 10),
                             ('v0.1.2-preview.1', updates.INTERVAL - 10))
            self.assertEqual(fetch.call_count, 1)
            updates.check_updates(self.path, self.current, self.now + updates.INTERVAL)
            self.assertEqual(fetch.call_count, 2)

    def test_numeric_prerelease_order_drafts_and_unrelated_tags(self):
        releases = [{'tag_name': tag} for tag in ('v0.1.1-preview.2', 'v0.1.1-preview.10',
                    'v0.1.1-preview.9', 'extension-99', 'v0.1.0', 'not a url')]
        releases.append({'tag_name': 'v99.0.0', 'draft': True})
        with patch('updates.fetch_releases', return_value=releases):
            self.assertEqual(updates.check_updates(self.path, self.current, self.now)[0],
                             'v0.1.1-preview.10')
        self.assertTrue(updates.newer_tag('v0.1.1', 'v0.1.1-preview.10'))
        self.assertTrue(updates.newer_tag('v0.1.10', 'v0.1.9'))
        self.assertIsNone(updates.newer_tag('v0.1.1-preview.10', 'v0.1.1'))

    def test_upgrade_hides_cached_icon_without_an_extra_request(self):
        with patch('updates.fetch_releases', return_value=[{'tag_name': 'v0.1.2'}]) as fetch:
            updates.check_updates(self.path, self.current, self.now)
            self.assertIsNone(updates.check_updates(self.path, 'v0.1.2', self.now + 1)[0])
            self.assertEqual(fetch.call_count, 1)

    def test_offline_and_rate_limits_keep_cache_and_wait_a_day(self):
        for error in (OSError('offline'), HTTPError(updates.API_URL, 403, 'rate limited', {}, None)):
            with self.subTest(error=error):
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps({'checked': 0, 'tag': 'v0.1.2'}))
                with patch('updates.fetch_releases', side_effect=error) as fetch:
                    self.assertEqual(updates.check_updates(self.path, self.current, self.now)[0], 'v0.1.2')
                    updates.check_updates(self.path, self.current, self.now + 1)
                    self.assertEqual(fetch.call_count, 1)

    def test_removed_release_clears_cached_icon(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({'checked': 0, 'tag': 'v0.1.2'}))
        with patch('updates.fetch_releases', return_value=[]):
            self.assertIsNone(updates.check_updates(self.path, self.current, self.now)[0])

    def test_malformed_state_and_response_do_not_break_startup(self):
        self.path.parent.mkdir(parents=True)
        for content in ('[]', 'invalid', '{"checked": "yesterday", "tag": []}'):
            self.path.write_text(content)
            with patch('updates.fetch_releases', side_effect=ValueError('bad JSON')):
                self.assertEqual(updates.check_updates(self.path, self.current, self.now),
                                 (None, updates.INTERVAL))

    def test_monitor_stop_discards_late_result(self):
        changed = Mock()
        monitor = updates.UpdateMonitor(self.path, self.current, changed)
        def check(*args):
            monitor.stop()
            return 'v0.1.2', updates.INTERVAL
        with patch('updates.check_updates', side_effect=check):
            monitor.run()
        changed.assert_not_called()

    def test_http_timeout_size_and_shape(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        for payload in (b'{}', b'[42]', b'x' * (1024 * 1024 + 1)):
            response.read.return_value = payload
            with patch('updates.urlopen', return_value=response) as opening:
                with self.assertRaises(ValueError):
                    updates.fetch_releases()
                self.assertEqual(opening.call_args.kwargs['timeout'], 10)

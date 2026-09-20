import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import enable


class EnableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        metadata = self.root / 'gnome-shell/extensions' / enable.EXTENSION_UUID / 'metadata.json'
        metadata.parent.mkdir(parents=True)
        metadata.write_text('{}')
        self.values = {'enabled-extensions': ['other@example', enable.LEGACY_UUID],
                       'disabled-extensions': ['disabled@example', enable.EXTENSION_UUID]}
        self.settings = Mock()
        self.settings.get_strv.side_effect = lambda key: list(self.values[key])
        self.settings.set_strv.side_effect = self.save
        self.settings.get_boolean.return_value = False
        self.version = '50.1'
        self.info = {'state': 1}
        self.bus = Mock()
        self.bus.call_sync.side_effect = self.reply
        patches = [patch.object(enable.Gio, 'bus_get_sync', return_value=self.bus),
                   patch.object(enable.Gio.Settings, 'new', return_value=self.settings),
                   patch.object(enable.Gio.Settings, 'sync'),
                   patch.object(enable.GLib, 'get_user_data_dir', return_value=str(self.root)),
                   patch.object(enable.GLib, 'get_system_data_dirs', return_value=[])]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def save(self, key, values):
        self.values[key] = values
        return True

    def reply(self, destination, path, interface, method, params, *args):
        if method == 'Get':
            value = (self.version,)
        elif method == 'GetExtensionInfo':
            value = (self.info,)
        elif method == 'EnableExtension':
            value = (True,)
        else:
            raise AssertionError(method)
        result = Mock()
        result.unpack.return_value = value
        return result

    def test_enables_bundled_extension_and_preserves_other_preferences(self):
        self.assertIn('floating H is on', enable.enable_extension())
        self.assertEqual(self.values['enabled-extensions'], ['other@example', enable.EXTENSION_UUID])
        self.assertEqual(self.values['disabled-extensions'], ['disabled@example', enable.LEGACY_UUID])
        self.settings.set_boolean.assert_not_called()

    def test_new_install_reports_login_without_claiming_visible(self):
        self.info = {}
        self.assertIn('Log out and log back in', enable.enable_extension())
        self.assertIn(enable.EXTENSION_UUID, self.values['enabled-extensions'])

    def test_global_extension_switch_is_not_changed(self):
        self.settings.get_boolean.return_value = True
        self.assertIn('desktop extensions are turned off', enable.enable_extension())
        self.settings.set_boolean.assert_not_called()

    def test_unsupported_desktop_and_missing_payload_do_not_enable(self):
        self.version = '49.3'
        self.assertIn('needs GNOME 50', enable.enable_extension())
        self.settings.set_strv.assert_not_called()
        self.version = '50.1'
        (self.root / 'gnome-shell/extensions' / enable.EXTENSION_UUID / 'metadata.json').unlink()
        self.assertIn('missing', enable.enable_extension())
        self.settings.set_strv.assert_not_called()

    def test_extension_error_is_reported(self):
        self.info = {'state': 3, 'error': 'test failure'}
        self.assertIn('test failure', enable.enable_extension())

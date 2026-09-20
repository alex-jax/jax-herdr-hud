#!/usr/bin/python3
"""Native update badge, worker delivery and release link without network or servers."""
import os
os.environ.setdefault('GDK_BACKEND', 'x11')
os.environ['G_DEBUG'] = 'fatal-criticals'
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
import hud
import updates
from hud import Gtk, Gdk

class NoMonitor:
    def __init__(self, *args): pass
    def start(self): pass
    def stop(self): pass
hud.Monitor = NoMonitor
hud.Hud.shell_call = lambda *args: None

def pump():
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    time.sleep(.01)

with tempfile.TemporaryDirectory(prefix='herdr-hud-updates-') as tmp:
    hud.CONFIG = Path(tmp)
    def releases():
        assert threading.current_thread() is not threading.main_thread()
        return [{'tag_name': 'v99.0.0-preview.1'}]
    with patch('updates.fetch_releases', side_effect=releases) as fetch, \
            patch('hud.install_update') as installer:
        app = hud.Hud()
        app.set_application_id('io.github.herdr.Hud.UpdateTest')
        app.register(None)
        app.show()
        try:
            assert not app.update_button.get_visible()
            deadline = time.monotonic() + 5
            while not app.update_button.get_visible() and time.monotonic() < deadline:
                pump()
            assert app.update_button.get_visible()
            assert '99.0.0-preview.1' in app.update_button.get_tooltip_text()
            for _ in range(20):
                pump()
            header = app.window.get_titlebar()
            credits = next(w for w in header.get_children() if w.get_accessible().get_name() == 'Credits')
            assert credits.get_allocation().x < app.update_button.get_allocation().x
            app.update_button.clicked()
            deadline = time.monotonic() + 5
            while app.update_pending and time.monotonic() < deadline:
                pump()
            installer.assert_called_once()
            assert installer.call_args.args[0] == 'v99.0.0-preview.1'
            assert 'Update installed' in app.status.get_text()
            assert not app.update_button.get_visible()
            app.update_available('v99.1.0')
            app.hide()
            app.show()
            pump()
            assert app.update_button.get_visible()
            assert fetch.call_count == 1
            assert (hud.CONFIG / 'updates.json').is_file()
            print('PASS: background check, six-hour cache, adjacent update icon, version tooltip and click-to-install worker')
            app.update_available(None)
            header.show_all()
            assert not app.update_button.get_visible()
            app.closing = True
            app.update_available('v99.1.0')
            assert not app.update_button.get_visible()
            app.closing = False
            print('PASS: no-update icon stays hidden and late results are ignored during shutdown')
        finally:
            app.exit_hud()
            app.update_monitor.join(2)
            assert not app.update_monitor.is_alive()

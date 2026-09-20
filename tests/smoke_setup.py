#!/usr/bin/python3
"""Native setup flow with a missing dependency, then a selected fake Herdr."""
import os
from pathlib import Path
import sys
import tempfile
import time
import threading
from unittest.mock import patch
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
import hud
# Network discovery is covered separately; these desktop tests stay offline.
class NoUpdates:
    def __init__(self, *args): pass
    def start(self): pass
    def stop(self): pass
hud.UpdateMonitor = NoUpdates
import backend
from hud import Gtk, GLib

class NoMonitor:
    def __init__(self, *args): pass
    def start(self): pass
    def stop(self): pass
hud.Monitor = NoMonitor
hud.Hud.shell_call = lambda *args: None
with tempfile.TemporaryDirectory(prefix='herdr-hud-setup-') as directory:
    hud.CONFIG = Path(directory)
    app = hud.Hud()
    app.set_application_id('io.github.herdr.Hud.SetupTest')
    app.register(None)
    app.show()
    def pump():
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(.01)
    try:
        app.sessions_changed(None, backend.HerdrUnavailable('Herdr was not found'))
        assert app.stack.get_visible_child_name() == 'setup'
        assert 'not found' in app.setup_message.get_text()
        app.herdr_entry.set_text('relative/file')
        app.retry_herdr()
        until = time.monotonic() + 5
        while app.setup_pending and time.monotonic() < until:
            pump()
        assert not app.setup_pending
        assert app.stack.get_visible_child_name() == 'setup'
        assert 'absolute path' in app.setup_message.get_text()
        program = Path(directory) / 'herdr with spaces'
        program.write_text('#!/bin/sh\nprintf "herdr 0.9.1\\n"\n')
        program.chmod(0o755)
        app.herdr_entry.set_text(str(program))
        app.retry_button.clicked()
        until = time.monotonic() + 5
        while app.setup_pending and time.monotonic() < until:
            pump()
        assert not app.setup_pending
        assert app.stack.get_visible_child_name() == 'empty'
        assert app.settings['herdr_path'] == str(program)
        assert backend.resolve_herdr() == str(program)
        app.show_setup()
        def enable_h():
            assert threading.current_thread() is not threading.main_thread()
            return 'The floating H is ready. Log out and log back in once to show it.'
        with patch('hud.enable_extension', side_effect=enable_h) as enable:
            app.extension_button.clicked()
            assert not app.extension_button.get_sensitive()
            app.extension_button.clicked()
            until = time.monotonic() + 5
            while app.extension_pending and time.monotonic() < until:
                pump()
            assert not app.extension_pending
            assert app.extension_button.get_sensitive()
            assert 'Log out and log back in' in app.extension_message.get_text()
            enable.assert_called_once()
        print('PASS: bundled H button runs off-thread, prevents duplicate requests and explains login')
        assert app.herdr_entry.get_text() == str(program)
        print('PASS: missing dependency, invalid path, executable with spaces, Retry and persisted selection')
        def close_about():
            dialog = next(w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.AboutDialog))
            assert dialog.get_version() == hud.VERSION
            assert 'Alex Finn' in dialog.get_comments() and 'Alex Jax' in dialog.get_comments()
            dialog.response(Gtk.ResponseType.CLOSE)
            return GLib.SOURCE_REMOVE
        GLib.idle_add(close_about)
        app.show_about()
        print('PASS: release version and upstream/publisher attribution in About')
    finally:
        app.exit_hud()
        backend.configure_herdr()

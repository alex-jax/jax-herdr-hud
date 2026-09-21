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
            app.enable_floating_h()
            app.enable_floating_h()
            until = time.monotonic() + 5
            while app.extension_pending and time.monotonic() < until:
                pump()
            assert not app.extension_pending
            assert 'Log out and log back in' in app.extension_message.get_text()
            enable.assert_called_once()
        print('PASS: bundled H setup runs off-thread, prevents duplicate requests and explains login')
        with patch('hud.enable_extension', return_value='Ready') as enable:
            app.auto_enable_floating_h()
            app.auto_enable_floating_h()
            until = time.monotonic() + 5
            while app.extension_pending and time.monotonic() < until:
                pump()
            enable.assert_called_once_with(automatic=True)
        print('PASS: startup enables H once without a separate off control')
        assert not hasattr(app, 'extension_button')
        assert app.herdr_entry.get_text() == str(program)
        print('PASS: missing dependency, invalid path, executable with spaces, Retry and persisted selection')
        def close_about():
            dialog = next(w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.AboutDialog))
            assert dialog.get_version() == hud.VERSION
            assert 'Christian Hergert' in dialog.get_comments()
            assert any('https://gitlab.gnome.org/chergert/ptyxis' in author for author in dialog.get_authors())
            assert 'Alex Finn' in dialog.get_comments() and 'Alex Jax' in dialog.get_comments()
            dialog.response(Gtk.ResponseType.CLOSE)
            return GLib.SOURCE_REMOVE
        GLib.idle_add(close_about)
        app.show_about()
        print('PASS: release version and upstream/publisher attribution in About')
        def descendants(widget):
            yield widget
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    yield from descendants(child)
        widgets = list(descendants(app.stack.get_child_by_name('setup')))
        assert [w.get_label() for w in widgets if isinstance(w, Gtk.Frame)] == [
            'Appearance', 'Floating H', 'Herdr connection']
        assert app.appearance_button.get_halign() == Gtk.Align.START
        assert app.appearance_button.get_allocated_height() <= 40
        assert not any(isinstance(w, Gtk.Label) and 'Christian Hergert' in w.get_text() for w in widgets)
        from gi.repository import Gdk
        output = Path(os.environ.get('HUD_TEST_OUTPUT', tempfile.mkdtemp(prefix='hud-settings-preview-')))
        output.mkdir(parents=True, exist_ok=True)
        app.show_setup(); pump()
        width, height = app.window.get_size()
        pixels = Gdk.pixbuf_get_from_window(app.window.get_window(), 0, 0, width, height)
        if pixels:
            pixels.savev(str(output / 'settings.png'), 'png', [], [])
        print('PASS: compact Settings sections; credits only in About. Screenshot:', output)
    finally:
        app.exit_hud()
        backend.configure_herdr()

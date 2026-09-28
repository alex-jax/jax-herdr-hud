#!/usr/bin/python3
"""Real GTK/VTE + disposable Herdr server integration test. Requires desktop access."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
os.environ.setdefault('GDK_BACKEND', 'x11')
output_dir = Path(os.environ.get('HUD_TEST_OUTPUT', tempfile.mkdtemp(prefix='herdr-hud-test-output-')))
output_dir.mkdir(parents=True, exist_ok=True)
import hud
# Network discovery is covered separately; these desktop tests stay offline.
class NoUpdates:
    def __init__(self, *args): pass
    def start(self): pass
    def stop(self): pass
hud.UpdateMonitor = NoUpdates
import backend
from hud import Gtk, Gdk, Gio, GLib
from backend import request, SessionWatcher

temp = tempfile.TemporaryDirectory(prefix='herdr-hud-smoke-')
base_env = hud.environment

def test_env():
    return {**base_env(), 'XDG_CONFIG_HOME': temp.name, 'HERDR_NO_UPDATE_CHECK': '1'}
hud.environment = test_env
backend.environment = test_env
hud.CONFIG = Path(temp.name) / 'hud-settings'
if os.environ.get('HUD_TEST_HERDR'):
    hud.CONFIG.mkdir(parents=True)
    (hud.CONFIG / 'settings.json').write_text(json.dumps({'herdr_path': os.environ['HUD_TEST_HERDR']}))
app = hud.Hud()
app.set_application_id('io.github.herdr.Hud.Smoke')
app.register(None)
app.show()


def pump(seconds=0.2):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.01)


def until(fn, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        pump()
        try:
            result = fn()
            if result:
                return result
        except (OSError, ValueError, RuntimeError):
            pass
    raise AssertionError('Timed out: ' + repr(fn))

path = str(Path(temp.name) / 'herdr/herdr.sock')
try:
    until(lambda: app.selected in app.terminals)
    app.monitor.stop(); app.monitor.join(6); pump()
    terminal = app.terminals[app.selected]
    until(lambda: terminal.pid)
    pump(1)
    terminal.feed_child(b"for i in $(seq 1 200); do printf '\\033[31mHISTORY_ROW_%03d abcdefghijklmnopqrstuvwxyz\\033[0m\\n' $i; done\r")
    until(lambda: 'HISTORY_ROW_200' in terminal.get_text_format(hud.Vte.Format.TEXT))
    pid = terminal.pid
    pointer = Gdk.Display.get_default().get_default_seat().get_pointer()
    def mouse(kind, y, state):
        event = Gdk.Event.new(kind); event.set_device(pointer)
        data = event.motion if kind == Gdk.EventType.MOTION_NOTIFY else event.button
        data.window = app.terminal_input_window(terminal)
        data.time = int(GLib.get_monotonic_time()/1000) & 0xffffffff
        data.x, data.y, data.state = 100, y, state
        if kind != Gdk.EventType.MOTION_NOTIFY: data.button = 1
        terminal.event(event); pump(.1)
    shift = Gdk.ModifierType.SHIFT_MASK
    height = app.terminal_input_window(terminal).get_height()
    # Start by dragging DOWN from a scrolled live attachment, without first
    # opening the overlay or manipulating its adjustment. Use an unmodified motion while
    # continuing the button drag, like a normal terminal selection.
    pane_id = app.panes[app.selected]['pane_id']
    request(path, 'pane.scroll', {'pane_id': pane_id, 'offset_from_bottom': 100})
    until(lambda: 'HISTORY_ROW_100' in terminal.get_text_format(hud.Vte.Format.TEXT))
    mouse(Gdk.EventType.BUTTON_PRESS, height/3, 0)
    mouse(Gdk.EventType.MOTION_NOTIFY, height-2, Gdk.ModifierType.BUTTON1_MASK)
    until(lambda: app.history_selection and app.history_selection.get('ready'))
    first_view = app.history_selection['view']
    before_down = first_view.get_vadjustment().get_value()
    pump(.7)
    assert first_view.get_vadjustment().get_value() > before_down
    first_rows = first_view.get_row_count()
    mouse(Gdk.EventType.BUTTON_RELEASE, height-2, 0)
    first_copy = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
    assert first_copy and first_copy.count('HISTORY_ROW_') > first_rows, first_copy
    assert app.history_selection is None
    assert terminal.has_focus()
    app.end_history_selection()
    request(path, 'pane.scroll', {'pane_id': pane_id, 'offset_from_bottom': 0})
    until(lambda: 'HISTORY_ROW_200' in terminal.get_text_format(hud.Vte.Format.TEXT))
    print('PASS: first drag scrolls down from live attachment; normal drag keeps selection scrolling', flush=True)
    mouse(Gdk.EventType.BUTTON_PRESS, height/2, 0)
    mouse(Gdk.EventType.MOTION_NOTIFY, 2, shift | Gdk.ModifierType.BUTTON1_MASK)
    until(lambda: app.history_selection and app.history_selection.get('view'))
    pump(.3)
    view = app.history_selection['view']
    adjustment = view.get_vadjustment()
    before = adjustment.get_value()
    assert adjustment.get_upper() > adjustment.get_page_size() + 100, (adjustment.get_upper(), adjustment.get_page_size())
    mouse(Gdk.EventType.MOTION_NOTIFY, 2, shift | Gdk.ModifierType.BUTTON1_MASK)
    pump(.7)
    assert adjustment.get_value() < before
    view_rows = view.get_row_count()
    mouse(Gdk.EventType.BUTTON_RELEASE, 2, shift)
    copied = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
    assert copied and copied.count('HISTORY_ROW_') > view_rows, copied
    assert '\x1b' not in copied
    assert not Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_is_target_available(Gdk.Atom.intern('text/html', False))
    assert app.history_selection is None, 'Release must return directly to the terminal'
    assert terminal.has_focus()
    assert terminal.pid == pid and terminal.alive
    assert app.stack.get_visible_child() is terminal
    print('PASS: real Herdr history selection scrolls beyond attachment viewport and preserves live PTY', flush=True)
finally:
    app.exit_hud()
    try: request(path, 'server.stop')
    except (OSError, ValueError, RuntimeError): pass
    pump(); temp.cleanup()

#!/usr/bin/python3
"""GTK focus-loss hiding and saved preference; no Herdr servers or agents."""
import os
import sys
import tempfile
import time
import json
from pathlib import Path
os.environ.setdefault('GDK_BACKEND', 'x11')
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
import hud
from hud import Gtk, Gdk

class NoMonitor:
    def __init__(self, *args): pass
    def start(self): pass
    def stop(self): pass

hud.Monitor = hud.UpdateMonitor = NoMonitor
hud.Hud.shell_call = lambda *args: None
hud.resolve_herdr = lambda: '/test/herdr'

def pump(seconds=.3):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(.005)

def until(condition):
    for _ in range(30):
        pump(.1)
        if condition():
            return
    raise AssertionError('Focus/window state did not settle: ' + repr([
        (w.get_title(), w.is_active(), w.get_visible(), w.get_transient_for())
        for w in Gtk.Window.list_toplevels()]))

with tempfile.TemporaryDirectory(prefix='hud-auto-hide-') as tmp:
    hud.CONFIG = Path(tmp)
    app = hud.Hud()
    app.set_application_id('io.github.herdr.Hud.AutoHideTest')
    app.register(None)
    app.show()
    outside = Gtk.Window(title='Outside Hud')
    dialog = None
    try:
        until(lambda: app.window.is_active())
        assert app.auto_hide_switch.get_active()
        outside.show_all(); outside.present()
        until(lambda: not app.window.get_visible())
        assert not app.closing, 'Auto-hide quit the companion'
        app.show()
        until(lambda: app.window.is_active())
        header = app.window.get_titlebar()
        held = [True]
        app.header_button_is_down = lambda: held[0]
        event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        event.button.button = 1
        event.button.window = header.get_window()
        header.emit('button-press-event', event)
        assert app.header_interaction_id, 'Header press did not start gesture protection'
        outside.present(); pump(.5)
        assert app.window.get_visible(), 'Titlebar interaction hid Hud while held'
        held[0] = False
        until(lambda: not app.header_interaction_id and app.window.is_active())
        assert app.window.get_visible(), 'Titlebar interaction hid Hud on release'
        outside.present()
        until(lambda: not app.window.get_visible())
        del app.header_button_is_down
        app.show()
        until(lambda: app.window.is_active())
        app.widget_interaction(True)
        outside.present(); pump(.5)
        assert app.window.get_visible(), 'Dragging widget hid the window'
        app.widget_interaction(False)
        app.show()
        until(lambda: app.window.is_active())
        outside.present()
        until(lambda: not app.window.get_visible())
        app.show()
        until(lambda: app.window.is_active())
        app.auto_hide_switch.set_active(False)
        outside.present(); pump(.5)
        assert app.window.get_visible()
        app.outside_click()
        assert app.window.get_visible(), 'Disabled auto-hide ignored for desktop click'
        assert json.loads((hud.CONFIG / 'settings.json').read_text())['hide_on_focus_loss'] is False
        assert hud.Hud().settings['hide_on_focus_loss'] is False
        app.show()
        until(lambda: app.window.is_active())
        app.auto_hide_switch.set_active(True)
        dialog = Gtk.Dialog(title='Hud dialog', transient_for=app.window, modal=True)
        dialog.show_all(); dialog.present(); pump(.5)
        assert app.window.get_visible(), 'Opening a Hud dialog hid the parent'
        app.outside_click()
        assert app.window.get_visible(), 'Desktop click hid Hud while a dialog was open'
        outside.present(); pump(.4)
        assert app.window.get_visible(), 'An open Hud dialog must be protected'
        dialog.destroy(); dialog = None
        outside.present()
        until(lambda: not app.window.get_visible())
        assert not app.auto_hide_id
        app.show()
        until(lambda: app.window.is_active())
        app.outside_click()
        assert not app.window.get_visible(), 'Desktop click did not hide Hud'
        print('PASS: outside focus hides to widget; off stays visible and persists; dialogs protected; timers cleaned')
    finally:
        if dialog is not None:
            dialog.destroy()
        outside.destroy()
        app.exit_hud()

#!/usr/bin/python3
"""Exercise window-manager resize and outside focus with an X11 test pointer."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault('GDK_BACKEND', 'x11')
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
import hud
from hud import Gtk

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
    for _ in range(40):
        pump(.1)
        if condition():
            return
    raise AssertionError('Window state did not settle')

def pointer(*args):
    subprocess.run(['xdotool', *map(str, args)], check=True)

with tempfile.TemporaryDirectory(prefix='hud-resize-pointer-') as tmp:
    hud.CONFIG = Path(tmp)
    app = hud.Hud()
    app.set_application_id('io.github.herdr.Hud.ResizePointerTest')
    app.register(None)
    app.show()
    outside = Gtk.Window(title='Outside Hud')
    try:
        until(lambda: app.window.is_active())
        before = app.window.get_size()
        window = app.window.get_window()
        _ok, origin_x, origin_y = window.get_origin()
        x = origin_x + window.get_width() - 4
        y = origin_y + window.get_height() - 4
        pointer('mousemove', x, y)
        pointer('click', 1)
        pump(.8)
        assert app.window.get_visible(), 'Quick corner click hid Hud'
        until(lambda: app.window.is_active())
        pointer('mousemove', x, y)
        pointer('mousedown', 1)
        pump(.6)
        assert app.window.get_visible(), 'Resize press hid Hud'
        pointer('mousemove', x + 80, y + 70)
        pump(.6)
        assert app.window.get_visible(), 'Resize drag hid Hud'
        pointer('mouseup', 1)
        pump(.8)
        after = app.window.get_size()
        assert app.window.get_visible(), 'Resize release hid Hud'
        assert after.width > before.width and after.height > before.height, (before, after)
        until(lambda: app.window.is_active())
        outside.show_all(); outside.present()
        until(lambda: not app.window.get_visible())
        print('PASS: corner drag resizes Hud, preserves visibility and still permits outside auto-hide')
    finally:
        pointer('mouseup', 1)
        outside.destroy()
        app.exit_hud()

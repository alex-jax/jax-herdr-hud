#!/usr/bin/python3
"""Exercise titlebar clicks and drags using a real X11 test pointer."""
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

with tempfile.TemporaryDirectory(prefix='hud-header-pointer-') as tmp:
    hud.CONFIG = Path(tmp)
    app = hud.Hud()
    app.set_application_id('io.github.herdr.Hud.HeaderPointerTest')
    app.register(None)
    app.show()
    try:
        until(lambda: app.window.is_active())
        for drag in (False, True):
            header = app.window.get_titlebar()
            _ok, origin_x, origin_y = app.window.get_window().get_origin()
            x, y = header.translate_coordinates(app.window, header.get_allocated_width() // 2,
                                                header.get_allocated_height() // 2)
            x, y = x + origin_x, y + origin_y
            pointer('mousemove', x, y)
            pointer('mousedown', 1)
            pump(.6)
            assert app.header_interaction_id and app.window.get_visible(), 'Header press hid Hud'
            if drag:
                pointer('mousemove', x + 80, y + 70)
                pump(.6)
                assert app.window.get_visible(), 'Header drag hid Hud'
            pointer('mouseup', 1)
            pump(.8)
            assert app.window.get_visible(), 'Header release hid Hud'
        print('PASS: titlebar click and drag keep Hud visible')
    finally:
        pointer('mouseup', 1)
        app.exit_hud()

#!/usr/bin/python3
"""Native VTE selection scrolling, with no live shells or agents."""
import os
os.environ.setdefault('GDK_BACKEND', 'x11')
import sys
from pathlib import Path
import time
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
from hud import Terminal, Gtk, Gdk, GLib

def pump(seconds=.15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(.005)

window = Gtk.Window()
terminal = Terminal()
window.add(terminal)
window.set_default_size(640, 300)
window.show_all()
pump()
terminal.feed(('\r\n'.join(f'ROW {n:03d} selection text' for n in range(200))).encode())
pump()
def find_window(window):
    event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
    event.button.window = window
    if Gtk.get_event_widget(event) == terminal:
        return window
    for child in window.get_children():
        found = find_window(child)
        if found:
            return found

input_window = find_window(terminal.get_window())
pointer = Gdk.Display.get_default().get_default_seat().get_pointer()
shift = Gdk.ModifierType.SHIFT_MASK
def mouse(kind, y, state):
    event = Gdk.Event.new(kind)
    event.set_device(pointer)
    data = event.motion if kind == Gdk.EventType.MOTION_NOTIFY else event.button
    data.window = input_window
    data.time = int(GLib.get_monotonic_time() / 1000) & 0xffffffff
    data.x, data.y, data.state = 60, y, state
    if kind != Gdk.EventType.MOTION_NOTIFY:
        data.button = 1
    terminal.event(event)
    pump()

try:
    adjustment = terminal.get_vadjustment()
    for direction in ('up', 'down'):
        adjustment.set_value(100)
        pump()
        start = adjustment.get_value()
        height = terminal.get_allocated_height()
        mouse(Gdk.EventType.BUTTON_PRESS, height / 2, shift)
        edge = 2 if direction == 'up' else height - 2
        mouse(Gdk.EventType.MOTION_NOTIFY, edge, shift | Gdk.ModifierType.BUTTON1_MASK)
        pump(.4)
        moved = adjustment.get_value()
        assert moved < start if direction == 'up' else moved > start, (direction, start, moved)
        assert terminal.get_has_selection()
        mouse(Gdk.EventType.BUTTON_RELEASE, edge, shift)
        pump(.2)
        stopped = adjustment.get_value()
        pump(.3)
        assert adjustment.get_value() == stopped, 'Scroll continued after release'
        copied = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
        assert copied and copied.count('ROW ') > terminal.get_row_count(), copied
        terminal.unselect_all()
    print('PASS: Shift+drag at both edges scrolls and copies beyond the viewport; release stops scrolling')
finally:
    window.destroy()

#!/usr/bin/python3
"""Native VTE selection scrolling, with no live shells or agents."""
import os
os.environ.setdefault('GDK_BACKEND', 'x11')
import sys
import subprocess
from pathlib import Path
import time
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
from hud import Terminal, Gtk, Gdk, GLib

def pump(seconds=.15):
    loop = GLib.MainLoop()
    GLib.timeout_add(max(1, int(seconds*1000)), lambda: (loop.quit(), GLib.SOURCE_REMOVE)[1])
    loop.run()

window = Gtk.Window()
terminal = Terminal()
window.add(terminal)
window.set_default_size(640, 300)
window.move(150, 150)
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
real_pointer = os.environ.get('HUD_TEST_POINTER') == '1'
if real_pointer:
    subprocess.run(['xdotool', 'windowfocus', str(window.get_window().get_xid())], check=True)
def mouse(kind, y, state):
    if real_pointer:
        origin = input_window.get_origin()
        subprocess.run(['xdotool', 'mousemove',
                        str(origin[-2]+60), str(origin[-1]+int(y))], check=True)
        if kind != Gdk.EventType.MOTION_NOTIFY:
            subprocess.run(['xdotool', 'mousedown' if kind == Gdk.EventType.BUTTON_PRESS else 'mouseup', '1'], check=True)
        pump()
        return
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
    cases = [('down', False), ('up', False)]
    if not real_pointer:
        cases += [('down', True), ('up', True)]
    for direction, add_shift in cases:
        adjustment.set_value(100)
        pump()
        start = adjustment.get_value()
        height = input_window.get_height()
        mouse(Gdk.EventType.BUTTON_PRESS, height / 2, 0)
        edge = (-30 if direction == 'up' else height+30) if real_pointer else (2 if direction == 'up' else height-2)
        if real_pointer:
            mouse(Gdk.EventType.MOTION_NOTIFY, height/4 if direction == 'up' else height*3/4, Gdk.ModifierType.BUTTON1_MASK)
        mouse(Gdk.EventType.MOTION_NOTIFY, edge, (shift if add_shift else 0) | Gdk.ModifierType.BUTTON1_MASK)
        pump(.4)
        moved = adjustment.get_value()
        assert moved < start if direction == 'up' else moved > start, (direction, start, moved)
        assert terminal.get_has_selection()
        mouse(Gdk.EventType.BUTTON_RELEASE, edge, shift if add_shift else 0)
        pump(.2)
        stopped = adjustment.get_value()
        pump(.3)
        assert adjustment.get_value() == stopped, 'Scroll continued after release'
        copied = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
        assert copied and copied.count('ROW ') > terminal.get_row_count(), copied
        terminal.unselect_all()
    print('PASS: Drag at both edges scrolls and copies beyond the viewport; release stops scrolling')
finally:
    if real_pointer:
        subprocess.run(['xdotool', 'mouseup', '1'], check=False)
    window.destroy()

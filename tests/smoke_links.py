#!/usr/bin/python3
"""Check native VTE link hit testing without opening a browser or network URL."""
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('GDK_BACKEND', 'x11')
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
from hud import Terminal, Gtk, Gdk, Gio, GLib


def pump():
    end = time.monotonic() + .15
    while time.monotonic() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(.01)


window = Gtk.Window()
terminal = Terminal()
window.add(terminal)
window.set_default_size(900, 300)
window.show_all()
pump()
terminal.feed(b'https://example.invalid:8443/path?q=1\r\n'
              b'\x1b]8;;https://example.invalid/labelled\x1b\\Open dashboard\x1b]8;;\x1b\\\r\n')
pump()
opened = []
original = Gio.AppInfo.launch_default_for_uri_async
Gio.AppInfo.launch_default_for_uri_async = lambda uri, *args: opened.append(uri)


def input_window(window):
    probe = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
    probe.button.window = window
    if Gtk.get_event_widget(probe) == terminal:
        return window
    for child in window.get_children():
        found = input_window(child)
        if found:
            return found


try:
    target = input_window(terminal.get_window())
    assert target is not None
    for row in (0, 1):
        event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        event.set_device(Gdk.Display.get_default().get_default_seat().get_pointer())
        event.button.window = target
        event.button.button = 1
        event.button.x = terminal.get_char_width() * 3
        event.button.y = terminal.get_char_height() * (row + .5)
        event.button.state = Gdk.ModifierType.CONTROL_MASK
        terminal.event(event)
        pump()
        assert terminal.link_click, (row, opened)
        event.type = Gdk.EventType.BUTTON_RELEASE
        terminal.event(event)
        assert not terminal.link_click
    assert opened == ['https://example.invalid:8443/path?q=1',
                      'https://example.invalid/labelled'], opened
    print('PASS: Ctrl+click opens plain URLs and OSC 8 hyperlinks through the desktop launcher')
finally:
    Gio.AppInfo.launch_default_for_uri_async = original
    window.destroy()

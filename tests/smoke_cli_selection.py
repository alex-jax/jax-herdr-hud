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
    loop = GLib.MainLoop()
    GLib.timeout_add(max(1, int(seconds*1000)), lambda: (loop.quit(), GLib.SOURCE_REMOVE)[1])
    loop.run()


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
    import shlex
    fixture = Path(temp.name) / 'scrolling_cli.py'
    fixture.write_text(r'''import os, re, tty, termios
saved = termios.tcgetattr(0)
tty.setraw(0)
offset = 50
height = os.get_terminal_size().lines
body = height - 3
try:
    os.write(1, b"\x1b[?1049h\x1b[?1002h\x1b[?1006h")
    def draw():
        rows = ['CLI transcript'] + [f'MESSAGE_{i:03d} text from a scrolling conversation' for i in range(offset, offset+body)] + ['Enter a message', 'CLI footer']
        os.write(1, ('\x1b[H\x1b[36m'+'\r\n'.join(rows)+'\x1b[0m').encode())
    draw()
    pending = b''
    while True:
        pending += os.read(0, 4096)
        if b'q' in pending: break
        for match in re.finditer(rb'\x1b\[<(\d+);(\d+);(\d+)[mM]',pending):
            code = int(match[1])
            # Like real CLIs, only the transcript accepts wheel scrolling.
            if not 2 <= int(match[3]) <= height-2: continue
            if code == 65: offset = min(200-body, offset+3)
            if code == 64: offset = max(0, offset-3)
            draw()
        pending = b''
finally:
    os.write(1,b"\x1b[?1002l\x1b[?1006l\x1b[?1049l")
    termios.tcsetattr(0, termios.TCSANOW, saved)
''')
    terminal.feed_child(('python3 '+shlex.quote(str(fixture))+'\r').encode())
    until(lambda: 'MESSAGE_050' in terminal.get_text_format(hud.Vte.Format.TEXT))
    pane = app.panes[app.selected]
    request(path,'pane.report_agent',{'pane_id':pane['pane_id'],'source':'custom:hud-test','agent':'hud-test','state':'idle'})
    session = app.snapshots[path][0]
    app.snapshot_changed(session,request(path,'session.snapshot')['snapshot'],None);pump()
    pointer = Gdk.Display.get_default().get_default_seat().get_pointer()
    real_pointer = os.environ.get('HUD_TEST_POINTER') == '1'
    def mouse(kind, y, state):
        if real_pointer:
            origin = app.terminal_input_window(terminal).get_origin()
            subprocess.run(['xdotool', 'mousemove',
                            str(origin[-2]+10), str(origin[-1]+int(y))], check=True)
            if kind != Gdk.EventType.MOTION_NOTIFY:
                subprocess.run(['xdotool', 'mousedown' if kind == Gdk.EventType.BUTTON_PRESS else 'mouseup', '1'], check=True)
            pump(.1)
            return
        event = Gdk.Event.new(kind); event.set_device(pointer)
        data = event.motion if kind == Gdk.EventType.MOTION_NOTIFY else event.button
        data.window = app.terminal_input_window(terminal)
        data.time = int(GLib.get_monotonic_time()/1000) & 0xffffffff
        data.x, data.y, data.state = 10, y, state
        if kind != Gdk.EventType.MOTION_NOTIFY: data.button = 1
        terminal.event(event);pump(.05)
    height = app.terminal_input_window(terminal).get_height()
    direction = os.environ.get('HUD_TEST_DIRECTION', 'down')
    edge = (height+30 if direction == 'down' else -30) if real_pointer else (height-2 if direction == 'down' else 2)
    start = terminal.get_char_height()*3.5 if direction == 'down' else height-terminal.get_char_height()*3.5
    window_size = app.window.get_size()
    mouse(Gdk.EventType.BUTTON_PRESS, start, 0)
    if real_pointer:
        mouse(Gdk.EventType.MOTION_NOTIFY, height/2, Gdk.ModifierType.BUTTON1_MASK)
    mouse(Gdk.EventType.MOTION_NOTIFY, edge, Gdk.ModifierType.BUTTON1_MASK)
    until(lambda: app.history_selection and app.history_selection.get('ready'))
    selection = app.history_selection
    assert selection.get('live'), 'Alternate-screen CLI was not recognized'
    assert isinstance(selection['view'], Gtk.Fixed), 'Transcript must stay in the colored VTE'
    assert terminal.has_focus(), 'Selection stole focus from the CLI'
    assert app.stack.get_visible_child() is terminal
    until(lambda: len(selection.get('document',[])) > terminal.get_row_count()+12)
    assert app.window.get_size() == window_size, 'Selection changed the terminal layout'
    mouse(Gdk.EventType.BUTTON_RELEASE,edge,0)
    assert app.history_selection is None, 'Release left a selection mode open'
    assert terminal.has_focus(), 'Release requires Escape before typing'
    assert app.stack.get_visible_child() is terminal
    copied = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
    assert copied and copied.count('MESSAGE_') > terminal.get_row_count(), repr(copied)
    lines = [line.strip() for line in copied.splitlines() if line.strip().startswith('MESSAGE_')]
    assert len(lines)==len(set(lines)), lines
    numbers = [int(line.split()[0].split('_')[1]) for line in lines]
    assert numbers == list(range(numbers[0],numbers[-1]+1)), numbers
    if direction == 'down':
        assert '052' in copied.splitlines()[0], 'Selection lost its original anchor: '+repr(copied)
    snapshot = request(path,'pane.read',{'pane_id':pane['pane_id'],'source':'recent','format':'text','lines':20000})['read']['text']
    pump(.6)
    assert snapshot == request(path,'pane.read',{'pane_id':pane['pane_id'],'source':'recent','format':'text','lines':20000})['read']['text'], 'CLI kept scrolling after release'
    app.end_history_selection()
    terminal.feed_child(b'q')
    print('PASS: '+('real pointer outside border: ' if real_pointer else '')+direction+' alternate-screen CLI scrolls during edge selection; copied lines are contiguous, unique, and exceed one screen; release stops scrolling')
finally:
    if os.environ.get('HUD_TEST_POINTER') == '1':
        subprocess.run(['xdotool', 'mouseup', '1'], check=False)
    app.exit_hud()
    try: request(path, 'server.stop')
    except (OSError, ValueError, RuntimeError): pass
    pump();temp.cleanup()

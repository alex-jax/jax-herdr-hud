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
    until(lambda: app.selected is not None and app.selected in app.terminals)
    app.monitor.stop()
    app.monitor.join(6)
    pump()
    until(lambda: app.snapshots[path][1]['workspaces'][0]['label'] == 'Space 1')
    session, snap = app.snapshots[path]
    assert len(snap['workspaces']) == len(snap['panes']) == 1, snap
    assert snap['workspaces'][0]['label'] == 'Space 1', snap
    pane = snap['panes'][0]
    key = (path, pane['terminal_id'])
    assert app.selected == key
    _, reopened = backend.ensure_session('default')
    assert [p['terminal_id'] for p in reopened['panes']] == [key[1]]
    print('PASS: cold startup opens the single default Space 1 terminal; reuse adds no space', flush=True)
    terminal = app.terminals[key]
    until(lambda: terminal.pid)
    pump(1)
    def screen():
        return terminal.get_text_format(hud.Vte.Format.TEXT) or ''
    until(lambda: '$' in screen() or '#' in screen())
    terminal.feed_child(b"printf 'HUD_INPUT_%s\\n' AC")
    terminal.feed_child(b'\x1b[DB\r')
    until(lambda: 'HUD_INPUT_ABC' in screen())
    assert 'spaces' not in screen() and 'agents' not in screen(), screen()
    print('PASS: headless session creation; terminal-only view; input and left-arrow editing', flush=True)
    # Deliver complete GTK mouse events, with a device and timestamp.
    lines = screen().splitlines()
    row = next(i for i, line in enumerate(lines) if line.startswith('HUD_INPUT_ABC'))
    cw, ch = terminal.get_char_width(), terminal.get_char_height()
    pointer = Gdk.Display.get_default().get_default_seat().get_pointer()
    # VTE is windowless for drawing but owns a separate input-only GDK window.
    # Sending events to get_window() hits its parent and VTE rightly ignores them.
    def input_window(window):
        probe = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        probe.button.window = window
        if Gtk.get_event_widget(probe) == terminal:
            return window
        for child in window.get_children():
            found = input_window(child)
            if found:
                return found
        return None
    event_window = input_window(terminal.get_window())
    assert event_window is not None, 'VTE input window was not found'
    def mouse(kind, x, y, state=0):
        event = Gdk.Event.new(kind)
        event.set_device(pointer)
        data = event.motion if kind == Gdk.EventType.MOTION_NOTIFY else event.button
        data.window = event_window
        data.time = int(GLib.get_monotonic_time() / 1000) & 0xffffffff
        data.x, data.y, data.state = x, y, state
        if kind != Gdk.EventType.MOTION_NOTIFY:
            data.button = 1
        terminal.event(event)
        pump(0.05)
    mouse(Gdk.EventType.BUTTON_PRESS, 2, row * ch + ch / 2, Gdk.ModifierType.SHIFT_MASK)
    for i in range(1, 14):
        mouse(Gdk.EventType.MOTION_NOTIFY, i * cw, row * ch + ch / 2, Gdk.ModifierType.BUTTON1_MASK | Gdk.ModifierType.SHIFT_MASK)
    mouse(Gdk.EventType.BUTTON_RELEASE, 13 * cw, row * ch + ch / 2, Gdk.ModifierType.BUTTON1_MASK | Gdk.ModifierType.SHIFT_MASK)
    width, height = app.window.get_size()
    pixels = Gdk.pixbuf_get_from_window(app.window.get_window(), 0, 0, width, height)
    if pixels and os.environ.get('GDK_BACKEND') == 'x11': pixels.savev(str(output_dir / 'hud-preview.png'), 'png', [], [])
    assert terminal.get_has_selection(), 'Shift+drag did not select text'
    print('PASS: Shift+drag selects terminal text', flush=True)
    terminal.select_all()
    pump()
    clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    copied = clip.wait_for_text()
    assert copied and 'HUD_INPUT_ABC' in copied, repr(copied)
    print('PASS: selection automatically copies to system clipboard', flush=True)
    assert terminal.get_has_selection()
    clip.set_text("printf 'HUD_PASTE_OK\\n'", -1)
    event = Gdk.EventButton()
    event.type = Gdk.EventType.BUTTON_PRESS
    event.button = 3
    event.window = terminal.get_window()
    terminal.do_button_press_event(event)
    pump()
    terminal.feed_child(b'\r')
    until(lambda: 'HUD_PASTE_OK' in screen())
    assert not terminal.get_has_selection(), 'Right-click paste left text selected'
    assert clip.wait_for_text() == "printf 'HUD_PASTE_OK\\n'"
    terminal.select_all(); pump()
    clip.set_text("printf 'HUD_KEY_PASTE_OK\\n'", -1)
    terminal.emit('paste-clipboard'); pump()
    assert not terminal.get_has_selection(), 'Keyboard paste left text selected'
    terminal.feed_child(b'\r')
    until(lambda: 'HUD_KEY_PASTE_OK' in screen())
    print('PASS: mouse and keyboard paste clear selection and preserve clipboard text', flush=True)
    # Exercise click reporting through VTE -> native attach -> Herdr -> child PTY.
    import shlex
    mouse_log = Path(temp.name) / 'mouse-input'
    mouse_ready = Path(temp.name) / 'mouse-ready'
    mouse_done = Path(temp.name) / 'mouse-done'
    probe = Path(temp.name) / 'mouse-probe.py'
    probe.write_text('''import os, sys, termios, tty
from pathlib import Path
saved = termios.tcgetattr(0)
try:
    tty.setraw(0)
    os.write(1, b'\\x1b[2J\\x1b[HHUD_MOUSE_TARGET\\r\\n\\x1b[?1002h\\x1b[?1006h')
    Path(sys.argv[2]).touch()
    with open(sys.argv[1], 'ab', buffering=0) as log:
        while True:
            data = os.read(0, 4096)
            if b'q' in data:
                break
            log.write(data)
finally:
    os.write(1, b'\\x1b[?1002l\\x1b[?1006l\\r\\n')
    termios.tcsetattr(0, termios.TCSANOW, saved)
    Path(sys.argv[3]).touch()
''')
    command = 'python3 ' + ' '.join(shlex.quote(str(p)) for p in (probe, mouse_log, mouse_ready, mouse_done))
    terminal.feed_child((command + '\r').encode())
    until(mouse_ready.exists)
    pump(.3)
    terminal.unselect_all()
    mouse(Gdk.EventType.BUTTON_PRESS, 6 * cw, ch / 2)
    mouse(Gdk.EventType.BUTTON_RELEASE, 6 * cw, ch / 2, Gdk.ModifierType.BUTTON1_MASK)
    until(lambda: mouse_log.exists() and b'm' in mouse_log.read_bytes())
    clicks = mouse_log.read_bytes()
    import re
    assert re.search(rb'\x1b\[<0;\d+;\d+M', clicks), clicks
    assert re.search(rb'\x1b\[<0;\d+;\d+m', clicks), clicks
    assert not terminal.get_has_selection(), 'CLI click unexpectedly selected text'
    shift = Gdk.ModifierType.SHIFT_MASK
    mouse(Gdk.EventType.BUTTON_PRESS, 2, ch / 2, shift)
    for column in range(1, 15):
        mouse(Gdk.EventType.MOTION_NOTIFY, column * cw, ch / 2, shift | Gdk.ModifierType.BUTTON1_MASK)
    mouse(Gdk.EventType.BUTTON_RELEASE, 14 * cw, ch / 2, shift | Gdk.ModifierType.BUTTON1_MASK)
    assert terminal.get_has_selection(), 'Shift+drag did not select in mouse-reporting mode'
    assert 'HUD_MOUSE' in (clip.wait_for_text() or '')
    assert mouse_log.read_bytes() == clicks, 'Shift+drag leaked mouse clicks to the CLI'
    terminal.unselect_all()
    terminal.feed_child(b'q')
    until(mouse_done.exists)
    print('PASS: native CLI receives left-button press/release; Shift+drag selects and copies without sending clicks', flush=True)
    old = app.dark
    app.toggle_theme()
    assert app.dark != old
    app.toggle_theme()
    print('PASS: light/dark theme switching', flush=True)
    attached_pid = terminal.pid
    app.settings['terminal_palette'] = 'Horizon'
    app.apply_theme()
    expected = '#1C1E26' if app.dark else '#FDF0ED'
    assert terminal.get_color_background_for_draw().to_string() == hud.rgba(expected).to_string()
    app.toggle_theme()
    expected = '#1C1E26' if app.dark else '#FDF0ED'
    assert terminal.get_color_background_for_draw().to_string() == hud.rgba(expected).to_string()
    assert app.terminals[key] is terminal and terminal.pid == attached_pid and terminal.alive
    app.settings['terminal_palette'] = 'hud'
    app.toggle_theme()
    terminal.feed_child(b"printf '\\033[31mHUD_RED_FILE\\033[0m\\n'\r")
    until(lambda: 'HUD_RED_FILE' in screen())
    pump()
    html = terminal.get_text_format(hud.Vte.Format.HTML)
    (output_dir / 'terminal-colors.html').write_text(html)
    expected_red = app.terminal_colors()[2][1].upper()
    assert f'<font color="{expected_red}">HUD_RED_FILE</font>' in html, html
    print('PASS: real shell ANSI filename color survives the PTY relay into VTE', flush=True)
    print('PASS: imported palette and variant changes recolor live VTE without reconnecting', flush=True)
    app.hide()
    observed = []
    watcher = SessionWatcher(session, lambda *a: None, lambda s, m: observed.append(m))
    watcher.start()
    pump(1)
    request(path, 'pane.report_agent', {'pane_id': pane['pane_id'], 'source': 'custom:hud-test', 'agent': 'hud-test', 'state': 'working'})
    until(lambda: any(m.get('data', {}).get('agent_status') == 'working' for m in observed))
    request(path, 'pane.report_agent', {'pane_id': pane['pane_id'], 'source': 'custom:hud-test', 'agent': 'hud-test', 'state': 'blocked'})
    until(lambda: any(m.get('data', {}).get('agent_status') == 'blocked' for m in observed))
    app.snapshot_changed(session, request(path, 'session.snapshot')['snapshot'], None)
    pump()
    agent_row = app.sidebar_rows[('agent', key)]
    assert agent_row.get_parent() is app.agent_rows
    assert 'hud-test' in agent_row.subtitle_label.get_text()
    assert 'Needs input' in agent_row.subtitle_label.get_text()
    assert app.terminals[key] is terminal
    print('PASS: real Herdr agent reports populate Agents without reconnecting the terminal', flush=True)
    watcher.stop()
    print('PASS: live Herdr event subscription delivers working/blocked states', flush=True)
    assert request(path, 'session.snapshot')['snapshot']['panes']
    app.transition(key, pane, 'working')
    app.transition(key, pane, 'blocked')
    assert key in app.unread
    app.transition(key, pane, 'blocked')
    assert len(app.unread) == 1
    app.show()
    assert key not in app.unread
    print('PASS: hide preserves session, attention notification and acknowledgement', flush=True)
    pump()
    app.new_terminal(path)
    until(lambda: len(app.panes) == 2 and app.selected != key and not app.adding_terminals)
    second_key = app.selected
    second = app.terminals[second_key]
    until(lambda: second.pid)
    until(lambda: '$' in (second.get_text_format(hud.Vte.Format.TEXT) or '') or '#' in (second.get_text_format(hud.Vte.Format.TEXT) or ''))
    second.feed_child(b"printf 'HUD_SECOND_TERMINAL\\n'\r")
    until(lambda: 'HUD_SECOND_TERMINAL' in (second.get_text_format(hud.Vte.Format.TEXT) or ''))
    assert 'HUD_SECOND_TERMINAL' not in screen()
    assert app.panes[second_key]['session']['socket_path'] == path
    app.select(key)
    assert app.stack.get_visible_child() == terminal and 'HUD_MOUSE_TARGET' in screen()
    assert terminal.get_margin_start() == 16 and terminal.get_margin_end() == 16
    print('PASS: + adds independent terminal in the same session; switching preserves both; 16px padding', flush=True)
    checked = []
    def check_dialog():
        dialog = next(w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.Dialog))
        entry = next(w for w in dialog.get_content_area().get_children() if isinstance(w, Gtk.Entry))
        checked.append(entry.get_text() == 'Space 2' and entry.get_placeholder_text() == 'Name your space'
                       and dialog.get_widget_for_response(Gtk.ResponseType.OK).get_sensitive())
        entry.set_text('  ')
        assert not dialog.get_widget_for_response(Gtk.ResponseType.OK).get_sensitive()
        cancel = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        start = dialog.get_widget_for_response(Gtk.ResponseType.OK)
        cx, cy = cancel.translate_coordinates(dialog, 0, 0)
        sx, sy = start.translate_coordinates(dialog, 0, 0)
        ex, ey = entry.translate_coordinates(dialog, 0, 0)
        assert cy == sy and cx < sx
        assert cancel.get_allocated_width() == start.get_allocated_width()
        assert abs((cx + sx + start.get_allocated_width()) / 2
                   - (ex + entry.get_allocated_width() / 2)) <= 2
        assert ex >= 16 and cy >= ey + entry.get_allocated_height() + 8
        entry.set_text('another-session')
        checked.append(dialog.get_widget_for_response(Gtk.ResponseType.OK).get_sensitive())
        dialog.response(Gtk.ResponseType.CANCEL)
        return GLib.SOURCE_REMOVE
    GLib.idle_add(check_dialog)
    app.new_session()
    assert checked == [True, True], checked
    print('PASS: new space suggests Space 2 and rejects a blank name', flush=True)
    # Rename a real pane through the dialog and verify Herdr persists the label.
    def submit_rename():
        dialog = next(w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.Dialog))
        entry = next(w for w in dialog.get_content_area().get_children() if isinstance(w, Gtk.Entry))
        entry.set_text('Renamed terminal')
        dialog.response(Gtk.ResponseType.OK)
        return GLib.SOURCE_REMOVE
    def pencil_action(row, index, close_label='Close'):
        row.rename_button.clicked()
        menu = Gtk.Menu.get_for_attach_widget(row.rename_button)[0]
        assert [item.get_label() for item in menu.get_children()] == ['Rename', close_label]
        menu.get_children()[index].activate()
        menu.popdown()
        menu.destroy()
    GLib.idle_add(submit_rename)
    pencil_action(app.sidebar_rows[('terminal', second_key)], 0)
    until(lambda: app.panes[second_key].get('label') == 'Renamed terminal')
    persisted = request(path, 'session.snapshot')['snapshot']
    assert any(p.get('label') == 'Renamed terminal' for p in persisted['panes'])
    renamed_tab = app.panes[second_key]['tab_id']
    assert next(t for t in persisted['tabs'] if t['tab_id'] == renamed_tab)['label'] == 'Renamed terminal'
    assert app.panes[second_key]['tab_label'] == 'Renamed terminal'
    assert next(t for t in persisted['tabs'] if t['tab_id'] == pane['tab_id'])['label'] != 'Renamed terminal'
    pump()
    row = app.sidebar_rows[('terminal', second_key)]
    app.open_session_menu(row)
    menu = next(w for w in Gtk.Menu.get_for_attach_widget(row))
    assert [item.get_label() for item in menu.get_children()] == ['Rename', 'Close']
    menu.get_children()[1].activate()
    menu.popdown()
    until(lambda: second_key not in app.panes and not second.alive)
    assert key in app.panes and terminal.alive
    assert len(request(path, 'session.snapshot')['snapshot']['panes']) == 1
    print('PASS: Rename persists in Herdr; context-menu Exit closes only its targeted terminal', flush=True)
    app.create_session('Shared HUD workspace')
    until(lambda: not app.creating_session and app.selected not in (key, second_key))
    shared_key = app.selected
    assert shared_key[0] == path
    created = request(path, 'session.snapshot')['snapshot']
    assert len(created['workspaces']) == len(created['panes']) == 2
    shared_workspace = app.panes[shared_key]['workspace_id']
    # Bare Herdr's API uses the same default server as its original TUI.
    original = subprocess.run([backend.resolve_herdr(), 'api', 'snapshot'], env=test_env(),
                              capture_output=True, text=True, check=True)
    assert 'Shared HUD workspace' in original.stdout
    assert shared_key[1] in original.stdout
    pump()
    group = app.sidebar_rows[('group', (path, shared_workspace))]
    assert group.title_label.get_text() == 'Shared HUD workspace'
    GLib.idle_add(submit_rename)
    pencil_action(group, 0)
    until(lambda: app.panes[shared_key]['workspace_label'] == 'Renamed terminal')
    pump()
    assert group.title_label.get_text() == 'Renamed terminal'
    for target_row in (group, app.sidebar_rows[('terminal', shared_key)]):
        button_x, _ = target_row.rename_button.translate_coordinates(target_row, 0, 0)
        label_x, _ = target_row.title_label.translate_coordinates(target_row, 0, 0)
        assert button_x < label_x, 'Pencil must precede the name'
    original = subprocess.run([backend.resolve_herdr(), 'api', 'snapshot'], env=test_env(),
                              capture_output=True, text=True, check=True)
    assert 'Renamed terminal' in original.stdout and 'Shared HUD workspace' not in original.stdout
    print('PASS: leading pencil buttons rename spaces and sessions in Herdr', flush=True)
    # Plus must add to this workspace even while a different one is selected.
    app.select(key)
    group.add_button.clicked()
    until(lambda: not app.adding_terminals and app.selected != key)
    assert app.panes[app.selected]['workspace_id'] == shared_workspace
    assert len([p for p in app.panes.values() if p['workspace_id'] == shared_workspace]) == 2
    assert len(backend.list_sessions()) == 1
    print('PASS: HUD creation is visible in original default Herdr; workspace groups and + target correctly', flush=True)
    pencil_action(group, 1)
    until(lambda: not any(p['workspace_id'] == shared_workspace for p in app.panes.values()))
    assert key in app.panes and terminal.alive
    app.select(key)
    print('PASS: pencil Close stops the targeted space without closing other spaces', flush=True)
    # Capture the actual GTK widget, not a mock rendering.
    width, height = app.window.get_size()
    pixels = Gdk.pixbuf_get_from_window(app.window.get_window(), 0, 0, width, height)
    if pixels and os.environ.get('GDK_BACKEND') == 'x11':
        pixels.savev(str(output_dir / 'hud-preview.png'), 'png', [], [])
    terminal.detach()
    pump()
    assert request(path, 'session.snapshot')['snapshot']['panes']
    print('PASS: detaching Hud clients leaves server and shell running', flush=True)
    # The first space keeps its last pane, including an agent terminal.
    assert not app.can_close_sidebar_item(('terminal', key))
    app.close_sidebar_item(('terminal', key))
    pump()
    assert key in app.panes
    assert len(request(path, 'session.snapshot')['snapshot']['panes']) == 1
    def confirm_agent_close():
        dialogs = [w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.MessageDialog)]
        assert len(dialogs) == 1
        dialogs[0].response(Gtk.ResponseType.OK)
        return False
    for agent in (False, True):
        app.create_session('Disposable space')
        until(lambda: not app.creating_session and app.selected != key)
        closing_key = app.selected
        closing_pane = app.panes[closing_key]
        group_id = ('group', (path, closing_pane['workspace_id']))
        if agent:
            request(path, 'pane.report_agent', {'pane_id': closing_pane['pane_id'],
                'source': 'custom:hud-test', 'agent': 'hud-test', 'state': 'working'})
            app.snapshot_changed(session, request(path, 'session.snapshot')['snapshot'], None)
            pump()
            GLib.idle_add(confirm_agent_close)
        row = app.sidebar_rows[('agent' if agent else 'terminal', closing_key)]
        # Open the actual ListBox right-click menu, then activate Close.
        rows = row.get_parent()
        allocation = row.get_allocation()
        event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        event.set_device(Gdk.Display.get_default().get_default_seat().get_pointer())
        event.button.window = rows.get_window()
        event.button.time = int(GLib.get_monotonic_time() / 1000) & 0xffffffff
        event.button.x = allocation.x + 3
        event.button.y = allocation.y + allocation.height / 2
        event.button.button = 3
        event.button.state = 0
        rows.event(event)
        menu = Gtk.Menu.get_for_attach_widget(row)[0]
        assert [item.get_label() for item in menu.get_children()] == [
            'Rename', 'Close terminal and stop agent' if agent else 'Close']
        menu.get_children()[1].activate()
        menu.popdown()
        menu.destroy()
        until(lambda: closing_key not in app.panes)
        pump()
        assert group_id not in app.sidebar_rows, 'Empty secondary space remained visible'
        assert ('agent', closing_key) not in app.sidebar_rows
        current = request(path, 'session.snapshot')['snapshot']
        assert len(current['workspaces']) == len(current['panes']) == 1
        assert current['panes'][0]['terminal_id'] == key[1]
        assert app.selected == key
    print('PASS: right-click Close on last shell or agent removes its secondary space; first space keeps its last pane and receives selection', flush=True)

finally:
    app.exit_hud()
    try:
        request(path, 'server.stop')
    except (OSError, ValueError, RuntimeError):
        pass
    pump()
    temp.cleanup()

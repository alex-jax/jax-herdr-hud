#!/usr/bin/python3
"""Regression: dispatch actual GTK sidebar clicks, not direct Hud.select() calls."""
import os
os.environ.setdefault('GDK_BACKEND', 'x11')
os.environ['G_DEBUG'] = 'fatal-criticals'
import sys
from pathlib import Path
import tempfile
import time
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
output_dir = Path(os.environ.get('HUD_TEST_OUTPUT', tempfile.mkdtemp(prefix='herdr-hud-test-output-')))
output_dir.mkdir(parents=True, exist_ok=True)
import hud
from hud import Gtk, Gdk, GLib

class NoMonitor:
    def __init__(self, *args): pass
    def start(self): pass
    def stop(self): pass
hud.Monitor = NoMonitor
# Exercise native widgets without touching existing sessions or spawning agents.
def launch(self, argv):
    self.alive = True
    self.feed(('Terminal ' + argv[-1] + '\r\n').encode())
hud.Terminal.launch = launch
hud.resolve_herdr = lambda: '/test/herdr'
hud.Hud.shell_call = lambda *args: None
with tempfile.TemporaryDirectory(prefix='herdr-hud-click-') as tmp:
    hud.CONFIG = Path(tmp)
    app = hud.Hud()
    app.set_application_id('io.github.herdr.Hud.ClickTest')
    app.register(None)
    app.show()
    def pump(seconds=0.08):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            time.sleep(.005)
    panes = [dict(pane_id=f'w1:p{i}', terminal_id=f'terminal-{i}', workspace_id='w1',
                  tab_id=f'w1:t{i}', agent_status='idle', label=f'Terminal {i}') for i in (1,2)]
    snapshot = {'panes':panes, 'workspaces':[{'workspace_id':'w1','label':'Home'}],
                'tabs':[{'tab_id':f'w1:t{i}', 'label':f'Terminal {i}'} for i in (1,2)]}
    session = {'name':'Click test', 'socket_path':tmp+'/test.sock', 'running':True}
    app.snapshot_changed(session, snapshot, None)
    other_session = {'name':'Second session', 'socket_path':tmp+'/second.sock', 'running':True}
    app.snapshot_changed(other_session, {**snapshot, 'panes':panes[:1]}, None)
    targets = [(session['socket_path'], 'terminal-1'), (session['socket_path'], 'terminal-2'),
               (other_session['socket_path'], 'terminal-1')]
    pump(.3)
    pointer = Gdk.Display.get_default().get_default_seat().get_pointer()
    for n in range(30):
        key = targets[(n // 2) % len(targets)]
        app.search.grab_focus()
        row = next(r for r in app.rows.get_children() if getattr(r, 'key', None) == key)
        allocation = row.get_allocation()
        for kind in (Gdk.EventType.BUTTON_PRESS, Gdk.EventType.BUTTON_RELEASE):
            event = Gdk.Event.new(kind)
            event.set_device(pointer)
            event.button.window = app.rows.get_window()
            event.button.time = int(GLib.get_monotonic_time()/1000) & 0xffffffff
            event.button.x = allocation.x + 25
            event.button.y = allocation.y + allocation.height/2
            event.button.button = 1
            event.button.state = 0 if kind == Gdk.EventType.BUTTON_PRESS else Gdk.ModifierType.BUTTON1_MASK
            app.rows.event(event)
        pump()
        assert app.selected == key, (app.selected, key)
        assert app.window.get_visible()
        assert app.window.get_focus() == app.terminals[key], 'Session click did not focus the terminal'
    print('PASS: 30 GTK pointer clicks across two sessions and their terminals without destroying the active click target', flush=True)
    # Send right-clicks to GTK's actual ListBox input window, not menu helpers.
    selected_before = app.selected
    for session_path in (session['socket_path'], other_session['socket_path']):
        group_identity = ('group', (session_path, 'w1'))
        assert not app.can_close_sidebar_item(group_identity)
        assert not app.can_close_sidebar_item(('terminal', (session_path, 'terminal-1')))
    assert app.can_close_sidebar_item(('terminal', targets[1]))
    second_space_pane = dict(pane_id='w2:p1', terminal_id='second-space-first',
                             workspace_id='w2', tab_id='w2:t1', agent_status='idle', label='First tab')
    app.snapshot_changed(session, {
        'panes': panes + [second_space_pane],
        'workspaces': snapshot['workspaces'] + [{'workspace_id':'w2', 'label':'Second space'}],
        'tabs': snapshot['tabs'] + [{'tab_id':'w2:t1', 'label':'First tab'}]}, None)
    pump()
    second_space_identity = ('terminal', (session['socket_path'], 'second-space-first'))
    assert app.can_close_sidebar_item(second_space_identity)
    assert app.can_close_sidebar_item(('group', (session['socket_path'], 'w2')))
    assert not app.can_close_sidebar_item(('terminal', targets[0]))
    row = app.sidebar_rows[second_space_identity]
    row.rename_button.clicked()
    menu = Gtk.Menu.get_for_attach_widget(row.rename_button)[0]
    assert [item.get_label() for item in menu.get_children()] == ['Rename', 'Close']
    menu.popdown()
    menu.destroy()
    app.snapshot_changed(session, snapshot, None)
    pump()
    print('PASS: first tab in second space offers Close; first space and its first tab remain protected', flush=True)
    before_close = dict(app.panes)
    app.close_sidebar_item(('terminal', targets[0]))
    app.close_sidebar_item(('group', (session['socket_path'], 'w1')))
    pump()
    assert app.panes == before_close
    for target in targets:
        row = app.sidebar_rows[('terminal', target)]
        allocation = row.get_allocation()
        for x in (allocation.x + 3, allocation.x + allocation.width - 3):
            event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
            event.set_device(pointer)
            event.button.window = app.rows.get_window()
            event.button.time = int(GLib.get_monotonic_time()/1000) & 0xffffffff
            event.button.x = x
            event.button.y = allocation.y + allocation.height / 2
            event.button.button = 3
            event.button.state = 0
            app.rows.event(event)
            pump()
            menus = Gtk.Menu.get_for_attach_widget(row) or []
            assert menus, 'Right-click did not open the row context menu'
            menu = menus[0]
            assert menu.get_visible()
            assert [item.get_label() for item in menu.get_children()] == (
                ['Rename', 'Close'] if target[1] == 'terminal-2' else ['Rename'])
            assert app.selected == selected_before, 'Right-click switched terminals'
            menu.popdown()
            menu.destroy()
            pump()
    print('PASS: real GTK right-click events open Rename/Close at both edges of each terminal row', flush=True)
    # Agent identity controls placement; working/done/idle never disconnect a pane.
    agent_key = targets[0]
    app.select(agent_key)
    pump()
    stable_terminal = app.terminals[agent_key]
    stable_row = app.sidebar_rows[('terminal', agent_key)]
    for agent in ('codex', 'claude', 'gemini', 'opencode', 'custom:test-agent'):
        for state in ('working', 'blocked', 'done', 'idle', 'unknown'):
            reported = {**panes[0], 'agent':agent, 'display_agent':agent, 'agent_status':state}
            app.snapshot_changed(session, {**snapshot, 'panes':[reported, panes[1]]}, None)
            pump(.03)
            assert stable_row.get_parent() == app.agent_rows
            assert stable_row not in app.rows.get_children()
            assert app.agent_rows.get_selected_row() is stable_row
            assert app.rows.get_selected_row() is None
            assert app.stack.get_visible_child() is stable_terminal
            assert app.window.get_focus() is stable_terminal
            assert agent in stable_row.subtitle_label.get_text()
        app.snapshot_changed(session, snapshot, None)
        pump()
        assert stable_row.get_parent() == app.rows
        assert app.rows.get_selected_row() is stable_row
        assert app.agent_rows.get_selected_row() is None
        assert app.terminals[agent_key] is stable_terminal
    # Spaces consisting entirely of agents must remain usable.
    app.snapshot_changed(session, {**snapshot, 'panes':[
        {**p, 'agent':'codex', 'agent_status':'working'} for p in panes]}, None)
    pump()
    group = app.sidebar_rows[('group', (session['socket_path'], 'w1'))]
    assert group.get_visible() and group.add_button.get_sensitive()
    assert group.subtitle_label.get_text() == '0 terminals · 2 agents'
    agent_row = app.sidebar_rows[('terminal', targets[1])]
    allocation = agent_row.get_allocation()
    for kind in (Gdk.EventType.BUTTON_PRESS, Gdk.EventType.BUTTON_RELEASE):
        event = Gdk.Event.new(kind)
        event.set_device(pointer)
        event.button.window = app.agent_rows.get_window()
        event.button.time = int(GLib.get_monotonic_time()/1000) & 0xffffffff
        event.button.x = allocation.x + allocation.width - 20
        event.button.y = allocation.y + allocation.height / 2
        event.button.button = 1
        event.button.state = 0 if kind == Gdk.EventType.BUTTON_PRESS else Gdk.ModifierType.BUTTON1_MASK
        app.agent_rows.event(event)
    pump()
    assert app.selected == targets[1]
    assert app.window.get_focus() is app.terminals[targets[1]]
    assert app.rows.get_selected_row() is None
    width, height = app.window.get_size()
    pixels = Gdk.pixbuf_get_from_window(app.window.get_window(), 0, 0, width, height)
    if pixels:
        pixels.savev(str(output_dir / 'herdr-hud-sections.png'), 'png', [], [])
    app.search.set_text('codex')
    pump(.3)
    assert stable_row.get_visible() and group.get_visible()
    app.search.set_text('')
    app.snapshot_changed(session, snapshot, None)
    pump(.3)
    app.sections.set_position(180)
    pump()
    app.space_section.set_expanded(False)
    pump()
    app.space_section.set_expanded(True)
    pump()
    assert app.sections.get_position() == 180, (app.sections.get_position(), app.section_position)
    app.agent_section.set_expanded(False)
    pump()
    app.save()
    import json
    section_settings = json.loads((hud.CONFIG / 'settings.json').read_text())
    assert section_settings['section_position'] == 180
    assert section_settings['spaces_expanded'] and not section_settings['agents_expanded']
    app.agent_section.set_expanded(True)
    pump()
    assert app.sections.get_position() == 180, (app.sections.get_position(), app.section_position)
    print('PASS: agent lifecycle moves the same row without duplicate terminals or lost focus; sections persist and search includes agents', flush=True)
    app.select(key)
    pump()
    # Exercise the same path with keyboard navigation, plus an unread badge refresh.
    app.unread[key] = 'Finished'
    app.rows.select_row(next(r for r in app.rows.get_children() if getattr(r,'key',None) != key and hasattr(r,'key')))
    pump()
    app.rows.select_row(next(r for r in app.rows.get_children() if getattr(r,'key',None) == key))
    pump()
    assert key not in app.unread
    print('PASS: keyboard selection and notification acknowledgement keep the Hud open', flush=True)
    selected_row = app.rows.get_selected_row()
    terminal = app.terminals[key]
    selection_events = []
    handler = app.rows.connect('row-selected', lambda _, row: selection_events.append(row))
    original_rows = list(app.rows.get_children())
    label_updates = []
    selected_row.title_label.connect('notify::label', lambda *_: label_updates.append(True))
    for _ in range(20):
        app.snapshot_changed(session, snapshot, None)
        pump(.01)
        assert app.rows.get_selected_row() is selected_row
        assert app.rows.get_children() == original_rows
        assert app.stack.get_visible_child() is terminal
        assert app.window.get_focus() is terminal
    assert not label_updates, 'Unchanged snapshots rewrote the selected label'
    app.states[key] = 'working'
    app.rebuild_sidebar()
    pump()
    assert selected_row.title_label.get_text().startswith('◉')
    extra_session = {'name':'New session', 'socket_path':tmp+'/new.sock', 'running':True}
    app.snapshot_changed(extra_session, snapshot, None)
    pump()
    assert app.rows.get_selected_row() is selected_row
    # Adding/removing a terminal in another group must retain all existing rows.
    app.snapshot_changed(other_session, snapshot, None)
    pump()
    assert all(row in app.rows.get_children() for row in original_rows)
    app.snapshot_changed(other_session, {**snapshot, 'panes':panes[:1]}, None)
    pump()
    assert app.rows.get_selected_row() is selected_row
    assert not selection_events, 'Background refresh changed GTK selection'
    app.rows.disconnect(handler)
    app.search.set_text('no matching sessions')
    pump(.3)
    assert not selected_row.get_visible()
    app.search.set_text('')
    pump(.3)
    assert app.rows.get_selected_row() is selected_row and selected_row.get_visible()
    assert app.stack.get_visible_child() is terminal
    print('PASS: repeated snapshots, status changes and new sessions preserve rows, selection and terminal; search restores the same row', flush=True)
    original_position = app.split.get_position()
    app.split.set_position(0)
    pump()
    assert app.split.get_position() == 0 and app.split.get_property('min-position') == 0
    far_right = app.split.get_property('max-position')
    app.split.set_position(far_right)
    pump()
    assert app.split.get_position() == far_right
    assert far_right >= app.split.get_allocated_width() - 12
    app.split.set_position(original_position)
    pump()
    assert app.split.get_position() == original_position
    print('PASS: divider reaches both edges and restores a usable split', flush=True)
    app.split.set_position(310)
    pump()
    app.sidebar_toggle.clicked()
    pump()
    assert app.split.get_position() == 0 and app.sidebar_expanded_width == 310
    app.hide()
    app.show()
    pump()
    assert app.split.get_position() == 0 and app.window.get_focus() == app.terminals[app.selected]
    app.sidebar_toggle.clicked()
    pump()
    assert app.split.get_position() == 310
    assert app.divider_grip.get_allocated_width() == 3
    grip_x, _ = app.divider_grip.translate_coordinates(app.split_overlay, 0, 0)
    assert abs(grip_x - 312) <= 2, grip_x
    app.save()
    import json
    saved = json.loads((hud.CONFIG / 'settings.json').read_text())
    assert saved['sidebar_width'] == 310 and saved['sidebar_expanded_width'] == 310
    print('PASS: grip, collapse/expand, saved sidebar width and terminal focus after clicking/showing', flush=True)
    normal_size = app.window.get_size()
    normal_position = app.window.get_position()
    app.expand_button.clicked()
    pump(.5)
    assert app.window.is_maximized()
    assert app.expand_button.get_tooltip_text() == 'Restore window'
    app.save()
    saved_expanded = json.loads((hud.CONFIG / 'settings.json').read_text())
    assert (saved_expanded['width'], saved_expanded['height']) == tuple(normal_size)
    app.expand_button.clicked()
    pump(.5)
    assert not app.window.is_maximized()
    assert tuple(app.window.get_size()) == tuple(normal_size)
    assert tuple(app.window.get_position()) == tuple(normal_position)
    assert app.expand_button.get_tooltip_text() == 'Expand HUD'
    print('PASS: expand/restore returns to the user window size and position without overwriting saved geometry', flush=True)
    app.exit_hud()

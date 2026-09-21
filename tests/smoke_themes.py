#!/usr/bin/python3
"""Native theme chooser, offline and without spawning Herdr or agents."""
import os
os.environ.setdefault('GDK_BACKEND', 'x11')
os.environ['G_DEBUG'] = 'fatal-criticals'
import sys
from pathlib import Path
import tempfile
import time
sys.path.insert(0, os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
import hud
from hud import Gtk, Gdk
from terminal_themes import palettes
class NoMonitor:
    def __init__(self, *args): pass
    def start(self): pass
    def stop(self): pass
hud.Monitor = hud.UpdateMonitor = NoMonitor
hud.Hud.shell_call = lambda *args: None
hud.resolve_herdr = lambda: '/test/herdr'
hud.Terminal.launch = lambda *args: None

def pump():
    end = time.monotonic() + .25
    while time.monotonic() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(.005)

with tempfile.TemporaryDirectory(prefix='hud-themes-') as tmp:
    hud.CONFIG = Path(tmp)
    app = hud.Hud()
    app.set_application_id('io.github.herdr.Hud.ThemeTest')
    app.register(None)
    app.show()
    try:
        assert app.theme == 'dark' and app.dark
        assert app.settings['terminal_palette'] == 'gnome'
        from terminal_themes import palette
        assert app.terminal_colors()[1] == palette('gnome', True)['background']
        app.toggle_theme()
        assert app.terminal_colors()[1] == palette('gnome', False)['background']
        app.toggle_theme()
        print('PASS: fresh install defaults to GNOME Dark; light toggle uses GNOME Light')
        app.show_setup()
        app.appearance_button.clicked(); pump()
        picker = app.theme_picker
        assert len(picker.cards) == 245
        assert sum(picker.matches(c) for c in picker.flow.get_children()) == 13
        picker.search.set_text('  dracula  '); pump()
        assert [c.palette_key for c in picker.flow.get_children() if picker.matches(c)] == ['dracula']
        picker.cards['dracula'][1].clicked(); pump()
        picker.mode.set_active_id('dark'); pump()
        assert app.terminal_colors()[:2] == ('#f8f8f2', '#282a36')
        picker.mode.set_active_id('light'); pump()
        assert app.terminal_colors()[:2] == ('#282a36', '#ffffff')
        restored = hud.Hud()
        assert restored.settings['terminal_palette'] == 'dracula' and restored.theme == 'light'
        picker.search.set_text('not-a-real-theme'); pump()
        assert picker.summary.get_text() == 'No themes match your search'
        picker.search.set_text(''); picker.all_palettes.set_active(True); pump()
        assert sum(picker.matches(c) for c in picker.flow.get_children()) == 245
        picker.cards['Aci'][1].clicked(); pump()
        assert app.terminal_colors()[1] == '#0D1926'
        picker.cards['hud'][1].clicked(); pump()
        assert app.terminal_colors()[1] == '#ffffff'
        picker.all_palettes.set_active(False)
        output = Path(os.environ.get('HUD_TEST_OUTPUT', tempfile.mkdtemp(prefix='hud-themes-images-')))
        output.mkdir(parents=True, exist_ok=True)
        for mode in ('dark', 'light'):
            picker.mode.set_active_id(mode); pump()
            width, height = picker.get_size()
            pixels = Gdk.pixbuf_get_from_window(picker.get_window(), 0, 0, width, height)
            pixels.savev(str(output / f'theme-picker-{mode}.png'), 'png', [], [])
        picker.response(Gtk.ResponseType.CLOSE); pump()
        assert app.theme_picker is None
        session = dict(name='default', socket_path=tmp+'/preview.sock', running=True)
        app.snapshot_changed(session, dict(
            workspaces=[dict(workspace_id='w1', label='Studio')],
            tabs=[dict(tab_id='t1', label='Workspace')],
            panes=[dict(pane_id='p1', terminal_id='term1', workspace_id='w1',
                        tab_id='t1', agent_status='idle', label='Workspace')]), None)
        pump()
        app.select((session['socket_path'], 'term1')); pump()
        term = app.terminals[(session['socket_path'], 'term1')]
        term.feed(b'\x1b[1;34msrc/\x1b[0m  \x1b[32mrun.sh\x1b[0m  README.md\r\n\r\n'
                  b'\x1b[35mdef\x1b[0m greet(name):\r\n'
                  b'    \x1b[36mprint\x1b[0m(\x1b[33m"Hello"\x1b[0m, name)\r\n')
        for mode in ('dark', 'light'):
            app.theme = mode
            app.settings['terminal_palette'] = 'Horizon'
            app.apply_theme(); pump()
            expected = '#1C1E26' if mode == 'dark' else '#FDF0ED'
            actual = app.window.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
            assert actual.to_string() == hud.rgba(expected).to_string()
            sidebar = app.rows.get_parent()
            assert term.get_color_background_for_draw().to_string() == hud.rgba(expected).to_string()
            width, height = app.window.get_size()
            pixels = Gdk.pixbuf_get_from_window(app.window.get_window(), 0, 0, width, height)
            pixels.savev(str(output / f'hud-horizon-{mode}.png'), 'png', [], [])
        print('PASS: whole-window palette styling and colored terminal preview')
        print('PASS: 244 imported palettes, featured/all/search, selection, light/dark variants, persistence and classic palette')
        print('Screenshots:', output)
    finally:
        app.exit_hud()

"""Offline bundled-app integration gate, isolated from user Herdr and settings."""
import json
import os
from pathlib import Path
import signal
import tempfile
import time


def main():
    import ssl
    import certifi
    assert ssl.create_default_context(cafile=certifi.where()).get_ca_certs()
    import hud
    from hud import Gtk, GLib, Vte
    class NoMonitor:
        def __init__(self, *args): pass
        def start(self): pass
        def stop(self): pass
    hud.Monitor = hud.UpdateMonitor = NoMonitor
    hud.resolve_herdr = lambda: '/not-used/herdr'
    with tempfile.TemporaryDirectory(prefix='hud-mac-smoke-') as directory:
        hud.CONFIG = Path(directory)
        app = hud.Hud()
        app.register(None)
        app.show()
        result = {}
        def pump(seconds=.2):
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                while Gtk.events_pending():
                    Gtk.main_iteration_do(False)
                time.sleep(.01)
        try:
            pump()
            assert app.dark and app.settings['terminal_palette'] == 'Vs Code'
            app.toggle_theme()
            assert not app.dark
            app.toggle_theme()
            app.show_appearance()
            pump()
            assert len(app.theme_picker.cards) == 245
            app.theme_picker.destroy()
            result['themes'] = True
            original_launch = hud.Terminal.launch
            hud.Terminal.launch = lambda *_: None
            session = dict(name='default', socket_path=directory + '/fake.sock', running=True)
            app.snapshot_changed(session, dict(workspaces=[dict(workspace_id='w', label='Mac test')],
                tabs=[dict(tab_id='t', label='Test terminal')],
                panes=[dict(pane_id='p', terminal_id='term', workspace_id='w', tab_id='t',
                            agent_status='idle', label='Test terminal')]), None)
            pump()
            # Exercise the real frozen display relay, without starting Herdr.
            try:
                app.select((session['socket_path'], 'term'))
            finally:
                hud.Terminal.launch = original_launch
            terminal = app.terminals[(session['socket_path'], 'term')]
            terminal.launch(['/bin/sh', '-c', 'sleep 1; printf "HUD_RELAY_OK\\n"; exec /bin/sleep 30'])
            pump(4)
            assert 'HUD_RELAY_OK' in terminal.get_text_format(Vte.Format.TEXT)
            assert terminal.pid is not None
            result['frozen_relay'] = True
            import cairo
            output = Path(os.environ['HUD_SMOKE_RESULT']).parent
            width, height = app.window.get_size()
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            app.window.draw(cairo.Context(surface))
            surface.write_to_png(str(output / 'macos-hud-dark.png'))
            terminal.select_all()
            pump()
            clip = Gtk.Clipboard.get(hud.Gdk.SELECTION_CLIPBOARD)
            assert 'HUD_RELAY_OK' in (clip.wait_for_text() or '')
            result['clipboard'] = True
            app.publish('Mac test notification')
            pump()
            assert app.desktop.toast is not None and app.desktop.toast.isVisible()
            app.desktop.suspend()
            assert not app.desktop.panel.isVisible()
            app.desktop.suspend('lock')
            app.desktop.resume()
            assert not app.desktop.panel.isVisible(), 'Waking must not clear a separate screen lock'
            app.desktop.resume('lock')
            assert app.desktop.panel.isVisible()
            app.hide()
            assert terminal.alive
            app.show()
            result['bubble_and_hide'] = True
            app.save()
            assert (hud.CONFIG / 'window.json').exists()
            result['geometry'] = True
            pid = terminal.pid
            app.exit_hud()
            pump(.5)
            assert app.desktop.closed and not app.desktop.panel.isVisible()
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                result['relay_detach'] = True
            assert result.get('relay_detach'), 'Relay remained alive after exit'
        finally:
            if not app.closing:
                app.exit_hud()
        Path(os.environ['HUD_SMOKE_RESULT']).write_text(json.dumps(result, indent=2))

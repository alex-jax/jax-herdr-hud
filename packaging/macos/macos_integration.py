"""Exercise the packaged app with a separately supplied, disposable Herdr server."""
import json
import os
from pathlib import Path
import tempfile
import time


def main():
    executable = Path(os.environ['HUD_TEST_HERDR']).resolve(strict=True)
    import backend
    import hud
    from hud import Gtk, Vte
    class NoUpdates:
        def __init__(self, *args): pass
        def start(self): pass
        def stop(self): pass
    hud.UpdateMonitor = NoUpdates
    original_environment = backend.environment
    with tempfile.TemporaryDirectory(prefix='hud-real-mac-') as directory:
        root = Path(directory)
        def environment():
            return dict(original_environment(), XDG_CONFIG_HOME=str(root), HERDR_NO_UPDATE_CHECK='1')
        backend.environment = hud.environment = environment
        hud.CONFIG = root / 'hud'
        hud.CONFIG.mkdir()
        (hud.CONFIG / 'settings.json').write_text(json.dumps({'herdr_path': str(executable)}))
        app = hud.Hud()
        app.register(None)
        app.show()
        path = str(root / 'herdr/herdr.sock')
        def pump(seconds=.15):
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                while Gtk.events_pending():
                    Gtk.main_iteration_do(False)
                time.sleep(.01)
        def wait(predicate, seconds=20):
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                pump()
                if predicate():
                    return
            raise AssertionError('Timed out waiting for real Herdr integration: ' + app.status.get_text())
        try:
            wait(lambda: app.selected in app.terminals and app.terminals[app.selected].pid)
            terminal = app.terminals[app.selected]
            pump(1)
            terminal.feed_child(b"printf 'HUD_REAL_MAC_%s\\n' OK\r")
            wait(lambda: 'HUD_REAL_MAC_OK' in terminal.get_text_format(Vte.Format.TEXT))
            snapshot = backend.request(path, 'session.snapshot')['snapshot']
            ids = [p['terminal_id'] for p in snapshot['panes']]
            app.hide()
            assert terminal.alive
            app.show()
            app.exit_hud()
            pump(.5)
            after = backend.request(path, 'session.snapshot')['snapshot']
            assert [p['terminal_id'] for p in after['panes']] == ids
            Path(os.environ['HUD_INTEGRATION_RESULT']).write_text(json.dumps({
                'herdr': backend.check_herdr()[1], 'native_attach_input_output': True,
                'hide_keeps_attachment': True, 'exit_preserves_server_and_panes': True}, indent=2))
        finally:
            if not app.closing:
                app.exit_hud()
            # This exact socket belongs to the temporary configuration above.
            try:
                backend.request(path, 'server.stop')
            except (OSError, ValueError, RuntimeError):
                pass
            pump()

"""Pre-port GTK/Quartz/VTE bundle gate; no Herdr or user preferences touched."""
import json
import os
from pathlib import Path
import platform
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gdk, GLib, Gtk, Vte


def main():
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    assert Gtk.init_check()[0], 'No graphical macOS session'
    display = Gdk.Display.get_default()
    assert 'Quartz' in type(display).__name__, type(display).__name__
    window = Gtk.Window()
    terminal = Vte.Terminal()
    window.add(terminal)
    window.show_all()
    result = {'display': type(display).__name__, 'architecture': platform.machine(),
              'macos': platform.mac_ver()[0], 'frozen': bool(getattr(sys, 'frozen', False))}

    def finish():
        text = terminal.get_text_format(Vte.Format.TEXT)
        result['screen'] = text
        result['pty'] = 'HUD_MAC_PTY_OK' in text
        Path(os.environ['HUD_PROBE_RESULT']).write_text(json.dumps(result, indent=2))
        Gtk.main_quit()
        return False

    def spawned(_terminal, pid, error, *_):
        result['pid'] = pid
        result['spawn_error'] = str(error) if error else None

    terminal.connect('child-exited', lambda _terminal, status: result.update(exit_status=status))
    terminal.spawn_async(Vte.PtyFlags.DEFAULT, '/tmp',
                         ['/bin/sh', '-c', 'printf "HUD_MAC_PTY_OK\\n"; sleep 2'],
                         ['PATH=/usr/bin:/bin', 'TERM=xterm-256color'],
                         GLib.SpawnFlags.DEFAULT, None, None, -1, None, spawned, None)
    GLib.timeout_add_seconds(4, finish)
    Gtk.main()
    assert result.get('pty'), result


if __name__ == '__main__':
    main()

"""Platform boundaries; Herdr model and terminal behavior stay shared."""
import os
from pathlib import Path
import sys

IS_MAC = sys.platform == 'darwin'


def config_directory():
    if os.environ.get('XDG_CONFIG_HOME'):
        return Path(os.environ['XDG_CONFIG_HOME']) / 'herdr-hud'
    if IS_MAC:
        return Path.home() / 'Library/Application Support/Herdr Hud'
    return Path.home() / '.config/herdr-hud'


def cache_directory():
    if os.environ.get('XDG_CACHE_HOME'):
        return Path(os.environ['XDG_CACHE_HOME']) / 'herdr-hud'
    if IS_MAC:
        return Path.home() / 'Library/Caches/Herdr Hud'
    return Path.home() / '.cache/herdr-hud'


def relay_command(argv):
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--display-relay', *argv]
    return [sys.executable, str(Path(__file__).with_name('terminal_display.py')), *argv]


def create_desktop(app, config):
    if IS_MAC:
        from macos_desktop import MacDesktop
        return MacDesktop(app, config)
    return GnomeDesktop(app)


class GnomeDesktop:
    def __init__(self, app):
        self.app = app
        self.watch = None

    def start(self):
        from gi.repository import Gio
        self.settings = Gio.Settings.new('org.gnome.desktop.interface')
        self.settings.connect('changed::color-scheme', lambda *_: self.app.apply_theme())

    def ready(self):
        from gi.repository import Gio
        self.watch = Gio.bus_watch_name(Gio.BusType.SESSION, 'org.gnome.Shell',
            Gio.BusNameWatcherFlags.NONE, lambda *_: self.app.publish(), None)

    def prefers_dark(self):
        return self.settings.get_string('color-scheme') == 'prefer-dark'

    def call(self, method, signature='', values=()):
        from gi.repository import Gio, GLib
        def completed(connection, result):
            try:
                connection.call_finish(result)
            except GLib.Error:
                pass
        Gio.bus_get_sync(Gio.BusType.SESSION, None).call('org.gnome.Shell',
            '/org/gnome/Shell/Extensions/HerdrHud', 'org.gnome.Shell.Extensions.HerdrHud',
            method, GLib.Variant('(' + signature + ')', values), None,
            Gio.DBusCallFlags.NONE, 1000, None, completed)

    def save(self):
        pass  # GNOME owns window.json and bubble.json.

    def stop(self):
        if self.watch is not None:
            from gi.repository import Gio
            Gio.bus_unwatch_name(self.watch)
            self.watch = None

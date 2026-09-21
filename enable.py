#!/usr/bin/python3
"""Enable the bundled floating H without changing unrelated extension preferences."""
from pathlib import Path
from gi.repository import Gio, GLib
from app_info import EXTENSION_UUID

LEGACY_UUID = 'herdr-hud@local'
INTERFACE = 'org.gnome.Shell.Extensions'


def enable_extension(automatic=False):
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def call(method, params=None, interface=INTERFACE):
        return bus.call_sync('org.gnome.Shell', '/org/gnome/Shell', interface,
            method, params, None, Gio.DBusCallFlags.NONE, 3000, None).unpack()

    version = call('Get', GLib.Variant('(ss)', (INTERFACE, 'ShellVersion')),
                   'org.freedesktop.DBus.Properties')[0]
    if str(version).split('.')[0] != '50':
        return 'The floating H needs GNOME 50. You can still use the main app.'

    roots = [GLib.get_user_data_dir(), *GLib.get_system_data_dirs()]
    if not any((Path(root) / 'gnome-shell/extensions' / EXTENSION_UUID /
                'metadata.json').is_file() for root in roots):
        return 'The bundled H extension is missing. Reinstall Herdr Hud to restore it.'

    settings = Gio.Settings.new('org.gnome.shell')
    if automatic and EXTENSION_UUID in settings.get_strv('disabled-extensions'):
        return 'The floating H was turned off in Extensions. Enable it here to turn it back on.'
    enabled = [item for item in settings.get_strv('enabled-extensions') if item != LEGACY_UUID]
    if EXTENSION_UUID not in enabled:
        enabled.append(EXTENSION_UUID)
    disabled = [item for item in settings.get_strv('disabled-extensions') if item != EXTENSION_UUID]
    if LEGACY_UUID not in disabled:
        disabled.append(LEGACY_UUID)
    if not settings.set_strv('enabled-extensions', enabled):
        return 'Your desktop settings do not allow enabling the floating H.'
    if not settings.set_strv('disabled-extensions', disabled):
        return 'Your desktop settings do not allow enabling the floating H.'
    Gio.Settings.sync()
    if settings.get_boolean('disable-user-extensions'):
        return ('The floating H is ready, but desktop extensions are turned off. '
                'Turn them on in the Extensions app, then try again.')

    info = call('GetExtensionInfo', GLib.Variant('(s)', (EXTENSION_UUID,)))[0]
    if not info:
        return 'The floating H is ready. Log out and log back in once to show it.'
    call('EnableExtension', GLib.Variant('(s)', (EXTENSION_UUID,)))
    info = call('GetExtensionInfo', GLib.Variant('(s)', (EXTENSION_UUID,)))[0]
    if info.get('state') == 1:
        return 'The floating H is on. Click H to show or hide Herdr Hud.'
    if info.get('error'):
        return 'GNOME could not start the floating H: ' + str(info['error'])
    return 'The floating H is enabled. Log out and log back in once to show it.'


if __name__ == '__main__':
    try:
        print(enable_extension())
    except (GLib.Error, OSError) as exc:
        raise SystemExit('Could not enable the floating H. Open Herdr Hud in a GNOME desktop session. ' + str(exc))

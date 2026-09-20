#!/usr/bin/python3
"""Enable our extension while preserving all other extension preferences."""
from gi.repository import Gio, GLib
uuid = 'herdr-hud@alex-jax.github.io'
legacy_uuid = 'herdr-hud@local'
settings = Gio.Settings.new('org.gnome.shell')
enabled = [item for item in settings.get_strv('enabled-extensions') if item != legacy_uuid]
settings.set_strv('enabled-extensions', enabled)
if uuid not in enabled:
    settings.set_strv('enabled-extensions', enabled + [uuid])
disabled = settings.get_strv('disabled-extensions')
if legacy_uuid not in disabled:
    disabled.append(legacy_uuid)
    settings.set_strv('disabled-extensions', disabled)
if uuid in disabled:
    settings.set_strv('disabled-extensions', [item for item in disabled if item != uuid])
Gio.Settings.sync()
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
try:
    info = bus.call_sync('org.gnome.Shell', '/org/gnome/Shell', 'org.gnome.Shell.Extensions',
                         'GetExtensionInfo', GLib.Variant('(s)', (uuid,)), None,
                         Gio.DBusCallFlags.NONE, 3000, None).unpack()[0]
except GLib.Error:
    info = {}
if info:
    print('Extension registered; enabled for this desktop and future logins.')
else:
    print('Extension enabled for next login. Log out and log in once to load the floating H.')
if settings.get_boolean('disable-user-extensions'):
    print('GNOME globally disables user extensions. Turn Extensions on in the Extensions app.')

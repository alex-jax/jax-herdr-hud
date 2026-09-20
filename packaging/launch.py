"""Bootstrap the GUI, retaining an unmodified host environment for Herdr."""
import json
import hashlib
import subprocess
import os
from pathlib import Path
import runpy
import sys

root = Path(os.environ['SNAP'])
sys.path.insert(0, str(root / 'usr/lib/herdr-hud'))
from runtime_env import RUNTIME_KEYS

host = dict(os.environ)
for key in ('PYTHONHOME', 'PYTHONPATH'):
    value = host.pop('_HUD_HOST_' + key, '')
    present = host.pop('_HUD_HOST_' + key + '_SET', '')
    if present:
        host[key] = value
    else:
        host.pop(key, None)
# Classic snaps should retain host paths; repair only snap-generated defaults.
if host.get('SNAP_REAL_HOME'):
    host['HOME'] = host['SNAP_REAL_HOME']
for key, suffix in [('XDG_CONFIG_HOME', '.config'), ('XDG_DATA_HOME', '.local/share'),
                    ('XDG_STATE_HOME', '.local/state'), ('XDG_CACHE_HOME', '.cache')]:
    value = host.get(key, '')
    if value and any(value == host.get(p) or value.startswith(host.get(p, '\0') + '/')
                     for p in ('SNAP_USER_DATA', 'SNAP_USER_COMMON')):
        host[key] = str(Path(host['HOME']) / suffix)
host['PATH'] = ':'.join(p for p in host.get('PATH', os.defpath).split(':')
                        if p and p != str(root) and not p.startswith(str(root) + '/'))
os.environ['_HUD_HOST_ENV'] = json.dumps({k: host.get(k) for k in RUNTIME_KEYS})
for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
    if key in host:
        os.environ[key] = host[key]
# Python paths refer exclusively to the packaged interpreter and GI bindings.
sys.path[:] = [p for p in sys.path if p and str(Path(p).resolve()).startswith(str(root.resolve()) + '/')]
sys.path.extend([str(root / 'usr/lib/python3/dist-packages')])
lib = root / 'usr/lib/x86_64-linux-gnu'
os.environ.update(
    GI_TYPELIB_PATH=str(lib / 'girepository-1.0'),
    GSETTINGS_SCHEMA_DIR=str(root / 'usr/share/glib-2.0/schemas'),
    GIO_MODULE_DIR=str(lib / 'gio/modules'),
    GTK_EXE_PREFIX=str(root / 'usr'), GTK_DATA_PREFIX=str(root / 'usr'),
    XDG_DATA_DIRS=str(root / 'usr/share') + ':' + host.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share'))
os.environ.pop('GIO_EXTRA_MODULES', None)
os.environ.pop('GTK_PATH', None)
os.environ.pop('GTK_MODULES', None)
# GdkPixbuf's compiled-in loader cache points at /usr; create a relocatable cache
# for this exact extracted tree/snap revision, including the packaged SVG loader.
query = lib / 'gdk-pixbuf-2.0/gdk-pixbuf-query-loaders'
loaders = sorted((lib / 'gdk-pixbuf-2.0/2.10.0/loaders').glob('*.so'))
if query.exists() and loaders:
    cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'herdr-hud'
    cache.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    target = cache / ('pixbuf-' + digest + '.cache')
    if not target.exists():
        data = subprocess.check_output([str(lib / 'ld-linux-x86-64.so.2'),
            '--library-path', str(lib), str(query), *map(str, loaders)])
        temp = target.with_suffix('.' + str(os.getpid()) + '.tmp')
        temp.write_bytes(data)
        temp.replace(target)
    os.environ['GDK_PIXBUF_MODULE_FILE'] = str(target)
# The loader path loads the GUI libraries but is not inherited by Herdr's loader.
if __name__ == '__main__':
    if sys.argv[1:2] == ['--runtime-check']:
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('Vte', '2.91')
        from gi.repository import Gtk, Vte
        from app_info import VERSION
        print(json.dumps({'version': VERSION, 'python': sys.version.split()[0],
                          'gi': gi.__file__, 'gtk': Gtk.get_major_version(),
                          'vte': Vte.get_major_version()}))
    else:
        runpy.run_path(str(root / 'usr/lib/herdr-hud/hud.py'), run_name='__main__')

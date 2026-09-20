"""Separate the bundled UI runtime from host shells and Herdr processes."""
import json
import os

# Only runtime variables are recorded; credentials are never serialized.
RUNTIME_KEYS = ('PATH', 'HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME',
                'XDG_STATE_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_DIRS',
                'LD_LIBRARY_PATH', 'LD_PRELOAD', 'PYTHONHOME', 'PYTHONPATH',
                'GI_TYPELIB_PATH', 'GIO_MODULE_DIR', 'GIO_EXTRA_MODULES',
                'GSETTINGS_SCHEMA_DIR', 'GTK_PATH', 'GTK_EXE_PREFIX',
                'GTK_DATA_PREFIX', 'GTK_MODULES', 'GDK_PIXBUF_MODULE_FILE', 'GDK_PIXBUF_MODULEDIR')


def host_environment(source=None):
    env = dict(os.environ if source is None else source)
    saved = env.pop('_HUD_HOST_ENV', None)
    if saved:
        values = json.loads(saved)
        for key in RUNTIME_KEYS:
            if values.get(key) is None:
                env.pop(key, None)
            else:
                env[key] = values[key]
    for key in list(env):
        if key == 'SNAP' or key.startswith(('HERDR_', 'SNAP_', '_HUD_HOST_')):
            del env[key]
    env['TERM'] = 'xterm-256color'
    return env

"""Capture host values before PyInstaller's GI runtime hooks change them."""
import json
import os
import sys
from runtime_env import RUNTIME_KEYS

os.environ['_HUD_HOST_ENV'] = json.dumps({key: os.environ.get(key) for key in RUNTIME_KEYS})
os.environ['GDK_BACKEND'] = 'quartz'
# Use the same font rasterizer and metrics as the reference GTK/VTE build.
# CoreText's cached family list can omit process-registered bundled fonts.
os.environ['PANGOCAIRO_BACKEND'] = 'fc'
os.environ['FONTCONFIG_FILE'] = os.path.join(sys._MEIPASS, 'fonts.conf')
os.environ['FONTCONFIG_PATH'] = sys._MEIPASS

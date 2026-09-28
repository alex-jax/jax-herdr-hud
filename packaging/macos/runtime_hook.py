"""Capture host values before PyInstaller's GI runtime hooks change them."""
import json
import os
import sys
from runtime_env import RUNTIME_KEYS

os.environ['_HUD_HOST_ENV'] = json.dumps({key: os.environ.get(key) for key in RUNTIME_KEYS})
os.environ['GDK_BACKEND'] = 'quartz'
os.environ['FONTCONFIG_FILE'] = os.path.join(sys._MEIPASS, 'fonts.conf')
os.environ['FONTCONFIG_PATH'] = sys._MEIPASS

"""Test harness, never included in the companion snap."""
import os
from pathlib import Path
import runpy
import sys

root = Path(os.environ['SNAP'])
script = Path(sys.argv[1]).resolve()
runpy.run_path(str(root / 'usr/lib/herdr-hud/launch.py'), run_name='test_bootstrap')
os.environ['HUD_TEST_SOURCE'] = str(root / 'usr/lib/herdr-hud')
sys.argv = [str(script)]
runpy.run_path(str(script), run_name='__main__')

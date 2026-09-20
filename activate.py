#!/usr/bin/python3
"""Enable the extension and reopen the installed companion after an update."""
import os
from pathlib import Path
import runpy
import subprocess
import time
runpy.run_path(str(Path(__file__).with_name('enable.py')), run_name='__main__')
launcher = str(Path.home() / '.local/bin/herdr-hud')
subprocess.run([launcher, '--quit'], timeout=10, check=False)
time.sleep(0.4)
log_dir = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'herdr-hud'
log_dir.mkdir(parents=True, exist_ok=True)
with (log_dir / 'hud.log').open('ab') as log:
    subprocess.Popen([launcher], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
print('Opened the updated Herdr Hud. Existing Herdr sessions remain running.')

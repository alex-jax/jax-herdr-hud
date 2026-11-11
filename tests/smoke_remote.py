#!/usr/bin/env python3
"""Real SSH transport test against a prestarted disposable Herdr session.

Set HUD_TEST_SSH_TARGET and HUD_TEST_REMOTE_SESSION; optionally HUD_TEST_SSH_CONFIG.
Creates/closes only its own workspace and never stops the supplied server.
"""
import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
import backend

original_ssh = backend.ssh_command


def ssh(target):
    command = original_ssh(target)
    config = os.environ.get('HUD_TEST_SSH_CONFIG')
    return command[:1] + (['-F', config] if config else []) + command[1:]


backend.ssh_command = ssh
ready = threading.Event()
results = []


def changed(session, snapshot, error):
    results.append((session, snapshot, error))
    ready.set()


with tempfile.TemporaryDirectory(dir='/tmp') as directory:
    watcher = backend.RemoteWatcher(dict(label='SSH smoke',
        target=os.environ['HUD_TEST_SSH_TARGET'],
        session=os.environ['HUD_TEST_REMOTE_SESSION']), directory, changed)
    workspace = process = master = None
    watcher.start()
    try:
        assert ready.wait(20), 'No remote snapshot'
        session, snapshot, error = results[0]
        assert not error, error
        path = session['socket_path']
        workspace = backend.request(path, 'workspace.create', {'label': 'SSH smoke', 'focus': False})
        terminal = workspace['root_pane']['terminal_id']
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
        process = subprocess.Popen([sys.executable, str(SOURCE / 'terminal_display.py')] +
            backend.attach_command(session, terminal), stdin=slave, stdout=slave, stderr=slave,
            env=backend.environment(), start_new_session=True)
        os.close(slave)
        time.sleep(1)
        os.write(master, b"printf 'HUD_REMOTE_%s\\n' SUCCESS\r")
        output = b''
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if select.select([master], [], [], .2)[0]:
                output += os.read(master, 65536)
            if b'HUD_REMOTE_SUCCESS' in output:
                break
        assert b'HUD_REMOTE_SUCCESS' in output, output[-1000:]
        print('PASS: native remote terminal attach and keyboard input', flush=True)
        process.send_signal(signal.SIGHUP)
        process.wait(timeout=8)
        snapshot = backend.request(path, 'session.snapshot')['snapshot']
        assert terminal in [pane['terminal_id'] for pane in snapshot['panes']]
        print('PASS: relay detach preserves remote pane and server', flush=True)
        start = len(results)
        with watcher.process_lock:
            watcher.process.terminate()
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            updates = results[start:]
            if any(item[2] for item in updates) and updates[-1][1] is not None:
                break
            time.sleep(.1)
        else:
            raise AssertionError('Remote connection did not report failure and recover')
        assert results[-1][0]['socket_path'] == path
        assert terminal in [pane['terminal_id'] for pane in results[-1][1]['panes']]
        print('PASS: tunnel failure reconnects with the same terminal identity', flush=True)
    finally:
        try:
            if process is not None and process.poll() is None:
                process.send_signal(signal.SIGHUP)
                process.wait(timeout=8)
            if master is not None:
                os.close(master)
            if workspace:
                backend.request(session['socket_path'], 'workspace.close',
                                {'workspace_id': workspace['workspace']['workspace_id']})
        finally:
            watcher.stop()
            watcher.join(15)
            assert not watcher.is_alive()

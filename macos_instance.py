"""Per-user singleton without a session D-Bus; only show/background/quit commands."""
import fcntl
import hashlib
import os
from pathlib import Path
import socket
import tempfile
import threading
import time


class Instance:
    def __init__(self, config, dispatch):
        self.dispatch = dispatch
        self.config = Path(config)
        digest = hashlib.sha256(str(self.config.resolve()).encode()).hexdigest()[:16]
        self.directory = Path(tempfile.gettempdir()) / f'herdr-hud-{os.getuid()}-{digest}'
        self.address = str(self.directory / 'control')
        self.lock = None
        self.server = None
        self.thread = None
        self.stopped = threading.Event()

    def claim(self, command):
        if command not in ('show', 'background', 'quit'):
            raise ValueError('Unknown Hud command')
        self.directory.mkdir(mode=0o700, exist_ok=True)
        stat = self.directory.lstat()
        if self.directory.is_symlink() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
            raise RuntimeError('Hud control directory must be private to this user')
        self.lock = (self.directory / 'lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            self.lock = None
            for _ in range(50):
                try:
                    with socket.socket(socket.AF_UNIX) as client:
                        client.settimeout(1)
                        client.connect(self.address)
                        client.sendall(command.encode() + b'\n')
                        if client.recv(16) != b'ok\n':
                            raise RuntimeError('Hud did not acknowledge the command')
                        return False
                except (FileNotFoundError, ConnectionRefusedError):
                    time.sleep(.1)
            raise RuntimeError('Hud is starting but its control socket is unavailable')
        if command == 'quit':
            self.close()
            return False
        Path(self.address).unlink(missing_ok=True)
        self.server = socket.socket(socket.AF_UNIX)
        self.server.bind(self.address)
        self.server.listen(4)
        self.server.settimeout(.25)
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        return True

    def _listen(self):
        while not self.stopped.is_set():
            try:
                client, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with client:
                client.settimeout(1)
                try:
                    data = b''
                    while b'\n' not in data and len(data) <= 16:
                        chunk = client.recv(17 - len(data))
                        if not chunk:
                            break
                        data += chunk
                    if data in (b'show\n', b'background\n', b'quit\n'):
                        self.dispatch(data.decode().strip())
                        client.sendall(b'ok\n')
                except OSError:
                    pass

    def close(self):
        self.stopped.set()
        if self.server:
            self.server.close()
            if self.thread:
                self.thread.join(2)
            Path(self.address).unlink(missing_ok=True)
            self.server = None
        if self.lock:
            self.lock.close()
            self.lock = None

"""Herdr's local JSON-lines API and reconnecting session/event monitor."""
import json
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from runtime_env import host_environment

_herdr_path = None


class HerdrUnavailable(RuntimeError):
    """Actionable dependency failure; safe to display in the setup view."""


def configure_herdr(path=None):
    global _herdr_path
    _herdr_path = path or None


def resolve_herdr(path=None):
    selected = path if path is not None else _herdr_path
    if selected:
        candidate = Path(selected)
        if not candidate.is_absolute() or not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise HerdrUnavailable('Choose an absolute path to an executable Herdr file: ' + str(selected))
        return str(candidate)
    env = environment()
    candidate = Path(env.get('HOME', str(Path.home()))) / '.local/bin/herdr'
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    found = shutil.which('herdr', path=env.get('PATH', os.defpath))
    if found:
        return str(Path(found).absolute())
    raise HerdrUnavailable('Herdr was not found. Install Herdr 0.9.1 or select its executable below.')


def check_herdr(path=None):
    executable = resolve_herdr(path)
    try:
        result = subprocess.run([executable, '--version'], env=environment(),
                                capture_output=True, text=True, timeout=5, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise HerdrUnavailable('Could not run Herdr: ' + str(exc)) from exc
    version = result.stdout.strip()
    if not version.startswith('herdr '):
        raise HerdrUnavailable('The selected file did not identify itself as Herdr.')
    return executable, version


def environment():
    return host_environment()


def request(path, method, params=None):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(3)
        sock.connect(path)
        sock.sendall((json.dumps({'id': 'hud', 'method': method, 'params': params or {}}) + '\n').encode())
        with sock.makefile('rb') as stream:
            result = json.loads(stream.readline(8 * 1024 * 1024))
    if not isinstance(result, dict):
        raise RuntimeError('Unsupported Herdr protocol: expected an object reply (tested with 0.9.1).')
    if 'error' in result:
        error = result['error']
        raise RuntimeError(error.get('message', str(error)) if isinstance(error, dict) else str(error))
    if not isinstance(result.get('result'), dict):
        raise RuntimeError('Unsupported Herdr protocol: missing result object (tested with 0.9.1).')
    if method == 'session.snapshot':
        validate_snapshot(result['result'].get('snapshot'))
    return result['result']


def validate_snapshot(snapshot):
    fields = {'panes': ('pane_id', 'terminal_id', 'workspace_id', 'tab_id', 'agent_status'),
              'workspaces': ('workspace_id', 'label'), 'tabs': ('tab_id', 'label')}
    if not isinstance(snapshot, dict):
        raise RuntimeError('Unsupported Herdr snapshot (tested with 0.9.1).')
    for collection, keys in fields.items():
        rows = snapshot.get(collection)
        if not isinstance(rows, list) or any(not isinstance(row, dict) or
                any(not isinstance(row.get(key), str) for key in keys) for row in rows):
            raise RuntimeError('Unsupported Herdr snapshot: invalid ' + collection + ' (tested with 0.9.1).')


def list_sessions():
    try:
        result = subprocess.run([resolve_herdr(), 'session', 'list', '--json'], env=environment(),
                                capture_output=True, text=True, timeout=5, check=True)
        data = json.loads(result.stdout)
        sessions = data.get('sessions') if isinstance(data, dict) else None
        if not isinstance(sessions, list) or any(not isinstance(s, dict) or
                not all(isinstance(s.get(k), str) for k in ('name', 'socket_path')) or
                not isinstance(s.get('running'), bool) for s in sessions):
            raise ValueError('expected a sessions array with names, socket paths and running flags')
        return sessions
    except FileNotFoundError as exc:
        raise HerdrUnavailable('Herdr is no longer available. Select its executable again.') from exc
    except (ValueError, subprocess.SubprocessError) as exc:
        raise RuntimeError('Could not read Herdr sessions (tested with 0.9.1): ' + str(exc)) from exc


def attention(previous, current):
    if current == 'blocked' and previous != 'blocked':
        return 'Needs your input'
    if current == 'done' and previous != 'done':
        return 'Finished'
    if current == 'idle' and previous == 'working':
        return 'Finished'
    return None


class SessionWatcher(threading.Thread):
    def __init__(self, session, changed, event):
        super().__init__(daemon=True)
        self.session, self.changed, self.event = session, changed, event
        self.stopping = threading.Event()
        self.sock = None

    def stop(self):
        self.stopping.set()
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def run(self):
        while not self.stopping.is_set():
            try:
                snapshot = request(self.session['socket_path'], 'session.snapshot')['snapshot']
                self.changed(self.session, snapshot, None)
                panes = {p['pane_id'] for p in snapshot['panes']}
                with socket.socket(socket.AF_UNIX) as sock:
                    self.sock = sock
                    sock.settimeout(3)
                    sock.connect(self.session['socket_path'])
                    subs = [{'type': t} for t in ['pane.created', 'pane.closed', 'pane.updated',
                            'pane.exited', 'pane.moved', 'workspace.renamed', 'tab.renamed']]
                    subs += [{'type': 'pane.agent_status_changed', 'pane_id': p} for p in panes]
                    sock.sendall((json.dumps({'id': 'events', 'method': 'events.subscribe',
                                             'params': {'subscriptions': subs}}) + '\n').encode())
                    with sock.makefile('rb') as stream:
                        ack = json.loads(stream.readline())
                        if not isinstance(ack, dict):
                            raise RuntimeError('Unsupported Herdr subscription reply')
                        if 'error' in ack:
                            raise RuntimeError(str(ack['error']))
                        # Periodic reconnection reconciles missed events and new panes.
                        sock.settimeout(10)
                        for line in stream:
                            if self.stopping.is_set():
                                break
                            message = json.loads(line)
                            if not isinstance(message, dict) or not isinstance(message.get('data', {}), dict):
                                raise RuntimeError('Unsupported Herdr event reply')
                            if 'event' in message:
                                self.event(self.session, message)
                                snap = request(self.session['socket_path'], 'session.snapshot')['snapshot']
                                self.changed(self.session, snap, None)
                                if {p['pane_id'] for p in snap['panes']} != panes:
                                    break
            except (OSError, ValueError, RuntimeError) as exc:
                if not isinstance(exc, (TimeoutError, socket.timeout)):
                    self.changed(self.session, None, str(exc))
            finally:
                self.sock = None
            self.stopping.wait(0.5)


class Monitor(threading.Thread):
    def __init__(self, changed, event, sessions_changed):
        super().__init__(daemon=True)
        self.changed, self.event, self.sessions_changed = changed, event, sessions_changed
        self.stopping = threading.Event()
        self.watchers = {}
        self.lock = threading.Lock()

    def stop(self):
        self.stopping.set()
        with self.lock:
            for watcher in list(self.watchers.values()):
                watcher.stop()

    def run(self):
        while not self.stopping.is_set():
            try:
                sessions = list_sessions()
                if self.stopping.is_set():
                    break
                self.sessions_changed(sessions, None)
                live = {s['socket_path']: s for s in sessions if s['running']}
                with self.lock:
                    if self.stopping.is_set():
                        break
                    for path in list(self.watchers):
                        if path not in live:
                            self.watchers.pop(path).stop()
                    for path, session in live.items():
                        if path not in self.watchers:
                            watcher = SessionWatcher(session, self.changed, self.event)
                            self.watchers[path] = watcher
                            watcher.start()
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                self.sessions_changed(None, exc)
            self.stopping.wait(3)


def ensure_session(name, cwd=None, initialize=True):
    """Start a named headless server if needed; never launch Herdr's full TUI."""
    sessions = list_sessions()
    session = next((s for s in sessions if s['name'] == name and s['running']), None)
    if session is None:
        log_dir = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'herdr-hud'
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / 'server-start.log').open('ab') as log:
            process = subprocess.Popen([resolve_herdr(), '--session', name, 'server'],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=environment(),
                start_new_session=True)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            session = next((s for s in list_sessions() if s['name'] == name and s['running']), None)
            if session:
                break
            if process.poll() is not None:
                raise RuntimeError('Herdr could not start this session. Check the session name and server-start.log.')
            time.sleep(0.15)
        if not session:
            raise RuntimeError('Herdr did not become ready within 10 seconds. Try selecting the session again.')
    snapshot = request(session['socket_path'], 'session.snapshot')['snapshot']
    if initialize and not snapshot['panes']:
        request(session['socket_path'], 'workspace.create', {'cwd': cwd or str(Path.home())})
        snapshot = request(session['socket_path'], 'session.snapshot')['snapshot']
    return session, snapshot


def create_terminal(session, workspace_id, label, cwd=None):
    """Add a terminal tab to an explicitly selected session/workspace."""
    result = request(session['socket_path'], 'tab.create', {
        'workspace_id': workspace_id, 'label': label,
        'cwd': cwd or str(Path.home()), 'focus': False})
    pane = result['root_pane']
    snapshot = request(session['socket_path'], 'session.snapshot')['snapshot']
    return snapshot, pane['terminal_id']


def create_shared_workspace(label, cwd=None):
    """Create HUD sessions where an ordinary `herdr` client can see them."""
    session, _ = ensure_session('default', cwd, initialize=False)
    result = request(session['socket_path'], 'workspace.create', {
        'label': label, 'cwd': cwd or str(Path.home()), 'focus': False})
    snapshot = request(session['socket_path'], 'session.snapshot')['snapshot']
    return session, snapshot, result['root_pane']['terminal_id']

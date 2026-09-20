"""Daily, best-effort GitHub release discovery; never downloads or installs updates."""
import json
from http.client import HTTPException
import math
import re
import threading
import time
from urllib.request import Request, urlopen

INTERVAL = 24 * 60 * 60
UPDATE_GUIDE_URL = 'https://github.com/alex-jax/jax-herdr-hud/blob/'
API_URL = 'https://api.github.com/repos/alex-jax/jax-herdr-hud/releases?per_page=100'


def version_key(tag):
    """Order numeric releases and SemVer prereleases (including preview.10)."""
    if not isinstance(tag, str):
        return None
    match = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
                         r'(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?', tag)
    if not match:
        return None
    major, minor, patch, preview = match.groups()
    parts = tuple((0, int(p)) if p.isdigit() else (1, p)
                  for p in preview.split('.')) if preview else ()
    return (int(major), int(minor), int(patch), preview is None, parts)


def newer_tag(tag, current):
    candidate, installed = version_key(tag), version_key(current)
    return tag if candidate and installed and candidate > installed else None


def fetch_releases():
    request = Request(API_URL, headers={'Accept': 'application/vnd.github+json',
                      'User-Agent': 'Herdr-Hud-update-check',
                      'X-GitHub-Api-Version': '2022-11-28'})
    with urlopen(request, timeout=10) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('Release response too large')
    releases = json.loads(data)
    if not isinstance(releases, list) or any(not isinstance(r, dict) for r in releases):
        raise ValueError('Invalid release list')
    return releases


def check_updates(path, current, now=None):
    """Return (available tag, seconds until next check), persisting attempts too."""
    now = time.time() if now is None else now
    try:
        state = json.loads(path.read_text())
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    tag = newer_tag(state.get('tag'), current)
    checked = state.get('checked')
    if (isinstance(checked, (int, float)) and not isinstance(checked, bool)
            and math.isfinite(checked) and 0 <= checked <= now
            and now - checked < INTERVAL):
        return tag, max(1, math.ceil(INTERVAL - (now - checked)))

    def save():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state))
        temporary.replace(path)

    # Record the attempt before networking, so offline restarts cannot hammer GitHub.
    state['checked'] = now
    try:
        save()
        releases = fetch_releases()
        candidates = [r['tag_name'] for r in releases if not r.get('draft', False)
                      and newer_tag(r.get('tag_name'), current)]
        tag = max(candidates, key=version_key) if candidates else None
        state['tag'] = tag
        save()
    except (OSError, ValueError, HTTPException):
        pass  # Offline, API failures and unwritable preferences do not interrupt terminals.
    return tag, INTERVAL


class UpdateMonitor(threading.Thread):
    def __init__(self, path, current, changed):
        super().__init__(daemon=True)
        self.path, self.current, self.changed = path, current, changed
        self.stopping = threading.Event()

    def stop(self):
        self.stopping.set()

    def run(self):
        while not self.stopping.is_set():
            tag, delay = check_updates(self.path, self.current)
            if self.stopping.is_set():
                break
            self.changed(tag)
            self.stopping.wait(delay)

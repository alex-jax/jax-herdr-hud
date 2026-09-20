"""Quiet six-hour GitHub checks and user-initiated Debian updates."""
import hashlib
import subprocess
import tempfile
from pathlib import Path
import json
from http.client import HTTPException
import math
import re
import threading
import time
from urllib.request import Request, urlopen

INTERVAL = 6 * 60 * 60
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


def install_update(tag, progress=lambda message: None):
    """Download this project's exact release asset, verify it, then ask PolicyKit/APT.

    Called only after an Update click and off the GTK thread. No credentials are
    collected by Hud. APT/PolicyKit owns authorization and package installation.
    """
    if not version_key(tag):
        raise ValueError('Invalid release version')
    releases = fetch_releases()
    release = next((r for r in releases if r.get('tag_name') == tag and not r.get('draft')), None)
    if release is None:
        raise ValueError('This release is no longer available on GitHub.')
    version = tag.removeprefix('v')
    filename = 'jax-herdr-hud_' + version + '-1_all.deb'
    asset = next((a for a in release.get('assets', []) if a.get('name') == filename), None)
    if not asset:
        raise ValueError('This release does not contain the Ubuntu installer yet.')
    url = 'https://github.com/alex-jax/jax-herdr-hud/releases/download/' + tag + '/' + filename
    if asset.get('browser_download_url') != url:
        raise ValueError('Unexpected installer download URL.')
    size = asset.get('size')
    digest = asset.get('digest', '')
    if not isinstance(size, int) or not 0 < size <= 64 * 1024 * 1024:
        raise ValueError('Invalid installer size.')
    if not isinstance(digest, str) or not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
        raise ValueError('GitHub has not provided an installer checksum. Please update from the release page.')
    with tempfile.TemporaryDirectory(prefix='herdr-hud-update-') as directory:
        package = Path(directory) / filename
        checksum = hashlib.sha256()
        total = 0
        with urlopen(Request(url, headers={'User-Agent': 'Herdr-Hud-update'}), timeout=30) as response, package.open('wb') as output:
            while chunk := response.read(128 * 1024):
                total += len(chunk)
                if total > size:
                    raise ValueError('Installer exceeds the expected size.')
                checksum.update(chunk)
                output.write(chunk)
        if total != size or checksum.hexdigest() != digest[7:].lower():
            raise ValueError('Installer checksum verification failed; nothing was installed.')
        metadata = subprocess.run(['/usr/bin/dpkg-deb', '--show',
            '--showformat=${Package}\\n${Version}\\n${Architecture}', str(package)],
            capture_output=True, text=True, check=True, timeout=15).stdout.splitlines()
        if metadata != ['jax-herdr-hud', version + '-1', 'all']:
            raise ValueError('Installer package identity does not match the release.')
        progress('Installing update… approve the Ubuntu authentication prompt if shown.')
        result = subprocess.run(['/usr/bin/pkexec', '/usr/bin/apt-get', 'install', '--yes',
                                 str(package)], capture_output=True, text=True)
        if result.returncode:
            if result.returncode in (126, 127):
                raise RuntimeError('Installation was cancelled or authorization was unavailable.')
            raise RuntimeError('Ubuntu could not install the package. Check your network or another running package manager.')

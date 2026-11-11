#!/usr/bin/python3
"""Run under dbus-run-session with a fresh XDG_RUNTIME_DIR: GNOME Wayland resize."""
import json
import shutil
import os
from pathlib import Path
import subprocess
import tempfile
import time
import sys
from gi.repository import Gio, GLib

os.environ['GDK_BACKEND'] = 'wayland'
os.environ['WAYLAND_DISPLAY'] = 'herdr-hud-test'
tmp = tempfile.TemporaryDirectory(prefix='herdr-hud-shell-')
os.environ['XDG_CONFIG_HOME'] = tmp.name
os.environ['XDG_CACHE_HOME'] = tmp.name + '/cache'
os.environ['XDG_STATE_HOME'] = tmp.name + '/state'
os.environ['GSETTINGS_BACKEND'] = 'keyfile'
update_state = Path(tmp.name) / 'herdr-hud/updates.json'
update_state.parent.mkdir(parents=True)
update_state.write_text(json.dumps({'checked': time.time()}))
# Instrument only a temporary copy, never the user's installed extension.
source = Path(os.environ.get('HUD_TEST_SOURCE', str(Path(__file__).resolve().parents[1])))
sys.path.insert(0, str(source))
from backend import request
output_dir = Path(os.environ.get('HUD_TEST_OUTPUT', tempfile.mkdtemp(prefix='herdr-hud-shell-output-')))
output_dir.mkdir(parents=True, exist_ok=True)
extension_source = Path(os.environ.get('HUD_TEST_EXTENSION', str(source / 'extension')))
uuid = json.loads((extension_source / 'metadata.json').read_text())['uuid']
os.environ['XDG_DATA_HOME'] = tmp.name + '/data'
extension = Path(os.environ['XDG_DATA_HOME']) / ('gnome-shell/extensions/' + uuid)
shutil.copytree(extension_source, extension)
script = (extension / 'extension.js').read_text()
script = script.replace('<method name="ShowBubble"/>', '<method name="ShowBubble"/><method name="TestPointer"><arg name="kind" type="s" direction="in"/><arg name="x" type="d" direction="in"/><arg name="y" type="d" direction="in"/></method><method name="TestState"><arg name="state" type="s" direction="out"/></method>')
launch_command = json.loads(os.environ.get('HUD_TEST_LAUNCHER', json.dumps([sys.executable, str(source / 'hud.py')])))
assert isinstance(launch_command, list) and launch_command and all(isinstance(v, str) for v in launch_command)
start = script.index('    _launch(background = false) {')
end_launch = script.index('    _toggle(', start)
script = script[:start] + "    _launch(background = false) {}\n\n" + script[end_launch:]
end = script.rfind('}')
script = script[:end] + (source / 'tests/pointer_test_hooks.js').read_text() + script[end:]
(extension / 'extension.js').write_text(script)
# The child and this test use the same temporary settings backend.
settings = Gio.Settings.new('org.gnome.shell')
settings.set_strv('enabled-extensions', [uuid])
Gio.Settings.sync()
logfile = (output_dir / 'extension-test.log').open('w')
process = subprocess.Popen(['gnome-shell', '--headless', '--virtual-monitor', '1280x800',
                            '--wayland-display', 'herdr-hud-test'], stdout=logfile, stderr=subprocess.STDOUT)
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
def call(path, iface, method, params=None):
    return bus.call_sync('org.gnome.Shell', path, iface, method, params, None,
                         Gio.DBusCallFlags.NONE, 3000, None).unpack()
try:
    info = None
    for _ in range(80):
        time.sleep(0.25)
        try:
            info = call('/org/gnome/Shell', 'org.gnome.Shell.Extensions', 'GetExtensionInfo',
                        GLib.Variant('(s)', (uuid,)))[0]
            if info.get('state') == 1:
                break
            if info.get('state') == 3 and info.get('error'):
                raise AssertionError(info)
        except GLib.Error:
            pass
    assert info and info.get('state') == 1, repr(info)
    iface = 'org.gnome.Shell.Extensions.HerdrHud'
    path = '/org/gnome/Shell/Extensions/HerdrHud'
    def state():
        return json.loads(call(path, iface, 'TestState')[0])
    def pointer(kind, x=0., y=0.):
        call(path, iface, 'TestPointer', GLib.Variant('(sdd)', (kind, float(x), float(y))))
        time.sleep(0.07)

    time.sleep(3)
    subprocess.Popen(launch_command + ['--background'])
    time.sleep(1)
    pointer('init')
    actions = Gio.DBusActionGroup.get(bus, 'io.github.herdr.Hud', '/io/github/herdr/Hud')
    for _ in range(50):
        while GLib.MainContext.default().iteration(False): pass
        if 'show' in actions.list_actions(): break
        time.sleep(.1)
    assert 'show' in actions.list_actions(), actions.list_actions()
    actions.activate_action('show', None)
    for _ in range(40):
        time.sleep(.25)
        st=state()
        if st['window']: break
    assert st['window'], st
    pointer('move-window', 100, 120)
    time.sleep(1)
    rect = state()['window']
    # Move away from the hot corner before closing the startup overview.
    pointer('motion', rect['x'] + 200, rect['y'] + 200)
    time.sleep(.7)
    pointer('hide-overview')
    time.sleep(1)
    actions.activate_action('show', None)
    time.sleep(.7)
    bubble = state()
    assert bubble['window'], bubble
    pointer('motion', bubble['x'] + 28, bubble['y'] + 28)
    pointer('press')
    pointer('release')
    time.sleep(.5)
    assert not state()['window'], 'Widget click did not hide Hud'
    pointer('press')
    pointer('release')
    time.sleep(.6)
    bubble = state()
    assert bubble['window'], 'Widget click did not reopen Hud'
    pointer('press')
    pointer('motion', bubble['x'] - 60, bubble['y'] - 40)
    time.sleep(.5)
    assert state()['window'], 'Dragging widget hid Hud'
    pointer('release')
    time.sleep(.7)
    after_bubble_drag = state()
    assert after_bubble_drag['window'] and after_bubble_drag['x'] != bubble['x'], after_bubble_drag
    rect = after_bubble_drag['window']
    x, y = rect['x'] + rect['width'] + 4, rect['y'] + rect['height'] + 4
    pointer('motion', x, y)
    assert 'MetaSurfaceActorWayland' in state()['pointer']['actor'], state()
    pointer('press')
    time.sleep(.7)
    held = state()
    assert held['window'] and held['windowGrab'], held
    pointer('motion', x + 65, y + 45)
    time.sleep(.7)
    dragged = state()
    assert dragged['windowGrab'] and dragged['window'], dragged
    assert dragged['window']['width'] > rect['width'] and dragged['window']['height'] > rect['height'], dragged
    pointer('release')
    time.sleep(1)
    released = state()
    assert released['window'] and not released['windowGrab'], released
    pointer('motion', 30, 740)
    pointer('press')
    pointer('release')
    time.sleep(.8)
    after_outside = state()
    assert not after_outside['window'], f'Outside click did not hide Hud after resize: {after_outside}'
    print('PASS: GNOME Wayland corner drag resizes Hud; outside click hides it afterwards', flush=True)
finally:
    try:
        Gio.DBusActionGroup.get(bus, 'io.github.herdr.Hud', '/io/github/herdr/Hud').activate_action('exit', None)
        time.sleep(.2)
    except GLib.Error:
        pass
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    logfile.close()
    # Startup now creates a server; stop only this test's disposable instance.
    try:
        request(str(Path(tmp.name) / 'herdr/herdr.sock'), 'server.stop')
    except (OSError, ValueError, RuntimeError):
        pass
    tmp.cleanup()

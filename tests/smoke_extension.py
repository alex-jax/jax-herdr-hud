#!/usr/bin/python3
"""Run under dbus-run-session: isolated headless GNOME, real extension lifecycle."""
import json
import shutil
import os
from pathlib import Path
import subprocess
import tempfile
import time
import sys
from gi.repository import Gio, GLib

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
from enable import enable_extension
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
end_launch = script.index('    _toggle() {', start)
script = script[:start] + "    _launch(background = false) {\n        const argv = " + json.dumps(launch_command) + ";\n        if (background) argv.push('--background');\n        Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);\n    }\n\n" + script[end_launch:]
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
    call('/org/gnome/Shell', 'org.gnome.Shell.Extensions', 'DisableExtension',
         GLib.Variant('(s)', (uuid,)))
    assert 'floating H is on' in enable_extension()
    print('PASS: bundled H setup enables the extension in an isolated GNOME 50 desktop', flush=True)
    iface = 'org.gnome.Shell.Extensions.HerdrHud'
    path = '/org/gnome/Shell/Extensions/HerdrHud'
    def state():
        return json.loads(call(path, iface, 'TestState')[0])
    def pointer(kind, x=0., y=0.):
        call(path, iface, 'TestPointer', GLib.Variant('(sdd)', (kind, float(x), float(y))))
        time.sleep(0.07)
    # Let Shell finish the startup overview, which otherwise intercepts clicks.
    time.sleep(2)
    pointer('init')
    time.sleep(0.5)
    for _ in range(6):
        before = state()
        pointer('motion', before['x'] + 28, before['y'] + 28)
        pointer('press')
        assert state()['grab'], state()
        pointer('release')
        after = state()
        assert not after['grab'] and not after['stageGrab'] and not after['drag'], after
        assert after['toggles'] == before['toggles'] + 1, (before, after)
    print('PASS: six real pointer clicks each toggle once and release the desktop grab', flush=True)
    before = state()
    pointer('motion', before['x'] + 28, before['y'] + 28)
    pointer('press')
    pointer('repeat-press', before['x'] + 28, before['y'] + 28)
    pointer('motion', before['x'] - 90, before['y'] + 90)
    pointer('release')
    after = state()
    assert not after['grab'] and not after['stageGrab'], after
    assert after['toggles'] == before['toggles'] and after['x'] != before['x'], (before, after)
    print('PASS: dragging moves the bubble without toggling, repeated press cannot leak a grab', flush=True)
    pointer('motion', after['x'] + 28, after['y'] + 28)
    pointer('press')
    pointer('escape')
    assert not state()['grab'] and not state()['stageGrab'], state()
    pointer('release')
    pointer('press')
    call(path, iface, 'ExitHud')
    assert not state()['grab'] and not state()['stageGrab'], state()
    pointer('release')
    call(path, iface, 'ShowBubble')
    print('PASS: Escape and hiding the bubble release input during a press', flush=True)
    call(path, iface, 'SetStatus', GLib.Variant('(usb)', (2, 'Agent needs your input', True)))
    call(path, iface, 'ShowBubble')
    actions = Gio.DBusActionGroup.get(bus, 'io.github.herdr.Hud', '/io/github/herdr/Hud')
    for _ in range(20):
        while GLib.MainContext.default().iteration(False):
            pass
        if 'show' in actions.list_actions():
            break
        time.sleep(0.1)
    actions.activate_action('show', None)
    time.sleep(5.5)
    pointer('accent-red')
    time.sleep(.3)
    red = state()['accent']
    pointer('accent-blue')
    time.sleep(.3)
    blue = state()['accent']
    assert red != blue, (red, blue)
    print('PASS: floating outline responds to Ubuntu accent changes', flush=True)
    pointer('move-window', 110, 140)
    time.sleep(.4)
    before = state()['window']
    assert before and before['x'] == 110 and before['y'] == 140, before
    for _ in range(2):
        bubble = state()
        pointer('motion', bubble['x'] + 28, bubble['y'] + 28)
        pointer('press')
        pointer('release')
        time.sleep(.5)
    after = state()['window']
    assert after == before, (before, after)
    stored = json.loads((Path(tmp.name) / 'herdr-hud/window.json').read_text())
    assert stored == before, (stored, before)
    print('PASS: moving/resizing Hud persists exact geometry across floating-button hide/show', flush=True)
    call(path, iface, 'SetStatus', GLib.Variant('(usb)', (0, '', False)))
    call(path, iface, 'ExitHud')
    call(path, iface, 'ShowBubble')
    print('PASS: badge/theme/tooltip timer/show/exit D-Bus methods', flush=True)
    errors = call('/org/gnome/Shell', 'org.gnome.Shell.Extensions', 'GetExtensionErrors',
                  GLib.Variant('(s)', (uuid,)))[0]
    assert not errors, errors
    call('/org/gnome/Shell', 'org.gnome.Shell.Extensions', 'DisableExtension',
         GLib.Variant('(s)', (uuid,)))
    time.sleep(0.3)
    logfile.flush()
    text = (output_dir / 'extension-test.log').read_text()
    assert 'extension.js:' not in text, text
    print('PASS: companion window placement and clean extension disable', flush=True)
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

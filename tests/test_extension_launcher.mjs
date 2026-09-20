// Execute the real production launcher method with controlled filesystem/process APIs.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
const script = readFileSync(new URL('../extension/extension.js', import.meta.url), 'utf8');
const method = script.slice(script.indexOf('    _launch(background = false) {'), script.indexOf('    _toggle() {'));
function fixture(existing) {
    const spawned = [], messages = [];
    const GLib = {get_home_dir: () => '/home/test', build_filenamev: parts => parts.join('/'),
        file_test: path => existing.includes(path), FileTest: {IS_EXECUTABLE: 1}};
    const Gio = {Subprocess: {new: argv => spawned.push(argv)}, SubprocessFlags: {NONE: 0}};
    const instance = new (Function('GLib', 'Gio', `return class {${method}}`)(GLib, Gio))();
    instance._toast = message => messages.push(message);
    return {instance, spawned, messages};
}
test('prefers snap and preserves background argument', () => {
    const f = fixture(['/snap/bin/herdr-hud-alex-jax', '/home/test/.local/bin/herdr-hud']);
    f.instance._launch(true);
    assert.deepEqual(f.spawned, [['/snap/bin/herdr-hud-alex-jax', '--background']]);
});
test('falls back to source launcher without shell interpolation', () => {
    const f = fixture(['/home/test/.local/bin/herdr-hud']);
    f.instance._launch();
    assert.deepEqual(f.spawned, [['/home/test/.local/bin/herdr-hud']]);
});
test('missing companion explains installation without spawning anything', () => {
    const f = fixture([]);
    f.instance._launch();
    assert.equal(f.spawned.length, 0);
    assert.match(f.messages[0], /Install.*companion/);
});

test('starts the native Debian companion', () => {
    const f = fixture(['/usr/bin/herdr-hud']);
    f.instance._launch(true);
    assert.deepEqual(f.spawned, [['/usr/bin/herdr-hud', '--background']]);
});

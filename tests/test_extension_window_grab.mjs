// Exercise the production Mutter-grab coordination with controlled actions.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const source = readFileSync(new URL('../extension/extension.js', import.meta.url), 'utf8');
const methods = source.slice(source.indexOf('    _beginWindowGrab(window) {'), source.indexOf('    _area() {'));
const GLib = {Variant: class { constructor(_type, value) { this.value = value; } }};

function fixture() {
    const calls = [], focused = [], window = {hud: true}, other = {hud: false};
    const global = {get_window_actors: () => [{meta_window: window, visible: true}]};
    const Main = {activateWindow: value => focused.push(value)};
    const instance = new (Function('GLib', 'global', 'Main', `return class {${methods}}`)(GLib, global, Main))();
    instance._isHud = value => value?.hud === true;
    instance._running = true;
    instance._actions = {activate_action: (name, value) => calls.push([name, value?.value])};
    return {instance, window, other, calls, focused};
}

test('only Hud window grabs suspend and restore auto-hide', () => {
    const f = fixture();
    f.instance._beginWindowGrab(f.other);
    assert.deepEqual(f.calls, []);
    f.instance._beginWindowGrab(f.window);
    f.instance._beginWindowGrab(f.window);
    f.instance._endWindowGrab(f.other);
    assert.deepEqual(f.calls, [['widget-interaction', true]]);
    f.instance._endWindowGrab(f.window);
    assert.deepEqual(f.calls, [['widget-interaction', true], ['widget-interaction', false]]);
    assert.deepEqual(f.focused, [f.window]);
});

test('disable clears a live grab without activating a window', () => {
    const f = fixture();
    f.instance._beginWindowGrab(f.window);
    f.instance._finishWindowGrab(false);
    assert.equal(f.instance._windowGrab, null);
    assert.deepEqual(f.calls, [['widget-interaction', true], ['widget-interaction', false]]);
    assert.deepEqual(f.focused, []);
});

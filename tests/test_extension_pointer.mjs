// Exercise the production gesture state machine without replacing Shell input.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const source = readFileSync(new URL('../extension/extension.js', import.meta.url), 'utf8');
const methods = source.slice(source.indexOf('    _pointerEvent(event) {'), source.indexOf('    _area() {'));
const Clutter = {EventType: {BUTTON_PRESS: 1, MOTION: 2, BUTTON_RELEASE: 3, KEY_PRESS: 4},
    KEY_Escape: 27, ModifierType: {BUTTON1_MASK: 1}, EVENT_STOP: true, EVENT_PROPAGATE: false};
const GLib = {PRIORITY_DEFAULT: 0, SOURCE_REMOVE: false, SOURCE_CONTINUE: true,
    Variant: class { constructor(_type, value) { this.value = value; } },
    timeout_add: () => 1, Source: {remove() {}}};

function fixture(visible) {
    const calls = [];
    const shell = {get_window_actors: () => visible ? [{visible: true, meta_window: {minimized: false}}] : [],
        stage: {grab: () => ({dismiss() {}})}, get_pointer: () => [0, 0, 1]};
    const instance = new (Function('Clutter', 'GLib', 'global', `return class {${methods}}`)(Clutter, GLib, shell))();
    instance._running = true;
    instance._actions = {activate_action: (name, value) => calls.push([name, value?.value])};
    instance._bubble = {x: 20, y: 30, set_position(x, y) { this.x = x; this.y = y; }};
    instance._tooltip = {hide() {}};
    instance._isHud = () => true;
    instance._clamp = instance._savePosition = instance._positionWindow = () => {};
    instance._toggle = value => calls.push(['toggle', value]);
    const event = (type, x = 25, y = 35) => ({type: () => type, get_button: () => 1, get_coords: () => [x, y]});
    return {instance, calls, event};
}

for (const visible of [false, true]) {
    test(`click toggles once when Hud is ${visible ? 'open' : 'closed'}`, () => {
        const f = fixture(visible);
        f.instance._pointerEvent(f.event(1));
        f.instance._pointerEvent(f.event(3));
        assert.deepEqual(f.calls, [['widget-interaction', true], ['widget-interaction', false], ['toggle', visible]]);
    });
    test(`drag preserves ${visible ? 'open' : 'closed'} state`, () => {
        const f = fixture(visible);
        f.instance._pointerEvent(f.event(1));
        f.instance._pointerEvent(f.event(2, 80, 90));
        f.instance._pointerEvent(f.event(3, 80, 90));
        assert.deepEqual(f.calls, [['widget-interaction', true], ['widget-interaction', false],
            ...(visible ? [['show', undefined]] : [])]);
        assert.deepEqual([f.instance._bubble.x, f.instance._bubble.y], [75, 85]);
    });
}

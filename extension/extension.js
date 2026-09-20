import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import Meta from 'gi://Meta';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const IFACE = `<node><interface name="org.gnome.Shell.Extensions.HerdrHud">
<method name="SetStatus"><arg name="count" type="u" direction="in"/><arg name="message" type="s" direction="in"/><arg name="dark" type="b" direction="in"/></method>
<method name="ShowBubble"/><method name="ExitHud"/>
</interface></node>`;
const APP = 'io.github.herdr.Hud';
const PATH = '/io/github/herdr/Hud';

export default class HerdrHud extends Extension {
    enable() {
        this._sources = new Set();
        this._hidden = false;
        this._windowSignals = new Map();
        this._windowGeometryFile = Gio.File.new_for_path(GLib.build_filenamev([GLib.get_user_config_dir(), 'herdr-hud', 'window.json']));
        this._windowGeometry = null;
        try {
            const [, bytes] = this._windowGeometryFile.load_contents(null);
            const saved = JSON.parse(new TextDecoder().decode(bytes));
            if (['x', 'y', 'width', 'height'].every(key => Number.isFinite(saved[key])) && saved.width > 0 && saved.height > 0)
                this._windowGeometry = saved;
        } catch (_) { /* First launch. */ }
        this._positionFile = Gio.File.new_for_path(GLib.build_filenamev([GLib.get_user_config_dir(), 'herdr-hud', 'bubble.json']));
        this._bubble = new St.Widget({reactive: true, can_focus: true, width: 56, height: 56,
            accessible_name: 'Herdr Hud — click to open, drag to move'});
        this._button = new St.Button({label: 'H', style_class: 'herdr-bubble', width: 56, height: 56,
            reactive: false, can_focus: false});
        this._bubble.add_child(this._button);
        this._badge = new St.Widget({style_class: 'herdr-badge', width: 14, height: 14, visible: false});
        this._badge.set_position(42, 0);
        this._bubble.add_child(this._badge);
        Main.layoutManager.addChrome(this._bubble, {trackFullscreen: false});
        this._tooltip = new St.Label({style_class: 'herdr-tooltip', visible: false, reactive: false});
        Main.layoutManager.addChrome(this._tooltip, {trackFullscreen: false});
        const area = Main.layoutManager.getWorkAreaForMonitor(Main.layoutManager.primaryIndex);
        let x = area.x + area.width - 80;
        let y = area.y + Math.round(area.height / 2);
        try {
            const [, bytes] = this._positionFile.load_contents(null);
            const saved = JSON.parse(new TextDecoder().decode(bytes));
            if (Number.isFinite(saved.x) && Number.isFinite(saved.y)) {
                x = saved.x;
                y = saved.y;
            }
        } catch (_) { /* First launch. */ }
        this._bubble.set_position(x, y);
        this._clamp();
        // Grabbed events bypass the capture phase: handle them on the grab actor.
        this._bubble.connect('event', (_actor, event) => this._pointerEvent(event));
        this._bubble.connect('notify::mapped', () => {
            if (!this._bubble.mapped)
                this._endDrag();
        });
        this._bubble.connect('key-press-event', (_actor, event) => {
            if ([Clutter.KEY_Return, Clutter.KEY_space].includes(event.get_key_symbol())) {
                this._toggle();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => {
            this._clamp();
            this._positionWindow(null, true);
        });
        this._modeId = Main.sessionMode.connect('updated', () => this._syncVisibility());
        this._mapId = global.window_manager.connect('map', (_wm, actor) => {
            if (this._isHud(actor.meta_window))
                this._later(() => this._positionWindow(actor.meta_window), 100);
        });
        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE, this);
        this._dbus.export(Gio.DBus.session, '/org/gnome/Shell/Extensions/HerdrHud');
        this._actions = Gio.DBusActionGroup.get(Gio.DBus.session, APP, PATH);
        this._nameWatch = Gio.bus_watch_name(Gio.BusType.SESSION, APP, Gio.BusNameWatcherFlags.NONE,
            () => { this._running = true; }, () => { this._running = false; });
        this._syncVisibility();
        this._launch(true);
    }

    _later(callback, ms) {
        const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            this._sources.delete(id);
            callback();
            return GLib.SOURCE_REMOVE;
        });
        this._sources.add(id);
        return id;
    }

    _launch(background = false) {
        const candidates = ['/snap/bin/herdr-hud-alex-jax', '/usr/bin/herdr-hud',
            GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'herdr-hud'])];
        const launcher = candidates.find(path => GLib.file_test(path, GLib.FileTest.IS_EXECUTABLE));
        if (!launcher) {
            this._toast('Install the Herdr Hud companion from its GitHub release, then click H again.');
            return;
        }
        const argv = [launcher];
        if (background)
            argv.push('--background');
        try {
            Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);
        } catch (error) {
            console.error(`Herdr Hud: ${error.message}`);
            this._toast('Herdr Hud could not start. Open it from Applications.');
        }
    }

    _toggle() {
        if (this._running)
            this._actions.activate_action('toggle', null);
        else
            this._launch();
    }

    _pointerEvent(event) {
        const type = event.type();
        if (type === Clutter.EventType.BUTTON_PRESS)
            return this._press(event);
        const drag = this._drag;
        if (!drag)
            return Clutter.EVENT_PROPAGATE;
        if (type === Clutter.EventType.KEY_PRESS && event.get_key_symbol() === Clutter.KEY_Escape) {
            this._endDrag();
            this._clamp();
            return Clutter.EVENT_STOP;
        }
        if (type === Clutter.EventType.MOTION) {
            const [x, y] = event.get_coords();
            const dx = x - drag.x;
            const dy = y - drag.y;
            if (Math.hypot(dx, dy) > 5)
                drag.moved = true;
            if (drag.moved) {
                this._bubble.set_position(drag.bx + dx, drag.by + dy);
                this._tooltip.hide();
            }
            return Clutter.EVENT_STOP;
        }
        if (type === Clutter.EventType.BUTTON_RELEASE && event.get_button() === 1) {
            // Release input before opening/hiding any window. Dismissal can re-enter
            // event handling, so _endDrag clears its state before dismissing the grab.
            this._endDrag();
            this._clamp();
            if (drag.moved) {
                this._savePosition();
                this._positionWindow();
            } else {
                this._toggle();
            }
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    _press(event) {
        if (event.get_button() !== 1)
            return Clutter.EVENT_PROPAGATE;
        // Double/multiple presses must never overwrite a live grab.
        if (this._drag)
            return Clutter.EVENT_STOP;
        const [x, y] = event.get_coords();
        this._drag = {x, y, bx: this._bubble.x, by: this._bubble.y, moved: false};
        try {
            this._grab = global.stage.grab(this._bubble);
            // Recover even if another Shell interaction consumes the release.
            this._dragWatchId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
                const [, , modifiers] = global.get_pointer();
                if (!this._drag || !(modifiers & Clutter.ModifierType.BUTTON1_MASK)) {
                    this._dragWatchId = 0;
                    this._endDrag();
                    this._clamp();
                    return GLib.SOURCE_REMOVE;
                }
                return GLib.SOURCE_CONTINUE;
            });
        } catch (error) {
            this._endDrag();
            console.error(`Herdr Hud pointer: ${error.message}`);
        }
        return Clutter.EVENT_STOP;
    }

    _endDrag() {
        if (this._dragWatchId) {
            GLib.Source.remove(this._dragWatchId);
            this._dragWatchId = 0;
        }
        const grab = this._grab;
        this._grab = null;
        this._drag = null;
        grab?.dismiss();
    }

    _area() {
        const x = this._bubble.x + 28;
        const y = this._bubble.y + 28;
        const monitors = Main.layoutManager.monitors;
        let index = monitors.findIndex(m => x >= m.x && x < m.x + m.width && y >= m.y && y < m.y + m.height);
        if (index < 0)
            index = Main.layoutManager.primaryIndex;
        return Main.layoutManager.getWorkAreaForMonitor(index);
    }

    _clamp() {
        const area = this._area();
        this._bubble.set_position(Math.max(area.x, Math.min(this._bubble.x, area.x + area.width - 56)),
            Math.max(area.y, Math.min(this._bubble.y, area.y + area.height - 56)));
    }

    _savePosition() {
        try {
            GLib.mkdir_with_parents(this._positionFile.get_parent().get_path(), 0o700);
            this._positionFile.replace_contents(JSON.stringify({x: this._bubble.x, y: this._bubble.y}),
                null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        } catch (error) {
            console.error(`Herdr Hud position: ${error.message}`);
        }
    }

    _isHud(window) {
        return window && window.get_window_type() === Meta.WindowType.NORMAL && (window.get_gtk_application_id() === APP || window.get_wm_class() === APP);
    }

    _writeWindowGeometry() {
        if (!this._windowGeometry)
            return;
        try {
            GLib.mkdir_with_parents(this._windowGeometryFile.get_parent().get_path(), 0o700);
            this._windowGeometryFile.replace_contents(JSON.stringify(this._windowGeometry),
                null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        } catch (error) {
            console.error(`Herdr Hud geometry: ${error.message}`);
        }
    }

    _rememberWindow(window) {
        if (window.minimized || window.is_fullscreen() || window.is_maximized() || this._restoringWindow)
            return;
        const rect = window.get_frame_rect();
        if (rect.width < 100 || rect.height < 100)
            return;
        this._windowGeometry = {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
        if (this._windowSaveId) {
            GLib.Source.remove(this._windowSaveId);
            this._sources.delete(this._windowSaveId);
        }
        this._windowSaveId = this._later(() => {
            this._windowSaveId = 0;
            this._writeWindowGeometry();
        }, 150);
    }

    _trackWindow(window) {
        if (this._windowSignals.has(window))
            return;
        const ids = [
            window.connect('position-changed', () => this._rememberWindow(window)),
            window.connect('size-changed', () => this._rememberWindow(window)),
            window.connect('unmanaged', () => {
                this._writeWindowGeometry();
                const signals = this._windowSignals.get(window) ?? [];
                this._windowSignals.delete(window);
                for (const id of signals)
                    window.disconnect(id);
            }),
        ];
        this._windowSignals.set(window, ids);
    }

    _positionWindow(window = null, force = false) {
        const windows = global.get_window_actors().map(a => a.meta_window);
        if (!window)
            window = windows.find(w => this._isHud(w) && !w.minimized);
        // A hide can unmanage the Wayland window before a pending map callback runs.
        if (!window || !windows.includes(window))
            return;
        window.make_above();
        window.stick();
        if (window.is_fullscreen() || window.is_maximized()) {
            this._trackWindow(window);
            return;
        }
        // Showing an existing window or moving the bubble must not reposition it.
        if (this._windowSignals.has(window) && !force)
            return;
        const saved = this._windowGeometry;
        let area = this._area();
        if (saved) {
            const monitors = Main.layoutManager.monitors;
            let index = monitors.findIndex(m => saved.x + saved.width / 2 >= m.x &&
                saved.x + saved.width / 2 < m.x + m.width && saved.y + saved.height / 2 >= m.y &&
                saved.y + saved.height / 2 < m.y + m.height);
            if (index >= 0)
                area = Main.layoutManager.getWorkAreaForMonitor(index);
        }
        const frame = saved ?? window.get_frame_rect();
        const width = Math.min(Math.max(620, frame.width), area.width);
        const height = Math.min(Math.max(360, frame.height), area.height);
        const right = this._bubble.x < area.x + area.width / 2;
        const wantedX = saved ? saved.x : (right ? this._bubble.x + 68 : this._bubble.x - width - 12);
        const wantedY = saved ? saved.y : this._bubble.y - 30;
        const x = Math.max(area.x, Math.min(wantedX, area.x + area.width - width));
        const y = Math.max(area.y, Math.min(wantedY, area.y + area.height - height));
        this._restoringWindow = true;
        try {
            window.move_resize_frame(false, Math.round(x), Math.round(y), Math.round(width), Math.round(height));
            this._windowGeometry = {x: Math.round(x), y: Math.round(y), width: Math.round(width), height: Math.round(height)};
            this._trackWindow(window);
        } finally {
            this._restoringWindow = false;
        }
        this._writeWindowGeometry();
    }

    SetStatus(count, message, dark) {
        this._badge.visible = count > 0;
        this._bubble.accessible_name = `Herdr Hud${count ? ` — ${count} unread notifications` : ''}`;
        this._button.set_style(dark ? 'background-color: #303030; color: #ffffff;' : 'background-color: #faf9f8; color: #2c2c2c;');
        if (message)
            this._toast(message);
    }

    _toast(message) {
        if (this._hidden || Main.sessionMode.isLocked)
            return;
        if (this._toastId) {
            GLib.Source.remove(this._toastId);
            this._sources.delete(this._toastId);
        }
        this._tooltip.text = message.slice(0, 180);
        this._tooltip.show();
        const area = this._area();
        const [, width] = this._tooltip.get_preferred_width(-1);
        const [, height] = this._tooltip.get_preferred_height(width);
        this._tooltip.set_position(Math.max(area.x + 8, Math.min(this._bubble.x - width + 56, area.x + area.width - width - 8)),
            this._bubble.y >= area.y + height + 12 ? this._bubble.y - height - 10 : this._bubble.y + 66);
        this._toastId = this._later(() => { this._tooltip.hide(); this._toastId = 0; }, 5000);
    }

    _syncVisibility() {
        this._bubble.visible = !this._hidden && !Main.sessionMode.isLocked && !Main.sessionMode.isGreeter;
        if (!this._bubble.visible) {
            this._endDrag();
            this._tooltip.hide();
        }
    }

    ShowBubble() {
        this._hidden = false;
        this._syncVisibility();
        this._later(() => {
            this._positionWindow();
            const window = global.get_window_actors().map(a => a.meta_window).find(w => this._isHud(w));
            if (window)
                Main.activateWindow(window);
        }, 150);
    }

    ExitHud() {
        this._hidden = true;
        this._syncVisibility();
    }

    disable() {
        this._endDrag();
        this._writeWindowGeometry();
        for (const [window, ids] of this._windowSignals) {
            for (const id of ids)
                window.disconnect(id);
        }
        this._windowSignals.clear();
        for (const id of this._sources)
            GLib.Source.remove(id);
        this._sources.clear();
        if (this._running)
            this._actions.activate_action('exit', null);
        Gio.bus_unwatch_name(this._nameWatch);
        Main.layoutManager.disconnect(this._monitorsId);
        Main.sessionMode.disconnect(this._modeId);
        global.window_manager.disconnect(this._mapId);
        this._dbus.unexport();
        this._bubble.destroy();
        this._tooltip.destroy();
        this._bubble = null;
        this._tooltip = null;
        this._actions = null;
        this._toastId = 0;
    }
}

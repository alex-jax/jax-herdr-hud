    TestPointer(kind, x, y) {
        if (!this._testPointer) {
            Main.overview.hide();
            const seat = global.stage.get_context().get_backend().get_default_seat();
            this._testPointer = seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
            this._testKeyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
            const toggle = this._toggle.bind(this);
            this._toggle = () => { this._testToggleCount = (this._testToggleCount ?? 0) + 1; toggle(); };
        }
        if (kind.startsWith('accent-')) {
            const settings = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
            settings.set_string('accent-color', kind.slice(7));
        }
        if (kind === 'move-window') {
            const window = global.get_window_actors().map(a => a.meta_window).find(w => this._isHud(w));
            window?.move_resize_frame(false, x, y, 800, 520);
        }
        const now = GLib.get_monotonic_time();
        if (kind === 'motion')
            this._testPointer.notify_absolute_motion(now, x, y);
        if (kind === 'press')
            this._testPointer.notify_button(now, 1, Clutter.ButtonState.PRESSED);
        if (kind === 'release')
            this._testPointer.notify_button(now, 1, Clutter.ButtonState.RELEASED);
        if (kind === 'escape') {
            this._testKeyboard.notify_keyval(now, Clutter.KEY_Escape, Clutter.KeyState.PRESSED);
            this._testKeyboard.notify_keyval(now + 1000, Clutter.KEY_Escape, Clutter.KeyState.RELEASED);
        }
        if (kind === 'repeat-press')
            this._press({get_button: () => 1, get_coords: () => [x, y]});
    }

    TestState() {
        const window = global.get_window_actors().map(a => a.meta_window).find(w => this._isHud(w));
        const rect = window?.get_frame_rect();
        return JSON.stringify({drag: !!this._drag, grab: !!this._grab,
            stageGrab: global.stage.get_grab_actor() === this._bubble,
            x: this._bubble.x, y: this._bubble.y,
            toggles: this._testToggleCount ?? 0, tooltip: this._tooltip.visible,
            accent: this._button.get_theme_node().get_border_color(0).to_string(),
            savedWindow: this._windowGeometry,
            window: rect ? {x: rect.x, y: rect.y, width: rect.width, height: rect.height} : null});
    }

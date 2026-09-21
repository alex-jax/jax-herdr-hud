#!/usr/bin/python3
"""Herdr Hud — native terminal companion for the GNOME floating H."""
import json
import os
from pathlib import Path
import signal
import threading
import sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Gio, GLib, Pango, Vte
from backend import (Monitor, attention, environment, ensure_session, create_terminal,
                     create_shared_workspace, request, resolve_herdr, configure_herdr,
                     check_herdr, HerdrUnavailable)
from enable import enable_extension
from updates import UpdateMonitor, install_update
from terminal_themes import palettes, palette
from theme_picker import ThemePicker
from app_info import RELEASE_TAG, VERSION, ATTRIBUTION, AUTHOR_URL, UPSTREAM_URL, HERDR_URL

APP_ID = 'io.github.herdr.Hud'
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'herdr-hud'
SHELL_PATH = '/org/gnome/Shell/Extensions/HerdrHud'
SHELL_IFACE = 'org.gnome.Shell.Extensions.HerdrHud'


def idle(fn, *args):
    def invoke():
        fn(*args)
        return GLib.SOURCE_REMOVE
    GLib.idle_add(invoke)


def rgba(value):
    color = Gdk.RGBA()
    color.parse(value)
    return color


class Terminal(Vte.Terminal):
    """Use native VTE mouse reporting, selection-to-copy and right-click paste."""
    def __init__(self):
        super().__init__()
        self.pid = None
        self.alive = False
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(8)
        self.set_margin_bottom(12)
        self.set_scrollback_lines(20000)
        self.set_font(Pango.FontDescription('Ubuntu Mono 12'))
        self.set_audible_bell(False)
        self.set_mouse_autohide(True)
        self.set_scroll_on_keystroke(True)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.connect('selection-changed', self.copy_selection)
        self.connect('child-exited', self.exited)

    def copy_selection(self, *_):
        if self.get_has_selection():
            self.copy_clipboard_format(Vte.Format.TEXT)

    def do_button_press_event(self, event):
        if event.button == 3:
            self.grab_focus()
            self.paste_clipboard()
            return True
        return Vte.Terminal.do_button_press_event(self, event)

    def do_button_release_event(self, event):
        if event.button == 3:
            return True
        return Vte.Terminal.do_button_release_event(self, event)

    def exited(self, *_):
        self.alive = False
        self.pid = None
        self.feed(b'\r\n\x1b[90mDisconnected. Select this terminal again to reconnect.\x1b[0m\r\n')

    def launch(self, argv):
        self.alive = True
        env = [f'{key}={value}' for key, value in environment().items()]
        argv = [sys.executable, str(Path(__file__).with_name("terminal_display.py")), *argv]
        self.spawn_async(Vte.PtyFlags.DEFAULT, str(Path.home()), argv, env,
                         GLib.SpawnFlags.DEFAULT, None, None, -1, None, self.spawned, None)

    def spawned(self, terminal, pid, error, *_):
        if error:
            self.alive = False
            self.feed(('\r\nCould not attach: ' + str(error) + '\r\n').encode())
        else:
            self.pid = pid

    def detach(self):
        # The display relay forwards SIGHUP only to its direct-attach client.
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
            self.pid = None


class Hud(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.terminals = {}
        self.panes = {}
        self.snapshots = {}
        self.states = {}
        self.unread = {}
        self.sessions = []
        self.creating_session = False
        self.selected = None
        self.initial_selection_pending = True
        self.checked_initial_spaces = set()
        self.rebuilding = False
        self.sidebar_refresh_id = 0
        self.sidebar_rows = {}
        self.selected_workspace = None
        self.workspace_selection = {}
        self.collapsed_spaces = set()
        self.closing = False
        self.theme = 'dark'
        self.session_errors = {}
        self.adding_terminals = set()
        try:
            self.settings = json.loads((CONFIG / 'settings.json').read_text())
            if not isinstance(self.settings, dict):
                self.settings = {}
        except (OSError, ValueError):
            self.settings = {}
        configure_herdr(self.settings.get('herdr_path'))
        self.extension_pending = False
        self.auto_h_checked = False
        self.setup_pending = False
        self.update_tag = None
        self.theme = self.settings.get('theme', 'dark')
        self.theme_picker = None
        self.settings.setdefault('terminal_palette', 'gnome')
        if (not isinstance(self.settings['terminal_palette'], str) or
                self.settings['terminal_palette'] not in {'hud', *palettes()}):
            self.settings['terminal_palette'] = 'gnome'
        self.sidebar_expanded_width = max(32, self.settings.get('sidebar_expanded_width',
            self.settings.get('sidebar_width', 245) or 245))

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()
        for name, callback in [('toggle', self.toggle), ('exit', self.exit_hud), ('show', self.show)]:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', lambda action, value, cb=callback: cb())
            self.add_action(action)
        self.system_settings = Gio.Settings.new('org.gnome.desktop.interface')
        self.system_settings.connect('changed::color-scheme', lambda *_: self.apply_theme())
        self.build_window()
        self.monitor = Monitor(lambda *a: idle(self.snapshot_changed, *a),
                               lambda *a: idle(self.event_received, *a),
                               lambda *a: idle(self.sessions_changed, *a))
        self.monitor.start()
        self.update_monitor = UpdateMonitor(CONFIG / 'updates.json', RELEASE_TAG,
            lambda tag: idle(self.update_available, tag))
        self.update_monitor.start()
        self.shell_watch = Gio.bus_watch_name(Gio.BusType.SESSION, 'org.gnome.Shell',
                             Gio.BusNameWatcherFlags.NONE, lambda *_: self.publish(), None)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if '--quit' in args:
            self.exit_hud()
        else:
            self.auto_enable_floating_h()
            if '--background' not in args:
                self.show()
        self.publish()
        return 0

    def update_available(self, tag):
        if self.closing or getattr(self, 'update_pending', False):
            return
        if tag == getattr(self, 'installed_update', None):
            tag = None
        self.update_tag = tag
        self.update_button.set_visible(bool(tag))
        if tag:
            label = 'Herdr Hud ' + tag.removeprefix('v') + ' is available — click to download and install'
            self.update_button.set_tooltip_text(label)
            self.update_button.get_accessible().set_name(label)

    def open_update(self):
        if not self.update_tag or getattr(self, 'update_pending', False):
            return
        tag = self.update_tag
        self.update_pending = True
        self.update_button.set_sensitive(False)
        self.status.set_text('Downloading Herdr Hud ' + tag.removeprefix('v') + '…')
        def work():
            try:
                install_update(tag, lambda message: idle(self.update_progress, message))
            except Exception as exc:
                idle(self.update_finished, str(exc))
            else:
                idle(self.update_finished, None)
        threading.Thread(target=work, daemon=True).start()

    def update_progress(self, message):
        if not self.closing:
            self.status.set_text(message)

    def update_finished(self, error):
        self.update_pending = False
        if self.closing:
            return
        self.update_button.set_sensitive(True)
        if error:
            self.status.set_text('Update not installed: ' + error + ' Click the update arrow to retry.')
        else:
            self.installed_update = self.update_tag
            self.update_button.hide()
            self.update_tag = None
            self.status.set_text('Update installed. Restart Herdr Hud from Applications to use it. Your sessions keep running.')

    def show_about(self):
        dialog = Gtk.AboutDialog(transient_for=self.window, modal=True,
            program_name='Herdr Hud', version=VERSION,
            comments=ATTRIBUTION + '\nIndependent Ubuntu companion for Herdr.\nColor schemes from Ptyxis by Christian Hergert and contributors.',
            website=AUTHOR_URL, website_label='Alex Jax on GitHub',
            authors=['Alex Jax', 'Original Herdr HUD: Alex Finn — ' + UPSTREAM_URL,
                     'Ptyxis color schemes: Christian Hergert and contributors — https://gitlab.gnome.org/chergert/ptyxis'],
            copyright='Copyright © 2026 Alex Jax; upstream portions © 2026 Alex Finn',
            license_type=Gtk.License.GPL_3_0, wrap_license=True)
        dialog.run()
        dialog.destroy()

    def show_setup(self, message=None):
        self.setup_message.set_text(message or 'Use your existing Herdr installation. Tested with Herdr 0.9.1.')
        self.herdr_entry.set_text(self.settings.get('herdr_path') or '')
        self.stack.set_visible_child_name('setup')
        self.active_title.set_text('Settings')

    def auto_enable_floating_h(self):
        if self.auto_h_checked or self.closing:
            return
        self.auto_h_checked = True
        self.enable_floating_h(automatic=True)

    def enable_floating_h(self, automatic=False):
        if self.extension_pending or self.closing:
            return
        self.extension_pending = True
        self.extension_button.set_sensitive(False)
        self.extension_message.set_text('Turning on the floating H…')
        def work():
            try:
                message = enable_extension(automatic=True) if automatic else enable_extension()
            except (GLib.Error, OSError) as exc:
                message = 'Could not change the floating H. Open Hud in a GNOME desktop session. ' + str(exc)
            idle(self.extension_enabled, message)
        threading.Thread(target=work, daemon=True).start()

    def extension_enabled(self, message):
        self.extension_pending = False
        if self.closing:
            return
        self.extension_button.set_sensitive(True)
        self.extension_message.set_text(message)

    def choose_herdr(self):
        dialog = Gtk.FileChooserDialog(title='Choose Herdr executable', transient_for=self.window,
                                      action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Select', Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            self.herdr_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def retry_herdr(self):
        if self.setup_pending:
            return
        candidate = self.herdr_entry.get_text().strip()
        self.setup_pending = True
        self.retry_button.set_sensitive(False)
        self.setup_message.set_text('Checking Herdr…')
        def work():
            try:
                # Empty text explicitly requests automatic discovery, not the old setting.
                executable, version = check_herdr(candidate)
                idle(self.herdr_checked, candidate, version, None)
            except (OSError, ValueError, RuntimeError) as exc:
                idle(self.herdr_checked, candidate, None, str(exc))
        threading.Thread(target=work, daemon=True).start()

    def herdr_checked(self, candidate, version, error):
        self.setup_pending = False
        if self.closing:
            return
        self.retry_button.set_sensitive(True)
        if error:
            self.setup_message.set_text(error)
            return
        configure_herdr(candidate)
        self.settings['herdr_path'] = candidate
        self.save()
        self.status.set_text(version + (' — tested version' if version == 'herdr 0.9.1'
                                       else ' — compatibility tested with 0.9.1'))
        self.setup_message.set_text('Connected to ' + version)
        self.leave_setup()

    def leave_setup(self):
        if self.selected in self.terminals:
            self.stack.set_visible_child(self.terminals[self.selected])
        else:
            self.stack.set_visible_child_name('empty')
        self.active_title.set_text('Herdr Hud')
        idle(self.focus_selected_terminal)

    def shell_call(self, method, signature='', values=()):
        if self.closing and method != 'ExitHud':
            return
        def completed(connection, result):
            try:
                connection.call_finish(result)
            except GLib.Error:
                pass  # Companion remains usable before the next GNOME login.
        Gio.bus_get_sync(Gio.BusType.SESSION, None).call('org.gnome.Shell', SHELL_PATH,
            SHELL_IFACE, method, GLib.Variant('(' + signature + ')', values), None,
            Gio.DBusCallFlags.NONE, 1000, None, completed)

    def publish(self, message=''):
        self.shell_call('SetStatus', 'usb', (len(self.unread), message, self.dark))

    def build_window(self):
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title('Herdr Hud')
        self.window.set_wmclass('herdr-hud', self.get_application_id())
        self.window.set_icon_name(APP_ID)
        self.window.set_default_size(self.settings.get('width', 1040), self.settings.get('height', 660))
        self.window.set_size_request(620, 360)
        self.window.connect('delete-event', lambda *_: self.hide())
        self.window.connect('focus-in-event', lambda *_: self.acknowledge())
        self.window.connect('window-state-event', self.window_state_changed)
        header = Gtk.HeaderBar(title='Herdr Hud', subtitle='Your terminals, within reach')
        header.set_show_close_button(False)
        self.window.set_titlebar(header)
        credits = self.icon_button('help-about-symbolic', 'About Herdr Hud', self.show_about)
        credits.set_valign(Gtk.Align.CENTER)
        credits.set_tooltip_text(ATTRIBUTION)
        credits.get_accessible().set_name('Credits')
        header.pack_start(credits)
        self.update_button = self.icon_button('go-down-symbolic',
            'Download and install update', self.open_update)
        self.update_button.set_no_show_all(True)
        self.update_button.get_style_context().add_class('suggested-action')
        header.pack_start(self.update_button)
        header.pack_start(self.icon_button('preferences-system-symbolic', 'Settings: appearance, Herdr and floating H', self.show_setup))
        self.theme_button = self.icon_button('weather-clear-night-symbolic', 'Switch theme', self.toggle_theme)
        header.pack_end(self.icon_button('system-shutdown-symbolic', 'Exit Hud — keep sessions running', self.exit_hud))
        header.pack_end(self.theme_button)
        self.expand_button = self.icon_button('view-fullscreen-symbolic',
            'Expand HUD', self.toggle_expanded)
        header.pack_end(self.expand_button)
        header.pack_end(self.icon_button('window-minimize-symbolic', 'Hide Hud', self.hide))
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(outer)
        self.split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.split.set_wide_handle(True)
        self.split.set_position(self.settings.get('sidebar_width', 245))
        self.split_overlay = Gtk.Overlay()
        self.split_overlay.add(self.split)
        outer.pack_start(self.split_overlay, True, True, 0)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar.set_name('sidebar')
        sidebar.set_size_request(180, -1)
        sidebar.set_border_width(4)
        self.search = Gtk.SearchEntry(placeholder_text='Find a terminal or agent…')
        self.search.set_margin_start(12)
        self.search.set_margin_end(12)
        self.search.set_margin_top(12)
        self.search.connect('search-changed', lambda *_: self.rebuild_sidebar())
        sidebar.pack_start(self.search, False, False, 0)
        self.sections = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.sections.set_wide_handle(True)
        self.section_position = self.settings.get('section_position', 260)
        self.restoring_sections = False
        self.sections.set_position(self.section_position)
        self.sections.connect('notify::position', self.section_position_changed)
        self.rows = self.make_sidebar_list()
        self.agent_rows = self.make_sidebar_list()
        self.space_section = self.make_sidebar_section('SPACES', self.rows,
            self.settings.get('spaces_expanded', True))
        self.agent_section = self.make_sidebar_section('AGENTS', self.agent_rows,
            self.settings.get('agents_expanded', True))
        empty_agents = Gtk.Label(label='No agents running', margin=12)
        self.empty_agents = empty_agents
        empty_agents.get_style_context().add_class('dim-label')
        empty_agents.show()
        self.agent_rows.set_placeholder(empty_agents)
        self.sections.pack1(self.space_section, True, False)
        self.sections.pack2(self.agent_section, True, False)
        self.space_section.connect('notify::expanded', self.section_expanded)
        self.agent_section.connect('notify::expanded', self.section_expanded)
        sidebar.pack_start(self.sections, True, True, 0)
        idle(self.restore_section_position)
        create = Gtk.Button(label='+  New space')
        create.set_margin_start(12)
        create.set_margin_end(12)
        create.set_margin_bottom(12)
        create.connect('clicked', lambda *_: self.new_session())
        sidebar.pack_start(create, False, False, 0)
        self.split.pack1(sidebar, False, True)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.active_title = Gtk.Label(label='Welcome to Herdr Hud', xalign=0)
        self.active_title.set_margin_start(16)
        self.active_title.set_margin_top(12)
        self.active_title.set_margin_bottom(12)
        right.pack_start(self.active_title, False, False, 0)
        self.stack = Gtk.Stack()
        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        empty.set_valign(Gtk.Align.CENTER)
        empty.set_halign(Gtk.Align.CENTER)
        empty.pack_start(Gtk.Image.new_from_icon_name('utilities-terminal-symbolic', Gtk.IconSize.DIALOG), False, False, 0)
        empty.pack_start(Gtk.Label(label='Your agents. One place.'), False, False, 0)
        empty.pack_start(Gtk.Label(label='Choose a space on the left, or start a new one.'), False, False, 0)
        button = Gtk.Button(label='Start a space')
        button.connect('clicked', lambda *_: self.new_session())
        empty.pack_start(button, False, False, 0)
        self.stack.add_named(empty, 'empty')
        self.stack.add_named(Gtk.Label(label='Opening your terminal…'), 'loading')
        setup = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=18)
        setup.set_name('settings-panel')
        setup.set_valign(Gtk.Align.START)
        def section(title):
            frame = Gtk.Frame(label=title)
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)
            frame.add(content)
            setup.pack_start(frame, False, False, 0)
            return content
        appearance = section('Appearance')
        self.appearance_button = Gtk.Button(label='Choose theme…')
        self.appearance_button.set_halign(Gtk.Align.START)
        self.appearance_button.connect('clicked', lambda *_: self.show_appearance())
        appearance.pack_start(self.appearance_button, False, False, 0)
        floating = section('Floating H')
        self.extension_message = Gtk.Label(
            label='Enabled automatically. Log out and back in after installation or an extension update.',
            wrap=True, xalign=0)
        self.extension_message.set_max_width_chars(55)
        floating.pack_start(self.extension_message, False, False, 0)
        self.extension_button = Gtk.Button(label='Enable floating H')
        self.extension_button.set_halign(Gtk.Align.START)
        self.extension_button.connect('clicked', lambda *_: self.enable_floating_h())
        floating.pack_start(self.extension_button, False, False, 0)
        herdr = section('Herdr connection')
        self.setup_message = Gtk.Label(label='Use your existing Herdr installation.', wrap=True, xalign=0)
        self.setup_message.set_max_width_chars(55)
        herdr.pack_start(self.setup_message, False, False, 0)
        self.herdr_entry = Gtk.Entry(placeholder_text='Automatic, or choose the Herdr executable')
        self.herdr_entry.set_text(self.settings.get('herdr_path') or '')
        self.herdr_entry.connect('activate', lambda *_: self.retry_herdr())
        herdr.pack_start(self.herdr_entry, False, False, 0)
        controls = Gtk.Box(spacing=6)
        for label, callback in [('Browse…', self.choose_herdr), ('Retry', self.retry_herdr)]:
            control = Gtk.Button(label=label)
            control.connect('clicked', lambda _, cb=callback: cb())
            controls.pack_start(control, False, False, 0)
            if label == 'Retry':
                self.retry_button = control
        install_link = Gtk.LinkButton(uri=HERDR_URL, label='Install Herdr')
        controls.pack_start(install_link, False, False, 0)
        herdr.pack_start(controls, False, False, 0)
        back = Gtk.Button(label='Back to terminals')
        back.set_halign(Gtk.Align.START)
        back.connect('clicked', lambda *_: self.leave_setup())
        setup.pack_start(back, False, False, 0)
        setup_scroll = Gtk.ScrolledWindow()
        setup_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        setup_scroll.add(setup)
        self.stack.add_named(setup_scroll, 'setup')
        right.pack_start(self.stack, True, True, 0)
        self.split.pack2(right, True, True)
        self.sidebar_toggle = self.icon_button('pan-start-symbolic', 'Collapse sidebar', self.toggle_sidebar)
        self.sidebar_toggle.set_name('sidebar-toggle')
        self.sidebar_toggle.set_size_request(24, 26)
        self.split_overlay.add_overlay(self.sidebar_toggle)
        self.divider_grip = Gtk.Box()
        self.divider_grip.set_name('divider-grip')
        self.divider_grip.set_size_request(3, 28)
        self.split_overlay.add_overlay(self.divider_grip)
        self.split_overlay.set_overlay_pass_through(self.divider_grip, True)
        self.split_overlay.connect('get-child-position', self.position_divider_control)
        self.split.connect('notify::position', self.sidebar_position_changed)
        self.sidebar_position_changed()
        self.status = Gtk.Label(label='Shift+drag to copy  ·  Click CLI controls  ·  Right-click to paste', xalign=0)
        self.status.set_margin_start(14)
        self.status.set_margin_top(7)
        self.status.set_margin_bottom(7)
        self.status.get_style_context().add_class('dim-label')
        outer.pack_end(self.status, False, False, 0)
        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.css,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.apply_theme()
        outer.show_all()
        header.show_all()

    def position_divider_control(self, overlay, child, allocation):
        width, height = (24, 26) if child == self.sidebar_toggle else (3, 28)
        allocation.x = max(0, min(self.split.get_position() + 3 - width // 2,
                                  overlay.get_allocated_width() - width))
        allocation.y = 4 if child == self.sidebar_toggle else max(34, (overlay.get_allocated_height() - height) // 2)
        allocation.width, allocation.height = width, height
        return True

    def sidebar_position_changed(self, *_):
        position = self.split.get_position()
        if position > 0:
            self.sidebar_expanded_width = position
        collapsed = position == 0
        # The overlay toggle is clamped to the left edge when the split closes.
        self.active_title.set_margin_start(max(16, 40 - position))
        self.sidebar_toggle.set_image(Gtk.Image.new_from_icon_name(
            'pan-end-symbolic' if collapsed else 'pan-start-symbolic', Gtk.IconSize.MENU))
        self.sidebar_toggle.set_tooltip_text('Expand sidebar' if collapsed else 'Collapse sidebar')
        self.split_overlay.queue_allocate()

    def toggle_sidebar(self):
        if self.split.get_position() > 0:
            self.sidebar_expanded_width = self.split.get_position()
            self.split.set_position(0)
        else:
            self.split.set_position(min(self.sidebar_expanded_width, self.split.get_property('max-position')))
        self.save()
        idle(self.focus_selected_terminal)

    def focus_selected_terminal(self):
        terminal = self.terminals.get(self.selected)
        if not self.closing and self.window.get_visible() and terminal and self.stack.get_visible_child() == terminal:
            terminal.grab_focus()

    def make_sidebar_list(self):
        rows = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        rows.set_margin_start(12)
        rows.set_margin_end(12)
        rows.set_sort_func(lambda a, b: (a.order > b.order) - (a.order < b.order))
        rows.connect('row-selected', self.row_selected)
        rows.set_activate_on_single_click(True)
        rows.connect('row-activated', self.row_activated)
        rows.connect('button-press-event', self.sidebar_button_press)
        return rows

    def make_sidebar_section(self, name, rows, expanded):
        section = Gtk.Expander(label=name, expanded=expanded)
        section.get_label_widget().get_style_context().add_class('section-title')
        section.set_margin_top(8)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(0)
        scroll.add(rows)
        section.add(scroll)
        return section

    def section_position_changed(self, *_):
        if (not self.restoring_sections and hasattr(self, 'agent_section') and self.space_section.get_expanded()
                and self.agent_section.get_expanded()):
            self.section_position = self.sections.get_position()

    def section_expanded(self, *_):
        self.restoring_sections = True
        idle(self.restore_section_position)

    def restore_section_position(self):
        if not self.space_section.get_expanded():
            self.sections.set_position(32)
        elif not self.agent_section.get_expanded():
            self.sections.set_position(max(32, self.sections.get_allocated_height() - 38))
        else:
            self.sections.set_position(self.section_position)
        self.restoring_sections = False

    def icon_button(self, icon, tooltip, callback):
        button = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        button.set_tooltip_text(tooltip)
        button.connect('clicked', lambda *_: callback())
        return button

    def show_appearance(self):
        if self.theme_picker is None:
            self.theme_picker = ThemePicker(self)
            self.theme_picker.connect('destroy', lambda *_: setattr(self, 'theme_picker', None))
        self.theme_picker.present()

    def apply_theme(self):
        self.dark = self.theme == 'dark' or (self.theme == 'system' and
                     self.system_settings.get_string('color-scheme') == 'prefer-dark')
        fg, bg, ansi = self.terminal_colors()
        def blend(first, second, amount):
            a, b = rgba(first), rgba(second)
            return '#{:02x}{:02x}{:02x}'.format(*[
                round((x * (1 - amount) + y * amount) * 255)
                for x, y in zip((a.red, a.green, a.blue), (b.red, b.green, b.blue))])
        side, line = blend(bg, fg, .055), blend(bg, fg, .22)
        hover, selected = blend(bg, fg, .12), blend(bg, ansi[4], .35)
        accent = ansi[12] if self.dark else ansi[4]
        background = rgba(bg)
        Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',
            .2126 * background.red + .7152 * background.green + .0722 * background.blue < .5)
        self.css.load_from_data(f'''
            window, dialog, messagedialog, .background, stack, viewport, scrolledwindow {{ background: {bg}; color: {fg}; }}
            headerbar, toolbar, menu, popover {{ background-image: none; background-color: {side}; color: {fg}; border-color: {line}; }}
            button, entry, searchentry, combobox, spinbutton {{ background-image: none; background-color: {side}; color: {fg}; border-color: {line}; box-shadow: none; text-shadow: none; }}
            button:hover, menuitem:hover {{ background-image: none; background-color: {hover}; color: {fg}; }}
            button:active, button:checked, menuitem:selected {{ background-image: none; background-color: {selected}; color: {fg}; }}
            entry selection, textview text selection {{ background: {selected}; color: {fg}; }}
            check, radio {{ background-image: none; background-color: {side}; color: {fg}; border-color: {line}; }}
            check:checked, radio:checked {{ background-color: {selected}; color: {fg}; }}
            scrollbar, scrollbar trough {{ background: {bg}; }}
            scrollbar slider {{ background: {line}; }}
            separator {{ background: {line}; }}
            *:focus {{ outline-color: {accent}; }}
            button:disabled {{ color: {line}; }}
            label:link, link {{ color: {accent}; }}
            #sidebar {{ background: {side}; }}
            #sidebar button {{ padding: 8px 12px; }}
            #sidebar button.rename-button {{ padding: 2px; min-width: 16px; min-height: 16px;
                background: transparent; border: 1px solid {line}; border-radius: 5px; box-shadow: none; opacity: 0;
                color: {fg}; }}
            #sidebar row:hover button.rename-button {{ opacity: 1; }}
            #sidebar label.activity-dot.active {{ color: {'#f6d365' if self.dark else '#b58100'}; }}
            #sidebar label.activity-dot.working {{ color: {'#8bd17c' if self.dark else '#287a27'}; }}
            list, row {{ background: transparent; }}
            row {{ border-radius: 0; padding: 10px 8px; margin: 0; }}
            row:selected {{ background: {selected}; color: {fg}; }}
            #sidebar row.terminal-row {{ border: none; }}
            #sidebar row {{ padding: 3px 6px; min-height: 24px; }}
            #sidebar row.space-row {{ margin-top: 8px; padding: 4px 6px; }}
            #sidebar row.shell-row {{ border-left: 1px solid {line}; padding-left: 10px; }}
            #sidebar row.agent-row {{ padding: 5px 6px; }}
            #sidebar button.space-toggle {{ padding: 0; min-width: 16px; min-height: 16px; }}
            #sidebar button.space-add {{ padding: 2px 5px; min-width: 18px; min-height: 18px; }}
            #space-divider {{ background: {line}; min-height: 1px; }}
            .section-title {{ font-size: 10px; font-weight: bold; letter-spacing: 1px; }}
            .dim-label {{ opacity: 0.7; font-size: 11px; }}
            .group-label {{ font-weight: bold; font-size: 12px; }}
            paned > separator {{ background: {line}; min-width: 6px; }}
            paned > separator:hover {{ background: {fg}; }}
            #divider-grip {{ background: {line}; border-radius: 2px; min-width: 3px; min-height: 28px; }}
            #sidebar-toggle {{ padding: 2px; min-width: 20px; min-height: 22px; border-radius: 4px; }}
            headerbar {{ min-height: 42px; }}
            #settings-panel button {{ padding: 4px 10px; min-height: 22px; min-width: 0; }}
            #settings-panel frame > border {{ border: 1px solid {line}; border-radius: 8px; }}
            #settings-panel frame > label {{ font-weight: bold; }}
        '''.encode())
        self.theme_button.set_image(Gtk.Image.new_from_icon_name(
            'weather-clear-symbolic' if self.dark else 'weather-clear-night-symbolic', Gtk.IconSize.BUTTON))
        self.theme_button.set_tooltip_text('Use light theme' if self.dark else 'Use dark theme')
        for terminal in self.terminals.values():
            self.color_terminal(terminal)
        if self.theme_picker is not None:
            self.theme_picker.refresh()
        self.publish()

    def color_terminal(self, terminal):
        foreground, background, ansi = self.terminal_colors()
        terminal.set_colors(rgba(foreground), rgba(background), [rgba(c) for c in ansi])
        colors = palette(self.settings.get('terminal_palette', 'gnome'), self.dark)
        terminal.set_color_cursor(rgba(colors['cursor'] if colors else foreground))

    def terminal_colors(self, palette_key=None):
        colors = palette(palette_key if palette_key is not None else
                         self.settings.get('terminal_palette', 'gnome'), self.dark)
        if colors:
            return colors['foreground'], colors['background'], colors['colors']
        if self.dark:
            return '#f6f5f4', '#242424', [
                '#2e3436', '#cc0000', '#4e9a06', '#c4a000', '#3465a4', '#75507b', '#06989a', '#d3d7cf',
                '#555753', '#ef2929', '#8ae234', '#fce94f', '#729fcf', '#ad7fa8', '#34e2e2', '#eeeeec']
        return '#2c2c2c', '#ffffff', [
            '#2e3436', '#a51d2d', '#267326', '#876000', '#205a9d', '#74407f', '#006f73', '#d3d7cf',
            '#555753', '#c01c28', '#287a27', '#956700', '#2463a6', '#813d9c', '#00777d', '#eeeeec']

    def toggle_theme(self):
        self.theme = 'light' if self.dark else 'dark'
        self.apply_theme()
        self.save()

    def toggle_expanded(self):
        if self.window.is_maximized():
            self.window.unmaximize()
        else:
            self.save()
            self.window.maximize()

    def window_state_changed(self, window, event):
        expanded = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        self.expand_button.set_image(Gtk.Image.new_from_icon_name(
            'view-restore-symbolic' if expanded else 'view-fullscreen-symbolic', Gtk.IconSize.BUTTON))
        self.expand_button.set_tooltip_text('Restore window' if expanded else 'Expand HUD')
        return False

    def save(self):
        width, height = self.window.get_size()
        if self.window.is_maximized():
            width = self.settings.get('width', 1040)
            height = self.settings.get('height', 660)
        self.settings.update(theme=self.theme, width=width, height=height,
                             sidebar_width=self.split.get_position(),
                             sidebar_expanded_width=self.sidebar_expanded_width,
                             section_position=self.section_position,
                             spaces_expanded=self.space_section.get_expanded(),
                             agents_expanded=self.agent_section.get_expanded())
        CONFIG.mkdir(parents=True, exist_ok=True)
        temp = CONFIG / 'settings.json.tmp'
        temp.write_text(json.dumps(self.settings, indent=2))
        temp.replace(CONFIG / 'settings.json')

    def sessions_changed(self, sessions, error):
        if self.closing:
            return
        if error:
            self.status.set_text('Could not list sessions: ' + str(error))
            if isinstance(error, HerdrUnavailable) and self.stack.get_visible_child_name() != 'setup':
                self.show_setup(str(error))
            return
        self.sessions = sessions
        live = {s['socket_path'] for s in sessions if s['running']}
        removed = set(self.snapshots) - live
        for path in removed:
            del self.snapshots[path]
        if removed:
            self.update_panes()

    def snapshot_changed(self, session, snapshot, error):
        if self.closing:
            return
        path = session['socket_path']
        if error:
            self.session_errors[path] = error
            self.status.set_text(f"Reconnecting to {session['name']}…")
            return
        self.session_errors.pop(path, None)
        self.snapshots[path] = (session, snapshot)
        if session['name'] == 'default' and snapshot['workspaces']:
            first = snapshot['workspaces'][0]
            identity = (path, first['workspace_id'])
            if identity not in self.checked_initial_spaces:
                self.checked_initial_spaces.add(identity)
                if first['label'] == '~':
                    self.change_item(session, 'workspace.rename',
                                     {'workspace_id': first['workspace_id'], 'label': 'Space 1'})
        for pane in snapshot['panes']:
            key = (path, pane['terminal_id'])
            self.transition(key, pane, pane['agent_status'])
        self.update_panes()

        if self.initial_selection_pending and session['name'] == 'default' and snapshot['panes']:
            self.initial_selection_pending = False
            if self.selected is None:
                idle(self.select_initial_terminal, (path, snapshot['panes'][0]['terminal_id']))

    def select_initial_terminal(self, key):
        if not self.closing and self.selected is None and key in self.panes:
            self.select(key)

    def transition(self, key, pane, state):
        previous = self.states.get(key)
        self.states[key] = state
        message = attention(previous, state)
        if message and not (key == self.selected and self.window.is_active() and self.window.get_visible()):
            title = pane.get('label') or pane.get('display_agent') or pane.get('agent') or pane.get('title') or 'Terminal'
            self.unread[key] = message
            self.publish(f'{title} — {message}')

    def event_received(self, session, message):
        if self.closing:
            return
        data = message.get('data', {})
        for key, pane in list(self.panes.items()):
            if key[0] == session['socket_path'] and pane['pane_id'] == data.get('pane_id'):
                if 'agent_status' in data:
                    self.transition(key, {**pane, **data}, data['agent_status'])
                elif message.get('event') in ('pane.exited', 'pane_exited'):
                    self.unread[key] = 'Terminal exited'
                    self.publish(f"{pane.get('label') or 'Terminal'} — Terminal exited")

    def update_panes(self):
        panes = {}
        for path, (session, snapshot) in self.snapshots.items():
            workspaces = {w['workspace_id']: w['label'] for w in snapshot['workspaces']}
            tabs = {t['tab_id']: t['label'] for t in snapshot['tabs']}
            for pane in snapshot['panes']:
                panes[(path, pane['terminal_id'])] = {**pane, 'session': session,
                    'workspace_label': workspaces.get(pane['workspace_id'], ''),
                    'tab_label': tabs.get(pane['tab_id'], '')}
        self.panes = panes
        for key in list(self.terminals):
            if isinstance(key, tuple) and key not in panes:
                terminal = self.terminals.pop(key)
                if self.window.get_focus() is terminal:
                    self.window.set_focus(None)
                if self.stack.get_visible_child() is terminal:
                    self.stack.set_visible_child_name('empty')
                terminal.detach()
                terminal.hide()
                self.stack.remove(terminal)
                idle(terminal.destroy)
        self.unread = {k: v for k, v in self.unread.items() if k in panes}
        self.states = {k: v for k, v in self.states.items() if k in panes}
        if self.selected is not None and self.selected not in panes:
            self.selected = None
            idle(self.restore_workspace_selection)
            self.stack.set_visible_child_name('empty')
            self.active_title.set_text('Choose a terminal')
        self.rebuild_sidebar()
        self.publish()

    def pane_title(self, pane):
        tab = pane.get('tab_label', '')
        return (pane.get('label') or pane.get('display_agent') or pane.get('agent')
                or (tab if tab and not tab.isdigit() else None)
                or pane.get('terminal_title_stripped') or pane.get('title')
                or ('Terminal ' + tab if tab else 'Terminal'))

    def rebuild_sidebar(self):
        # GtkListBox still uses its clicked row after emitting row-selected.
        # Never destroy that row inside the signal's stack. Coalesce updates and
        # render only after the current GTK event has returned to the main loop.
        if self.closing or self.sidebar_refresh_id:
            return
        self.sidebar_refresh_id = GLib.idle_add(self._refresh_sidebar)

    def _refresh_sidebar(self):
        self.sidebar_refresh_id = 0
        if self.closing:
            return GLib.SOURCE_REMOVE
        self._render_sidebar()
        return GLib.SOURCE_REMOVE

    def _render_sidebar(self):
        # Keep widgets (and GTK selection/focus) stable across monitor snapshots.
        # Only sessions/terminals that actually disappeared lose their rows.
        self.rebuilding = True
        try:
            self._update_sidebar_rows()
        finally:
            self.rebuilding = False

    def _update_sidebar_rows(self):
        query = self.search.get_text().strip().casefold()
        self.empty_agents.set_text('No matching agents' if query else 'No agents running')
        groups = {(path, w['workspace_id']): []
                  for path, (_, snapshot) in self.snapshots.items()
                  for w in snapshot['workspaces']}
        for key, pane in self.panes.items():
            groups.setdefault((key[0], pane['workspace_id']), []).append((key, pane))
        self.collapsed_spaces.intersection_update(groups)
        desired = []
        for path, members in groups.items():
            session, snapshot = self.snapshots[path[0]]
            workspace = next(w for w in snapshot['workspaces'] if w['workspace_id'] == path[1])
            group_title = workspace.get('label') or session['name']
            if session['name'] != 'default':
                group_title = session['name'] + ' / ' + group_title
            titles = {}
            for number, (key, pane) in enumerate(members, 1):
                agent = pane.get('display_agent') or pane.get('agent')
                name = pane.get('tab_label') or pane.get('label') or ''
                if not name or name.isdigit() or name.casefold() == str(agent or '').casefold():
                    name = f'Terminal {number}'
                titles[key] = f'{agent} · {name}' if agent else self.pane_title(pane)
            visible = {key for key, pane in members if not query or query in
                       ' '.join(str(value or '') for value in (
                           titles[key], self.pane_title(pane), pane.get('label'), pane.get('tab_label'),
                           pane.get('title'), pane.get('terminal_title_stripped'),
                           pane.get('display_agent'), pane.get('agent'))).casefold()}
            agents = sum(bool(p.get('agent')) for _, p in members)
            count = len(members)
            counts = f"{count} terminal{'s' if count != 1 else ''}"
            if agents:
                counts += f" · {agents} agent{'s' if agents != 1 else ''}"
            activity = {key: ('working' if self.states.get(key) == 'working' else
                              'unread' if key in self.unread else '')
                        for key, _ in members}
            group_activity = ('unread' if 'unread' in activity.values() else
                              'working' if 'working' in activity.values() else '')
            desired.append((('group', path), group_title,
                            counts,
                            f"{group_title} — {counts}", not query or any(
                                key in visible for key, pane in members),
                            group_activity))
            for key, pane in members:
                state = self.states.get(key, 'unknown')
                subtitle = self.unread.get(key) or (state.capitalize() if pane.get('agent') else 'Shell')
                if pane.get('agent'):
                    status = {'blocked': 'Needs input', 'done': 'Finished'}.get(state, state.capitalize())
                    subtitle = f"{pane.get('display_agent') or pane['agent']} · {status} · {group_title}"
                tooltip = f"{session['name']} / {pane['workspace_label']}\n{pane.get('foreground_cwd') or pane.get('cwd') or ''}"
                desired.append((('terminal', key), titles[key],
                                subtitle, tooltip, key in visible and
                                (bool(query) or path not in self.collapsed_spaces),
                                activity[key]))
                if pane.get('agent'):
                    desired.append((('agent', key), titles[key], subtitle, tooltip,
                                    key in visible, activity[key]))

        wanted = {item[0] for item in desired}
        for identity in self.sidebar_rows.keys() - wanted:
            self.sidebar_rows.pop(identity).destroy()
        order_changed = False
        for order, (identity, title, subtitle, tooltip, visible, active) in enumerate(desired):
            row = self.sidebar_rows.get(identity)
            is_group = identity[0] == 'group'
            target_list = self.agent_rows if identity[0] == 'agent' else self.rows
            if row is None:
                row = Gtk.ListBoxRow(selectable=True, activatable=True)
                row.is_group = is_group
                row.order = order
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                row.title_label = Gtk.Label(xalign=0)
                row.title_label.set_ellipsize(Pango.EllipsizeMode.END)
                row.subtitle_label = Gtk.Label(xalign=0)
                row.subtitle_label.set_ellipsize(Pango.EllipsizeMode.END)
                row.subtitle_label.get_style_context().add_class('dim-label')
                title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                row.rename_button = self.icon_button('edit-symbolic',
                    'Space actions' if is_group else 'Session actions',
                    lambda target=identity: self.open_item_menu(
                        target, self.sidebar_rows[target].rename_button))
                row.rename_button.set_relief(Gtk.ReliefStyle.NONE)
                row.rename_button.get_image().set_pixel_size(14)
                row.rename_button.get_style_context().add_class('rename-button')
                if is_group:
                    row.collapse_button = self.icon_button('pan-down-symbolic', 'Collapse space',
                        lambda group=identity[1]: self.toggle_space(group))
                    row.collapse_button.set_relief(Gtk.ReliefStyle.NONE)
                    row.collapse_button.get_image().set_pixel_size(12)
                    row.collapse_button.get_style_context().add_class('space-toggle')
                    title_box.pack_start(row.collapse_button, False, False, 0)
                title_box.pack_start(row.rename_button, False, False, 0)
                row.status_dot = Gtk.Label(label='○')
                row.status_dot.get_style_context().add_class('activity-dot')
                title_box.pack_start(row.status_dot, False, False, 0)
                title_box.pack_start(row.title_label, True, True, 0)
                box.pack_start(title_box, False, False, 0)
                box.pack_start(row.subtitle_label, False, False, 0)
                if is_group:
                    row.title_label.get_style_context().add_class('group-label')
                    row.group_key = identity[1]
                    row.get_style_context().add_class('space-row')
                    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                    header.pack_start(box, True, True, 0)
                    row.add_button = self.icon_button('list-add-symbolic',
                        'New terminal in this space', lambda group=identity[1]: self.new_terminal(*group))
                    row.add_button.get_style_context().add_class('space-add')
                    header.pack_end(row.add_button, False, False, 0)
                    row.add(header)
                else:
                    row.get_style_context().add_class('terminal-row')
                    row.key = identity[1]
                    row.add(box)
                row.connect('popup-menu', self.session_keyboard_menu)
                self.sidebar_rows[identity] = row
                target_list.add(row)
                row.show_all()
            if row.get_parent() != target_list:
                row.set_header(None)
                previous_list = row.get_parent()
                previous_list.unselect_row(row)
                previous_list.remove(row)
                target_list.add(row)
            is_agent = identity[0] == 'agent'
            row.set_margin_start(18 if not is_group and not is_agent else 0)
            for style, enabled in (('shell-row', not is_group and not is_agent),
                                  ('agent-row', is_agent)):
                context = row.get_style_context()
                if enabled:
                    context.add_class(style)
                else:
                    context.remove_class(style)
            row.subtitle_label.set_visible(is_agent)
            if is_group:
                expanded = bool(query) or identity[1] not in self.collapsed_spaces
                icon = 'pan-down-symbolic' if expanded else 'pan-end-symbolic'
                if row.collapse_button.get_image().get_icon_name()[0] != icon:
                    row.collapse_button.get_image().set_from_icon_name(icon, Gtk.IconSize.MENU)
                    row.collapse_button.get_image().set_pixel_size(12)
                row.collapse_button.set_sensitive(not query)
                row.collapse_button.set_tooltip_text('Search shows matching terminals' if query else
                    'Collapse space' if expanded else 'Expand space')
                empty = not groups[identity[1]]
                row.add_button.set_label('New terminal' if empty else '')
                row.add_button.set_always_show_image(True)
                row.add_button.set_sensitive(identity[1][0] not in self.adding_terminals)
            if row.order != order:
                row.order = order
                order_changed = True
            marker = '●' if active else '○'
            if row.status_dot.get_text() != marker:
                row.status_dot.set_text(marker)
            dot_style = row.status_dot.get_style_context()
            if active:
                dot_style.add_class('active')
            else:
                dot_style.remove_class('active')
            if active == 'working':
                dot_style.add_class('working')
            else:
                dot_style.remove_class('working')
            if row.title_label.get_text() != title:
                row.title_label.set_text(title)
            if row.subtitle_label.get_text() != subtitle:
                row.subtitle_label.set_text(subtitle)
            tooltip_widget = row
            if tooltip_widget.get_tooltip_text() != tooltip:
                tooltip_widget.set_tooltip_text(tooltip)
            if row.get_visible() != visible:
                row.set_visible(visible)
        if order_changed:
            self.rows.invalidate_sort()
            self.agent_rows.invalidate_sort()
        for rows, identity in ((self.rows, ('terminal', self.selected)),
                               (self.agent_rows, ('agent', self.selected))):
            selected_row = self.sidebar_rows.get(identity)
            desired_selection = (selected_row if selected_row and selected_row.get_visible()
                                 and selected_row.get_parent() == rows else None)
            if rows.get_selected_row() != desired_selection:
                rows.select_row(desired_selection)

    def toggle_space(self, group):
        if self.closing:
            return
        if group in self.collapsed_spaces:
            self.collapsed_spaces.remove(group)
        else:
            self.collapsed_spaces.add(group)
        self.rebuild_sidebar()

    def sidebar_button_press(self, rows, event):
        # ListBox owns the input window; its windowless rows never receive
        # button events directly. Resolve the target from list coordinates.
        if event.button != 3:
            return False
        row = rows.get_row_at_y(int(event.y))
        if row is None or not (hasattr(row, 'key') or hasattr(row, 'group_key')):
            return False
        self.open_session_menu(row, event)
        return True

    def session_keyboard_menu(self, row):
        self.open_session_menu(row)
        return True

    def open_session_menu(self, row, event=None):
        identity = ('group', row.group_key) if row.is_group else ('terminal', row.key)
        self.open_item_menu(identity, row, event)

    def open_item_menu(self, identity, anchor, event=None):
        if identity[0] == 'agent':
            identity = ('terminal', identity[1])
        if identity[0] == 'terminal' and identity[1] not in self.panes:
            return
        if identity[0] == 'group' and identity not in self.sidebar_rows:
            return
        menu = Gtk.Menu()
        menu.attach_to_widget(anchor, None)
        rename = Gtk.MenuItem(label='Rename')
        rename.connect('activate', lambda *_: self.rename_sidebar_item(identity))
        menu.append(rename)
        if self.can_close_sidebar_item(identity):
            agent = identity[0] == 'terminal' and self.panes[identity[1]].get('agent')
            close = Gtk.MenuItem(label='Close terminal and stop agent' if agent else 'Close')
            close.set_tooltip_text('Stop all terminals in this space' if identity[0] == 'group'
                                  else 'Stop this terminal and its running process')
            close.connect('activate', lambda *_: self.close_sidebar_item(identity))
            menu.append(close)
        menu.connect('selection-done', lambda *_: menu.destroy())
        menu.show_all()
        if event:
            menu.popup_at_pointer(event)
        else:
            menu.popup_at_widget(anchor, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST,
                                 Gtk.get_current_event())

    def can_close_sidebar_item(self, identity):
        kind, key = identity
        entry = self.snapshots.get(key[0])
        if not entry:
            return False
        snapshot = entry[1]
        if kind == 'group':
            workspaces = snapshot['workspaces']
            return bool(workspaces and key[1] != workspaces[0]['workspace_id']
                        and any(w['workspace_id'] == key[1] for w in workspaces))
        pane = self.panes.get(key)
        if not pane:
            return False
        workspaces = snapshot['workspaces']
        if workspaces and pane['workspace_id'] == workspaces[0]['workspace_id']:
            return sum(k[0] == key[0] and p['workspace_id'] == pane['workspace_id']
                       for k, p in self.panes.items()) > 1
        return True

    def close_sidebar_item(self, identity):
        if not self.can_close_sidebar_item(identity):
            return
        kind, key = identity
        if kind == 'terminal':
            pane = self.panes.get(key)
            if pane and pane.get('agent'):
                dialog = Gtk.MessageDialog(transient_for=self.window, modal=True,
                    message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.NONE,
                    text='Close terminal and stop agent?')
                dialog.format_secondary_text('This stops the agent and any other process in this terminal. Unfinished work may be lost.')
                dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL,
                                   'Close terminal and stop agent', Gtk.ResponseType.OK)
                dialog.set_default_response(Gtk.ResponseType.CANCEL)
                response = dialog.run()
                dialog.destroy()
                if response != Gtk.ResponseType.OK:
                    return
            # A confirmation dialog runs GTK events; another pane may have closed.
            if self.can_close_sidebar_item(identity):
                self.change_terminal(key, 'pane.close')
        else:
            pane = next((p for k, p in self.panes.items()
                         if k[0] == key[0] and p['workspace_id'] == key[1]), None)
            entry = self.snapshots.get(key[0])
            if entry:
                self.change_item(entry[0], 'workspace.close', {'workspace_id': key[1]})

    def rename_terminal(self, key):
        self.rename_sidebar_item(('terminal', key))

    def rename_sidebar_item(self, identity):
        kind, key = identity
        if kind == 'group':
            pane = next((p for k, p in self.panes.items()
                         if k[0] == key[0] and p['workspace_id'] == key[1]), None)
        else:
            pane = self.panes.get(key)
        is_space = kind == 'group'
        if is_space:
            entry = self.snapshots.get(key[0])
            workspace = next((w for w in entry[1]['workspaces'] if w['workspace_id'] == key[1]), None) if entry else None
            if not workspace:
                return
            session = entry[0]
            current = workspace.get('label', '')
        else:
            if not pane:
                return
            current = self.pane_title(pane)
        dialog = Gtk.Dialog(title='Rename space' if is_space else 'Rename session',
                            transient_for=self.window, modal=True)
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Rename', Gtk.ResponseType.OK)
        entry = Gtk.Entry(text=current, activates_default=True)
        entry.set_placeholder_text('Name your space' if is_space else 'Name your session')
        dialog.set_response_sensitive(Gtk.ResponseType.OK, bool(current.strip()))
        entry.set_margin_start(16)
        entry.set_margin_end(16)
        entry.set_margin_top(16)
        entry.set_margin_bottom(16)
        entry.connect('changed', lambda field: dialog.set_response_sensitive(
            Gtk.ResponseType.OK, bool(field.get_text().strip())))
        dialog.get_content_area().add(entry)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        entry.grab_focus()
        entry.select_region(0, -1)
        response = dialog.run()
        name = entry.get_text().strip()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and name:
            if is_space:
                self.change_item(session, 'workspace.rename',
                                 {'workspace_id': key[1], 'label': name})
            else:
                self.change_terminal(key, 'pane.rename', name)

    def change_terminal(self, key, method, name=None):
        pane = self.panes.get(key)
        if not pane:
            return
        session = pane['session']
        params = {'pane_id': pane['pane_id']}
        if method == 'pane.rename':
            params['label'] = name
            self.change_item(session, method, params,
                             ('tab.rename', {'tab_id': pane['tab_id'], 'label': name}))
        else:
            self.change_item(session, method, params)

    def change_item(self, session, method, params, followup=None):
        def work():
            try:
                request(session['socket_path'], method, params)
                if followup:
                    request(session['socket_path'], followup[0], followup[1])
                snapshot = request(session['socket_path'], 'session.snapshot')['snapshot']
                idle(self.terminal_changed, session, snapshot, None)
            except Exception as exc:
                idle(self.terminal_changed, session, None, str(exc))
        threading.Thread(target=work, daemon=True).start()

    def terminal_changed(self, session, snapshot, error):
        if self.closing:
            return
        if error:
            self.status.set_text('Could not update terminal: ' + error)
            return
        self.snapshot_changed(session, snapshot, None)
        if self.selected in self.panes:
            pane = self.panes[self.selected]
            self.active_title.set_text(pane['session']['name'] + '  /  ' + self.pane_title(pane))
        idle(self.focus_selected_terminal)

    def new_terminal(self, path, workspace_id=None):
        if path in self.adding_terminals:
            return
        members = [p for key, p in self.panes.items() if key[0] == path
                   and (workspace_id is None or p['workspace_id'] == workspace_id)]
        entry = self.snapshots.get(path)
        if not entry:
            return
        selected = self.panes.get(self.selected)
        source = selected if selected in members else (members[0] if members else {})
        session = entry[0]
        workspace_id = workspace_id or source.get('workspace_id')
        if not workspace_id:
            return
        number = len(members) + 1
        labels = {p['tab_label'] for p in members}
        while f'Terminal {number}' in labels:
            number += 1
        self.adding_terminals.add(path)
        self.rebuild_sidebar()
        def work():
            try:
                snapshot, terminal_id = create_terminal(session, workspace_id,
                    f'Terminal {number}', source.get('foreground_cwd') or source.get('cwd'))
                idle(self.terminal_created, session, snapshot, terminal_id, None)
            except Exception as exc:
                idle(self.terminal_created, session, None, None, str(exc))
        threading.Thread(target=work, daemon=True).start()

    def terminal_created(self, session, snapshot, terminal_id, error):
        self.adding_terminals.discard(session['socket_path'])
        if self.closing:
            return
        if error:
            self.status.set_text('Could not add terminal: ' + error)
            self.rebuild_sidebar()
            return
        pane = next((p for p in snapshot['panes'] if p['terminal_id'] == terminal_id), None)
        if pane:
            self.collapsed_spaces.discard((session['socket_path'], pane['workspace_id']))
        self.snapshot_changed(session, snapshot, None)
        self.select((session['socket_path'], terminal_id))
        self.status.set_text('Shift+drag to copy  ·  Click CLI controls  ·  Right-click to paste')

    def row_activated(self, rows, row):
        self.row_selected(rows, row)

    def row_selected(self, _, row):
        if self.rebuilding or row is None:
            return
        if row.is_group:
            self.select_workspace(row.group_key)
        else:
            self.select(row.key)

    def select_workspace(self, group):
        members = [key for key, pane in self.panes.items()
                   if (key[0], pane['workspace_id']) == group]
        if not members:
            return
        key = self.workspace_selection.get(group)
        self.select(key if key in members else members[0])

    def restore_workspace_selection(self):
        if self.closing or self.selected is not None:
            return
        self.select_workspace(self.selected_workspace)
        if self.selected is None and self.panes:
            self.select(next(iter(self.panes)))

    def select(self, key):
        pane = self.panes.get(key)
        if self.closing or not pane:
            return
        self.selected = key
        self.selected_workspace = (key[0], pane['workspace_id'])
        self.workspace_selection[self.selected_workspace] = key
        terminal = self.terminals.get(key)
        if terminal and not terminal.alive:
            terminal.destroy()
            del self.terminals[key]
            terminal = None
        if terminal is None:
            try:
                executable = resolve_herdr()
            except HerdrUnavailable as exc:
                self.show_setup(str(exc))
                return
            terminal = Terminal()
            self.terminals[key] = terminal
            self.color_terminal(terminal)
            self.stack.add_named(terminal, f'terminal-{len(self.terminals)}-{GLib.get_monotonic_time()}')
            terminal.show()
            terminal.launch([executable, '--session', pane['session']['name'], 'terminal', 'attach', pane['terminal_id']])
        self.stack.set_visible_child(terminal)
        self.active_title.set_text(pane['session']['name'] + '  /  ' + self.pane_title(pane))
        self.acknowledge()
        self.rebuild_sidebar()
        # GtkListBox grabs row focus after row-selected returns. Focus the terminal
        # only after that event and the queued sidebar refresh have finished.
        idle(self.focus_selected_terminal)

    def acknowledge(self):
        if self.selected in self.unread:
            del self.unread[self.selected]
            self.publish()
            self.rebuild_sidebar()
        return False

    def new_session(self):
        try:
            resolve_herdr()
        except HerdrUnavailable as exc:
            self.show_setup(str(exc))
            return
        dialog = Gtk.Dialog(title='New space', transient_for=self.window, modal=True,
                            use_header_bar=False)
        dialog.set_default_size(360, -1)
        dialog.set_resizable(False)
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Start', Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        content.set_border_width(16)
        content.set_spacing(16)
        actions = dialog.get_action_area()
        actions.set_border_width(0)
        actions.set_layout(Gtk.ButtonBoxStyle.CENTER)
        actions.set_spacing(8)
        for response in (Gtk.ResponseType.CANCEL, Gtk.ResponseType.OK):
            dialog.get_widget_for_response(response).set_size_request(88, 36)
        entry = Gtk.Entry(placeholder_text='Name your space')
        dialog.set_response_sensitive(Gtk.ResponseType.OK, False)
        entry.connect('changed', lambda field: dialog.set_response_sensitive(
            Gtk.ResponseType.OK, bool(field.get_text().strip())))
        entry.set_text(self.next_space_name())
        entry.select_region(0, -1)
        entry.set_activates_default(True)
        content.pack_start(entry, False, False, 0)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        response = dialog.run()
        name = entry.get_text().strip()
        dialog.destroy()
        if response != Gtk.ResponseType.OK or not name:
            return
        self.create_session(name)

    def next_space_name(self):
        workspaces = [space for session, snapshot in self.snapshots.values()
                      if session['name'] == 'default' for space in snapshot['workspaces']]
        numbers = [int(space['label'][6:]) for space in workspaces
                   if space['label'].startswith('Space ') and space['label'][6:].isascii()
                   and space['label'][6:].isdigit()]
        return f'Space {max([len(workspaces), *numbers], default=0) + 1}'

    def create_session(self, name):
        if self.creating_session:
            return
        self.creating_session = True
        self.stack.set_visible_child_name('loading')
        self.active_title.set_text(name)
        def work():
            try:
                session, snapshot, terminal_id = create_shared_workspace(name)
                idle(self.session_created, session, snapshot, None, terminal_id)
            except Exception as exc:
                idle(self.session_created, None, None, str(exc))
        threading.Thread(target=work, daemon=True).start()

    def session_created(self, session, snapshot, error, terminal_id=None):
        self.creating_session = False
        if self.closing:
            return
        if error:
            self.stack.set_visible_child_name('empty')
            self.status.set_text('Could not open session: ' + error)
            return
        self.snapshot_changed(session, snapshot, None)
        if snapshot['panes']:
            self.select((session['socket_path'], terminal_id or snapshot['panes'][0]['terminal_id']))
            self.status.set_text('Shift+drag to copy  ·  Click CLI controls  ·  Right-click to paste')

    def show(self):
        self.window.show()
        self.window.present()
        self.shell_call('ShowBubble')
        idle(self.focus_selected_terminal)
        self.acknowledge()

    def hide(self):
        self.save()
        self.window.hide()
        return True

    def toggle(self):
        if self.window.get_visible():
            self.hide()
        else:
            self.show()

    def exit_hud(self):
        if self.closing:
            return
        self.save()
        self.closing = True
        if self.sidebar_refresh_id:
            GLib.Source.remove(self.sidebar_refresh_id)
            self.sidebar_refresh_id = 0
        self.monitor.stop()
        self.update_monitor.stop()
        for terminal in self.terminals.values():
            terminal.detach()
        self.shell_call('ExitHud')
        self.quit()

    def do_shutdown(self):
        self.update_monitor.stop()
        if not self.closing:
            self.monitor.stop()
            for terminal in self.terminals.values():
                terminal.detach()
        self.closing = True
        Gio.bus_unwatch_name(self.shell_watch)
        Gtk.Application.do_shutdown(self)


if __name__ == '__main__':
    if '--version' in sys.argv:
        print('Herdr Hud ' + VERSION)
    else:
        sys.exit(Hud().run(sys.argv))

"""AppKit floating H and desktop lifecycle, running on GTK's Quartz main thread."""
import json
import math
import os
from pathlib import Path
import plistlib
import sys
import threading

import AppKit as A
import Foundation as F
from gi.repository import Gdk, GLib


def read_object(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_object(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def numbers(value, names):
    return all(isinstance(value.get(k), (int, float)) and not isinstance(value[k], bool)
               and math.isfinite(value[k]) for k in names)


class BubbleView(A.NSView):
    def acceptsFirstResponder(self):
        return True

    def acceptsFirstMouse_(self, event):
        return True

    def drawRect_(self, rect):
        owner = self.owner
        circle = A.NSBezierPath.bezierPathWithOvalInRect_(F.NSMakeRect(2, 2, 52, 52))
        A.NSColor.colorWithCalibratedWhite_alpha_(.188 if owner.dark else .98, 1).setFill()
        circle.fill()
        A.NSColor.controlAccentColor().setStroke()
        circle.setLineWidth_(2)
        circle.stroke()
        font = A.NSFont.fontWithName_size_('Ubuntu', 27) or A.NSFont.boldSystemFontOfSize_(27)
        font = A.NSFontManager.sharedFontManager().convertFont_toHaveTrait_(font, A.NSBoldFontMask)
        label = F.NSAttributedString.alloc().initWithString_attributes_('H', {
            A.NSFontAttributeName: font,
            A.NSForegroundColorAttributeName: A.NSColor.whiteColor() if owner.dark else A.NSColor.darkGrayColor()})
        size = label.size()
        label.drawAtPoint_(F.NSMakePoint((56 - size.width) / 2, (56 - size.height) / 2))
        if owner.unread:
            badge = A.NSBezierPath.bezierPathWithOvalInRect_(F.NSMakeRect(42, 42, 12, 12))
            A.NSColor.colorWithCalibratedRed_green_blue_alpha_(.208, .518, .894, 1).setFill()
            badge.fill()
            A.NSColor.whiteColor().setStroke()
            badge.setLineWidth_(2)
            badge.stroke()

    def mouseDown_(self, event):
        if self.owner.drag is not None:
            return
        point = A.NSEvent.mouseLocation()
        origin = self.window().frame().origin
        self.owner.drag = (point.x, point.y, origin.x, origin.y)
        self.owner.moved = False
        self.window().makeKeyWindow()
        self.window().makeFirstResponder_(self)

    def mouseDragged_(self, event):
        if self.owner.drag is None:
            return
        point = A.NSEvent.mouseLocation()
        px, py, x, y = self.owner.drag
        if abs(point.x - px) + abs(point.y - py) > 6:
            self.owner.moved = True
        if self.owner.moved:
            self.window().setFrameOrigin_(F.NSMakePoint(x + point.x - px, y + point.y - py))

    def mouseUp_(self, event):
        if self.owner.drag is None:
            return
        click = not self.owner.moved
        self.owner.end_drag()
        if click:
            self.owner.app.toggle()

    def cancelOperation_(self, sender):
        self.owner.end_drag()


class BubblePanel(A.NSPanel):
    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return False


class ReopenHandler(F.NSObject):
    def handleReopen_withReplyEvent_(self, event, reply):
        if not self.owner.closed:
            self.owner.app.show()


class MacDesktop:
    def __init__(self, app, config):
        self.app, self.config = app, Path(config)
        self.panel = None
        self.toast = None
        self.toast_timer = 0
        self.timer = 0
        self.observers = []
        self.dark = True
        self.unread = 0
        self.drag = None
        self.moved = False
        self.suspended = False
        self.suspensions = set()
        self.closed = False
        self.restored = False
        self.last_dark = None

    def start(self):
        # Fonts belong to this process, never to the user's system font library.
        import CoreText
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent / 'packaging/macos'))
        if '_HUD_HOST_ENV' not in os.environ:
            from runtime_env import RUNTIME_KEYS
            os.environ['_HUD_HOST_ENV'] = json.dumps({key: os.environ.get(key) for key in RUNTIME_KEYS})
        os.environ['GTK_DATA_PREFIX'] = str(root)
        for path in (root / 'fonts').glob('*.ttf'):
            CoreText.CTFontManagerRegisterFontsForURL(F.NSURL.fileURLWithPath_(str(path)),
                                                      CoreText.kCTFontManagerScopeProcess, None)
        from gi.repository import Gtk
        # Match the reference GTK layout in logical pixels; Quartz handles Retina scaling.
        Gtk.Settings.get_default().set_property('gtk-xft-dpi', 96 * 1024)
        Gdk.Screen.get_default().set_resolution(96)
        Gtk.Settings.get_default().set_property('gtk-font-name', 'Ubuntu Sans 11')
        Gtk.Settings.get_default().set_property('gtk-theme-name', 'Yaru-blue')
        Gtk.IconTheme.get_default().prepend_search_path(str(root / 'share/icons'))
        Gtk.Settings.get_default().set_property('gtk-icon-theme-name', 'HerdrReference')

    def prefers_dark(self):
        return F.NSUserDefaults.standardUserDefaults().stringForKey_('AppleInterfaceStyle') == 'Dark'

    def ready(self):
        from gi.repository import Gio
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', lambda *_: self.app.exit_hud())
        self.app.add_action(quit_action)
        self.reopen = ReopenHandler.alloc().init()
        self.reopen.owner = self
        F.NSAppleEventManager.sharedAppleEventManager().setEventHandler_andSelector_forEventClass_andEventID_(
            self.reopen, b'handleReopen:withReplyEvent:', 0x61657674, 0x72617070)
        self.panel = self.make_panel(56, 56)
        self.view = BubbleView.alloc().initWithFrame_(F.NSMakeRect(0, 0, 56, 56))
        self.view.owner = self
        self.view.setAccessibilityLabel_('Herdr Hud')
        self.panel.setContentView_(self.view)
        screen = A.NSScreen.mainScreen().visibleFrame()
        saved = read_object(self.config / 'bubble.json')
        x, y = ((saved['x'], saved['y']) if numbers(saved, ('x', 'y')) else
                (screen.origin.x + screen.size.width - 76, screen.origin.y + 80))
        self.panel.setFrameOrigin_(F.NSMakePoint(x, y))
        self.clamp_bubble()
        self.panel.orderFrontRegardless()
        self.last_dark = self.prefers_dark()
        self.app.window.connect('configure-event', self.window_configured)
        self.observe(F.NSDistributedNotificationCenter.defaultCenter(),
                     'com.apple.screenIsLocked', lambda _: self.suspend('lock'))
        self.observe(F.NSDistributedNotificationCenter.defaultCenter(),
                     'com.apple.screenIsUnlocked', lambda _: self.resume('lock'))
        workspace = A.NSWorkspace.sharedWorkspace().notificationCenter()
        self.observe(workspace, A.NSWorkspaceSessionDidResignActiveNotification, lambda _: self.suspend('session'))
        self.observe(workspace, A.NSWorkspaceWillSleepNotification, lambda _: self.suspend('sleep'))
        self.observe(workspace, A.NSWorkspaceSessionDidBecomeActiveNotification, lambda _: self.resume('session'))
        self.observe(workspace, A.NSWorkspaceDidWakeNotification, lambda _: self.resume('sleep'))
        self.observe(F.NSNotificationCenter.defaultCenter(), A.NSApplicationDidChangeScreenParametersNotification,
                     lambda _: self.screens_changed())
        self.observe(F.NSNotificationCenter.defaultCenter(), A.NSApplicationWillTerminateNotification,
                     lambda _: self.app.exit_hud() if not self.app.closing else None)
        self.timer = GLib.timeout_add(250, self.tick)

    def make_panel(self, width, height):
        panel = BubblePanel.alloc().initWithContentRect_styleMask_backing_defer_(
            F.NSMakeRect(0, 0, width, height),
            A.NSWindowStyleMaskBorderless | A.NSWindowStyleMaskNonactivatingPanel,
            A.NSBackingStoreBuffered, False)
        panel.setReleasedWhenClosed_(False)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(A.NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setHidesOnDeactivate_(False)
        panel.setLevel_(A.NSFloatingWindowLevel)
        panel.setCollectionBehavior_(A.NSWindowCollectionBehaviorCanJoinAllSpaces |
                                     A.NSWindowCollectionBehaviorFullScreenAuxiliary)
        return panel

    def observe(self, center, name, callback):
        token = center.addObserverForName_object_queue_usingBlock_(name, None,
                     F.NSOperationQueue.mainQueue(), callback)
        self.observers.append((center, token))

    def tick(self):
        if self.closed:
            return False
        if self.drag is not None and not A.NSEvent.pressedMouseButtons() & 1:
            self.end_drag()
        dark = self.prefers_dark()
        if dark != self.last_dark:
            self.last_dark = dark
            self.app.apply_theme()
        self.view.setNeedsDisplay_(True)  # Also follows the system accent color.
        return True

    def clamp_bubble(self):
        if not self.panel:
            return
        origin = self.panel.frame().origin
        screens = [s.visibleFrame() for s in A.NSScreen.screens()]
        area = next((s for s in screens if s.origin.x <= origin.x + 28 < s.origin.x + s.size.width
                     and s.origin.y <= origin.y + 28 < s.origin.y + s.size.height), screens[0])
        x = max(area.origin.x, min(origin.x, area.origin.x + area.size.width - 56))
        y = max(area.origin.y, min(origin.y, area.origin.y + area.size.height - 56))
        self.panel.setFrameOrigin_(F.NSMakePoint(x, y))

    def end_drag(self):
        was_dragging = self.drag is not None
        self.drag = None
        self.moved = False
        self.clamp_bubble()
        if self.panel:
            if was_dragging:
                self.panel.resignKeyWindow()
            point = self.panel.frame().origin
            write_object(self.config / 'bubble.json', {'x': point.x, 'y': point.y})

    def suspend(self, reason='manual'):
        self.suspensions.add(reason)
        self.suspended = True
        self.end_drag()
        self.hide_toast()
        self.panel.orderOut_(None)

    def resume(self, reason='manual'):
        if self.closed:
            return
        self.suspensions.discard(reason)
        self.suspended = bool(self.suspensions)
        if self.suspended:
            return
        self.clamp_bubble()
        self.panel.orderFrontRegardless()

    def screens_changed(self):
        self.clamp_bubble()
        self.restore_window(force=True)

    def restore_window(self, force=False):
        if self.restored and not force:
            return
        self.restored = True
        window = self.app.window
        saved = read_object(self.config / 'window.json')
        display = Gdk.Display.get_default()
        width, height = window.get_size()
        x, y = window.get_position()
        if numbers(saved, ('x', 'y', 'width', 'height')):
            x, y, width, height = [int(saved[k]) for k in ('x', 'y', 'width', 'height')]
            monitor = display.get_monitor_at_point(x + width // 2, y + height // 2)
        else:
            # Quartz uses a bottom-left origin; GDK uses the desktop union's top-left.
            screens = [screen.frame() for screen in A.NSScreen.screens()]
            point = self.panel.frame().origin
            bx = int(point.x - min(screen.origin.x for screen in screens))
            by = int(max(screen.origin.y + screen.size.height for screen in screens) - point.y - 56)
            monitor = display.get_monitor_at_point(bx + 28, by + 28)
            area = monitor.get_workarea()
            x = bx + 68 if bx < area.x + area.width / 2 else bx - width - 12
            y = by - 30
        area = monitor.get_workarea()
        width, height = min(max(620, width), area.width), min(max(360, height), area.height)
        x, y = max(area.x, min(x, area.x + area.width - width)), max(area.y, min(y, area.y + area.height - height))
        if not window.is_maximized():
            window.resize(width, height)
            window.move(x, y)

    def window_configured(self, *_):
        if self.restored:
            self.save()
        return False

    def save(self):
        window = self.app.window
        if not self.restored or not window or window.is_maximized() or not window.get_visible():
            return
        x, y = window.get_position()
        width, height = window.get_size()
        write_object(self.config / 'window.json', dict(x=x, y=y, width=width, height=height))

    def enable(self):
        if self.panel and not self.suspended:
            self.panel.orderFrontRegardless()
        # Register only once; deleting/disabling the user's login item stays respected.
        if getattr(sys, 'frozen', False) and not self.app.settings.get('mac_login_configured'):
            executable = Path(sys.executable).resolve()
            bundle = executable.parents[2]
            if bundle.parent in (Path('/Applications'), Path.home() / 'Applications'):
                self.app.settings['mac_login_configured'] = True
                self.app.save()
                def register():
                    path = Path.home() / 'Library/LaunchAgents/io.github.herdr.Hud.plist'
                    try:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        if not path.exists():
                            temporary = path.with_suffix('.tmp')
                            temporary.write_bytes(plistlib.dumps({'Label': 'io.github.herdr.Hud',
                                'ProgramArguments': ['/usr/bin/open', '-g', '-a', str(bundle), '--args', '--background'],
                                'RunAtLoad': True, 'ProcessType': 'Interactive'}))
                            temporary.replace(path)
                    except OSError as error:
                        GLib.idle_add(self.login_error, str(error))
                threading.Thread(target=register, daemon=True).start()
        return 'Floating H is active. Login startup is managed in macOS Login Items.'

    def login_error(self, message):
        if not self.app.closing:
            self.app.settings['mac_login_configured'] = False
            self.app.save()
            self.app.extension_message.set_text('Floating H is active. Could not register login startup: ' + message)
        return False

    def hide_toast(self):
        if self.toast_timer:
            GLib.Source.remove(self.toast_timer)
            self.toast_timer = 0
        if self.toast:
            self.toast.orderOut_(None)
        return False

    def show_toast(self, message):
        self.hide_toast()
        if self.suspended or self.closed:
            return
        if self.toast is None:
            self.toast = self.make_panel(360, 68)
            self.toast.setIgnoresMouseEvents_(True)
            self.toast.contentView().setWantsLayer_(True)
            self.toast.contentView().layer().setBackgroundColor_(A.NSColor.colorWithCalibratedWhite_alpha_(.14, 1).CGColor())
            self.toast.contentView().layer().setCornerRadius_(10)
            self.toast_label = A.NSTextField.wrappingLabelWithString_('')
            self.toast_label.setFrame_(F.NSMakeRect(16, 10, 328, 48))
            self.toast_label.setTextColor_(A.NSColor.whiteColor())
            self.toast.contentView().addSubview_(self.toast_label)
        self.toast_label.setStringValue_(message[:180])
        point = self.panel.frame().origin
        screen = self.panel.screen().visibleFrame()
        x = max(screen.origin.x + 8, min(point.x - 304, screen.origin.x + screen.size.width - 368))
        y = point.y + 66 if point.y + 134 < screen.origin.y + screen.size.height else point.y - 78
        self.toast.setFrameOrigin_(F.NSMakePoint(x, y))
        self.toast.orderFrontRegardless()
        def expire():
            self.toast_timer = 0
            return self.hide_toast()
        self.toast_timer = GLib.timeout_add_seconds(5, expire)

    def call(self, method, signature='', values=()):
        if method == 'ExitHud':
            self.stop()
        elif self.closed or self.panel is None:
            return
        elif method == 'SetStatus':
            self.unread, message, self.dark = values
            self.view.setAccessibilityLabel_(f'Herdr Hud — {self.unread} unread' if self.unread else 'Herdr Hud')
            self.view.setNeedsDisplay_(True)
            if message:
                self.show_toast(message)
        elif method == 'ShowBubble':
            self.restore_window()
            if not self.suspended:
                self.panel.orderFrontRegardless()
                A.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def stop(self):
        if self.closed:
            return
        self.closed = True
        self.end_drag()
        self.hide_toast()
        if self.timer:
            GLib.Source.remove(self.timer)
            self.timer = 0
        for center, token in self.observers:
            center.removeObserver_(token)
        self.observers.clear()
        F.NSAppleEventManager.sharedAppleEventManager().removeEventHandlerForEventClass_andEventID_(
            0x61657674, 0x72617070)
        if self.panel:
            self.panel.close()
        if self.toast:
            self.toast.close()

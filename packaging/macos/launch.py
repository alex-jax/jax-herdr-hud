"""Frozen Mac entry point; the PTY relay must never initialize Cocoa or GTK."""
import os
import sys


def main():
    if sys.argv[1:2] == ['--display-relay']:
        from runtime_env import host_environment
        from terminal_display import run
        env = host_environment()
        os.environ.clear()
        os.environ.update(env)
        run(sys.argv[2:])
        return 0
    if '--version' in sys.argv:
        from app_info import VERSION
        print('Herdr Hud ' + VERSION)
        return 0
    if '--runtime-check' in sys.argv:
        from runtime_probe import main as probe
        probe()
        return 0
    if '--smoke-test' in sys.argv:
        from macos_smoke import main as smoke
        smoke()
        return 0
    from desktop import config_directory
    from macos_instance import Instance
    from gi.repository import GLib
    application = [None]
    def deliver(command):
        app = application[0]
        if app is None or app.window is None:
            GLib.timeout_add(50, deliver, command)
        elif not app.closing:
            if command == 'show':
                app.show()
            elif command == 'quit':
                app.exit_hud()
        return False
    instance = Instance(config_directory(), lambda command: GLib.idle_add(deliver, command))
    command = 'quit' if '--quit' in sys.argv else 'background' if '--background' in sys.argv else 'show'
    try:
        if not instance.claim(command):
            return 0
        from hud import Hud
        application[0] = Hud()
        return application[0].run(sys.argv)
    finally:
        instance.close()


if __name__ == '__main__':
    sys.exit(main())

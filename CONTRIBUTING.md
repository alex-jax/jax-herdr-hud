# Contributing

Fork this repository, create a branch, and open a pull request with a description
of the behaviour and relevant verification. This project is GPL-3.0-or-later;
preserve the retained upstream MIT attribution in NOTICE.md and licenses/.

Read MANUAL.md and AGENTS.md before changing process ownership, desktop handling
or terminal behaviour. Herdr is a separate dependency; never stop real servers
as part of an installation, update or test.

## Local checks

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_extension_launcher.mjs
```

GTK and integration checks require a graphical desktop and use temporary test
sessions. Run sequentially on a separate D-Bus session:

```sh
dbus-run-session -- python3 tests/smoke_updates.py
dbus-run-session -- python3 tests/smoke_setup.py
dbus-run-session -- python3 tests/smoke_sidebar.py
dbus-run-session -- python3 tests/smoke_desktop.py
dbus-run-session -- python3 tests/smoke_extension.py
```

The desktop test changes the clipboard. The extension test requires GNOME 50 and
starts an isolated headless compositor. See AGENTS.md for test output settings.

## Terminal interaction checks

Run the relevant checks sequentially. Xvfb provides an isolated X11 display;
real-pointer checks also require `xdotool`. Herdr history checks start disposable
servers. These tests may change the clipboard.

```sh
xvfb-run -a dbus-run-session -- python3 tests/smoke_history.py
xvfb-run -a dbus-run-session -- python3 tests/smoke_links.py
xvfb-run -a dbus-run-session -- python3 tests/smoke_themes.py
HUD_TEST_POINTER=1 xvfb-run -a dbus-run-session -- python3 tests/smoke_selection.py
HUD_TEST_POINTER=1 xvfb-run -a -s '-screen 0 1920x1200x24' dbus-run-session -- python3 tests/smoke_cli_selection.py
HUD_TEST_POINTER=1 HUD_TEST_DIRECTION=up xvfb-run -a -s '-screen 0 1920x1200x24' dbus-run-session -- python3 tests/smoke_cli_selection.py
```

Set `HUD_TEST_SOURCE` to an extracted package's `usr/lib/herdr-hud` directory to
check that payload. CLI fixtures do not establish compatibility with every CLI;
link tests record launcher calls without opening a browser. Theme tests verify
VS Code Dark for fresh preferences and preservation of saved choices.

## Release artifacts

```sh
python3 scripts/build_deb.py
python3 scripts/release.py
```

The `.deb` relies on system libraries and includes the optional GNOME extension.
It does not bundle Herdr. The extension ZIP and source archive are separate assets.
See docs/VALIDATION.md for the actual test results and docs/PUBLISHING.md for
the GitHub release workflow. Include terminal_display.py and updates.py in every
installer. Keep CLI settings unchanged: display color filtering belongs to Hud.

# Public preview validation — 0.1.1

Date: 20 September 2026. Target: Ubuntu 26.04, GNOME Shell 50, amd64,
Herdr 0.9.1. Public tag: `v0.1.1-preview.1`.

This update fixes cold startup: Hud initializes the default Herdr server, opens
its existing first terminal, and shows the single `~` workspace on a fresh server.
New space then creates exactly one additional workspace. Existing sessions remain
intact. Startup and workspace creation serialize server initialization.

## Checks run for 0.1.1

- Python unit tests: 12 passed, including startup retries, shutdown during
  initialization, environment restoration and Debian package payload/layout.
- Extension launcher tests: 4 passed with Node's test runner.
- Debian build: `jax-herdr-hud_0.1.1-1_all.deb`; extracted launcher reports
  `Herdr Hud 0.1.1`.
- APT simulated installation: dependencies resolve; no removals required.
- Setup, sidebar and desktop smoke tests against the extracted Debian payload:
  passed under separate D-Bus sessions. Cold startup opens one `~` workspace and
  automatically selects its terminal; reusing the server adds no workspace;
  New space adds exactly one workspace and one terminal. Input, clipboard,
  notifications, agent placement, focus, renaming and scoped Close also passed.
- Isolated headless GNOME 50 smoke with the extracted Debian launcher and
  packaged extension: passed, including pointer grabs, dragging, accent,
  hide/show geometry, D-Bus and extension disable. Cleanup stops only its
  disposable Herdr server.

The desktop smoke completed all assertions and exited zero, but emitted
`gtk_widget_get_window` critical messages during cleanup. Simulated menu actions
also emit “no trigger event” warnings. These are recorded, not treated as clean
GTK output. The sidebar smoke runs with GTK criticals fatal and passed.

This remains a development preview. A clean-VM install/upgrade/removal lifecycle,
other architectures and other desktop versions were not verified. No Snap binary
or Store submission is part of this update. The extension code/revision is unchanged.

## Reproduce

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_extension_launcher.mjs
python3 scripts/build_deb.py --output dist/0.1.1
dpkg-deb --extract dist/0.1.1/jax-herdr-hud_0.1.1-1_all.deb build/deb-0.1.1
build/deb-0.1.1/usr/bin/herdr-hud --version
apt-get --simulate install ./dist/0.1.1/jax-herdr-hud_0.1.1-1_all.deb
python3 scripts/release.py --output dist/0.1.1
```

Set `HUD_TEST_SOURCE` to the absolute extracted `usr/lib/herdr-hud` directory for
setup/sidebar/desktop tests. Run each with `dbus-run-session -- python3 tests/TEST`.
For the extension smoke, leave `HUD_TEST_SOURCE` unset and set `HUD_TEST_LAUNCHER`
to a JSON array containing the extracted launcher, plus `HUD_TEST_EXTENSION` to
the extracted `usr/share/gnome-shell/extensions/herdr-hud@alex-jax.github.io`.

---

## Previous release record

# Public preview validation — 0.1.0

Date: 20 September 2026. Target: Ubuntu 26.04, GNOME Shell 50, amd64.
Public GitHub tag: `v0.1.0-preview.1`. This is a development preview, not an
Ubuntu App Center or Snap Store approval.

## Native Debian package

Artifact: `jax-herdr-hud_0.1.0-1_all.deb`. Architecture `all` describes the
Python/JavaScript payload; only the amd64 host has been exercised.

Checks performed for this repository's public snapshot:

- Backend and distribution unit tests: passed (9 tests).
- Debian package build/layout regression: passed (1 test). Checks payload/source
  identity, directory permissions, launcher mode, desktop entry, extension files,
  autostart conffile and absence of maintainer scripts or a bundled Herdr binary.
- `dpkg-deb` metadata and content inspection: passed; all package paths are root-owned.
- APT simulated installation: dependencies resolved; no removal required on test host.
- Extracted `.deb` launcher `--version`: `Herdr Hud 0.1.0`.
- Setup smoke with extracted payload: passed, including missing Herdr, invalid
  executable paths, paths containing spaces, Retry and About attribution.
- Sidebar smoke with extracted payload: passed, including actual pointer events,
  agent row transitions, preserved focus, dividers, menu guards, search, and
  maximize/restore geometry.
- Desktop smoke with extracted payload and a disposable Herdr server: passed,
  including input/arrows, copy/paste, real agent reports, linked renaming,
  workspace/tab creation, Close and preserving servers after HUD detachment.
- Isolated GNOME 50 extension smoke with the extracted Debian launcher: passed;
  pointer grabs, dragging, accent changes, exact geometry across hide/show,
  notification badge/tooltip and clean shutdown were exercised.
- Extension launcher unit checks: passed for Snap, native `.deb`, source and missing app.

The tests use separate D-Bus sessions and temporary settings. Simulated menu
activation can emit GTK's “no trigger event” warning; test assertions pass.

These checks do **not** claim a clean-VM APT install/upgrade/remove lifecycle or
cross-distribution support. The preview should be tested on disposable machines
before adoption for important work. The `.deb` uses Ubuntu system dependencies;
it does not redistribute the Snap's bundled runtime libraries.

## Snap / App Center work

The source snapshot includes the separate `snap/snapcraft.yaml`, rootless builder,
release scripts and reviewer drafts. This GitHub release does not publish the
Snap binary. Its grade remains `devel` and its Store approval is pending.
Earlier local Snap test claims from another work session are not treated as
validation of this GitHub release. Follow PUBLISHING.md for remaining Snapcraft,
VM lifecycle, corresponding-source and store-review gates.

## Reproduction

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_extension_launcher.mjs
python3 scripts/build_deb.py
mkdir -p build/deb-test
dpkg-deb --extract dist/jax-herdr-hud_0.1.0-1_all.deb build/deb-test
build/deb-test/usr/bin/herdr-hud --version
apt-get --simulate install ./dist/jax-herdr-hud_0.1.0-1_all.deb
```

Set `HUD_TEST_SOURCE` to the absolute path of `build/deb-test/usr/lib/herdr-hud`
and run setup/sidebar/desktop smoke tests sequentially under `dbus-run-session`.
For the headless extension test, set `HUD_TEST_LAUNCHER` to a JSON array containing
the absolute path of `build/deb-test/usr/bin/herdr-hud`.

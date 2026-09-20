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

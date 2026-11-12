# Build and publish on GitHub

## Joint release 1.5

Ship Ubuntu and the native Apple silicon Mac app together from the same source
commit and tag `v1.5`. Keep the GitHub release in draft until both platform artifacts
are verified as described in [MACOS_VALIDATION.md](MACOS_VALIDATION.md). Do not publish an Ubuntu-only release for this version.

Ubuntu targets 26.04 / GNOME 50. The native AppKit/SwiftTerm app targets macOS 27;
it replaces the older experimental GTK/VTE Mac implementation for distribution.
The supported Mac minimum is macOS 27 on Apple silicon. Older macOS releases
are unsupported and are not publication gates (owner decision, 12 November 2026).

## Prepare the version

Set `VERSION = '1.5'` and `RELEASE_TAG = 'v1.5'` in `app_info.py` before
building. The update checker uses the release tag, including prerelease ordering.
The GNOME extension revision is separate; change it only when the extension changes.
Review [CHANGELOG.md](../CHANGELOG.md), the manual and installation guide together.

## Build

```sh
python3 scripts/build_deb.py
macos/scripts/build-dmg.sh
# Copy the tested .deb and native .dmg into the same clean output directory.
python3 scripts/release.py --output RELEASE_DIRECTORY
```

Building needs Python 3 and `dpkg-deb`, requires no root and does not install Herdr.
The Debian package uses system Python/GTK/VTE and includes the floating H extension.
The release script creates an extension ZIP, source archive and `SHA256SUMS` in
`dist`. Use a clean output directory so checksums include only intended artifacts.
All installers must include `terminal_display.py`, `terminal_themes.py`,
`theme_picker.py` and `updates.py`, plus the Ptyxis license notice.

## Verify the exact package

Run the unit suite and relevant native tests described in
[CONTRIBUTING.md](../CONTRIBUTING.md), sequentially under separate D-Bus sessions.
Extract the `.deb` with `dpkg-deb --extract PACKAGE.deb EXTRACTED_DIRECTORY`,
substituting the paths of the built package and an empty output directory.
Check the extracted `usr/bin/herdr-hud --version` and inspect the payload.
Use `apt-get --simulate install ./PACKAGE.deb` to check dependencies without installing.

For update/setup/sidebar/desktop smoke tests, set `HUD_TEST_SOURCE` to the absolute
extracted `usr/lib/herdr-hud` directory. For extension smoke, unset that variable
and set `HUD_TEST_LAUNCHER` to a JSON argv array containing the extracted launcher,
plus `HUD_TEST_EXTENSION` to the extracted extension directory. Use
`dbus-run-session` for every native smoke test. These tests use disposable servers;
never stop user Herdr servers to test an update.

Record only checks actually performed in [VALIDATION.md](VALIDATION.md).
Source test results do not establish that a new Debian artifact passed its checks.

## Publish

Commit the reviewed source and documentation, tag the same commit `v1.5`, and
push the commit and tag. Create a regular GitHub release with the approved release
notes; leave **Set as a pre-release** unchecked and mark it as the latest release.
Upload the tested `.deb`, `jax-herdr-hud-1.5-macos-arm64.dmg`, extension ZIP,
complete source archive and checksums under Assets. Verify the mounted DMG bundle
and its ad-hoc signature, and compare the installed app to the build. Keep one
installed app at `~/Applications/Herdr Hud.app`. Update publication status
in the README, changelog and validation record when done.

Use version-independent release-page links in the installation guide. Users download
`*_all.deb` under **Assets**. Keep the logout/login instruction prominent.

# Snap build and publishing guide

For the public GitHub source and native `.deb`, see [install.md](../install.md).
The preview `.deb` uses system dependencies and has a separate validation scope.

The current deliverable is a **development preview**, not an approved store
release. Read VALIDATION.md before distributing it. First target: Ubuntu 26.04,
GNOME 50, amd64, Herdr 0.9.1. No account registration or upload is automated.

## Build with Snapcraft

Use a disposable Ubuntu build machine with Snapcraft 9.1 or later and a supported
build provider. Install build tooling there following the official documentation:
https://ubuntu.com/docs/snapcraft/9/how-to/crafting/enable-classic-confinement/

```sh
snapcraft
python3 scripts/release.py --snap ./herdr-hud-alex-jax_0.1.1_amd64.snap
```

The recipe is `snap/snapcraft.yaml`, base `core26`, classic confinement, amd64.
It bundles the GUI runtime and no Herdr binary. It has no hooks or autostart service.
`grade: devel` deliberately prevents a premature stable release. After all release
checks pass, change to `grade: stable`, rebuild and retest that exact artifact.

Snapcraft execution has not been substituted with a claim that the recipe passed:
consult VALIDATION.md for the build method actually used.

## Rootless local build

On Ubuntu 26.04 amd64, when a privileged Snapcraft provider is unavailable:

```sh
python3 scripts/build_rootless.py
python3 scripts/release.py
```

Requires python3-apt, python3-yaml, dpkg-deb, glib-compile-schemas and snap's
rootless `pack` command. The builder resolves Depends/Pre-Depends (not Recommends),
uses only trusted Ubuntu APT candidates, verifies archive SHA-256 hashes and
extracts them under `build/rootless/prime`. It does not install host packages.
The package inventory records exact binary/source versions and archive URLs.
Its output is a real snap archive; it does not exercise Snapcraft's build provider,
classic linter or snapd installation. A later build may resolve newer Ubuntu updates.

## Test the artifact

In a disposable Ubuntu 26.04 GNOME desktop VM, with Herdr installed independently:

```sh
sudo snap install --dangerous --classic ./dist/herdr-hud-alex-jax_0.1.1_amd64.snap
herdr-hud-alex-jax --version
herdr-hud-alex-jax
```

Use a fresh user without python3-gi/VTE distro packages. Verify missing-Herdr
setup first; then install Herdr using its own instructions and Retry. Exercise
both the app launcher and the optional H. Do not use a real development session
for destructive Close tests.

Local extracted-runtime verification (does not replace the VM checks):

```sh
unsquashfs -d /tmp/herdr-hud-extracted dist/herdr-hud-alex-jax_0.1.1_amd64.snap
SNAP=/tmp/herdr-hud-extracted /tmp/herdr-hud-extracted/usr/bin/herdr-hud --runtime-check
python3 -m unittest discover -s tests -v
dbus-run-session -- scripts/run_packaged_test.sh /tmp/herdr-hud-extracted tests/smoke_setup.py
dbus-run-session -- scripts/run_packaged_test.sh /tmp/herdr-hud-extracted tests/smoke_sidebar.py
dbus-run-session -- scripts/run_packaged_test.sh /tmp/herdr-hud-extracted tests/smoke_desktop.py
```

The GTK tests use your display but a separate D-Bus session and temporary config.
The desktop test uses and changes the clipboard and starts/stops a disposable
Herdr server. `HUD_TEST_OUTPUT` selects a report directory; otherwise tests use
unique temporary directories. `HUD_TEST_SOURCE` selects an alternate code tree.
For the extension test, `HUD_TEST_LAUNCHER` is a JSON argv array:

```sh
SNAP=/tmp/herdr-hud-extracted HUD_TEST_LAUNCHER='["/tmp/herdr-hud-extracted/usr/bin/herdr-hud"]' \
  dbus-run-session -- python3 tests/smoke_extension.py
```

The Shell test modifies only a temporary extension copy. It must run on a separate
session bus, and uses the requested launcher instead of the installed development
copy. See GNOME_SUBMISSION.md for testing the actual extension ZIP.

## Required VM lifecycle checks

1. Start disposable default and named Herdr sessions; record their server and pane
   IDs and verify a long-running shell command survives Hud exit.
2. Set theme, divider widths and window geometry. Close Hud, install a second local
   snap revision with `sudo snap refresh --dangerous --classic <new-snap>` and
   reopen. Confirm the same Herdr sessions and preferences.
3. Exit Hud, run `sudo snap revert herdr-hud-alex-jax`, reopen and repeat checks.
4. Exit Hud and remove the snap. Confirm Herdr and its processes still run and
   preferences remain in host XDG directories. With no legacy launcher, clicking
   H should explain that the companion is missing.
5. Test with and without the extension, then install the ZIP and repeat pointer,
   lock/unlock, geometry, theme and notification checks.
6. Archive logs, exact artifact hashes and platform versions in VALIDATION.md.

## Source and third-party notices

The source tarball contains this project's complete preferred source, build scripts,
tests, license and notices. Runtime libraries have their own source obligations;
the source tarball is not their corresponding source. Before public binary
redistribution, obtain and host the exact Ubuntu source packages listed in
`runtime-packages.json`, with their original notices, alongside the binary release.
Use an Ubuntu archive with matching deb-src indexes and download each unique
`source=source_version` using `apt-get source --download-only` in a release-source
directory. If a source version is no longer available, obtain it from Ubuntu's
archive history or rebuild against available source versions; do not publish
with an incomplete source set. Keep source download instructions alongside the
binary, and retain that source for the required license periods.

## Submit to the Snap Store

1. Create/sign in to your Snapcraft publisher account; confirm the public identity
   is Alex Jax. Register `herdr-hud-alex-jax` if available. If unavailable, choose a
   new name and update the recipe, extension launcher, desktop file and docs together.
2. Make the source and runtime corresponding source publicly available at real URLs.
   Fill in the source/support links in the listing and review request.
3. Submit the completed CLASSIC_REQUEST.md through the Snapcraft forum. It explains
   terminal/development-environment access; approval is not assumed.
4. Upload the tested snap through the publisher dashboard or `snapcraft upload`.
   Record its revision, complete store review and release to beta for testers.
5. Upload the listing, icon and reviewed screenshots from STORE_LISTING.md. Clearly
   disclose existing-Herdr and separately installed-extension requirements.
6. After beta acceptance, build and validate with `grade: stable`; promote the
   approved revision to candidate and then stable. Stable is the normal App Center
   discovery channel. Do not describe the package as published before it is released.
7. Submit the extension separately using GNOME_SUBMISSION.md.

Official publication process:
https://ubuntu.com/docs/snapcraft/latest/how-to/publishing/publish-a-snap/

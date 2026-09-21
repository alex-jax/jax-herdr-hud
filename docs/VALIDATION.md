# Validation

## 1.1.1: automatic H and compact Settings — 21 September 2026

- 39 unit tests passed, including first-launch H registration, respecting GNOME
  Extensions opt-outs, and preserving unrelated extension settings.
- Native setup smoke passed: one automatic attempt per process, worker-thread
  enabling, logout/login guidance, compact Settings sections, and Credits attribution.
- Theme chooser smoke passed after removing its attribution link; all in-app
  credits now appear under the Credits icon.
- Isolated GNOME 50 extension smoke passed, including confirmation that disabling
  the extension also exits Hud. Production extension lifecycle code is unchanged.
- Settings screenshot inspected. Application icon is now a plain H in a blue
  outline with no dot; the floating H's live unread indicator is unchanged.
- Built `jax-herdr-hud_1.1.1-1_all.deb`; extracted launcher reports 1.1.1.
- Extracted Debian payload passed native setup and theme smoke tests. The packaged
  launcher and extension passed isolated GNOME 50 lifecycle/pointer smoke tests.
- Verified packaged source matches the checkout and the app icon has one blue
  circle with no badge. APT simulation accepts installation with no removals.
- Release artifacts: native Debian installer, source archive, extension ZIP and
  SHA256SUMS. The release does not install or restart the local app. Clean-VM
  installation and upgrade/removal were not tested.


## 1.1.0 — 21 September 2026

Target: Ubuntu 26.04 / GNOME Shell 50, amd64, stock Herdr 0.9.1.

- All 37 Python unit tests passed, including palette definitions, fragmented
  ANSI/indexed/RGB preservation, backend, updater and Debian payload checks.
- Built `jax-herdr-hud_1.1.0-1_all.deb`. Extracted launcher reports 1.1.0.
- Theme chooser smoke passed against the exact extracted Debian payload:
  fresh GNOME Dark, GNOME Light toggle, 244 palettes, search, selection persistence,
  classic palette and whole-window styling. Light/dark previews inspected.
- Extracted sidebar smoke passed. The test now waits for a newly populated agent
  list to receive its layout before dispatching its synthetic pointer click;
  an initial run clicked before the row was ready.
- Extracted real desktop smoke passed: live ANSI color output verified in VTE,
  palette changes preserve attachments, CLI mouse controls, clipboard, agent
  reports, workspace operations, last-terminal removal and safe detachment.
- Extracted setup smoke passed, including release version and Christian Hergert /
  Ptyxis attribution in About. All palette modules and license notices are bundled.
- APT simulation upgrades 1.0.0-1 to 1.1.0-1 without removing packages.
- `git diff --check` passed. Simulated-menu and isolated-session shutdown warnings
  remain present. The unchanged extension retains its previous validation below.

These checks do not replace clean-VM install, upgrade and removal testing.
This release was built and tested without replacing the user's installed app.

## Validation for the 1.0.0 release

Status: source and Debian payload checks passed for stable release `v1.0.0`. Target: Ubuntu 26.04 / GNOME Shell 50, amd64, Herdr 0.9.1.

## Checks completed

- Python unit suite: 35 tests passed in the public checkout. This includes display
  filtering across fragmented ANSI sequences, RGB/indexed colors, preserved controls,
  hyperlinks and color queries, alongside backend, update and packaging tests.
- Native desktop smoke passed with stock Herdr: cold startup, input and arrow keys,
  Shift+drag copy, right-click paste, CLI mouse press/release, theme switching, agent
  reports, notifications, workspace creation, rename, close and safe detachment.
- Native sidebar smoke passed: compact groups, search, collapse, focus and menus,
  including confirmation/cancellation of agent closure and empty-space recovery.
- Disposable Codex, Grok, Claude Code and agy sessions were visually checked in both
  Hud themes. The final display filter does not require the experimental Herdr theme
  synchronization build.
- Header layout measurement confirmed equal 6-pixel button gaps in light and dark
  themes, with the update arrow both shown and hidden.
- Installed Hud was restarted locally after the display change. All three existing
  pane IDs and shell PIDs were preserved.

Early desktop attempts timed out while typing before the attach client was ready.
The smoke test now waits for a visible shell prompt; the subsequent run passed.
Simulated menu and isolated desktop-service shutdown warnings were present.

## Debian 1.0.0 package checks

- Built `jax-herdr-hud_1.0.0-1_all.deb`; extracted launcher reports `Herdr Hud 1.0.0`.
- APT simulation resolves dependencies without removing packages.
- Update, setup, sidebar and desktop smoke tests passed against the extracted payload.
- Isolated GNOME 50 extension smoke passed with the extracted launcher and extension:
  click/drag input, grab cleanup, window geometry, theme, D-Bus and disable lifecycle.
- Four JavaScript extension-launcher tests passed.
- Upgrade comparison covers stable `v1.0.0` replacing `v0.1.2-preview.1`.
- Relative documentation links resolve and `git diff --check` passes.

The first package desktop runs exposed outdated expectations for the old `~` label
and blank new-space dialog. Tests now verify `Space 1`, the suggested `Space 2`
name and rejection of blank names. The final desktop run passed. No application
code was changed to bypass those checks. Service-shutdown and simulated-menu
warnings remain present in the isolated logs.

Clean-VM install/upgrade/removal and other architectures/desktops remain unverified.
See [PUBLISHING.md](PUBLISHING.md) for publication and
[CONTRIBUTING.md](../CONTRIBUTING.md) for test commands.

## Six-hour updater verification

Unit checks cover the six-hour interval, verified asset download, rejection of
foreign URLs, checksum/package mismatches and cancelled authorization. GTK update
smoke checks the click-to-install worker and inline success handling. Downloads
and privileged installation are mocked: no live upgrade or password prompt was
triggered during these tests. The Debian package now depends on `pkexec`.

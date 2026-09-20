# Validation for the 1.0.0 release

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

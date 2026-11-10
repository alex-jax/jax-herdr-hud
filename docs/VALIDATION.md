# Validation

## Ubuntu 1.4 source and local Debian build — 10 November 2026

- 57 unit tests passed after updating version metadata to 1.4/v1.4, including
  release checksums, Debian payload layout and agent startup command arguments.
- Built and extracted `jax-herdr-hud_1.4-1_all.deb`; the extracted launcher
  reports Herdr Hud 1.4. APT simulation upgrades only Hud, with no new dependency
  packages or removals.
- Exact Debian SHA256:
  `d4debe562dce10a0fd5c548e9025d1c5f9d0ddeb40a69997cb7f3fc31d98bfb3`.
- Installed this exact package locally as 1.4-1, compared installed hud.py,
  backend.py and app_info.py with source, confirmed the launcher reports 1.4,
  and restarted Hud. Herdr servers and user agents were preserved.
- The extracted 1.4 payload passed desktop, sidebar, theme and update smoke
  tests on separate D-Bus sessions. Desktop coverage includes a first right-click
  paste from an external clipboard owner while focus starts outside the terminal.
- Ran desktop smoke with `HUD_TEST_REAL_CODEX=1`: the installed Codex launched
  successfully in a disposable new workspace using the root pane ID. The test
  submitted no agent task and cleaned up its test server, leaving user servers
  alone. The default smoke run still mocks agent startup.
- Sidebar checks cover retaining a shell-reported identity when an agent takes
  over its title, isolation across servers with the same terminal ID, local
  identity fallback, and tooltips containing only user@host. Theme smoke covers
  active palette and light/dark switching.
- During source development, native selection, controlled retained-history
  fallback, and simulated CLI edge selection passed. Physical-pointer checks
  were inconsistent on this desktop: an initial downward run passed, but
  subsequent runs and upward runs did not reliably pass. No claim of complete
  physical-pointer coverage or clean-VM upgrade/removal validation is made.
- This version changes Ubuntu code only. Mac parity is proposed in
  [issue #3](https://github.com/alex-jax/jax-herdr-hud/issues/3); no Mac artifact
  was built or tested. Commit/push of 1.4 source does not publish GitHub Release
  assets; the latest published release remains v1.3.

## Ubuntu 1.4 auto-hide follow-up — 10 November 2026

- Added the saved `hide_on_focus_loss` preference and Settings → Floating H
  switch, enabled by default. Hiding preserves the companion, terminal clients,
  monitoring and agents. Open menus/transient dialogs suspend automatic hiding.
- 57 unit tests and the source desktop smoke passed. A new native GTK focus
  test checks auto-hide on outside focus, showing Hud again, disabling the
  behavior, preference persistence, transient-dialog protection and timer cleanup.
  Its first run timed out waiting for window focus; two subsequent source runs
  and the extracted-payload run passed. This test needs a working window manager.
- Rebuilt 1.4-1 with this follow-up. The extracted payload passed the focus test
  and theme smoke. SHA256 of the updated Debian artifact:
  `3b22ad66d286664be5602825c1fbd2d61dae0174bf20e69cb1d7e8d4c096dede`.
- Installed the updated package locally, confirmed hud.py matches the tested
  source and restarted Hud. The GNOME extension is unchanged; no desktop
  logout/login was performed. Mac parity was added to issue #3.

## 1.3 stable Debian release — 2 November 2026

Target: Ubuntu 26.04 / GNOME Shell 50, amd64, Herdr 0.9.1. The v1.3 release is
Debian-only; the Mac installer remains pending its separate manual gates.

- 54 unit tests passed, including package layout, update handling, platform
  portability and release checksum coverage.
- Built `jax-herdr-hud_1.3-1_all.deb`; extracted launcher reports Herdr Hud 1.3.
  APT dependency simulation proposed no package changes.
- The exact extracted Debian payload passed setup, theme, update, sidebar,
  real Herdr desktop and link smoke tests. The packaged extension passed the
  isolated GNOME 50 lifecycle and pointer smoke test.
- Release checksums verified for the `.deb`, extension ZIP and source archive.
  The local `1.3-1` installation was restarted during this release task, and its
  app modules match the extracted release payload. Existing Herdr sessions were
  retained.
- No Mac installer is included. Hands-on Mac validation remains pending; see
  [Mac validation](MACOS_VALIDATION.md).

## 1.3 Mac development validation — 28 September 2026

- Apple silicon runtime gate passed on macOS 26.6.2: native Quartz GTK/VTE,
  PTY output, frozen runtime launch and strict bundle signature verification.
  [Runtime workflow](https://github.com/alex-jax/jax-herdr-hud/actions/runs/36470757930).
- Linux: 53 unit tests passed. Source setup, updates, themes, sidebar, real Herdr
  desktop and link smoke tests passed, sequentially under separate session buses.
- The extracted 1.3 Debian payload passed theme, update and real Herdr desktop
  smoke checks. Installed that Debian package locally, restarted only Hud,
  verified installed application files match source and confirmed the existing
  Herdr server remained running. The app starts successfully as version 1.3.
- The isolated GNOME 50 extension smoke passed against the installed companion:
  pointer clicks/drag/Escape, accent changes, geometry, D-Bus messages and exit.
- The final test DMG from `96d9cf9` passed automated bundled-app and real Herdr
  integration on macOS 26.6.2 and 27.0, with Homebrew unavailable. This includes
  arm64/dependency/signature/identity audits, clipboard, themes, floating H,
  singleton launch, matching bundled terminal font metrics and session survival.
  [Workflow](https://github.com/alex-jax/jax-herdr-hud/actions/runs/36475705812).
- Hands-on Mac installation, complete visual/interaction parity, multiple monitors,
  lock/sleep, login startup and replacement/removal remain pending on both versions.
  The checksum and release checklist are in [Mac validation](MACOS_VALIDATION.md).

## 1.2 — 28 September 2026

Target: Ubuntu 26.04 / GNOME Shell 50, amd64, Herdr 0.9.1.

- Normal drag copies plain text; Shift+click sends unmodified CLI mouse input.
  Real-pointer tests move beyond both borders and verify copied lines remain
  contiguous, exceed the viewport, and stop extending after release.
- Tests cover both retained Herdr history and a full-screen CLI which accepts
  wheel events only over its transcript. VTE's cached pointer position must be
  moved to the transcript before scrolling; scroll-event coordinates alone do
  not control the emitted mouse report.
- The original colored VTE stays visible and focused while CLI selection grows.
  Release finishes selection immediately, without a text-only view or Escape.
  Tests verify that the terminal layout does not change.
- Tested the user's existing Codex pane on Wayland without submitting input or
  stopping its agent/server. The final live-terminal implementation copied 53
  lines downward from a 29-row viewport and retained focus on release.
- Unit coverage includes changing CLI footer controls, fragmented SGR color
  pairs, OSC hyperlink preservation, backend behavior and distribution.
- Native desktop coverage includes text paste, CLI mouse input, themes, agent
  tracking, space closure and detaching without stopping user sessions.
- Link smoke tests exercise plain URLs and OSC 8 links through a recorded desktop
  URI launcher. They do not launch a real external browser.
- Theme smoke tests check VS Code Dark for fresh preferences, its light variant,
  chooser filtering and preservation of saved palette/appearance choices.

Release checks (28 September 2026): 47 unit tests passed, including two-part
version ordering, legacy-version compatibility and future update discovery.
Source theme and link smoke checks passed during PR verification. The 1.2 Debian
payload passed theme and real Herdr desktop smoke checks; after the version-parser
change, the rebuilt final payload passed the update smoke check. Installed
`jax-herdr-hud_1.2-1_all.deb` locally, verified installed application modules
against source, confirmed the launcher reports 1.2, and restarted Hud successfully.
Existing user sessions were retained.

Limitations: no automated end-to-end test of every vendor CLI or the Voquill app;
no clean-VM installation/upgrade/removal test. The older update checker cannot
recognize two-part release tags, so existing users must download 1.2 manually.

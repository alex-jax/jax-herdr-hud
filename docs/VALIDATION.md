# Validation

## Widget gestures and outside-click hiding — 11 November 2026

On Ubuntu 26.04 ARM64 with GNOME Shell 50, a disposable headless Wayland
session exercised widget click and drag, corner resizing, and subsequent
desktop-background hiding with a virtual pointer. The checks passed against
both source and the extracted Debian companion and extension. The auto-hide
smoke checked the disabled preference and protected dialogs. The Python suite
passed 58 tests; GTK sidebar, desktop, titlebar and resize smokes passed, as did
six JavaScript gesture and window-grab checks. The separate full extension smoke
timed out during headless Shell startup; physical hardware and pointer behavior
remain separate acceptance checks.

The locally installed Debian artifact had SHA-256
`667acdba343257a851cf18e603e6757b3753d439050c998d7e4636bf846ce671`.
Installed companion and extension files matched the extracted payload, Hud
restarted successfully, and the running Herdr server and session were preserved.
GNOME Shell loaded extension revision 7 after reconnecting the session.

For the final source and documentation, the Debian artifact with SHA-256
`39e17e055099304ea05e7669901c666e774556b952d845aace07b933a42cee24`
passed extracted GTK auto-hide, titlebar, resize, sidebar and real-Herdr desktop
smokes, and was installed and restarted locally. Its companion and extension
matched the previously Wayland-tested artifact. Two attempts to repeat the
Wayland smoke against this final artifact timed out during headless Shell startup;
they do not constitute a passing Wayland run for this exact artifact. Installed
files matched the extracted payload and the existing Herdr server remained up.


## Ubuntu 1.4 and Herdr 0.9.5 on ARM64 — 11 November 2026

On Ubuntu 26.04.1 / GNOME Shell 50.1 in the Apple silicon VM, the integrated
1.4 source passed 58 unit tests and four JavaScript launcher tests. Setup,
sidebar, auto-hide and real Herdr desktop smoke tests passed against an
extracted 1.4 Debian payload. After a documentation-only package rebuild, the
final extracted package again passed setup and desktop smoke; its app modules
and extension files matched the previously tested payload. Final package SHA-256:
`33daab85bda40995891461933ec12946d9caa3d5c539eeeb0c22067239c45809`.

The package was installed inside the VM, its installed app modules and extension
files matched the extracted payload, and Hud restarted while the existing
Herdr 0.9.5 server and session were preserved. GNOME extension revision 5 was
installed on disk; the desktop still had revision 4 loaded and needs a fresh
login to load it. The isolated headless GNOME test for revision 5 did not pass
in the VM: an initial run encountered a stale test compositor and a retry timed
out. Earlier revision 4 runs also failed synthetic pointer checks. These
results do not establish physical pointer behavior, amd64 compatibility, or a
clean-machine installation. No GitHub release was published by this work.

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

## Ubuntu 1.4 widget toggle follow-up — 10 November 2026

- Clarified the switch label and help text: it controls automatic hiding only;
  clicking H always opens or hides Hud.
- Extension revision 5 captures visibility before taking the pointer grab and
  sends an explicit hide/show action on release. This prevents an auto-hide
  between press and release from reopening Hud.
- 57 unit tests, four JavaScript launcher tests and the isolated GNOME 50
  extension smoke passed. A new real-pointer regression forces hiding between
  press/release and verifies that Hud stays hidden, then opens on the next click.
- The exact extracted Debian companion and extension passed the full isolated
  extension smoke, including geometry, dragging and lifecycle checks. Package
  SHA256: `de794ca6fc1c6b8f89523b9eb17a784844ed68f928b175c301db0ab21b5cf713`.
- Installed this package locally, verified companion/extension files against
  source and restarted Hud. The current desktop had extension revision 4
  loaded; logout/login is required to load revision 5 under the GNOME 50
  workflow. The user's desktop session was not restarted during verification.

## Herdr 0.9.5 on Ubuntu ARM64 — 11 November 2026

Ubuntu 26.04.1 / GNOME Shell 50.1 ran in an Apple Virtualization Framework VM
on Apple silicon (ARM64). Herdr 0.9.5 and the public v1.3 Debian package were
verified using their release SHA-256 digests before installation. Source unit
checks passed: 55 tests. Against the installed release payload, the GTK sidebar
smoke and the real Herdr desktop integration smoke passed. The original desktop
agent fixture failed because Herdr clears self-reported agents in idle shells;
keeping a disposable foreground process alive corrected the fixture.

The installed extension loaded and could be enabled in a separate headless
GNOME session, but its synthetic pointer grab assertion failed twice in this VM.
The headless overview remained visible and the virtual pointer was not at the
requested position. A further instrumented run stalled during shell startup. This
is not a passing extension lifecycle or pointer test; the cause has not been
established. The VM checks do not validate amd64, a clean physical Ubuntu
installation, or every Herdr agent/CLI.

The current source adds 0.9.5 to its tested core-integration messages; the public
v1.3 release itself is unchanged. A locally rebuilt `1.3-1` Debian package has
SHA-256 `71d75337774291cdd74f6fb5a174a59f683ac9135aa7daa02f859fa8a427ada7`.
The source unit suite passed 55 tests, and the extracted package passed setup,
sidebar and desktop integration smoke tests with Herdr 0.9.5. Its extension
smoke timed out in the separate headless GNOME session. The rebuilt package was
installed inside the VM, and its installed launcher, app modules and extension
files matched the extracted payload. Hud started and attached to Herdr 0.9.5.
After a graphical session restart, the extension was ACTIVE, its D-Bus bridge
responded, and both the Hud window and H were visible. The existing test server
remained running across that session restart. Physical pointer/drag behavior was
not verified by those checks, and this VM installation was not a release or an
amd64 validation.

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

### Saved SSH machines — 11 November 2026 (unpublished working tree)

Implemented saved-machine discovery, per-machine SSH Unix-socket tunnels,
three-second remote snapshot polling, native remote terminal attach, disconnected
row/input handling, and bounded SSH display-relay shutdown. No remote server is
installed, started, restarted or stopped by this feature. Plain SSH shells are
not adopted as remote Herdr panes.

Actual checks:

- Ubuntu `ubuntu-hud` VM: 62 unit tests passed.
- Ubuntu sidebar smoke passed, including two Codex entries and a remote outage /
  recovery case retaining row identity. These agent snapshots are mocked.
- macOS: 7 backend and 4 remote unit tests passed.
- macOS -> Morpheus: real read-only SSH snapshot returned three panes and one
  Codex agent; stopping the tunnel preserved the server.
- `tests/smoke_remote.py`, macOS -> disposable Ubuntu VM session: real remote
  API, native terminal attach through the display relay, keyboard input, safe
  detach, and forced tunnel failure/reconnection preserving terminal identity
  all passed. The test uses a shell, not a live Codex task.
- Final Debian package built and installed in the Ubuntu VM; installed
  backend/hud/relay files compared with source. Desktop smoke against installed
  Python payload passed, including attachment and safe detachment.
- Final package SHA-256:
  `3cef11b451ceb1fcf9ae8fb9f833ad546c725780d3613bb30d256fcc0cd89674`.
- `git diff --check` passed.

The final package is staged in Morpheus's Downloads folder. SSH installation
could not authenticate (`No authentication agent found`); user installation is
pending. No GitHub release was published. Full macOS GUI validation and a new
Mac application bundle were not performed; host Python lacks GI. Real two-Codex
remote lifecycle testing remains outstanding. Existing v8 Codex session-hook
errors on Morpheus have not been diagnosed or changed by this feature.

### Ubuntu 1.5 release candidate — 11 November 2026

The versioned 1.5 Debian artifact passed 62 unit tests and sequential GTK sidebar
and desktop smoke tests against its extracted payload. Ten JavaScript extension
launcher/pointer/window-grab tests passed. It was installed in the local Ubuntu
VM; installed backend, Hud and display-relay files matched source. The restarted
Hud user service remained active, the Herdr server retained PID 2652, and the
session inventory was identical before and after the companion restart.

Exact Debian SHA-256:
`3564dd66b4ea1abc065f72f7ae83c5db4ffda1db76cfd4ebcc5b81f284c806a7`.

This release includes the previously validated SSH transport and recovery tests
above. No new Mac installer is included. Morpheus installation is deliberately
left to the user's local Codex, as requested; it is not a release prerequisite.

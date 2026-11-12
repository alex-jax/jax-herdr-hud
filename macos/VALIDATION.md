# macOS validation — 24 September 2026

## Outside-click hiding — 11 November 2026

On macOS 27.2 arm64, HudCoreChecks and the debug desktop smoke passed with a
disposable Herdr 0.9.5 server. The smoke exercises the outside-click handler,
including the widget exclusion and hiding without quitting; it does not inject
an actual system-wide mouse event. The signed release app was built, installed,
compared to the build and restarted. The existing Herdr session remained active.

Before the 1.4 source update, HudCoreChecks and the debug desktop smoke passed
again. The release bundle was rebuilt, signature-checked, installed, compared
to the build and restarted; the existing Herdr session remained active.

## Ubuntu reference appearance and 1.4 source — 11 November 2026

On macOS 27.2 arm64, the native app was compared with the Ubuntu 26.04 VM
reference. Sidebar list backgrounds now extend to the panel edges; dividers
draw as one-pixel lines while retaining their six-pixel drag area. The header
uses bundled Adwaita symbolic icons, and the UI uses the reference environment's
DejaVu Sans fallback. The same Ubuntu Mono font used in the VM and a 9 × 19
logical-pixel terminal grid are used for live and retained-history views.
These measurements do not establish identical rasterization on all displays.

The debug build passed core checks and five consecutive 0.9.5 desktop smoke
runs with simulated selection and controlled live CLI scrolling after adding a
shell-readiness handshake. A further run without diagnostic logging passed.
Earlier runs without that handshake intermittently timed out in the controlled
CLI and once lost the sidebar selection during a theme change. The theme path
now restores selection, and the visual smoke checks it. The physical-pointer
run could not proceed because macOS Accessibility permission was unavailable;
physical dragging in either direction remains unverified for this change.

The 1.4 release bundle was built, signature-checked, installed locally and
restarted. The installed files matched the build, the app attached to the
existing terminal, and the running Herdr session list remained unchanged. The
client was 0.9.5 and the preserved existing server reported 0.9.1.


Environment: macOS 27.0 (26A428), arm64, Apple Swift 6.4 Command Line Tools,
Herdr 0.9.1. Ubuntu source baseline: `2689465`.

## Completed

- Standalone `HudCoreChecks`: passed attention transitions, environment and
  executable selection, malformed preference recovery, fragmented streaming color
  sequences, Unix socket fragmentation/API errors/EOF, invalid snapshots,
  cross-server identity, and first-workspace close protection.
- Debug desktop harness with a unique disposable Herdr server: passed real terminal
  input/output, copy/paste and selection clearing, PTY resizing, all 244 bundled
  palettes plus Hud classic, search without reattachment, agent subscriptions and
  unread acknowledgment, workspace/pane/tab rename, secondary-space close,
  safe detach/reattach, sidebar collapse/restore without overlapping the terminal,
  saved preferences, offscreen geometry recovery, and simulated inactive-session
  hiding of the floating H. The harness stopped only its disposable server.
- Optimized release build and local ad-hoc code signing completed. Dynamic library
  inspection showed macOS system libraries; GTK/Python/Homebrew libraries are not
  runtime dependencies.
- Installed to `~/Applications/Herdr Hud.app` and launched from its bundle. Visually
  inspected the native sidebar, terminal output, and searchable palette Settings.
  Confirmed Settings follows Hud's dark appearance and used the installed window's
  Expand/Restore control to verify it returns to its normal dimensions.

The original XCTest attempt could not run because this machine has Command Line
Tools rather than full Xcode. The maintained core-check executable supplies the
checks without requiring XCTest.

## Not established by these checks

Physical lock/unlock, actual login startup, monitor hot-plug, other macOS builds,
Intel Macs, and public notarized distribution have not been verified. Simulated
activity/geometry checks do not establish those behaviors. The local build is a
preview and is not a signed public release.

Raw run outputs are in `/private/tmp/herdr-hud-core-checks.log`,
`/private/tmp/herdr-hud-smoke-result.txt`, and `/private/tmp/herdr-hud-release.log`.
These temporary files may be removed by macOS; this record describes the completed
run rather than claiming that archived logs prove later changes.


## GNOME appearance and floating H revision — 24 September 2026

- Rebuilt the AppKit header, sidebar, terminal framing, embedded Settings, and
  palette grid from the GNOME source layout and color formulas. Bundled Ubuntu
  Regular/Bold and Ubuntu Mono with their licence.
- Debug and optimized release builds completed with local code signing. Inspected
  the installed main window, embedded Settings, and theme preview grid through
  the desktop UI. Corrected clipped sidebar controls, font selection, and icon
  orientation found during that inspection.
- Replaced manual bubble movement with `NSWindow.performDrag(with:)` using the
  original mouse-down event. The H accepts the first press when inactive, tracks
  release even if WindowServer consumes mouse-up, clamps to a visible screen,
  and saves its position. Confirmed H's accessibility press reopens the window.
- The desktop automation tool could inspect the floating panel but rejected
  pointer drags with `noWindowsAvailable`; physical dragging is not established
  by this run. No automated test suites were run for this revision. Earlier test
  results above describe the original port, not these appearance changes.
- No Herdr servers, shells, or agent sessions were stopped during installation.


## Terminal attachment resource cleanup — 24 September 2026

Investigated `Could not attach: forkFailed(24)` on the installed app. Darwin's
`EMFILE` is errno 24 (too many open files). The affected Hud process had 2,547
pipe descriptors after approximately 93 minutes of uptime. Session discovery
calls `Host.run` repeatedly from a dispatch block that stays alive; Process/Pipe
objects had no per-call autorelease pool or explicit descriptor cleanup.

`Host.run` now scopes Foundation temporaries to one command, explicitly closes
both pipe ends on every return/throw, and closes the parent's write handles once
the child starts. Reader workers have their own autorelease pools. Attachment
errors now explain resource exhaustion and preserve the existing Herdr terminal;
stale termination callbacks cannot mark a replacement attachment disconnected.

The optimized release build and code signature completed successfully. Installed
and relaunched only Hud; the default Herdr server remained running at the same
socket. The first descriptor inspection of the updated process showed 4 pipes.
No automated test suites were added or run for this change. This observation is
not a long-duration stress result.


## Selected-row and paste-highlight contrast — 24 September 2026

Captured the running Hud window and read the affected pane's ANSI output without
sending input. The pane used inverse video for its selected resume-list row.
A read-only stream observer confirmed that Herdr encodes this as explicit RGB
black text on white. Hud's previous background filter discarded the white,
leaving black text against the dark Nord background.

The Mac display filter now tracks SGR foreground, background, bold, dim, and
inverse state. It preserves an explicit background when replacing it would reduce
text contrast below 3:1 and the original background provides better contrast.
Foreground colors and non-color controls remain intact. Foreground-only changes
re-evaluate the background; reset/reconnect preserve the palette configuration.
SwiftTerm's local selection colors also follow the Hud palette.

- `swift run --package-path macos HudCoreChecks`: passed existing core checks and
  new regressions for Herdr's flattened inverse highlight, every packet split,
  separate color updates, resets, ANSI/indexed/RGB colors, colon syntax, dim and
  inverse attributes, light themes, malformed sequences, and paste controls.
- Release build and code signature succeeded; installed and relaunched Hud.
- A fresh screenshot of the same live selected row confirmed readable black text
  on its retained white highlight. Herdr's session and pane were preserved.
- The pasted-text issue uses the same color handling. No text was pasted into the
  user's live agent during this check. The full desktop smoke suite was not run.

Local diagnostic captures: `/private/tmp/herdr-hud-contrast-before.png`,
`/private/tmp/herdr-hud-contrast-after.png`. Core output:
`/private/tmp/herdr-hud-contrast-checks.log`. These are temporary local files.

## Ubuntu 1.2 parity update — 2 November 2026

Environment: macOS 27.2 (26B123), arm64, Swift 6.4.2 Command Line Tools,
Herdr 0.9.1. Ubuntu source baseline: `a8a2066`. Native bundle version 1.2,
build 2. This update is confined to the native Mac port and its documentation;
Ubuntu Debian installation and GNOME smoke tests do not apply to this build.

Completed for this update:

- `swift run --package-path macos HudCoreChecks`: passed attention, executable
  discovery/environment, malformed and saved preferences, fresh VS Code Dark
  defaults, streaming color/control fragmentation, preserved SGR pairs and OSC 8
  links, suppressed OSC palette assignments, history overlap in both directions
  with pinned/changed controls, rejected unrelated redraws/blank overlaps, Unix
  socket fragmentation/errors, and identity/close guards.
- Debug bundle `--smoke-test`: passed automatic plain-text selection/copy,
  press-time selection versus CLI mouse routing while Shift changes, text paste,
  image-only paste fallback, plain/OSC 8 link activation, secondary Control-click,
  retained shell history, live CLI history in both directions, release timer cleanup,
  immediate typing/focus, and header focus restoration. An in-process renderer
  fixture checks redraw matching; a separate raw-mode Python CLI on the disposable
  real Herdr server verifies wheel reports, transcript copy, focus, and release
  cleanup through the native attachment in both directions.
- The same harness passed real Herdr terminal input/output, clipboard paste,
  resize, all 245 palettes, search without reattachment, attention/unread handling,
  rename/close, safe detach/reattach, sidebar layout, saved preferences, offscreen
  geometry recovery on a connected screen, and simulated inactive-session hiding.
  Only its uniquely named disposable server was stopped. The clipboard was restored.
- Optimized release bundle built and its ad-hoc signature verified. Installed to
  `~/Applications/Herdr Hud.app` and restarted only Hud. Compared SHA-256 hashes of
  every installed bundle file against the release bundle; all matched. The installed
  app reports version 1.2/build 2 and stayed running. A desktop screenshot confirmed
  the native window rendered the existing agent terminal and its colors.
- Compared the real Herdr session list before and after installation: unchanged.
  No user Herdr server, terminal, shell, or agent was stopped for the update.

The pointer tests dispatch synthetic AppKit events; they are not physical pointer
acceptance tests. Actual lock/login and monitor hot-plug behavior, Intel Macs,
other macOS builds, Developer ID signing, and notarization are not established.
The CLI fixture establishes the wheel/selection round trip, not compatibility
with every third-party interactive CLI. The native Mac app still uses manual DMG
updates. The release build excludes the debug harness and its input observers.

Current run logs are `/private/tmp/herdr-hud-1.2-core.log`,
`/private/tmp/herdr-hud-1.2-debug.log`, `/private/tmp/herdr-hud-1.2-smoke.log`,
`/private/tmp/herdr-hud-1.2-release.log`, and `/private/tmp/herdr-hud-1.2-install.log`.
These temporary outputs are not shipped. Publication status is separate from
local build/install validation; no public notarized release is claimed here.

## GitHub release and update cleanup — 2 November 2026

Per the project owner's distribution decision, the Mac app is released as version
1.2 without a preview designation. The app uses an ad-hoc signature, with factual
first-launch guidance in the DMG. Developer ID enrollment/notarization is not part
of this project's publication workflow. Internal bundle build number is now 3.

- Core checks passed again after updating release branding. Terminal behavior is
  unchanged from the tested Ubuntu 1.2 parity update above; this follow-up changes
  release branding, packaging, and the local installer.
- Built the optimized release and installed it locally. Verified every installed
  file against the build bundle and verified its code signature. Hud launched
  successfully as version 1.2/build 3, with the Herdr session list unchanged.
- Replaced launchable backup app bundles with verified ZIP archives. Existing
  generated backup and old build copies were archived, unregistered from
  LaunchServices, and removed from their old paths. A second installer run passed
  without recreating launchable backup apps. Cleanup is idempotent.
- Spotlight returned exactly one Hud app: `~/Applications/Herdr Hud.app`.
  Build bundles now live in `macos/dist/build.noindex`; ZIP backups live in
  `macos/dist/backups.noindex`. The installer stages/verifies the new bundle,
  waits for only Hud to quit, keeps a checked ZIP backup, and refreshes app
  registration. No Herdr servers or terminals were stopped.
- `bash -n` passed for build-app.sh, build-dmg.sh, and install-app.sh; the cleanup
  helper compiled and ran successfully against the generated duplicate bundles.

The existing Debian 1.2 artifact is retained. This Mac packaging update does not
claim a new Debian build or a new run of Ubuntu/GNOME integration tests.

## Edge selection update — 9 November 2026

On macOS 27.2 arm64 with Herdr 0.9.1, the debug desktop smoke passed with
simulated drag events at both terminal edges against a disposable real Herdr CLI
that did not report an agent. It also checked delayed retained-history loading,
copying, focus and stopping on release. A separate system-level pointer run could
not complete because the test app lacked macOS Accessibility permission; it does
not establish physical pointer behavior. The release bundle was built locally.


## Herdr 0.9.5 compatibility — 11 November 2026

On macOS 27.2 arm64, the current native source passed `HudCoreChecks` and
three consecutive debug desktop smoke runs against a disposable Herdr 0.9.5
server. The same smoke also passed against Herdr 0.9.1. These exercised native
attachment, input, output, resize, clipboard, search, workspace operations,
agent state/unread handling, and detach/reattach. The smoke simulates agent
reports; a separate isolated 0.9.5 session ran a real Codex request, during
which the user observed a stable background. This is one visual observation,
not proof that flicker cannot recur.

The previous agent fixture reported an agent while its pane was an idle shell.
Herdr 0.9.5 promptly cleared that report, causing intermittent smoke timeouts.
The fixture now waits for a disposable foreground process before reporting the
agent, matching the 0.9.2+ behavior. The display filters preserve synchronized
output controls even when fragmented. A disposable 0.9.1 server also accepted
a 0.9.5 client for discovery, direct terminal attachment and input/output.

These checks do not validate Ubuntu with Herdr 0.9.5, macOS 26, a published
DMG, or physical pointer, lock, sleep and multi-monitor behavior. The previously
published release was not changed.

The release bundle was built and installed locally. Its signature and contents
matched the build, it launched and attached to the existing terminal, and the
running session list was unchanged. The installed client is 0.9.5; the preserved
existing server still reports 0.9.1. The older client executable was backed up.

The Python display-filter tests passed (8 tests). Full Python unittest discovery
on macOS ran 45 tests with 7 failures and 4 errors: Linux packaging/GTK tools
(`dpkg-deb`, `gi`) are unavailable here, while Linux-specific update and PATH
expectations differ on macOS. This does not constitute Ubuntu validation.


## Joint 1.5 candidate — 11 November 2026

Environment: macOS 27.2 (26B123), arm64, Herdr 0.9.5. The native Mac build
now implements saved remote machines, optional agent launch in new spaces,
remembered identities, saved auto-hide control and GitHub update discovery/download.

- HudCoreChecks passed, including remote argument quoting/routing, working-directory
  fallback, version/asset selection and invalid update metadata rejection.
- The debug desktop smoke passed with two real Codex CLI agents in distinct panes;
  both appeared as separate agent shortcuts. Only the disposable test server was stopped.
- Live SSH into a disposable Ubuntu VM session passed snapshot discovery, workspace
  creation, native SwiftTerm remote attachment, keyboard/output round trip, safe
  detach with the pane retained, and label rename with stable socket identity.
- The desktop harness also exercised existing palette, selection/history, focus,
  clipboard, attention, rename/close and geometry behavior. Disabling automatic
  hiding was checked. Synthetic events do not establish physical-pointer parity.
- Built and installed the optimized ad-hoc signed app in `~/Applications`, verified
  its signature and launch, and compared Herdr inventories before/after: unchanged.
  The installed New space dialog visibly exposes the optional agent checkbox,
  kind selector and agent name field; it was cancelled without creating a session.
- Disk-image integrity verification passed. The release is still a draft.

Update version/metadata logic was tested locally; no newer public native release
exists yet to exercise an end-to-end update download. Actual lock/login, multiple
monitor hot-plug, and macOS 26 are not established. The native deployment target is
macOS 27. The root requirement for both macOS 26 and 27 validation remains a
publication blocker pending the owner's platform-support decision.

Logs: `/tmp/hud-mac-core-final.log`, `/tmp/hud-mac-parity-smoke-final.log`,
`/tmp/hud-mac-15-release-build.log`, `/tmp/hud-mac-15-install.log`.


## Joint publication approval — 12 November 2026

The owner approved publishing Ubuntu and native Apple silicon macOS 27+ together,
without testing older macOS versions. This resolves the platform-support gate
recorded above. The previously tested installers are retained byte-for-byte;
this follow-up changes release documentation and the source archive only. Embedded
candidate documentation reflects their build date; current release scope is 27+.
No new application tests, installation or desktop restart were needed for prose changes.

## Window menu and display movement — 12 November 2026

Added Window → Move to Display, listing connected monitors by number and name,
checking the current monitor and resolving display IDs again when selected.
Movement restores normal dimensions from an expanded window, fits and centers it
inside the destination's usable frame and saves placement. H placement is separate.

On macOS 27.2 arm64, HudCoreChecks passed. The debug desktop harness exercised the
menu actions across three connected PL2493H displays (left, main, right), verified
window containment, unchanged terminal instance/selection and saved geometry.
A synthetic smaller display above/left verified fitting with negative coordinates.
The first full smoke run timed out in the existing real CLI wheel-direction test;
an unchanged rerun passed the full harness, including the new monitor checks.
This does not establish physical monitor hot-plug or every desktop arrangement.

Ubuntu source inspection confirmed its native GTK titlebar and the existing
move/resize auto-hide guard. No physical multi-monitor Ubuntu test was performed.

Built and installed the optimized app at `~/Applications/Herdr Hud.app`, verified
its ad-hoc signature and every installed file against the release build, and
confirmed successful launch with an identical Herdr session inventory. Only Hud
was restarted. This change has not been added to a public release.

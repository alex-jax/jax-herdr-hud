# macOS release validation

Target: Apple silicon, macOS 26 and 27. The reference is Ubuntu release `v1.2`.
No Mac compatibility claim is established by Linux tests or successful packaging.
The public Mac release remains gated on the checks below on **both** OS versions.

## Build gate

The Apple silicon runtime workflow first exercises GTK's Quartz backend and a
real VTE PTY, then repeats that test inside a bundled application without build
environment paths. A failure blocks the full port; do not replace VTE or weaken
terminal interaction requirements just to produce an installer.

## Test-build checklist

Record the build commit, DMG SHA-256, Mac model and exact macOS version with results.
Use disposable Herdr workspaces for destructive Close tests.

- Download through a browser. Drag the app to Applications and eject the disk.
  Verify the documented Privacy & Security first-open flow, then launch again.
  Repeat on a Mac without Homebrew, Python, GTK or VTE installed.
- With Herdr absent, verify actionable setup; install Herdr separately and verify
  automatic discovery and explicit executable selection. An invalid explicit
  selection must not silently choose another executable.
- Compare screenshots with 1.2: header, sidebar, dividers, settings, theme chooser,
  fonts, spacing, default VS Code Dark palette, light variants and floating H.
- Create, rename, search and collapse spaces/terminals. Agent shortcuts must share
  the same terminal and unread state. Check first-space Close protection and agent
  confirmation using disposable sessions.
- Exercise live CLI input, colors, resize and Shift+click controls. Select/copy
  plain text normally, drag through both history edges, and type immediately after
  release. Check Ctrl+V, image-only clipboard fallback and right-click paste.
- Open plain and OSC 8 HTTP/HTTPS links with Ctrl+click. Confirm the CLI does not
  receive that click. Test non-ASCII text, keyboard layouts and composed input.
- Verify attention transitions, unread acknowledgement, floating H badge and
  messages. Drag/click H on each monitor; hide/show must retain terminal focus,
  selection, scrollback and saved placement. Test maximize/restore and unplugging
  a monitor. Lock/switch user, sleep and wake; H must not appear over the lock screen.
- Reopen the app while running: no duplicate companion. Verify login startup and
  the user's ability to disable it. Exit Hud must also remove H.
- Test an explicit update, offline checks, failed downloads and checksum mismatch.
  No download or installation may start from background checks alone.
- Keep a disposable Herdr process running through hide, quit, replacement and app
  removal. Confirm the same session and process survive, with preferences retained.

## Results

### Automated candidate — 28 September 2026

Source commit: `96d9cf93375d370a050041eb7f2b98ab4b28ba0c`.
[Successful workflow](https://github.com/alex-jax/jax-herdr-hud/actions/runs/36475705812)
and [downloadable test installer](https://github.com/alex-jax/jax-herdr-hud/actions/runs/36475705812/artifacts/10993551752).
The artifact ZIP contains the DMG and its checksum. GitHub sign-in may be required.

DMG: `jax-herdr-hud-1.3-macos-arm64.dmg`

SHA-256: `8ec210b93d09cb4251acf4344671b5195df209f7ac1a788bc67cca380f5584b6`

The same arm64 disk image passed automated checks on macOS **26.6.2** and **27.0**:

- Quartz GTK/VTE launch and PTY output with Homebrew temporarily unavailable.
- Bundle relocation, arm64 Mach-O audit, dependency paths, minimum OS 26.0,
  application identity/version, strict ad-hoc signature verification and DMG checksum.
- Shared theme chooser, light/dark switching, clipboard copy, frozen display relay,
  floating H/toast visibility, nested suspension reasons, saved geometry and exit cleanup.
- Bundled Ubuntu Sans/Ubuntu Mono resolution, 96 DPI and 9×19 terminal cells.
- Real Herdr 0.9.1 native attachment/input/output; hide retains the attachment;
  exiting Hud preserves the disposable server and pane identities.
- Normal background startup with a missing Herdr dependency, duplicate-launch
  forwarding and singleton quit.

Screenshots and JSON reports are retained in the workflow artifacts. These are
automated runner results, not hands-on installation or complete visual parity checks.

### Manual release gate

**Pending on both OS versions.** Complete the checklist above, especially browser
download/first-open approval, live selection/history and links, visual comparison,
multiple monitors, actual lock/sleep/wake, login startup, replacement and removal.
Return the OS version, Mac model and any failed steps for this exact checksum.
Do not publish `v1.3` until these results are recorded and any fixes are retested.

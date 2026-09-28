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

Pending. No macOS test results have been recorded yet.

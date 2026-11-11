# Herdr Hud 1.5 — native macOS

Native AppKit/SwiftTerm application for Apple silicon and macOS 27 or later.

- Display saved SSH machines, their spaces and agents beside local sessions.
  Remote terminal attachment uses Herdr's native client; disconnecting Hud leaves
  servers and agents running. Reconnects preserve terminal identity.
- Optionally start an agent in a new space. Failed startup leaves the workspace
  and shell available. Startup uses pane IDs; attachment uses terminal IDs.
- Remember reported user@host identities and show identity-only tooltips styled
  with the current palette. Unreported remote identities use the SSH target.
- Add a saved automatic-hiding toggle, while protecting menus, dialogs and widget
  gestures. H still explicitly shows or hides Hud when automatic hiding is off.
- Check for updates silently every six hours, with an explicit Settings check.
  Clicking the update arrow downloads and verifies the Mac installer before opening it.
- Preserve direct right-click paste, clipboard text/image handling, links, paired
  CLI colors, selection/history in both directions, and terminal focus.

The app is ad-hoc signed and is not Apple notarized. See the enclosed Read Me for
first-launch instructions. Keep a single installed app at
`~/Applications/Herdr Hud.app`; replace it after quitting when updating.

The DMG includes native source, shared palette sources, pinned dependencies and
licenses. See [VALIDATION.md](VALIDATION.md) for actual test results and remaining
physical hardware acceptance checks. This build does not support Intel Macs or
macOS releases older than 27.

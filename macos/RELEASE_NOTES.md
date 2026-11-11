# Herdr Hud 1.4 — native macOS source (unreleased)

Native AppKit/SwiftTerm build for Apple silicon and macOS 27 or later.
Herdr 0.9.1 and 0.9.5 have been exercised separately. This source build uses an ad-hoc signature and
is not Developer ID signed or Apple notarized. A 1.4 installer has not been published.
Ubuntu 1.4 feature parity is not yet complete.

- Match the Ubuntu reference sidebar with edge-to-edge list backgrounds, fine
  dividers, matching symbolic icons and interface font, and the empty Agents
  message. Theme changes retain sidebar selection.
- Use Ubuntu 26.04's Ubuntu Mono font and matching default terminal cell
  dimensions, including for history selection.
- Hide Hud when clicking outside the app, while keeping the floating H and
  existing terminal sessions available.

- Port Ubuntu 1.2's normal drag-to-select and plain-text automatic copy. Hold
  Shift to send mouse input to interactive CLIs; the route stays fixed for the gesture.
- Extend selection past terminal edges into retained shell history and live CLI
  transcripts. Preserve the original live terminal, colors, geometry, and focus.
  Capture is limited to 20,000 lines and pauses on unmatched redraws.
- Open plain and labelled HTTP/HTTPS terminal links with Command-click or
  Control-click, including AppKit's secondary-button Control-click events.
- Paste clipboard text with Command-V or Control-V, including dictation. Keep
  the CLI's keyboard-protocol encoding for image-only paste shortcuts.
- Preserve CLI foreground/background pairs so highlights remain readable.
- Default fresh preferences to VS Code Dark and retain saved theme choices.
- Keep one installed app during updates, with ZIP backups and unindexed build
  bundles instead of extra launchable app copies.
- Restore terminal focus after header actions. Release selection and type without
  an Escape step.

Install the DMG by dragging Herdr Hud into Applications, replacing the previous
copy after quitting Hud. Quitting Hud disconnects its display clients and retains
Herdr's servers, terminals, agents, and saved preferences. Automatic Mac updates
are not included.

The DMG includes the exact native sources, pinned dependency sources, build
scripts, and licenses in `Source.zip`. Its companion `.sha256` file verifies the
image. See the enclosed Read Me for macOS first-launch instructions.

Validation: core checks and the debug desktop harness, including a real disposable
Herdr server and controlled CLI wheel round trips in both directions. Pointer
checks use synthetic AppKit events; physical pointer, lock/login, and monitor
hot-plug acceptance are separate. This is not a compatibility claim for other
macOS versions or Intel Macs.

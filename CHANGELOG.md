# Release notes

## 1.5 — joint release candidate, 11 November 2026

- Discover enabled saved SSH machines and display their remote spaces and agents with machine/session labels.
- Attach to remote terminals through native Herdr direct attachment over SSH; preserve remote servers and agents on detach or exit.
- Reconnect remote state after connection loss, dim unavailable rows and disable their input until recovery.
- Keep machine identities separate and preserve terminal rows when a saved machine is renamed.
- Include the previously unpublished Ubuntu 1.4 improvements listed below. Extension revision remains 7.
- Prepare the Debian package, native Apple silicon DMG, extension ZIP, complete source archive and checksums for a single joint release. Publication remains pending the Mac release gate.
- Bring saved SSH machines, remote attachments, optional agent startup in new spaces, remembered identity headings/tooltips and saved auto-hide preferences to the native Mac app.
- Add silent six-hour native Mac update checks and explicit checksum-verified DMG downloads. Installation replaces the single app in `~/Applications` manually; sessions remain running.
- Avoid sending a Mac home directory when creating a remote terminal without a reported working directory.
- Remote support requires Linux/macOS remote Herdr sessions, existing noninteractive SSH authentication and Unix-socket forwarding. Plain SSH shells are not adopted.

## 1.4 — source milestone (included in Ubuntu 1.5)

- Keep single clicks on H deterministic and let dragging move only the widget. Protect titlebar moves and corner resizing from unintended automatic hiding, including on Wayland. GNOME extension revision is now 7; logout/login loads the updated extension.
- Hide back to the floating H when focus moves outside Hud; Settings → Floating H provides a saved on/off switch, enabled by default. Open menus and Hud dialogs are protected.
- On Ubuntu, clicking the desktop background also hides Hud when automatic hiding is enabled. On macOS, clicking outside the app hides Hud while leaving H and terminal sessions available.
- Optionally start an installed agent when creating a new space; choose its kind and name. Use the root pane ID for startup, and retain the workspace if startup fails.
- Paste clipboard text directly on the first right-click, including when focus changes or another application owns the clipboard. No extra menu or Paste button.
- Keep the last reported `user@host` visible when an agent replaces the shell title; use the documented local Herdr identity fallback when no identity has been observed.
- Show only `user@host` in terminal and agent hover tooltips, matching the active palette and dark/light theme.
- Try live edge selection for shells and CLIs, fall back to retained history after three unchanged initial frames, and restore focus after selection overlays close.
- Add regression checks for first-click paste, pane versus terminal IDs, real Codex startup in a disposable server, agent headings and identity-only tooltips.
- Exercise core integration with Herdr 0.9.5 on Ubuntu ARM64 and macOS; keep synchronized terminal output controls intact. Test fixtures keep a real foreground process alive for Herdr agent reports.
- Align the macOS sidebar and header with the Ubuntu reference: edge-to-edge list backgrounds, fine dividers with full drag targets, matching symbolic icons and interface font, and the empty Agents message. Preserve sidebar selection across theme changes.
- Use Ubuntu 26.04's Ubuntu Mono font and matching default terminal cell dimensions on macOS, including for history selection.
- Align the native macOS source version to 1.4; Ubuntu feature parity is not yet complete and is tracked in [issue #3](https://github.com/alex-jax/jax-herdr-hud/issues/3). GitHub release assets are not published by this commit.

## 1.3 — 2 November 2026 (Ubuntu/Debian)

- Stable Ubuntu 26.04 / GNOME 50 release. The Debian package includes the companion and floating H extension.
- Keep the 1.2 terminal behavior and bring Hud's window forward when the app is activated again.
- The GTK/VTE Apple silicon Mac port remains in development. This release contains no Mac installer; see [Mac validation](docs/MACOS_VALIDATION.md).

## 1.2 — 28 September 2026

- Default new installations to VS Code Dark; preserve saved theme choices.
- Use normal left dragging to select and automatically copy plain text; use Shift+click for interactive CLI controls.
- Scroll selection beyond either terminal edge, including CLI-owned conversation history, while preserving CLI colors and focus. Release finishes copying without an Escape step.
- Open HTTP/HTTPS links, including labelled terminal links, in the default browser with Ctrl+click.
- Paste clipboard text with Ctrl+V, including dictation tools; preserve the CLI image-paste shortcut for image-only clipboards.
- Keep CLI foreground/background colors together so pasted input and hovered controls remain readable.
- Restore terminal keyboard focus after top-bar actions so Enter reaches the CLI.
- Support two-part release versions (`1.2`, `1.3`, and so on) in the update checker. Install this update manually from the release Assets if upgrading from an older version.
- Expand real-pointer, clipboard, link, theme and history regression coverage; update the manual.

GitHub release downloads are retained only for the latest version.

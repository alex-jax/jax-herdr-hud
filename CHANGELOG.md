# Release notes

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

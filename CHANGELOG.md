# Release notes

## 1.1.0 — 21 September 2026

- Fresh installations use GNOME Dark by default, with GNOME Light when toggled.
  Existing saved appearance and palette choices are preserved.

- Settings now includes searchable preview cards for all 244 Ubuntu Ptyxis palettes,
  with saved selection, light/dark variants and Follow desktop appearance.
- Palettes color the whole Hud. Restore filename, folder and syntax colors by
  preserving ANSI, indexed and RGB terminal colors.

- Closing the last terminal or agent in a secondary space now removes the space.
- Protect the first space’s last terminal or agent from Close.

- Color schemes credited to Christian Hergert and the
  [Ptyxis project](https://gitlab.gnome.org/chergert/ptyxis), including bundled license notices.

## 1.0.0 — 20 September 2026

Stable GitHub release: `v1.0.0`.

- Compact, indented terminal rows with guide lines show which space they belong to.
  Each space collapses independently; search reveals only matching terminals and agents.
- Agent terminals stay under their space, with shortcuts to the same sessions in Agents.
- Green status dots indicate working tasks, yellow indicates unread activity, and
  hollow circles indicate read, idle items. Spaces summarize their members' activity.
- Hover reveals the edit pencil. Any terminal can be closed, including the first;
  closing an agent asks for confirmation. The first space itself remains protected.
  Empty spaces offer New terminal for as long as Hud remains open.
- Interactive CLI controls receive native mouse clicks. Shift+drag copies text;
  right-click pastes.
- Hud controls terminal display colors independently of CLI themes: white with dark
  text or dark with light text. Codex, Grok, Claude Code and agy input areas remain
  readable. Text is monochrome; bold, underline and selection highlighting remain.
- The collapsed-sidebar button no longer overlaps the terminal title. Header buttons
  use consistent spacing, including Credits and Settings.
- Silent GitHub update checks run every six hours. Click the update arrow to
  download a verified Debian package and install it through Ubuntu, with system
  authorization when needed. Restart Hud after installation.
- Installation and manual documentation are simplified and updated.

The release retains automatic default-space startup without duplicate terminals,
and the bundled floating H.
Hiding, exiting or restarting Hud leaves Herdr sessions running. Explicit terminal
or space Close stops the selected processes.

### Installation

Download the `*_all.deb` file under **Assets** on the
[release page](https://github.com/alex-jax/jax-herdr-hud/releases).
Install Herdr, then Hud. Start `herdr` once, **log out and log back in**, then open
Hud and enable the floating H in Settings. See [install.md](install.md).

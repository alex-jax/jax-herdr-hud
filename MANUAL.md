# Herdr Hud manual

Herdr Hud is a local desktop companion for Herdr: a GTK terminal window and a
GNOME Shell extension providing a floating **H** button. The project targets
Herdr 0.9.1 and GNOME 50 on Ubuntu/Wayland. The companion can run without the
extension, but the floating button and Shell-managed window placement require it.

This manual describes the 1.1.3 stable release.
See [CHANGELOG.md](CHANGELOG.md) for release notes and publication status.

A remix of Alex Finn’s version by [Alex Jax](https://github.com/alex-jax).
Original: [Herdr HUD for Omarchy](https://github.com/finna/omarchy-herdr-hud).
See [NOTICE.md](NOTICE.md) for GPL and retained MIT notices. See
[AGENTS.md](AGENTS.md) for implementation and development guidance.

## Requirements

- Python 3 with PyGObject, GTK 3 and VTE 2.91 available to `/usr/bin/python3`.
  The Ubuntu packages named in the project are `python3-gi`,
  `gir1.2-gtk-3.0` and `gir1.2-vte-2.91`.
- An existing Herdr installation, tested with 0.9.1. Discovery uses a configured
  absolute executable path, then `~/.local/bin/herdr`, then the host `PATH`.
- A graphical session with a session D-Bus and the GNOME desktop settings schemas.
- GNOME Shell 50 for the extension. Its metadata declares only version `50`.

## Installation and setup

1. Download the `*_all.deb` file under **Assets** on the
   [release page](https://github.com/alex-jax/jax-herdr-hud/releases).
2. Install Herdr, then install the downloaded Hud package.
3. Start `herdr` once, then open Hud once; it automatically enables the floating H.
4. **Save your work, log out and log back in** so GNOME discovers and loads H.

The fresh login is important: it lets GNOME discover the bundled extension and
connect it to Hud. Follow any further message shown beside the enable button.
See [install.md](install.md) for the short installation and update guide.
The `.deb` uses system Python/GTK/VTE, includes the extension and adds login
autostart. Herdr and agents are installed separately.

Open the setup button in the header to choose a Herdr executable. Leave the path
blank for automatic discovery. Browse selects a file; **Retry** validates it and
saves the selection. If Herdr is missing, this setup view opens automatically.
The app links to Herdr's own installation instructions; it never installs or
upgrades Herdr. Newer versions may work but only 0.9.1 is tested. Protocol failures
are reported rather than restarting servers. The Credits (information) button contains the app version and all in-app
attribution, including Alex Finn, Alex Jax, and Christian Hergert / Ptyxis.
Settings groups compact controls into Appearance, Floating H, and Herdr connection.
The application icon is a plain H in a blue circle, without an activity dot.

The following section is an alternative installation from source.

## Install and start from source

Run from the project directory as your desktop user:

```sh
python3 install.py
~/.local/bin/herdr-hud
```

Installation creates the launcher, Applications entry, icon, extension and a
login autostart entry. It does not install Herdr or system dependencies.
`enable.py` adds this extension to GNOME's enabled list and removes it from the
disabled list while preserving other entries. If GNOME globally disables user
extensions, enable them in the Extensions application.

Log out and back in if GNOME has not discovered the extension. The standalone
window can be opened immediately. Add `~/.local/bin` to your shell's `PATH` if
you want to use the shorter `herdr-hud` command.

| Command | Effect |
| --- | --- |
| `~/.local/bin/herdr-hud` | Show the singleton companion window. |
| `~/.local/bin/herdr-hud --background` | Start without showing the window; an already visible window stays visible. |
| `~/.local/bin/herdr-hud --quit` | Exit the companion and hide its bubble; retain Herdr sessions. |
| `python3 hud.py` | Run the source companion; shares the installed app's identity on the same session bus. |

The extension also starts the companion in the background when enabled. The
application's D-Bus identity prevents duplicate companion instances on one bus.

## Spaces, terminals and agents

At launch, Hud starts Herdr's `default` server if needed and opens its first
terminal. The first default-server space is automatically renamed from `~` to `Space 1`
when discovered. Custom names are preserved; the rename is also visible in Herdr.
Existing spaces are reused; reopening Hud does not add another space.

A **space** is a Herdr workspace. A terminal row in Hud represents a pane, attached by
its terminal ID. Herdr also has named **server sessions**, which may each contain
multiple workspaces. Some terminal action dialogs use the word “session”; this
does not mean they create or rename a server.

1. Click **+ New space** or **Start a space** and accept the suggested
   `Space 2`, `Space 3`, etc., or enter your own nonblank name. Numbering continues
   above the existing numbered names and space count.
2. Click **Start**. The Hud creates a workspace in Herdr's `default` server and
   opens its first terminal. It starts that server if necessary.
3. Terminals appear as compact, indented rows beneath their space in the sidebar.
4. Click a terminal to switch to it, or the **+** beside its space to add another.
   Clicking a space returns to the last terminal selected there.
5. Click the arrow beside a space to collapse or expand its terminal list. Each
   space keeps its own setting while Hud is open. Collapsing leaves its active
   terminal running and keeps agents available in the separate Agents section.
   Adding a terminal expands its space.

New spaces are visible in the original app opened with `herdr`. Existing named
servers are also discovered; their groups display `server / workspace` and can
be accessed in Herdr with `herdr --session NAME`. Processes are not migrated
between servers. A space name such as “codex” is only a label; launch agents from
its shell as usual.

The per-space **+** uses the selected terminal's current directory when it
belongs to that space, otherwise the first member's directory. Foreground
working directory takes precedence over the pane's stored directory; the home
directory is the fallback. New spaces start in the home directory.

**Spaces** shows each workspace with compact, indented terminal rows and a thin
vertical guide beneath it. Agent terminals stay under their space. **Agents**
provides shortcuts to those same terminals, labelled with the agent and terminal
name, plus their state and originating space. Both entries share the connection,
selection and unread status. When an agent exits, its shortcut disappears and the
terminal stays in its space. Herdr’s agent field determines whether a shortcut appears.

Search filters individual terminal names (including tab labels and process titles)
and agent identities, ignoring case and leading/trailing spaces. Only matching
terminal or agent rows remain visible; a matching terminal keeps its parent space
heading for context. Space/server names do not make unrelated children match.
Search temporarily reveals matching terminals inside collapsed spaces; clearing
the search restores their collapsed state. Searching and clearing the search
preserve the active terminal and its connection.
Spaces consisting only of agents still retain their **+** when the search is clear.

## Rename and close

Hover over a space, terminal or agent to reveal its pencil and open Rename/Close.
The pencil keeps its place so rows do not shift. All rows
support right-click and keyboard context menus. Opening a menu does not switch
the selected terminal.

- **Rename** requires a nonblank name. A space rename updates the Herdr workspace.
  A terminal rename updates both the pane label and its containing tab label.
- **Close** on a terminal sends `pane.close`, stopping that pane's running process.
- **Close** on a space sends `workspace.close`, stopping the terminals in that space.

Closing the last terminal in a secondary space also removes that space. Agent
terminals offer **Close terminal and stop agent** with a confirmation dialog;
cancelling leaves the session running. Closing a plain shell takes effect
immediately. Both the space entry and agent shortcut act on the same terminal.
The first workspace and its last terminal or agent are protected: their menus
omit Close. Add another terminal there before closing the existing one.
Closing is separate from hiding or exiting Hud, which leaves sessions running.

## Terminal interaction

The window embeds VTE with a Hud display helper around Herdr's native
`terminal attach` client. Keyboard
input, control sequences and terminal size changes go through that client.
Switching rows retains attached terminals and up to 20,000 VTE scrollback lines.
The configured font is `Ubuntu Mono 12`, with 16-pixel side margins.

- Hold **Shift** and drag with the left mouse button to select text and automatically copy it.
- Right-click inside the terminal to paste the clipboard.
- Interactive terminal apps receive normal left clicks and drags when they request
  mouse input, so their buttons work. Hold **Shift** while dragging to select and
  copy text instead. Right-click remains paste. GNOME-reserved shortcuts stay with
  the desktop.
- If a client disconnects, select its terminal again to create a new attachment.

Herdr controls input ownership. If another direct-attach client owns a terminal,
detach it with `Ctrl+B`, then `Q`, before opening it here. The Hud does not force
takeover. Existing terminal application windows are not embedded or closed.

## Window and floating button

Click **H** to show or hide the window; drag it to move the bubble. A focused
bubble also responds to Enter or Space. Escape cancels an active pointer grab.
Its outline uses the desktop accent colour. The bubble and tooltip are hidden
on the lock screen and greeter.

Move and resize the Hud normally. With the extension active, its normal window
geometry is saved and clamped to available monitor space when restored. The
extension keeps the window above other windows and visible across workspaces.
Moving the bubble does not reposition an already tracked window.

- Drag the vertical divider to resize the sidebar or collapse either side at
  an edge. Use the arrow at its top to collapse/restore the sidebar's last width.
  The arrow leaves room for the terminal title even when the sidebar is collapsed.
- Collapse **Spaces** and **Agents** independently; drag their horizontal divider
  to change their relative heights.
- Use **Expand HUD** to maximize and **Restore window** to return to normal size.
  Maximizing does not overwrite saved normal dimensions.
- Use the sun/moon button to switch between light and dark. Fresh installations use GNOME Dark; choosing light or dark saves an explicit override.
  Settings → Appearance offers **Follow desktop**, **Light**, and **Dark**.
- **Hide**, including a window-manager close request, keeps monitoring and
  attachments alive. **Exit Hud** disconnects only its attach clients and hides
  the bubble. Herdr servers, shells and agents remain running.

## Notifications

Unread activity produces a blue dot on the bubble and a tooltip lasting five
seconds. The dot indicates that unread items exist; it is not a numeric badge.
The accessible name includes their count. Each terminal has at most one unread
entry, held only in memory.

Sidebar dots are green while a task is working, yellow for finished or other
unread activity, and hollow once you open the completed item. A task that is
still working stays green. A space is yellow if any item has unread activity,
otherwise green if an item is running, and hollow when all are read and idle.
Reading one item does not clear unread activity on the others.

| State transition | Message |
| --- | --- |
| Any different state to `blocked` | Needs your input |
| Any different state to `done` | Finished |
| `working` to `idle` | Finished |
| Pane exit event | Terminal exited |

An initially observed `blocked` or `done` state can notify. `unknown` to `idle`
does not imply completion. State transitions for the visible, focused terminal
do not create unread activity. Selecting a terminal, showing its window or
focusing the window acknowledges the selected terminal. Removed panes lose
their unread entries. Notifications depend on Herdr's semantic reports; arbitrary
commands and unrecognised agents may never produce completion states.

## Files and preferences

Defaults below use your home directory. `XDG_DATA_HOME`, `XDG_CONFIG_HOME` and
`XDG_STATE_HOME` override the corresponding data, configuration and state roots.
The launcher and Herdr binary paths remain under `~/.local/bin`.

| Default location | Contents |
| --- | --- |
| `~/.local/bin/herdr-hud` | Generated Python launcher using `/usr/bin/python3`. |
| `~/.local/share/herdr-hud/` | Companion, backend, `terminal_display.py`, update checker and setup helpers. |
| `~/.local/share/gnome-shell/extensions/herdr-hud@alex-jax.github.io/` | Extension JavaScript, metadata and CSS. |
| `~/.local/share/applications/io.github.herdr.Hud.desktop` | Applications entry. |
| `~/.local/share/icons/hicolor/scalable/apps/io.github.herdr.Hud.svg` | Application icon. |
| `~/.config/autostart/io.github.herdr.Hud.desktop` | Background login launch. |
| `~/.config/herdr-hud/settings.json` | Theme, normal dimensions, sidebar and section preferences. |
| `~/.config/herdr-hud/bubble.json` | Bubble `x` and `y`, owned by the extension. |
| `~/.config/herdr-hud/window.json` | Window `x`, `y`, `width`, `height`, owned by the extension. |
| `~/.local/state/herdr-hud/server-start.log` | Output from servers started by the backend. |
| `~/.local/state/herdr-hud/hud.log` | Companion output when launched by `activate.py`. |

`settings.json` defaults are `terminal_palette: "gnome"`, `theme: "dark"`, `width: 1040`, `height: 660`,
`sidebar_width: 245`, `section_position: 260`, and both `spaces_expanded` and
`agents_expanded` true. `sidebar_expanded_width` restores the last expanded width,
falling back to the saved sidebar width or 245. The window minimum is 620 × 360.
`herdr_path` stores the optional executable override (empty means automatic).
Settings save on hide, exit and certain controls; they are not written on every
individual drag. Configuration files do not store terminal contents or sessions.

## Update and uninstall

Run `python3 install.py` again to copy changed files. Exit and reopen the companion
for Python changes. Opening Hud enables H automatically. `python3 activate.py`
is an explicit manual re-enable/restart command and appends output to `hud.log`.

For extension changes, log out and back in: the project's GNOME 50 workflow
requires a fresh login to reload already loaded JavaScript. `activate.py` does
not reload Shell code. Finish or save other desktop work before logging out.

For a source installation, run `python3 uninstall.py` to exit the Hud, remove its installation, launcher,
desktop files and extension, and remove its UUID from GNOME extension lists.
It preserves Herdr, its sessions, Hud preferences and log files. For a Debian
installation, exit Hud and use `sudo apt remove jax-herdr-hud` instead.

## Troubleshooting

| Symptom | Check or action |
| --- | --- |
| No floating H | Check GNOME 50 compatibility, run `enable.py`, check global extension enablement and log in again. Open the standalone launcher meanwhile. |
| Could not list sessions | Use the setup screen to check the executable and run `~/.local/bin/herdr session list --json` from the same desktop environment. |
| Reconnecting to a server | The backend retries automatically; check whether that Herdr server is still running and its socket is accessible. |
| Could not start a session | Inspect `server-start.log`; the backend allows ten seconds for startup. |
| Could not attach / Disconnected | Check ownership in the other attach client; select the row again after resolving the problem. |
| Missing GTK/VTE imports | Use the system Python with the distro GI libraries; a separate virtual environment may not expose them. |
| Old behaviour after editing source | Installed files are copies. Reinstall and restart the relevant component. |
| Broken layout after manually editing preferences | Exit the companion, back up `settings.json`, and move it aside to restore defaults. Coordinate extension-owned file resets with extension disable/reload so cached values do not overwrite edits. |
| Terminal text has no syntax colours | Fully exit and reopen Hud after updating. The command or editor must emit color output; Hud preserves ANSI, indexed and RGB text colors. |

The current settings loader handles missing files and invalid JSON syntax, but
does not validate every decoded value's type. Keep the configuration an object
with numeric sizes and valid theme strings. Local sessions only are supported;
there is no remote discovery or persistent notification history.

## Verification

From the source directory:

```sh
python3 -m unittest discover -s tests -v
dbus-run-session -- python3 tests/smoke_sidebar.py
dbus-run-session -- python3 tests/smoke_desktop.py
dbus-run-session -- python3 tests/smoke_extension.py
```

The unit suite needs only Python and local Unix sockets. Sidebar and desktop
smoke tests need a graphical display and default to X11, so Wayland sessions
need accessible XWayland unless `GDK_BACKEND` is explicitly set otherwise.
The sidebar test also expects a window manager for maximize/restore assertions.

The sidebar test uses fake terminals and temporary settings. The desktop test
creates and stops a disposable Herdr server and uses the clipboard. Screenshots
and logs go to unique temporary directories, or `HUD_TEST_OUTPUT` when supplied.
Run on a separate session bus as shown to isolate real Shell calls.

The extension test starts headless GNOME with a temporary instrumented extension.
It defaults to the source companion. Set `HUD_TEST_LAUNCHER` to a JSON argv array
to test an installed or extracted Debian launcher. Production extension files
never contain these test hooks. See the publishing guide and AGENTS.md for details.

## Update notifications

Hud checks this project's public GitHub releases in the background on first launch
and then once every six hours while running, including while hidden. The last attempt
and available release are saved in `herdr-hud/updates.json` alongside settings, so
restarts do not trigger extra checks. If the app was closed when a check became due,
it checks on its next launch. Offline or failed checks retry after six hours.

When a newer release is available, a download arrow appears beside the information
button. Checks do not send notification pop-ups. Clicking the arrow downloads the
release's Debian package from this project's GitHub Assets, verifies GitHub's
SHA-256 checksum and the package name/version, then starts Ubuntu's APT installer.
Ubuntu may request your password through its system authorization prompt. Hud never
collects your password. Download and installation run off the GTK thread.

The button is disabled while updating. Cancelled authorization, missing assets or
failed verification do not start installation. Failures show an inline retry message.
After installation, restart Hud from Applications to load the new version. The
update never stops Herdr servers or agents. Extension changes still need logout/login.
Source installations should use the source update procedure above; the built-in
installer installs the Debian package. Do not mix per-user and system installations.

## Automatic floating H

The Debian package and source installer include H for GNOME 50. Install Herdr
and Hud, start `herdr` once, then **open Hud once**. Hud enables H automatically
in the background. **Save your work, log out and log back in**: GNOME needs a
fresh login to discover the bundled extension. No separate ZIP or manual enable
step is normally needed. If H is still absent, open Hud and read its Settings message.

**Exit Hud** closes the companion and hides H together. There is no separate H
off control. Automatic startup respects a disabled extension in GNOME Extensions
and never switches the global extensions setting on. Use GNOME Extensions to explicitly restore it. If desktop extensions are globally off,
Settings explains what to do.

After an update that changes H, **log out and back in** to replace the loaded
extension. On the first launch after upgrading from a manual-enable release,
Hud enables H automatically unless it is disabled in GNOME Extensions. Opening or hiding
Hud repeatedly does not repeat setup within that app process.

## Terminal display colors

Open **Settings → Appearance → Choose theme…** for preview cards.
The chooser includes all 244 palettes bundled with Ubuntu's Ptyxis 50.1, plus
**Hud classic**. It starts with the 12 featured Ptyxis palettes and Hud classic;
use **Show all palettes** or search by name to browse the complete collection.
Click a card to apply it immediately to every open terminal. A checkmark and blue
outline identify the selection, which is saved for future launches. **Done**
closes the chooser; selecting GNOME restores the default palette. Fresh installations start in Dark
mode; switching to Light uses GNOME’s light variant. Saved choices are retained.

**Follow desktop**, **Light**, and **Dark** control Hud's appearance. Palettes with
light and dark variants switch with this setting and the header's sun/moon button.
Single-variant palettes keep their original colors in both modes. Palette selection
colors the entire Hud: header, sidebar, controls, menus and terminal. Terminal
foreground, background, cursor and ANSI colors use the selected palette. Ptyxis does not need to be installed,
and Hud never writes to Ptyxis or CLI preferences.

Hud classic uses a white background and dark text in light mode, and a dark
background with light text in dark mode. Filename, folder, syntax and CLI text colors
are preserved. ANSI colors follow the palette; explicitly requested RGB and
256-color foreground values retain the application’s colors. Explicit CLI background
colors use the selected Hud background, keeping input bars consistent in light
and dark mode. Reverse-video selection remains supported. Palette changes recolor
default/ANSI scrollback, while application-specific RGB colors stay unchanged.
Global palette replacement sequences are blocked to preserve your selection. Codex, Grok, Claude Code and agy keep their own
settings and sessions, and look unchanged outside Hud. No patched Herdr build
or CLI theme synchronization is needed.

The display helper wraps the native `herdr terminal attach` client, relaying input,
mouse reports and resize events. Closing Hud detaches that client only; it never
stops the pane, shell or agent.

## Color scheme credits

Color schemes are borrowed from [Ptyxis](https://gitlab.gnome.org/chergert/ptyxis),
created by **Christian Hergert**, with contributions from the Ptyxis and Gogh communities.
Thank you for making these palettes available. See [NOTICE.md](NOTICE.md) for attribution
and the retained license notices.

The terminal header shows its space name and terminal title. Renaming a space
updates the header too; named Herdr servers retain their prefix for clarity.

Space, terminal and agent names do not show hover tooltips. Action buttons retain
their short help labels.

Pasting with right-click or the terminal paste shortcut clears the text selection
automatically. Copied text remains available on the clipboard.

While holding Shift and dragging a text selection, move the pointer to the top or
bottom edge to scroll through terminal history. Release the mouse to stop.
Top-bar actions return keyboard focus to the visible terminal; Settings and
dialogs keep their own controls available.

When a Shift-drag reaches the terminal edge, Hud loads up to 20,000 lines of
retained Herdr history into a temporary selection view. Hold the mouse near the
top or bottom to extend the selection. Esc, a normal click or typing returns to
the live terminal; the agent stays connected throughout. History that the CLI
or Herdr has not retained cannot be recovered this way.
Selections copy as plain text, without fonts, colors, HTML or ANSI escape codes.

Ctrl+V pastes text from the clipboard into the active terminal, including
speech-to-text input. With an image-only clipboard, Ctrl+V is sent to the CLI
so its image-paste shortcut remains available. Ctrl+Shift+V and right-click
continue to use the terminal paste action.

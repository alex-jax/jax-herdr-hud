# Herdr Hud manual

Herdr Hud is a local desktop companion for Herdr: a GTK terminal window and a
GNOME Shell extension providing a floating **H** button. The project targets
Herdr 0.9.1 and GNOME 50 on Ubuntu/Wayland. The companion can run without the
extension, but the floating button and Shell-managed window placement require it.

This manual describes release 0.1.0, prepared on 20 September 2026.

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

The snap bundles its Python/GTK/VTE runtime and requires no host GI packages.
Source installation uses the system libraries listed above. Packaging instructions
are in [docs/PUBLISHING.md](docs/PUBLISHING.md).

## Native .deb installation

See [install.md](install.md) for exact download, installation, extension enablement,
update and removal commands. The `.deb` uses system Python/GTK/VTE and installs
`/usr/bin/herdr-hud`, the system extension, and GNOME login autostart. Herdr is a
separate dependency. Use APT to remove the `.deb`, not the source uninstall script.
The per-user paths below describe the source installer; settings paths are shared.

## Snap preview and setup

The development snap and optional GNOME extension are separate artifacts. They
have not been approved or published in the stores. Follow the
[publishing guide](docs/PUBLISHING.md) for local snap installation and
[extension guide](docs/GNOME_SUBMISSION.md) for the optional H.

Launch the snap with `herdr-hud-alex-jax`. `--version`, `--background` and `--quit`
are supported. The snap creates no login autostart entry and does not enable any
extension. The extension starts the companion in the background when enabled.

Open the setup button in the header to choose a Herdr executable. Leave the path
blank for automatic discovery. Browse selects a file; **Retry** validates it and
saves the selection. If Herdr is missing, this setup view opens automatically.
The app links to Herdr's own installation instructions; it never installs or
upgrades Herdr. Newer versions may work but only 0.9.1 is tested. Protocol failures
are reported rather than restarting servers. The About button shows version and
publisher/original-project attribution.

The following installation section describes the legacy-compatible **source
installer**, not the snap.

## Install and start from source

Run from the project directory as your desktop user:

```sh
python3 install.py
python3 enable.py
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

A **space** is a Herdr workspace. A terminal row represents a pane, attached by
its terminal ID. Herdr also has named **server sessions**, which may each contain
multiple workspaces. Some terminal action dialogs use the word “session”; this
does not mean they create or rename a server.

1. Click **+ New space** or **Start a space** and enter a nonblank name.
2. Click **Start**. The Hud creates a workspace in Herdr's `default` server and
   opens its first terminal. It starts that server if necessary.
3. Use the **+** beside a space to add an independent terminal tab there.
4. Click a terminal row to attach and focus it.

New spaces are visible in the original app opened with `herdr`. Existing named
servers are also discovered; their groups display `server / workspace` and can
be accessed in Herdr with `herdr --session NAME`. Processes are not migrated
between servers. A space name such as “codex” is only a label; launch agents from
its shell as usual.

The per-space **+** uses the selected terminal's current directory when it
belongs to that space, otherwise the first member's directory. Foreground
working directory takes precedence over the pane's stored directory; the home
directory is the fallback. New spaces start in the home directory.

**Spaces** contains ordinary terminals grouped by workspace. **Agents** contains
panes for which Herdr supplies an agent identity, across all discovered local
servers. Status alone does not classify a terminal as an agent. Agent rows show
agent type, state and originating space. Returning to a shell moves the row
back; idle or finished agents remain under Agents while their identity remains.
Moving between sections preserves the terminal connection, focus and scrollback.

Search matches terminal names, server names, workspace names and agent types.
It filters rows without closing terminals. A space containing only agents still
has its group header and **+** button.

## Rename and close

Use the pencil button beside a space or terminal name to open its action menu.
Terminal rows also support right-click and a keyboard context menu. Right-clicking
a row opens its menu without switching the selected terminal.

- **Rename** requires a nonblank name. A space rename updates the Herdr workspace.
  A terminal rename updates both the pane label and its containing tab label.
- **Close** on a terminal sends `pane.close`, stopping that pane's running process.
- **Close** on a space sends `workspace.close`, stopping the terminals in that space.

**Close takes effect without a separate confirmation dialog.** It is different
from hiding or exiting the Hud. The first workspace and the first pane in that
workspace are protected from closing through the Hud; ordering comes from the
server snapshot. The first terminal in a later workspace can be closed.

## Terminal interaction

The window embeds VTE running Herdr's native `terminal attach` client. Keyboard
input, control sequences and terminal size changes go through that client.
Switching rows retains attached terminals and up to 20,000 VTE scrollback lines.
The configured font is `Ubuntu Mono 12`, with 16-pixel side margins.

- Drag with the left mouse button to select text and automatically copy it.
- Right-click inside the terminal to paste the clipboard.
- These gestures are reserved for clipboard use, including when a terminal app
  requests mouse input. GNOME-reserved shortcuts remain with the desktop.
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
- Collapse **Spaces** and **Agents** independently; drag their horizontal divider
  to change their relative heights.
- Use **Expand HUD** to maximize and **Restore window** to return to normal size.
  Maximizing does not overwrite saved normal dimensions.
- Use the sun/moon button to switch between light and dark. Initial appearance
  follows the desktop; choosing a theme saves an explicit override. To restore
  system following, exit the companion and set `theme` to `"system"` in its
  settings file. There is no system-theme button in the current UI.
- **Hide**, including a window-manager close request, keeps monitoring and
  attachments alive. **Exit Hud** disconnects only its attach clients and hides
  the bubble. Herdr servers, shells and agents remain running.

## Notifications

Unread activity produces a blue dot on the bubble and a tooltip lasting five
seconds. The dot indicates that unread items exist; it is not a numeric badge.
The accessible name includes their count. Each terminal has at most one unread
entry, held only in memory.

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
| `~/.local/share/herdr-hud/` | Installed `hud.py` and `backend.py`. |
| `~/.local/share/gnome-shell/extensions/herdr-hud@alex-jax.github.io/` | Extension JavaScript, metadata and CSS. |
| `~/.local/share/applications/io.github.herdr.Hud.desktop` | Applications entry. |
| `~/.local/share/icons/hicolor/scalable/apps/io.github.herdr.Hud.svg` | Application icon. |
| `~/.config/autostart/io.github.herdr.Hud.desktop` | Background login launch. |
| `~/.config/herdr-hud/settings.json` | Theme, normal dimensions, sidebar and section preferences. |
| `~/.config/herdr-hud/bubble.json` | Bubble `x` and `y`, owned by the extension. |
| `~/.config/herdr-hud/window.json` | Window `x`, `y`, `width`, `height`, owned by the extension. |
| `~/.local/state/herdr-hud/server-start.log` | Output from servers started by the backend. |
| `~/.local/state/herdr-hud/hud.log` | Companion output when launched by `activate.py`. |

`settings.json` defaults are `theme: "system"`, `width: 1040`, `height: 660`,
`sidebar_width: 245`, `section_position: 260`, and both `spaces_expanded` and
`agents_expanded` true. `sidebar_expanded_width` restores the last expanded width,
falling back to the saved sidebar width or 245. The window minimum is 620 × 360.
`herdr_path` stores the optional executable override (empty means automatic).
Settings save on hide, exit and certain controls; they are not written on every
individual drag. Configuration files do not store terminal contents or sessions.

## Update and uninstall

Run `python3 install.py` again to copy changed files. Exit and reopen the companion
for Python changes. After installation, `python3 activate.py` enables the extension
and restarts the installed companion, appending output to `hud.log`.

For extension changes, log out and back in: the project's GNOME 50 workflow
requires a fresh login to reload already loaded JavaScript. `activate.py` does
not reload Shell code. Finish or save other desktop work before logging out.

For a source installation, run `python3 uninstall.py` to exit the Hud, remove its installation, launcher,
desktop files and extension, and remove its UUID from GNOME extension lists.
It preserves Herdr, its sessions, Hud preferences and log files. For the snap,
exit Hud and remove `herdr-hud-alex-jax` through App Center or snap. Remove the
optional extension separately; host preferences remain under the same XDG paths.

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
| Colours differ inside an agent | ANSI colours emitted by the terminal application can override the Hud palette. |

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
to test an extracted snap or installed launcher. Production extension files never
contain these test hooks. See the publishing guide and AGENTS.md for details.

# Coding agent guidance

## Scope and project shape

These instructions apply to this directory and its descendants. Read the relevant
source before changing it; [MANUAL.md](MANUAL.md) describes current user behaviour.
The project is a small native Python/GTK 3/VTE companion plus a GNOME Shell 50
GJS extension. The README targets Herdr 0.9.1. There is no web frontend or pip
dependency manifest. Distribution uses GitHub, the native Debian package and the
per-user source installer. See docs/PUBLISHING.md for builds and docs/VALIDATION.md
for completed checks. Check Git availability in the current directory; the public
checkout and local source directory may differ.

## Source map

| File | Responsibility |
| --- | --- |
| `backend.py` | Herdr executable discovery, sanitized child environment, JSON-lines RPC, server discovery, reconnecting watchers, server/workspace/tab creation. |
| `terminal_display.py` | Hud-only color filter and PTY relay around the native attach client; preserves input, resize and safe detachment. |
| `hud.py` | `Terminal` VTE subclass; singleton `Hud` application; sidebar rendering, actions, themes, preferences, notifications and attach-client lifecycle. |
| `extension/extension.js` | Floating actor, pointer grabs, D-Bus bridge, companion launch, monitor-aware window placement, geometry persistence and cleanup. |
| `extension/stylesheet.css` | Bubble, badge and tooltip styling, including native accent token. |
| `extension/metadata.json` | UUID `herdr-hud@alex-jax.github.io`, extension version and supported Shell versions. |
| `install.py` | Copy source to per-user install locations; generate launcher, desktop entries, icon and autostart. |
| `enable.py` | Update this UUID's enabled/disabled settings and query extension registration. |
| `activate.py` | Enable and restart the installed companion with log capture. |
| `uninstall.py` | Remove Hud installation and registration while retaining Herdr and preferences. |
| `tests/test_backend.py` | Unit tests for attention transitions and fragmented/error socket replies. |
| `tests/smoke_desktop.py` | Real GTK/VTE and disposable Herdr integration. |
| `tests/smoke_sidebar.py` | Native GTK click/layout regressions with mocked monitor and terminal launch. |
| `tests/smoke_extension.py` | Isolated headless GNOME lifecycle and pointer integration. |
| `tests/pointer_test_hooks.js` | Instrumentation injected only into the extension test's temporary copy. |

`__pycache__`, `hud-preview.png` and `extension-test*.log` are generated or
historical artifacts. Do not treat logs as source or current validation results.
Do not modify artifacts incidentally; preserve existing ones when running tests.

## Contracts to preserve

### Process ownership and model identity

- Hide keeps the app, watchers and attachments alive. Exit stops watchers and
  signals only VTE's display relay, which forwards SIGHUP to its direct-attach client. Never stop user Herdr
  servers, shell processes or agents as part of hide, exit, update or uninstall.
- Explicit terminal/space **Close** is intentionally destructive and separate:
  use `pane.close` / `workspace.close`, preserve the first-workspace guard in `can_close_sidebar_item()`. The first workspace
  also protects its last terminal; other agent terminals require confirmation. Keep actions
  scoped to their selected server and object IDs. Closing the last terminal in a
  secondary space removes that space; do not retain empty-space placeholders.
- New UI spaces call `create_shared_workspace()` on the `default` server, making
  them visible to bare `herdr`. Do not substitute a new named server per space.
- Terminal identity is `(socket_path, terminal_id)`; groups use
  `(socket_path, workspace_id)`. RPC mutations target pane/workspace/tab IDs.
  Never key terminals by label, agent name or terminal ID alone across servers.
- Renaming a terminal updates both pane and tab labels; a tab can contain more
  than one pane. Renaming a space updates its workspace label.
- Herdr's nonempty `agent` field determines shortcuts under Agents. Agent terminals
  remain under their spaces; both rows share the same VTE and unread state. Do not infer
  identity from workspace labels, process titles or status alone. Changing
  status or moving rows must retain the VTE instance and connection.
- Preserve native direct attachment and input ownership. Do not force takeover,
  embed another terminal window or launch the full Herdr TUI inside VTE.
- `environment()` removes inherited `HERDR_*` variables and sets
  `TERM=xterm-256color`. Keep argv arrays instead of interpolated shell commands.

### Threading and GTK lifecycle

- Blocking socket/subprocess work belongs in backend or worker threads. Marshal
  UI updates through `idle()` / `GLib.idle_add`; never mutate GTK from watchers.
- `rebuild_sidebar()` coalesces updates and defers rendering to an idle callback.
  Do not destroy a clicked row synchronously inside GTK selection/click signals;
  this previously caused crashes. Reuse rows and avoid changing unchanged labels.
- Preserve `rebuilding`, `closing`, refresh-source IDs and request-in-progress
  guards. Cancel pending sidebar refresh on exit and ignore late worker results.
- Defer terminal focus until GTK finishes processing selection. Preserve selection,
  focus and scrollback during snapshots, search and Spaces/Agents reparenting.
- VTE forwards normal left clicks/drags to mouse-aware CLIs; Shift+drag selects
  and copies text, and right-click pastes. Sidebar
  context menus are separate; ListBox owns its input window, so resolve row hits
  from ListBox coordinates.

### Backend and notification semantics

- RPC is one newline-delimited JSON request/reply over an AF_UNIX socket, with
  three-second timeout and an 8 MiB reply read limit. Surface API errors rather
  than converting them into empty sessions.
- `Monitor` discovers sessions about every three seconds. Each live socket has
  a watcher, which snapshots, subscribes and refreshes after events. A ten-second
  read timeout reconciles quiet streams; changed pane sets trigger resubscription.
- Preserve attention rules: entering `blocked` means input; entering `done` means
  completion; `working` to `idle` means completion. Unknown/initial idle is not
  completion. Repeated states must not duplicate notifications.
- Unread state is in memory and per terminal. Selection/focus acknowledges it;
  removal prunes it. Do not promise a durable event log or notifications for
  arbitrary processes lacking Herdr reports.

### Shell extension and persistence

- Keep the companion ID `io.github.herdr.Hud` consistent with desktop files,
  window matching and Gio actions. Actions `toggle`, `show`, `exit` live at
  `/io/github/herdr/Hud` on the companion's session-bus name.
- The extension exports `/org/gnome/Shell/Extensions/HerdrHud` on
  `org.gnome.Shell`, interface `org.gnome.Shell.Extensions.HerdrHud`:
  `SetStatus(u count, s message, b dark)`, `ShowBubble()`, `ExitHud()`.
  Keep both sides compatible. The companion must remain usable without the bridge.
- Handle grabbed input on the bubble actor. Never replace an active grab on a
  duplicate press. `_endDrag()` must clear state before dismissing the grab and
  cover release, Escape, unmap, hide, watchdog recovery and disable.
- Track/remove timers, signal handlers, bus watches, exported objects and actors.
  Test instrumentation must never enter the installed production extension.
- Preserve lock/greeter hiding and desktop accent styling via `-st-accent-color`.
- GTK owns `settings.json`; the extension owns `bubble.json` and `window.json`.
  Preserve replacement writes, XDG roots and normal geometry while maximized.
  Existing-window show or bubble drag must not reset the user's window placement.
- Keep metadata honest: only GNOME 50 is currently declared. A metadata edit alone
  is not evidence of compatibility with another Shell major version.

## Development and validation

Use the system Python with GI libraries. Read-only baseline:

```sh
python3 -m unittest discover -s tests -v
```

Choose integration tests according to the changed behaviour:

| Change | Relevant verification |
| --- | --- |
| RPC, state transitions, backend creation | Unit suite; desktop smoke for Herdr integration. |
| Sidebar, menus, row placement, search, focus, dividers, maximize | Sidebar smoke; desktop smoke for real mutations. |
| VTE, clipboard, attach/detach, creation, notifications | Desktop smoke. |
| Shell pointer, geometry, theme, D-Bus or lifecycle | Extension smoke with a matching installed companion. |
| Documentation only | Check statements and commands against source; do not install or restart the user's desktop merely to validate prose. |

Run smoke tests sequentially, from the project root:

```sh
dbus-run-session -- python3 tests/smoke_sidebar.py
dbus-run-session -- python3 tests/smoke_desktop.py
dbus-run-session -- python3 tests/smoke_extension.py
```

The first two require display access and default to X11; a separate session bus
does not provide a display. The sidebar test needs window-manager support for
maximize/restore. It disables the monitor, attach spawning and Shell bridge,
uses temporary preferences, treats GTK criticals as fatal and writes a screenshot
to its temporary output directory or `HUD_TEST_OUTPUT`.

The desktop test isolates Herdr through temporary configuration, starts a real
server and stops that disposable server in cleanup. It changes the clipboard
and writes `hud-preview.png` to its test output directory. It does not mock `shell_call()`, so use a fresh
session bus to avoid sending status/show/exit to the user's extension. Do not copy test output over the historical root preview unless requested.

The extension test must use `dbus-run-session`; it sets temporary XDG roots and a
keyfile settings backend, starts headless GNOME and injects pointer hooks into a
temporary extension copy. It defaults to the source companion. `HUD_TEST_LAUNCHER` supplies a JSON argv
array to test the packaged launcher; the override exists only in the temporary
extension copy. `HUD_TEST_EXTENSION` selects an unpacked release ZIP. Logs and
screenshots use temporary directories or `HUD_TEST_OUTPUT`. Do not run headless Shell on the user's bus.

Tests do not run through a unified runner: unittest discovery executes only the
backend and distribution unit tests, not `smoke_*.py`. Report exactly which checks ran and any
failure or missing prerequisite. Existing PASS messages in saved logs are not
evidence for a new change. Add regression coverage for behavioural fixes; avoid
tests that simply repeat implementation or unnecessary tests for prose changes.

## Known review caveats

- `settings.json` parsing catches file and JSON syntax errors but does not validate
  decoded object/value types. Valid JSON with the wrong shape can break startup.
- Protocol handling assumes expected keys and shapes after JSON decoding. Existing
  unit tests cover fragmentation and API errors, not all malformed responses,
  watcher races or server startup failures.
- The snapshot-then-subscribe sequence is reconciled periodically, not an atomic
  event history. Do not describe monitoring as lossless.
- Pane rename followed by tab rename uses two RPCs, not a transaction; the first
  can succeed even if the follow-up fails.
- Installation copies files; running source on the same bus as an installed
  instance may forward to that existing instance. Confirm what code is running.
- Extracted Debian smoke tests do not replace clean-VM install, upgrade and
  removal verification.

These are maintenance caveats, not instructions to expand every task into a
refactor. Keep changes scoped, use existing Python/GJS style and update the manual
when behaviour changes. Run install/enable/activate/uninstall only when relevant
to the user's requested work; they mutate the per-user desktop installation.
Companion changes need restart after copying; already loaded extension changes
need logout/login under this project's GNOME 50 workflow.


## Release packaging contracts

- App version is `1.1.1` with stable release tag `v1.1.1`; extension revision is
  separate. Keep app_info.py and retained packaging metadata synchronized.
- Retain `io.github.herdr.Hud` and host XDG preferences. New public extension UUID
  is `herdr-hud@alex-jax.github.io`; never enable it with the legacy UUID.
- Do not bundle or automatically install Herdr.
- Executable discovery is explicit absolute path, ~/.local/bin/herdr, host PATH.
  An invalid explicit selection is an error, not a silent fallback. Blank setup
  selection restores automatic discovery. Test dependency errors without agents.
- `runtime_env.py` restores saved host runtime variables before spawning Herdr.
  Preserve user-provided host environment values and keep GUI runtime overrides
  out of host shells.
- Test the extracted Debian payload using `HUD_TEST_SOURCE`, and the extension
  with `HUD_TEST_LAUNCHER`. Unit tests also cover real discovery,
  malformed protocol shapes and environment restoration.
- `scripts/release.py` generates a clean extension ZIP, project source archive
  and checksums. Exclude build trees, caches, personal output and test hooks.
- Keep GPL-3.0-or-later and Alex Finn's original MIT notice. Attribution and original
  link must identify this as Alex Jax's independent Ubuntu remix.
- Distribution is GitHub and the source installer. Store submission work was
  cancelled. A local build does not publish a release. Keep release status honest.

## Public GitHub and native Debian packaging

This checkout is the public repository at https://github.com/alex-jax/jax-herdr-hud.
`scripts/build_deb.py` builds a system-library `.deb` with no Herdr/runtime bundling,
no maintainer scripts, and no root required for building. It installs the native
launcher, optional GNOME 50 extension and login autostart. Read install.md before
changing those paths. Record validation of the exact Debian artifact separately from source checks.
The source-install scripts are not Debian removal scripts.

- Update checks use `RELEASE_TAG` in app_info.py for preview-aware version comparison.
  Keep it synchronized with the GitHub release tag when publishing. Include updates.py
  in every installer, and keep six-hour network checks and user-initiated downloads/installations off the
  GTK thread. Checks are silent; only an explicit Update click may start installation.

## Display colors

Hud preserves SGR colors and filters OSC palette replacements in terminal_display.py; it does not synchronize
CLI themes or require a patched Herdr. Preserve non-color controls, mouse input,
resize and attach-client ownership. Include the helper in every installer.

The theme chooser in theme_picker.py uses 244 bundled Ptyxis palettes from
terminal_themes.py. Include both modules and the Ptyxis license notice in installers.
Keep ANSI/indexed/RGB text colors; palettes style the whole Hud and VTE
without reconnecting terminals or changing external terminal/CLI preferences.
Run tests/smoke_themes.py on a separate session bus for chooser changes.

# Herdr Hud for macOS

Native AppKit/SwiftTerm companion for **macOS 27 on Apple silicon**, version **1.5**.
This joint Ubuntu/macOS release adds saved SSH machines, agent startup in new
spaces, remembered terminal identities, palette-matching identity tooltips,
a saved automatic-hiding preference, and in-app update checks.

Validation details and limitations are recorded in [VALIDATION.md](VALIDATION.md).
The older GTK/VTE Mac experiment is not the native application shipped here.

## Build and install

Install Apple's Command Line Tools and Herdr separately. From the repository root:

```sh
macos/scripts/build-app.sh release
macos/scripts/install-app.sh
open "$HOME/Applications/Herdr Hud.app"
```

The first build downloads the pinned SwiftTerm source and its Swift package
dependencies. `Package.resolved` records exact revisions. The installed app embeds
its palettes and terminal library; it needs no Python, GTK, VTE, or Homebrew runtime.
Updates replace the single installed app at `~/Applications/Herdr Hud.app`.
The installer keeps recoverable ZIP backups in `macos/dist/backups.noindex`,
cleans up old generated app copies, and refreshes macOS app registration. Build
bundles stay in `macos/dist/build.noindex` so they do not appear as extra installed apps.
The build uses a local ad-hoc signature. Developer ID signing, notarization,
Intel Macs and older macOS releases are outside this release.

## Share a DMG

```sh
macos/scripts/build-dmg.sh
```

This builds the release app and creates
`macos/dist/jax-herdr-hud-1.5-macos-arm64.dmg` plus a SHA-256 file.
The image contains the app, an Applications shortcut, installation/first-launch
instructions, and a source archive with the current Mac source, shared palette
sources, licenses, and pinned Swift dependency sources. It excludes personal
preferences, live sessions, Git metadata, and build caches.

Recipients need Apple silicon, macOS 27 or later, and a separate Herdr installation.
The DMG retains the local ad-hoc signature; it is not Developer ID signed or
notarized. See the enclosed Read Me for Apple's first-launch instructions.

## Appearance

The Mac window follows the GNOME companion's layout: a unified header, sidebar
search, Spaces/Agents sections, indented terminal rows, activity dots, bottom New
space control, terminal heading, and footer. Palette backgrounds, borders, hover,
and selection colors use the same blends as `hud.py`. CLI foreground and background colors stay paired, including selection and
pasted-text highlights. New preferences use VS Code Dark; saved choices are retained. Ubuntu Mono and DejaVu Sans are
bundled and registered only in this app. The Mac controls use the DejaVu Sans
fallback used by the Ubuntu reference environment; the terminal retains Ubuntu
Mono, using Ubuntu 26.04's font and 9 × 19 logical-pixel cells at the default
size. macOS text rasterization and system
menus/dialogs can still differ from GTK.

## Use

- Use **Window → Move to Display → display name** in the Mac menu bar to move Hud
  between monitors. The current display is checked; the list refreshes when opened.
  Moving an expanded window restores its normal size, fits it to the destination
  and saves the position. The floating H keeps its separate position.
- Click the floating **H** to show/hide Hud. Drag it to move it. Escape cancels a
  drag; Enter/Space activates the focused H. Its blue dot means unread activity.
- The menu bar **H** provides Show/Hide, Settings, Launch at Login, and Quit.
  Login startup is opt-in. macOS may require approval in System Settings.
- Closing the window hides it and keeps monitoring and attachments alive. **Quit**
  disconnects only Hud's attach clients. Herdr servers, shells, and agents remain.
- Clicking outside the app hides Hud to the floating H. Clicking or dragging H
  itself does not count as an outside click.
- When the terminal title begins with `user@host`, the heading shows that identity,
  including for SSH or containers that report it. The last reported identity is remembered per terminal while an agent runs.
  Without a reported identity, local agents use the local user/host and remote
  agents use the configured SSH target; these fallbacks are not detected logins.
- Spaces and Agents refer to the same live terminals. Search, collapse, rename,
  and theme changes retain connections and scrollback. Right-click a sidebar row
  for Rename/Close; use its space's **+** for a new terminal.
- The first workspace and its last terminal are protected. Closing other agent
  terminals requires confirmation. Explicit Close stops the selected terminal or
  workspace, unlike hiding or quitting.
- Normal left dragging selects and automatically copies plain text. Shift+click/drag
  sends mouse input to interactive CLIs. The route stays fixed until release.
- Drag to the top or bottom edge of the terminal to extend selection through retained shell
  history or a live agent transcript. Live selection keeps the original terminal,
  colors, geometry, and keyboard focus. Capture stops at 20,000 lines or pauses if
  a redraw cannot be matched safely. Release finishes copying; typing needs no Escape.
- Command-click or Control-click HTTP/HTTPS links opens the default browser,
  including labelled OSC 8 links, without sending that click to the CLI.
- Right-click, Command-V, and Control-V paste clipboard text (including dictation).
  Image-only Command-V/Control-V sends the CLI's Control-V shortcut. Command-C
  also copies selected text. Paste clears selection.
- Header theme, sidebar, and expand controls return keyboard focus to the selected
  terminal after their action. Settings and dialogs keep their own focus.
- The gear opens Settings in the terminal pane. **Choose theme…** opens the
  GNOME-style preview grid, with Light/Dark/Follow desktop and search. Enable
  **Show all palettes** for all 244 Ptyxis palettes plus Hud classic. Settings also
  contains Herdr executable discovery; clear its field for automatic lookup.
- A `blocked` transition means input is needed; `done` or `working` → `idle`
  means completion. Unread state is per terminal, cleared by focusing/selecting it,
  and kept only in memory. The app does not infer completion for unreported agents.

The app discovers local Herdr sessions and enabled saved SSH machines.
Configure remote machines using `herdr machine add <host>`; remote sessions must
already be running and support Unix-socket forwarding. Ordinary SSH shells are
not automatically adopted. Disconnected remote rows are dimmed and input is
disabled until their state reconnects. It initializes the default workspace if
necessary and puts new spaces in the default server, visible to ordinary `herdr`.
It never forces takeover from another direct-attach client. Detach the other client
before selecting a terminal again if it owns input.

## Files and command interface

- App: `~/Applications/Herdr Hud.app`
- Settings: `~/Library/Application Support/Herdr Hud/settings.json`
- Server startup log: `~/Library/Logs/Herdr Hud/server-start.log`
- App diagnostics: macOS Console, process `HerdrHud`

The bundle executable accepts `--background` and `--quit`. A second normal launch
shows the existing instance. The application ID is `io.github.herdr.Hud`.
Preferences use atomic replacement and tolerate malformed field values.

Hud silently checks published releases every six hours. Settings offers **Check
for updates**. When a newer Mac installer exists, a header arrow downloads it
only after you click; the GitHub checksum and disk image are verified before it
opens. Quit Hud and replace your existing app, then reopen it. Keep one installed
copy at `~/Applications/Herdr Hud.app`; do not create a second copy in `/Applications`.
Rebuild and reinstall for development updates. To remove the app, disable Launch at Login,
quit Hud, then move the app bundle to Trash. Settings and Herdr sessions are retained.
Ubuntu preferences and running processes are not automatically imported.

## Validation

Core and desktop results for this update are recorded in [VALIDATION.md](VALIDATION.md).

Core checks run without the XCTest framework or full Xcode:

```sh
swift run --package-path macos HudCoreChecks
```

A debug-only desktop harness creates a uniquely named disposable Herdr session,
uses temporary preferences/configuration, opens the app, exercises real terminal
and sidebar behavior, and stops only that disposable server during cleanup:

```sh
macos/scripts/build-app.sh debug
"macos/dist/build.noindex/Herdr Hud.app/Contents/MacOS/HerdrHud" --smoke-test
cat /private/tmp/herdr-hud-smoke-result.txt
```

The harness uses the clipboard and writes a screenshot at
`/private/tmp/herdr-hud-smoke.png`. Rebuild with `release` before installing.
Debug harness code is excluded from release builds. Real login/logout, lock/unlock,
and physical monitor changes require separate interactive acceptance checks.

## Architecture and licenses

`HudCore` implements Herdr discovery, bounded JSON-lines RPC, event watchers,
preferences, identity/close rules, and streaming display filtering. The app target
owns AppKit windows and keeps one SwiftTerm/PTY attachment for each
`(socket_path, terminal_id)`. Background workers perform network/process work;
UI updates are delivered to the main queue.

GPL-3.0-or-later applies to the port. The app retains Alex Finn's MIT notice,
Ptyxis palette notices, SwiftTerm's license, the Ubuntu Font Licence and the
DejaVu font notice in `Sources/HerdrHud/Resources/Fonts`. The bundled Adwaita
symbolic icons are by the [GNOME Project](https://www.gnome.org); their notice is in
`Sources/HerdrHud/Resources/Icons/Adwaita-LICENSE.txt`. Credits are in the About panel.

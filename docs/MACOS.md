# Herdr Hud on Apple silicon

The macOS port is being prepared for **1.3**, with the **1.2** interface and terminal
behavior as its reference. It targets **macOS 26 and 27 on Apple silicon**. Intel
Macs and Rosetta are not supported. Public release is pending the checks in
[Mac validation](MACOS_VALIDATION.md); a CI artifact is a test build, not a stable release.

## Installing a Mac build

1. Install [Herdr separately](https://herdr.dev/docs/install/). Hud does not bundle,
   install or upgrade Herdr or your agents.
2. Download `jax-herdr-hud-1.3-macos-arm64.dmg` from the supplied test-build link;
   after release, Mac installers will appear under
   [GitHub Releases → Assets](https://github.com/alex-jax/jax-herdr-hud/releases).
3. Open the DMG and drag **Herdr Hud** to **Applications**. Eject the disk image.
4. Open Herdr Hud from Applications. This build is **ad-hoc signed and not
   notarized**. If macOS blocks the first launch, open **System Settings → Privacy
   & Security**, find the blocked app and choose **Open Anyway**, then confirm.
   See [Apple's first-open instructions](https://support.apple.com/en-nz/102445).
5. If Herdr is not found, select its executable in Hud Settings and click Retry.
   Automatic discovery includes `~/.local/bin`, the host PATH and `/opt/homebrew/bin`.

Python, GTK, VTE, icons and fonts are bundled; users do not need Homebrew or a
separate Python installation. The floating H starts with Hud. macOS does not
need a GNOME extension or the Ubuntu logout/login installation step.

Normal dragging selects and copies plain text. Shift+click goes to CLI controls;
right-click and Ctrl+V paste. Ctrl+click opens HTTP/HTTPS links. Existing 1.2
shortcuts are retained, including Control rather than substituting Command.

## Startup, updates and removal

The first launch from Applications registers a per-user login startup item.
Manage background startup in macOS **Login Items**. The app does not recreate a
login item you delete after initial setup. Its registration file is
`~/Library/LaunchAgents/io.github.herdr.Hud.plist`.

Checks run silently every six hours. Only clicking the update arrow downloads an
installer. Hud verifies the download and opens the DMG; exit Hud, replace it in
Applications, and reopen it. An opened installer is not reported as an installed
update. Background checks never replace the app or stop Herdr.

To remove Hud, use **Exit Hud**, remove it from Login Items, delete the registration
file above if present, and move **Herdr Hud.app** to Trash. Keep Herdr installed if
you still use its terminals. Preferences remain in
`~/Library/Application Support/Herdr Hud`; downloaded updates are under
`~/Library/Caches/Herdr Hud`. Explicit `XDG_CONFIG_HOME` and `XDG_CACHE_HOME`
overrides take precedence.

## Building and validating

Use an Apple silicon Mac running macOS 26, with Xcode command-line tools and
Homebrew available to the builder:

```sh
brew install python@3.14 pygobject3 gtk+3 vte3 adwaita-icon-theme
/opt/homebrew/bin/python3.14 -m venv --system-site-packages build/mac-venv
build/mac-venv/bin/python -m pip install pyinstaller==6.22.3 pyobjc-framework-Cocoa==12.2.2 pyobjc-framework-CoreText==12.2.2 certifi==2026.7.22
build/mac-venv/bin/python scripts/build_macos.py
```

The builder produces the app under `build/macos/dist` and the DMG, checksum and
bundle audit under `dist/macos`. It checks arm64 architecture, deployment minimum,
dependency paths and code signatures. The workflow also launches a relocated
bundle while Homebrew is temporarily unavailable on its disposable runner.
Bundled third-party notices and build dependency metadata live inside the app.

Before public release, complete the [test checklist](MACOS_VALIDATION.md) on both
OS versions, including browser download/first-open, visual comparison, real Herdr,
monitors, lock/sleep, login startup and upgrade/removal. Automated tests do not
establish all of those behaviors.

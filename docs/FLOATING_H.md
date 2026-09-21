# Floating H extension

The Debian package and source installer already include the extension for
**GNOME Shell 50**. Hud enables it automatically on first launch.
After installing Herdr and Hud, start `herdr` once, open Hud once, then **save your
work, log out and log back in**. This lets GNOME discover and load the extension.
Installing a new extension version also requires logout/login.

**Exit Hud** closes the companion and hides H together. There is no separate H
off control. Automatic startup respects GNOME Extensions opt-outs and the global
extensions switch; **Enable floating H** in Settings explicitly restores H.

Click H to show or hide Hud; drag it to move it. Its outline follows the desktop
accent colour, and its notification dot indicates unread activity. Hud also works
without the extension.

## Manual ZIP installation

Use this only when installing the separate extension ZIP from GitHub Assets.
The extension UUID is `herdr-hud@alex-jax.github.io`.

```sh
gnome-extensions install --force ./herdr-hud@alex-jax.github.io.shell-extension.zip
```

Log out and back in, then enable it from Hud settings or run:

```sh
gnome-extensions enable herdr-hud@alex-jax.github.io
```

If the old `herdr-hud@local` extension is installed, disable it first; do not run
both UUIDs together. Loaded extension updates also require logout/login.
A per-user extension copy takes precedence over the `.deb` system copy, so avoid
mixing installation methods. Preferences remain under `~/.config/herdr-hud`.

Disabling the extension in GNOME Extensions also exits Hud, while leaving Herdr
servers and agents running.
For setup problems, see [the manual](../MANUAL.md#troubleshooting).

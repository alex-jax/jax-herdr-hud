# Floating H extension

The Debian package and source installer already include the extension for
**GNOME Shell 50**. Normally, use **gear → Enable floating H** in Hud.
After first installing Herdr and Hud, start `herdr` once, then **log out and log
back in** before opening Hud and enabling H. This lets GNOME discover the extension.

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

Disabling the extension exits Hud while leaving Herdr servers and agents running.
For setup problems, see [the manual](../MANUAL.md#troubleshooting).

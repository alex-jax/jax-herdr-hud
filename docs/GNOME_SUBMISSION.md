# Optional floating-H extension submission

Name: **Herdr Hud**

UUID: **herdr-hud@alex-jax.github.io**

Initial public extension revision: **4** (independent of companion version 0.1.0)

Shell compatibility: **50**

Publisher website: https://github.com/alex-jax

Description:

> Optional floating H for Herdr Hud on Ubuntu 26.04 / GNOME 50. Click to show or
> hide your native Herdr terminal companion; drag to move the button. Its badge
> reports unread agent activity. A remix of Alex Finn’s version by Alex Jax.
> Requires the separately installed Herdr Hud companion and Herdr.

Original project: https://github.com/finna/omarchy-herdr-hud

## ZIP and migration

Build with `python3 scripts/release.py`. The ZIP contains the extension at its
root, GPL license and the original MIT notice. It excludes tests, Python runtime,
binaries, caches and install scripts. Upload this ZIP to extensions.gnome.org
using your own GNOME Extensions account; never upload the test-instrumented copy.

Before manual installation, disable the legacy extension:

```sh
gnome-extensions disable herdr-hud@local
# A not-found result is expected on a new installation.
gnome-extensions install --force dist/herdr-hud@alex-jax.github.io.shell-extension.zip
```

Log out and log in so GNOME discovers the new UUID, then enable it:

```sh
gnome-extensions enable herdr-hud@alex-jax.github.io
```

Do not enable both UUIDs: they export the same companion bridge. Preferences
remain under `~/.config/herdr-hud`. The new extension checks the snap launcher
first and the existing per-user development launcher second. If neither exists,
clicking H explains how to install the companion. Disabling the extension exits
the companion through its existing action, leaving Herdr sessions running.

## Review checklist

- Runtime actors, bus export, signals and timers are created in `enable()`.
- `disable()` releases pointer grabs and cleans up actors, timers and signals.
- No GTK imports in the Shell process, bundled executable, downloaded code,
  arbitrary Shell evaluation or mutation of other extensions.
- External execution is limited to the separately installed companion using
  argument arrays; enabling the extension starts it with `--background`.
- Bubble/tooltip are hidden while locked and on the greeter. `unlock-dialog`
  session mode preserves lifecycle handling across lock transitions.
- Original MIT notice is retained alongside GPL-3.0-or-later licensing.
- Screenshots must show the Ubuntu/GNOME version, not the original Omarchy UI.

Attach test results and disclose external companion launching to reviewers.
A passing automated test does not guarantee catalogue acceptance.

Guidelines: https://gjs.guide/extensions/review-guidelines/review-guidelines.html

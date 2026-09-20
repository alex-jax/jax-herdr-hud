# Source installation and troubleshooting

### 1. Install dependencies and clone

Install Herdr using its official instructions, then:

```sh
sudo apt update
sudo apt install git python3 python3-gi gir1.2-gtk-3.0 gir1.2-vte-2.91 gsettings-desktop-schemas adwaita-icon-theme
git clone https://github.com/alex-jax/jax-herdr-hud.git
cd jax-herdr-hud
git checkout v0.1.2-preview.1
```

Use `git switch main` instead if you want the current development source.

### 2. Install as your desktop user

Do not run these commands with sudo:

```sh
python3 install.py
python3 enable.py
~/.local/bin/herdr-hud
```

The installer copies the application and extension into your home directory and
adds background login startup. Log out/in to load the new extension. The source
installer and `.deb` use the same settings and desktop app identity; choose one.

### 3. Modify, test and reinstall

```sh
git switch -c my-changes
python3 -m unittest discover -s tests -v
# After editing:
python3 install.py
python3 activate.py
```

Python changes take effect after restart. Loaded extension changes need logout/login.
See [CONTRIBUTING.md](../CONTRIBUTING.md) for GUI tests and packaging.
To remove a source installation, run `python3 uninstall.py` from this checkout.

## Build the .deb yourself

From a checkout with Python 3 and `dpkg-deb` (provided by Ubuntu's `dpkg`):

```sh
python3 scripts/build_deb.py
sudo apt install ./dist/jax-herdr-hud_0.1.2-1_all.deb
```

Building needs no root and performs no downloads. To prepare the separate extension
ZIP and source archive too, run `python3 scripts/release.py` after building.

## Troubleshooting and limitations

- **No H:** verify GNOME 50, extension enablement, then log out/in. A stale per-user
  copy of the same extension UUID takes precedence over the system `.deb` copy;
  uninstall that source installation before switching to the `.deb`.
- **Old UI:** exit the current singleton app before opening the newly installed one.
- **Missing Herdr:** use the setup screen and verify your executable with `--version`.
- **Agents not separated:** only agents identified or reported by Herdr enter Agents.
- **More details:** [MANUAL.md](../MANUAL.md), [validation](VALIDATION.md),
  [report an issue](https://github.com/alex-jax/jax-herdr-hud/issues).

# Install Herdr Hud on Ubuntu

These steps target **Ubuntu 26.04 with GNOME Shell 50**. The first public release
is a **development preview**, tested on amd64. The Python `.deb` is architecture
independent, but other CPU architectures and Ubuntu releases are not verified.
Herdr Hud is independent of Herdr and requires Herdr installed separately.
The Snap/App Center package is still being prepared; no Store listing is claimed.

## Option A — install the downloadable .deb (recommended)

### 1. Check your desktop

```sh
. /etc/os-release
printf '%s\n' "$PRETTY_NAME"
gnome-shell --version
```

Expect Ubuntu 26.04 and GNOME Shell 50. The floating H is supported only on
GNOME 50. Do not enable it on another Shell version by editing its metadata.

### 2. Install Herdr if you do not already have it

Keep an existing working Herdr installation. This HUD is tested with Herdr 0.9.1.
For a new installation, ensure the download tools are available:

```sh
sudo apt update
sudo apt install curl ca-certificates less
```

Then follow the [official Herdr instructions](https://herdr.dev/docs/install/).
The upstream installer can be downloaded, inspected and run as your normal user:

```sh
curl -fsSL https://herdr.dev/install.sh -o /tmp/herdr-install.sh
less /tmp/herdr-install.sh
sh /tmp/herdr-install.sh
```

Press `q` to exit `less`. Verify the installation (the official default location):

```sh
~/.local/bin/herdr --version
```

If you installed elsewhere, use that executable's path instead. Herdr Hud's setup
screen can select it. Install Codex, Claude, Gemini or other CLI agents separately
if you want to use them; the HUD does not install agents or their credentials.

### 3. Download the preview and verify it

Open the [release page](https://github.com/alex-jax/jax-herdr-hud/releases/tag/v0.1.1-preview.1)
and download `jax-herdr-hud_0.1.1-1_all.deb` and `SHA256SUMS`, or run:

```sh
mkdir -p ~/Downloads/jax-herdr-hud-0.1.1
cd ~/Downloads/jax-herdr-hud-0.1.1
curl -fLO https://github.com/alex-jax/jax-herdr-hud/releases/download/v0.1.1-preview.1/jax-herdr-hud_0.1.1-1_all.deb
curl -fLO https://github.com/alex-jax/jax-herdr-hud/releases/download/v0.1.1-preview.1/SHA256SUMS
sha256sum --check --ignore-missing SHA256SUMS
```

The `.deb` must report `OK`. Stop and re-download if it does not.

### 4. Install the package

If you used this project's source installer previously, first run
`python3 uninstall.py` from that old checkout as your normal user. This removes
its per-user files but preserves Herdr, running terminals and HUD preferences.
Use only one companion installation at a time; do not mix the preview Snap,
source installation and native `.deb`.

```sh
sudo apt update
sudo apt install ./jax-herdr-hud_0.1.1-1_all.deb
```

APT installs Python/GTK/VTE dependencies from Ubuntu. The `.deb` contains the HUD
and extension, not Herdr or bundled runtime libraries. It installs the companion
at `/usr/bin/herdr-hud` and the extension under `/usr/share/gnome-shell/extensions/`.
It does not start programs as root or modify running Herdr servers.

### 5. Open Herdr Hud

Open **Herdr Hud** in Ubuntu's application launcher, or run:

```sh
/usr/bin/herdr-hud
```

If setup appears, leave the executable field blank to discover Herdr automatically
and click **Retry**, or select your Herdr executable. The default `~` space and its terminal open automatically on a fresh start.
Choose **New space** to add another named space. Both are visible in `herdr`.

### 6. Enable the floating H (optional)

The standalone window works immediately. To use the bubble:

1. Save your desktop work, then **log out and log back in** so GNOME discovers the
   newly installed system extension.
2. Open a terminal and run these commands as your normal desktop user:

```sh
# Only needed when the legacy development extension was previously installed:
gnome-extensions disable herdr-hud@local 2>/dev/null || true

gnome-extensions enable herdr-hud@alex-jax.github.io
gnome-extensions info herdr-hud@alex-jax.github.io
```

3. If GNOME says user extensions are globally disabled, turn them on in the
   **Extensions** application, then repeat the enable command.
4. Click H to show/hide the HUD and drag H to reposition it.

Never enable the old and new UUIDs together. For extension code updates, log out
and back in again. The `.deb` enables background startup at GNOME login; it does
not automatically enable the extension. To disable background startup for your
user without removing the app:

```sh
mkdir -p ~/.config/autostart
cp /etc/xdg/autostart/io.github.herdr.Hud.desktop ~/.config/autostart/
printf '\nHidden=true\n' >> ~/.config/autostart/io.github.herdr.Hud.desktop
```

If the extension remains enabled, it also starts its companion. Disable the
extension as well if you do not want the HUD to start at login.

### 7. Update or remove

For updates, exit the HUD, download the next `.deb`, verify its checksum and run
`sudo apt install ./<downloaded-file>.deb`. Reopen the HUD; log out/in if the
extension changed. There is no automatic APT update repository for this preview.

To remove the `.deb` installation:

```sh
/usr/bin/herdr-hud --quit
gnome-extensions disable herdr-hud@alex-jax.github.io
sudo apt remove jax-herdr-hud
```

Hud preferences remain in `~/.config/herdr-hud/`. Herdr is separate and is not
removed or stopped. The per-user autostart override, if you created it, can remain
or be removed manually. Do not use `uninstall.py` for the `.deb`; that script is
for source installations only.

## Option B — install or modify the source

### 1. Install dependencies and clone

Install Herdr as described above, then:

```sh
sudo apt update
sudo apt install git python3 python3-gi gir1.2-gtk-3.0 gir1.2-vte-2.91 gsettings-desktop-schemas adwaita-icon-theme
git clone https://github.com/alex-jax/jax-herdr-hud.git
cd jax-herdr-hud
git checkout v0.1.1-preview.1
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
See [CONTRIBUTING.md](CONTRIBUTING.md) for GUI tests and packaging.
To remove a source installation, run `python3 uninstall.py` from this checkout.

## Build the .deb yourself

From a checkout with Python 3 and `dpkg-deb` (provided by Ubuntu's `dpkg`):

```sh
python3 scripts/build_deb.py
sudo apt install ./dist/jax-herdr-hud_0.1.1-1_all.deb
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
- **More details:** [MANUAL.md](MANUAL.md), [validation](docs/VALIDATION.md),
  [report an issue](https://github.com/alex-jax/jax-herdr-hud/issues).

# Install Herdr Hud

## macOS — Apple silicon

The Apple silicon Mac port targets macOS 26 and 27 and remains in development.
There is no Mac installer in the stable 1.3 release. See the [Mac installation,
updates and removal guide](docs/MACOS.md) for test builds and validation status.

## Ubuntu

For **Ubuntu 26.04 with GNOME 50**. The floating H is included in the download.

1. Open the [release page](https://github.com/alex-jax/jax-herdr-hud/releases) and, under **Assets**, **download the `*_all.deb` file**.
2. **Install Herdr** using the [official instructions](https://herdr.dev/docs/install/). Skip this if you already have it.
3. **Install Herdr Hud** by opening the downloaded `.deb` with your software installer.
4. **Start Herdr once** by running `herdr` in a terminal.
5. **Open Herdr Hud once.** It automatically enables the bundled floating H.
6. **Save your work, log out of Ubuntu, and log back in.** The floating H can now connect to Hud.

**The logout/login step is important:** it lets GNOME discover the bundled H
extension so it can connect to Hud. Installing the `.deb` alone cannot reload
GNOME. No manual enable step is normally needed. If H is not visible after login,
open Hud and check the message in Settings.

**Hud and H close together:** use **Exit Hud** to close the app and hide its
floating H. There is no separate H off control. If you previously disabled the
extension in GNOME Extensions, turn it back on in GNOME Extensions.

Click **H** to show or hide Hud, or drag it wherever you like.

New installations start with **VS Code Dark**. Change the palette in Settings →
Appearance or use the sun/moon button for light mode. Updates keep your saved choice.

<details>
<summary>If the .deb does not open in a software installer</summary>

Open a terminal in the download folder and run this, replacing
`downloaded-file.deb` with the name of the file you downloaded:

```sh
sudo apt install ./downloaded-file.deb
```

</details>

<a id="7-update-or-remove"></a>

## Updating

**Moving to 1.3:** Hud 1.2 can detect and install this update using the download
arrow. Older versions that do not recognize two-part version numbers must be
updated manually by downloading the `.deb` under **Assets**.

Hud checks GitHub silently every six hours. When the download arrow appears,
click it to download and install the new `.deb`. Approve Ubuntu's password prompt
if shown, then restart Hud. Your settings and Herdr sessions are kept. If an update
changes the H extension, **save your work, log out and log back in** to load it.
The first launch after upgrading enables H automatically. An extension disabled
in GNOME Extensions can be turned back on there; Hud Settings shows its status.

You can also download the newer `.deb` under **Assets** on the release page and
install it manually. No update notification pop-ups are shown.

## Removing Hud

Exit Hud, then run `sudo apt remove jax-herdr-hud`. Herdr is a separate application.

## Need help?

- **H does not appear:** read the **Floating H** status in Settings.
- **Herdr is not found:** use the gear to select your Herdr executable, then click **Retry**.
- [Source installation, building and troubleshooting](docs/INSTALL_ADVANCED.md)
- [User manual](MANUAL.md) · [Validation record](docs/VALIDATION.md)

The published release was tested on amd64 with Herdr 0.9.1. Current source core
integration was also tested on ARM64 with Herdr 0.9.5 in a VM; see
[validation details](docs/VALIDATION.md). See the release page for available builds.

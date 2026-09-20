# Install Herdr Hud on Ubuntu

For **Ubuntu 26.04 with GNOME 50**. The floating H is included in the download.

1. Open the [release page](https://github.com/alex-jax/jax-herdr-hud/releases) and, under **Assets**, **download the `*_all.deb` file**.
2. **Install Herdr** using the [official instructions](https://herdr.dev/docs/install/). Skip this if you already have it.
3. **Install Herdr Hud** by opening the downloaded `.deb` with your software installer.
4. **Start Herdr once** by running `herdr` in a terminal.
5. **Save your work, log out of Ubuntu, and log back in.**
6. **Open Herdr Hud**, click the **gear** at the top left, then **Enable floating H**.

**The logout/login step is important:** it lets GNOME discover the bundled H
extension so it can connect to Hud. If you enabled H before logging out, reopen
Hud after logging back in.

Click **H** to show or hide Hud, or drag it wherever you like.

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

Hud checks GitHub silently every six hours. When the download arrow appears,
click it to download and install the new `.deb`. Approve Ubuntu's password prompt
if shown, then restart Hud. Your settings and Herdr sessions are kept. If an update
changes the H extension, log out and back in.

You can also download the newer `.deb` under **Assets** on the release page and
install it manually. No update notification pop-ups are shown.

## Removing Hud

Exit Hud, then run `sudo apt remove jax-herdr-hud`. Herdr is a separate application.

## Need help?

- **H does not appear:** follow the message beside **Enable floating H** in settings.
- **Herdr is not found:** use the gear to select your Herdr executable, then click **Retry**.
- [Source installation, building and troubleshooting](docs/INSTALL_ADVANCED.md)
- [User manual](MANUAL.md) · [Validation record](docs/VALIDATION.md)

Tested on amd64 with Herdr 0.9.1. See the release page for the available version.

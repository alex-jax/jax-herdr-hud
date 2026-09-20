# Install Herdr Hud on Ubuntu

For **Ubuntu 26.04 with GNOME 50**. The floating H is included in the download.

1. Open the [release page](https://github.com/alex-jax/jax-herdr-hud/releases) and, under **Assets**, **download the `*_all.deb` file**.
2. **Install Herdr** using the [official instructions](https://herdr.dev/docs/install/). Skip this if you already have it.
3. **Install Herdr Hud** by opening the downloaded `.deb` with your software installer.
4. **Start Herdr once** by running `herdr` in a terminal.
5. **Save your work, log out of Ubuntu, and log back in.**
6. **Open Herdr Hud**, click the **gear** at the top left, then **Enable floating H**.

That's it. Click **H** to show or hide Hud, or drag it wherever you like.

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

When the download arrow appears in Hud, follow it to the update instructions.
Exit Hud, download and install the newer `.deb`, then open Hud again. Your settings
and Herdr sessions are kept. If an update changes the H extension, log out and back in.

## Need help?

- **H does not appear:** follow the message beside **Enable floating H** in settings.
- **Herdr is not found:** use the gear to select your Herdr executable, then click **Retry**.
- [Source installation, building and troubleshooting](docs/INSTALL_ADVANCED.md)
- [User manual](MANUAL.md) · [Preview validation](docs/VALIDATION.md)

This is a development preview, tested on amd64 with Herdr 0.9.1.

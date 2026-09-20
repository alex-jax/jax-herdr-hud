# Attribution and licenses

Herdr Hud — A remix of Alex Finn’s version by Alex Jax.

- Ubuntu implementation and packaging: Copyright © 2026 Alex Jax.
  [Publisher](https://github.com/alex-jax). Licensed GPL-3.0-or-later; see LICENSE.
- Original project: [Alex Finn’s Herdr HUD for Omarchy](https://github.com/finna/omarchy-herdr-hud).
  Copyright © 2026 Alex Finn, MIT. The original notice and permission text are
  preserved in licenses/Alex-Finn-MIT.txt. Upstream portions retain that notice;
  the Ubuntu distribution and modifications use GPL-3.0-or-later.
- [Herdr](https://github.com/herdrdev/herdr) is a separate application, not bundled,
  installed or updated by this project. Herdr 0.9.1 is the tested version.

This is an independently maintained Ubuntu remix, not an official release from
Alex Finn or the Herdr project. No endorsement is claimed.

The native Debian package uses system dependencies and bundles no Ubuntu runtime
libraries. Snap binary releases include Ubuntu runtime packages under their respective licenses.
Their package/version inventory and upstream copyright notices are included under
`usr/share/doc/herdr-hud/runtime-packages.json` and `usr/share/doc/*/copyright`.
The rootless builder additionally records authenticated archive SHA-256 values
and source package versions. See docs/PUBLISHING.md for source obligations before
redistributing binary runtime libraries. The project source archive alone does
not contain the corresponding source of the bundled Ubuntu packages.

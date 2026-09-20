# Draft: classic confinement request for herdr-hud-alex-jax

This is a draft for the publisher to submit in the Snapcraft forum's
`store-requests` category. It has not been sent and approval has not been granted.

## Publisher and application

Publisher: Alex Jax — https://github.com/alex-jax
Application: Herdr Hud, proposed snap name `herdr-hud-alex-jax`
Application source: attach the public source release URL when one exists.
Package/revision: attach the tested artifact's checksum and store revision.

Herdr Hud is a native GTK/VTE terminal companion and session browser. It uses
Herdr's local Unix-socket API and native direct-attach client to expose interactive
host terminals. Users run their own shells, coding agents and developer tools
in arbitrary project directories. Herdr Hud is an independently maintained remix
of https://github.com/finna/omarchy-herdr-hud.

## Why classic is requested

The core application is an interactive terminal/multiplexer client. Its purpose
is to operate the user's existing host development environment, including shells,
executables and projects not known when the snap is built. New Herdr workspaces
must use that same host environment and remain accessible to the user's ordinary
Herdr client. Confining these terminals to a separate application environment
would change that core behaviour.

The request is based on terminal emulation and host developer-tool execution,
not merely reading hidden files, supporting a hardcoded executable location,
or avoiding bundling dependencies. Python, GTK, VTE and associated libraries
are bundled. Herdr is user-supplied because this is a companion for existing
Herdr installations and sessions; we understand that a host-only dependency
is not by itself a justification for classic confinement.

A floating-H GNOME extension is distributed separately. The snap does not install,
enable or modify extensions and does not need classic access to act as an
extension installer. Its optional bridge calls the extension's defined D-Bus
methods, not arbitrary Shell evaluation.

## Behaviour for reviewers

- Runs as the desktop user; no daemon, root operations or package-install hooks.
- Discovers a selected Herdr executable, the usual user-local location or host PATH.
- Reads local session snapshots and events; attaches through VTE to user-selected panes.
- Executes explicit workspace/terminal create, rename and close actions.
- Exit detaches only owned clients; it does not stop Herdr servers or agents.
- Preferences remain in the user's existing XDG configuration directories.
- No telemetry or hosted Hud service. Agents have their own data/network behaviour.

Attach the validation report and note any outstanding VM or confinement tests.
Do not claim approval or broad distribution compatibility before review.

Policy: https://snapcraft.io/docs/reference/administration/reviewing-classic-confinement-snaps/

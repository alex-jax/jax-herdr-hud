# Snap Store listing draft

**Name:** Herdr Hud

**Proposed snap ID:** `herdr-hud-alex-jax` (not registered)

**Version:** 0.1.0

**Publisher:** Alex Jax — https://github.com/alex-jax

**License:** GPL-3.0-or-later

**Category:** Development

**Summary:** Native Herdr terminals and agents for Ubuntu

## Description

Herdr Hud brings your local Herdr terminals and coding agents into a native
Ubuntu window. Browse spaces, switch between real terminals, and see agent
activity without losing terminal connections or scrollback.

A remix of Alex Finn’s version by Alex Jax.

- Interactive terminals with keyboard input, drag-to-copy and right-click paste.
- Separate Spaces and Agents lists, search, and independent terminals per space.
- Rename spaces and terminals, adjust the sidebar, and choose light or dark appearance.
- Hide or exit the Hud while your Herdr sessions continue running.
- Optional floating H button and activity badge through a separate GNOME extension.

Requires Ubuntu 26.04 on x86-64 and an existing Herdr installation. Compatibility
is tested with Herdr 0.9.1. Herdr is not included or installed automatically.
Use the setup screen to choose its executable if it is not found automatically.
The floating H requires GNOME 50 and is installed separately; the companion
works without it. Agents must already be installed and authenticated through
their own tools. Only local Herdr sessions are supported in this release.

This terminal companion uses classic confinement to work with your host shells,
projects and developer tools. Closing a terminal or space stops its processes;
hiding or exiting the Hud only disconnects its clients.

Independently maintained by Alex Jax, not an official release from Alex Finn
or the Herdr project. Original project: https://github.com/finna/omarchy-herdr-hud
Publisher: https://github.com/alex-jax

## Images and metadata to submit

Use actual screenshots produced by the release test run. Label fixture screenshots
as demonstrations. Do not publish images containing personal terminal output,
credentials or account details. Use `snap/gui/io.github.herdr.Hud.svg` as the
app icon. Confirm the publisher account, registered snap name and support contact
in the store dashboard. No repository or issue URL has been invented.

## Data handling

The Hud reads local Herdr session information and sends terminal input to the
selected local Herdr process. Hud preferences are stored locally. The Hud does
not implement telemetry, an account system or a hosted backend. Herdr and agents
launched inside terminals have their own network behaviour and data policies.
Opening documentation links launches the user's browser.

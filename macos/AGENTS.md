# Native macOS maintenance

This subtree implements the approved native macOS port. Preserve the parent
repository's Herdr protocol, identity, attention, and process-ownership contracts.
Ubuntu packaging/install checks do not apply to changes confined to this subtree.

Build and install through scripts/build-app.sh and scripts/install-app.sh. Target
macOS 27 and arm64. Keep the SwiftTerm revision and Package.resolved synchronized.
Do not bundle or upgrade Herdr. Do not stop user servers during tests or updates.

Use `swift run --package-path macos HudCoreChecks` from the repository root for
core checks. Desktop integration uses a debug bundle's `--smoke-test`, which creates
and cleans up only a uniquely named disposable server and temporary configuration.
Its clipboard and window interactions require a desktop session. Record actual
checks and distinguish simulated activity/geometry from physical lock/monitor tests.

UI and terminal view operations belong on the main queue; socket and CLI operations
belong on workers. Keep terminal instances keyed by socket path and terminal ID.
Use scripts/export-palettes.py after changes to the shared Ubuntu palette source.
Build a release bundle after debug tests before installing. Public distribution
requires a separate signing/notarization workflow; local ad-hoc signing is intentional.

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
Build a release bundle after debug tests before installing. Distribution uses
GitHub and an ad-hoc signed DMG; Developer ID enrollment and Apple notarization
are not required for this project. Do not label releases as previews solely
because they use ad-hoc signing. Retain factual macOS first-launch instructions.

Updates must leave one installed app at ~/Applications/Herdr Hud.app. Keep build
bundles in dist/build.noindex and backups as ZIP files in dist/backups.noindex;
never retain launchable .previous.*.app backups. Run cleanup-apps.py through the
installer to archive old generated bundles and refresh LaunchServices registration.
Preserve Herdr sessions and skip cleanup of any build that is still running.

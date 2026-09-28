# Validation

## 1.2 — 28 September 2026

Target: Ubuntu 26.04 / GNOME Shell 50, amd64, Herdr 0.9.1.

- Normal drag copies plain text; Shift+click sends unmodified CLI mouse input.
  Real-pointer tests move beyond both borders and verify copied lines remain
  contiguous, exceed the viewport, and stop extending after release.
- Tests cover both retained Herdr history and a full-screen CLI which accepts
  wheel events only over its transcript. VTE's cached pointer position must be
  moved to the transcript before scrolling; scroll-event coordinates alone do
  not control the emitted mouse report.
- The original colored VTE stays visible and focused while CLI selection grows.
  Release finishes selection immediately, without a text-only view or Escape.
  Tests verify that the terminal layout does not change.
- Tested the user's existing Codex pane on Wayland without submitting input or
  stopping its agent/server. The final live-terminal implementation copied 53
  lines downward from a 29-row viewport and retained focus on release.
- Unit coverage includes changing CLI footer controls, fragmented SGR color
  pairs, OSC hyperlink preservation, backend behavior and distribution.
- Native desktop coverage includes text paste, CLI mouse input, themes, agent
  tracking, space closure and detaching without stopping user sessions.
- Link smoke tests exercise plain URLs and OSC 8 links through a recorded desktop
  URI launcher. They do not launch a real external browser.
- Theme smoke tests check VS Code Dark for fresh preferences, its light variant,
  chooser filtering and preservation of saved palette/appearance choices.

Release checks (28 September 2026): 47 unit tests passed, including two-part
version ordering, legacy-version compatibility and future update discovery.
Source theme and link smoke checks passed during PR verification. The 1.2 Debian
payload passed theme and real Herdr desktop smoke checks; after the version-parser
change, the rebuilt final payload passed the update smoke check. Installed
`jax-herdr-hud_1.2-1_all.deb` locally, verified installed application modules
against source, confirmed the launcher reports 1.2, and restarted Hud successfully.
Existing user sessions were retained.

Limitations: no automated end-to-end test of every vendor CLI or the Voquill app;
no clean-VM installation/upgrade/removal test. The older update checker cannot
recognize two-part release tags, so existing users must download 1.2 manually.

# Validation

## Current unreleased update

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

Final PR checks (28 September 2026): 46 unit tests passed. Source theme and
link smoke checks passed. Rebuilt `jax-herdr-hud_1.1.3-1_all.deb`; theme and
real Herdr desktop smoke checks passed against its extracted payload. Installed
that package locally, verified installed `hud.py`, `theme_picker.py` and
`terminal_display.py` against source, and restarted the normal Hud launcher
successfully. Existing user sessions were retained.

Limitations: no automated end-to-end test of every vendor CLI or the Voquill app;
no clean-VM installation/upgrade/removal test. No release is published by this PR.

## 1.1.3 — 21 September 2026

Target: Ubuntu 26.04 / GNOME Shell 50, amd64, Herdr 0.9.1.

- 40 unit tests passed, including fragmented SGR input, background normalization,
  preserved foreground components, controls and reverse video.
- Native sidebar, setup and real Herdr desktop checks passed during development.
- Real mouse and keyboard paste clear selection and preserve clipboard contents.
- A separate VTE rendering check sampled white and dark input-row backgrounds
  despite an explicit CLI RGB background.
- Clean-VM installation, upgrade and removal were not tested.

- Extracted release package passed setup and real Herdr desktop smoke checks.
  The first desktop attempt timed out at initial shell output; the repeat passed.
- Installed the release package locally, verified installed Python files against
  the source and restarted the normal launcher successfully before publication.
- Captured current sessions in Nord dark and light for the README.

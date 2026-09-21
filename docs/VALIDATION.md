# Validation

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

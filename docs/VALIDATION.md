# Validation

## 1.1.2 — 21 September 2026

Target: Ubuntu 26.04 / GNOME Shell 50, amd64, Herdr 0.9.1.

- All 39 unit tests passed.
- Extracted Debian payload passed the native sidebar smoke test, including space
  names in the header, live rename updates, named-server prefixes, preserving
  Settings, and retaining terminal identity.
- Sidebar selection, search, collapsing, context menus and window geometry checks passed.
- Packaged runtime matches the tested payload; release archives and checksums verified.
- No local installation or restart is performed by publication. Clean-VM
  install, upgrade and removal were not tested for this release.

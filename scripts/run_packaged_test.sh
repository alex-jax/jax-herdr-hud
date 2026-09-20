#!/bin/sh
# Execute a source smoke test using an extracted snap's Python and GI libraries.
set -eu
export SNAP="$(realpath "$1")"
shift
export _HUD_HOST_PYTHONHOME_SET="${PYTHONHOME+x}"
export _HUD_HOST_PYTHONHOME="${PYTHONHOME-}"
export _HUD_HOST_PYTHONPATH_SET="${PYTHONPATH+x}"
export _HUD_HOST_PYTHONPATH="${PYTHONPATH-}"
unset PYTHONPATH
export PYTHONHOME="$SNAP/usr"
exec "$SNAP/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2" \
  --library-path "$SNAP/usr/lib/x86_64-linux-gnu:$SNAP/lib/x86_64-linux-gnu" \
  "$SNAP/usr/bin/python3" -s "$(dirname "$0")/run_packaged_test.py" "$@"

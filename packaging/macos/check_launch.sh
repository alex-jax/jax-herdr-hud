#!/bin/bash
# Normal packaged startup and singleton IPC, with no Herdr on the test PATH.
set -eu
app=$1
root=$2
mkdir -p "$root/config" "$root/cache"
export XDG_CONFIG_HOME="$root/config" XDG_CACHE_HOME="$root/cache"
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
"$app" --background > "$root/launch.log" 2>&1 &
hud_pid=$!
cleanup() {
    "$app" --quit || true
    cat "$root/launch.log"
}
trap cleanup EXIT
sleep 3
kill -0 "$hud_pid"
"$app" --background
kill -0 "$hud_pid"
"$app" --quit
for ((attempt=0; attempt<50; attempt++)); do
    if ! kill -0 "$hud_pid" 2>/dev/null; then
        wait "$hud_pid"
        echo 'PASS: packaged startup, duplicate activation and quit'
        exit 0
    fi
    sleep 0.2
done
echo 'Hud did not exit after singleton quit' >&2
exit 1

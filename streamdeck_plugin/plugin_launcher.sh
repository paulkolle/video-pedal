#!/bin/sh
set -eu
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LOG_DIR="$HOME/Library/Logs/video-pedal"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/plugin-launch.log" 2>&1
printf 'launch %s args=%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
exec /usr/bin/env python3 "$PLUGIN_DIR/video_pedal_plugin.py" "$@"

#!/bin/sh
set -eu

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PLUGIN_DIR="$HOME/Library/Application Support/com.elgato.StreamDeck/Plugins/com.paul.video-pedal.sdPlugin"

mkdir -p "$PLUGIN_DIR/icons"
cp "$REPO_DIR/streamdeck_plugin/manifest.json" "$PLUGIN_DIR/manifest.json"
cp "$REPO_DIR/streamdeck_plugin/video_pedal_plugin.py" "$PLUGIN_DIR/video_pedal_plugin.py"
cp "$REPO_DIR/streamdeck_plugin/plugin_launcher.sh" "$PLUGIN_DIR/plugin_launcher.sh"
cp "$REPO_DIR/streamdeck_plugin/icons/"*.png "$PLUGIN_DIR/icons/"
chmod 755 "$PLUGIN_DIR/video_pedal_plugin.py" "$PLUGIN_DIR/plugin_launcher.sh"

printf '%s\n' "$PLUGIN_DIR"

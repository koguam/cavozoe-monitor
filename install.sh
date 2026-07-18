#!/bin/bash
# Install / start the launchd agent (runs the check every 3 minutes).
set -e
PLIST_SRC="/Users/maksymkogua/Vibecoding/hotel_monitor/com.cavozoe.monitor.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.cavozoe.monitor.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

# Reload cleanly if it was already loaded.
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Loaded com.cavozoe.monitor (every 180s)."
echo "Check status:  launchctl list | grep cavozoe"
echo "Live log:      tail -f /Users/maksymkogua/Vibecoding/hotel_monitor/logs/monitor.log"

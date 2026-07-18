#!/bin/bash
# Stop / remove the launchd agent.
PLIST_DST="$HOME/Library/LaunchAgents/com.cavozoe.monitor.plist"
launchctl unload "$PLIST_DST" 2>/dev/null || true
rm -f "$PLIST_DST"
echo "Removed com.cavozoe.monitor."

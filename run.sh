#!/bin/bash
# Wrapper used by launchd: runs one availability check and appends to a log.
cd "$(dirname "$0")" || exit 1
PY="/Users/maksymkogua/miniconda3/bin/python3"
"$PY" check.py >> logs/monitor.log 2>&1

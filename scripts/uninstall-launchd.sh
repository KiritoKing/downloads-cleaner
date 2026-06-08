#!/usr/bin/env bash
set -euo pipefail

PLIST_PATH="${HOME}/Library/LaunchAgents/com.local.downloads-cleaner.plist"
LABEL="com.local.downloads-cleaner"
SERVICE="gui/$(id -u)/${LABEL}"

launchctl bootout "gui/$(id -u)" "${PLIST_PATH}" >/dev/null 2>&1 || true
launchctl disable "${SERVICE}" >/dev/null 2>&1 || true
rm -f "${PLIST_PATH}"

echo "uninstalled ${LABEL}"
echo "kept config: ${HOME}/.config/downloads-cleaner/rules.toml"
echo "kept log: ${HOME}/Library/Logs/downloads-cleaner.log"

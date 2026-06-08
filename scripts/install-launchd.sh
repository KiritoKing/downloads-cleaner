#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${HOME}/.config/downloads-cleaner"
CONFIG_PATH="${CONFIG_DIR}/rules.toml"
LAUNCH_AGENT_DIR="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs"
STDOUT_PATH="${LOG_DIR}/downloads-cleaner.out"
STDERR_PATH="${LOG_DIR}/downloads-cleaner.err"
PLIST_PATH="${LAUNCH_AGENT_DIR}/com.local.downloads-cleaner.plist"
TEMPLATE_PATH="${PROJECT_DIR}/launchd/com.local.downloads-cleaner.plist.template"
VENV_DIR="${PROJECT_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
LABEL="com.local.downloads-cleaner"
SERVICE="gui/$(id -u)/${LABEL}"

pick_python() {
  local candidate
  for candidate in "${DOWNLOADS_CLEANER_PYTHON:-}" "${HOME}/.pyenv/shims/python3" "python3"; do
    if [[ -z "${candidate}" ]]; then
      continue
    fi
    if "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

PYTHON_SOURCE="$(pick_python || true)"
if [[ -z "${PYTHON_SOURCE}" ]]; then
  echo "Python 3.11+ is required. Set DOWNLOADS_CLEANER_PYTHON to a Python 3.11+ interpreter." >&2
  exit 2
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  "${PYTHON_SOURCE}" -m venv "${VENV_DIR}"
elif ! "${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
  echo "Existing ${VENV_DIR} is not Python 3.11+. Remove it and rerun this script." >&2
  exit 2
fi

"${PYTHON_BIN}" -m pip install --upgrade pip >/dev/null
"${PYTHON_BIN}" -m pip install -e "${PROJECT_DIR}" >/dev/null

mkdir -p "${CONFIG_DIR}" "${LAUNCH_AGENT_DIR}" "${LOG_DIR}"
if [[ ! -f "${CONFIG_PATH}" ]]; then
  cp "${PROJECT_DIR}/rules.toml" "${CONFIG_PATH}"
  echo "created ${CONFIG_PATH}"
else
  echo "kept existing ${CONFIG_PATH}"
fi

sed \
  -e "s#__PYTHON_BIN__#${PYTHON_BIN}#g" \
  -e "s#__CONFIG_PATH__#${CONFIG_PATH}#g" \
  -e "s#__STDOUT_PATH__#${STDOUT_PATH}#g" \
  -e "s#__STDERR_PATH__#${STDERR_PATH}#g" \
  "${TEMPLATE_PATH}" > "${PLIST_PATH}"

launchctl bootout "gui/$(id -u)" "${PLIST_PATH}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"
launchctl enable "${SERVICE}"
launchctl kickstart -k "${SERVICE}"

echo "installed ${LABEL}"
echo "config: ${CONFIG_PATH}"
echo "plist: ${PLIST_PATH}"

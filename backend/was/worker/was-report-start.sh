#!/bin/bash
# Start the WAS report process inside the container.
set -euo pipefail

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  exec was-report-batch "$@"
fi

if [ "${1:-}" = "was-reports" ] && { [ "${2:-}" = "--help" ] || [ "${2:-}" = "-h" ]; }; then
  shift
  exec was-reports "$@"
fi

if [ ! -f "${WAS_CONFIG_PATH:-/app/was_config.txt}" ]; then
  echo "WAS config file not found at ${WAS_CONFIG_PATH:-/app/was_config.txt}" >&2
  echo "Mount was_config.txt into the container, or set WAS_CONFIG_PATH." >&2
  exit 1
fi

if [ "${1:-}" = "was-reports" ]; then
  shift
  exec was-reports "$@"
fi

exec was-report-batch "$@"

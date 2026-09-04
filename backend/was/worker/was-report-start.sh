#!/bin/bash
# Start the WAS report process inside the container.
set -euo pipefail

if [ "${1:-}" = "was-report-on-demand" ] || [ "${1:-}" = "was-mailer" ]; then
  exec "$@"
fi

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  exec was-report-batch "$@"
fi

if [ "${1:-}" = "was-reports" ] && { [ "${2:-}" = "--help" ] || [ "${2:-}" = "-h" ]; }; then
  shift
  exec was-reports "$@"
fi

if [ "${1:-}" = "was-reports" ]; then
  shift
  exec was-reports "$@"
fi

if [ "${1:-}" = "was-export-xml" ]; then
  shift
  exec was-export-xml "$@"
fi

if [ "${1:-}" = "was-inventory" ]; then
  shift
  exec was-inventory "$@"
fi

if [ "${1:-}" = "was-menu" ]; then
  shift
  exec was-menu "$@"
fi

if [ "${1:-}" = "was-admin" ]; then
  shift
  exec was-admin "$@"
fi

if [ "${1:-}" = "was-special-cases" ]; then
  shift
  exec was-special-cases "$@"
fi

if [ "${1:-}" = "was-stakeholders" ]; then
  shift
  exec was-stakeholders "$@"
fi

if [ "${1:-}" = "was-tracker" ]; then
  shift
  exec was-tracker "$@"
fi

if [ "${1:-}" = "was-update-tracker" ]; then
  shift
  exec was-update-tracker "$@"
fi

exec was-report-batch "$@"

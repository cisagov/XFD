#!/usr/bin/env bash
# Monitor PE scan SQS queues until they drain (visible and in-flight both zero).
#
# Examples:
#   ./watch_queues.sh --scans dnstwist
#   ./watch_queues.sh --scans dnstwist,shodan,intelx --interval 30
#   ./watch_queues.sh --scans dnstwist --once

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/pe_queue_lib.sh"

SCANS=""
INTERVAL=30
CONFIRM_POLLS=2
ONCE=false

usage() {
  echo "Usage: $0 --scans SCAN[,SCAN...] [options]"
  echo
  echo "Options:"
  echo "  -s, --scans SCANS       Comma-separated catalog scan keys (e.g. dnstwist)"
  echo "  -i, --interval SECONDS  Poll interval when watching (default: 30)"
  echo "      --confirm N         Require N consecutive empty reads before exit (default: 2)"
  echo "      --once              Print status once and exit (no watch loop)"
  echo "  -h, --help              Show this help message"
  echo
  echo "Environment: PE_STAGE (default staging-cd), PE_QUEUE_PREFIX (derived: pe-staging or pe-integration),"
  echo "             AWS_REGION, AWS credentials"
  echo
  echo "Exit code 0 when all selected queues are empty; 1 while work remains (--once)"
  echo "or on error."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--scans) SCANS="$2"; shift 2 ;;
    -i|--interval) INTERVAL="$2"; shift 2 ;;
    --confirm) CONFIRM_POLLS="$2"; shift 2 ;;
    --once) ONCE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$SCANS" ]]; then
  echo "ERROR: --scans is required" >&2
  usage
  exit 1
fi

export PE_STAGE="${PE_STAGE:-staging-cd}"

command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required" >&2; exit 1; }

pe_queue_lib_init

print_status() {
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "=== ${timestamp} ==="
  if pe_print_queue_status_for_scans "$SCANS"; then
    echo "  (messages still present)"
    return 1
  fi
  echo "  (all selected queues empty)"
  return 0
}

if [[ "$ONCE" == true ]]; then
  if print_status; then
    exit 0
  fi
  exit 1
fi

echo "Watching PE queues for: ${SCANS}"
echo "Poll every ${INTERVAL}s; need ${CONFIRM_POLLS} consecutive empty reads to finish."
echo "Press Ctrl+C to stop."
echo

empty_streak=0
while true; do
  if print_status; then
    empty_streak=$((empty_streak + 1))
    if [[ "$empty_streak" -ge "$CONFIRM_POLLS" ]]; then
      echo
      echo "All selected PE scan queues are empty. Scans appear complete."
      exit 0
    fi
  else
    empty_streak=0
  fi
  echo
  sleep "$INTERVAL"
done

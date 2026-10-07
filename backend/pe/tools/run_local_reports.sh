#!/usr/bin/env bash
# Start local report container(s) and optionally copy PDFs to OUTPUT_DIR.
set -euo pipefail

PE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$PE_DIR/../.." && pwd)"
COMPOSE=(docker compose -f "${REPO_ROOT}/docker-compose.yml" -f "${REPO_ROOT}/docker-compose.override.local.yml")

REPORT_DATE="${REPORT_DATE:?REPORT_DATE is required (YYYY-MM-DD)}"
ORGS="${ORGS:-all}"
OUTPUT_DIR="${OUTPUT_DIR:-}"
REPORT_CONTAINER_PATH="${REPORT_CONTAINER_PATH:-/tmp/pe-reports}"

args=(--report-date "$REPORT_DATE" --orgs "$ORGS" --print-names)
if [[ -n "${COUNT:-}" ]]; then
  args+=(--count "$COUNT")
fi
if [[ "${SOC_MED:-false}" == "true" ]]; then
  args+=(--soc-med)
fi

containers=$("${COMPOSE[@]}" exec -T -e PYTHONPATH=/app backend \
  python /app/pe/tools/queue_local_reports.py "${args[@]}")

if [[ -z "$containers" ]]; then
  echo "Failed to start report container(s)" >&2
  exit 1
fi

echo "Started: ${containers//$'\n'/ }"
echo "Follow logs: docker logs -f ${containers%%$'\n'*}"

expand_path() {
  local path="$1"
  if [ "${path#\~/}" != "$path" ]; then
    printf '%s\n' "$HOME/${path#\~/}"
  elif [ "$path" = "~" ]; then
    printf '%s\n' "$HOME"
  else
    printf '%s\n' "$path"
  fi
}

wait_for_container() {
  local c="$1"
  echo "Waiting for $c..."
  # docker wait prints the container exit code on stdout (its own exit code is 0).
  local status
  status=$(docker wait "$c")
  if [[ "$status" -ne 0 ]]; then
    echo "Container $c failed (exit $status). Logs:" >&2
    docker logs "$c" >&2 || true
    exit "$status"
  fi
  echo "$c finished successfully"
}

if [[ -n "$OUTPUT_DIR" ]]; then
  out="$(expand_path "$OUTPUT_DIR")"
  mkdir -p "$out"
  for c in $containers; do
    wait_for_container "$c"
    docker cp "$c:${REPORT_CONTAINER_PATH}/." "$out/"
  done
  echo "Reports copied to $out"
else
  echo "When finished, copy PDFs with:"
  for c in $containers; do
    echo "  docker logs -f $c"
    echo "  docker cp $c:${REPORT_CONTAINER_PATH}/. <destination>/"
  done
fi

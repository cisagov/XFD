#!/usr/bin/env bash
# Start local ASM Sync container(s).
set -euo pipefail

PE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$PE_DIR/../.." && pwd)"
COMPOSE=(docker compose -f "${REPO_ROOT}/docker-compose.yml" -f "${REPO_ROOT}/docker-compose.override.local.yml")

ORGS="${ORGS:-all}"

args=(--orgs "$ORGS" --print-names)
if [[ -n "${COUNT:-}" ]]; then
  args+=(--count "$COUNT")
fi

containers=$("${COMPOSE[@]}" exec -T -e PYTHONPATH=/app backend \
  python /app/pe/tools/queue_local_asmsync.py "${args[@]}")

if [[ -z "$containers" ]]; then
  echo "Failed to start ASM Sync container(s)" >&2
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

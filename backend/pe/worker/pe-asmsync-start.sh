#!/bin/bash
# Start the in-container PE API, then run pe-asm-sync (Fargate and local Docker).
set -euo pipefail

export PE_API_URL="${PE_API_URL:-http://127.0.0.1:8000}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-pe_reports_django.settings}"
export DJANGO_ALLOW_ASYNC_UNSAFE="${DJANGO_ALLOW_ASYNC_UNSAFE:-true}"

ASMSYNC_ORGS="${ASMSYNC_ORGS:-all}"

cd /app/pe_reports_django_project
uvicorn pe_reports_django.asgi:app --host 127.0.0.1 --port 8000 &
API_PID=$!

cleanup() {
  kill "${API_PID}" 2>/dev/null || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -sf "${PE_API_URL}/apiv1/health" >/dev/null; then
    echo "PE API is ready at ${PE_API_URL}"
    break
  fi
  sleep 1
done

if ! curl -sf "${PE_API_URL}/apiv1/health" >/dev/null; then
  echo "PE API failed to start" >&2
  exit 1
fi

echo "Starting ASM Sync for orgs=${ASMSYNC_ORGS}..."
exec pe-asm-sync --orgs="${ASMSYNC_ORGS}"

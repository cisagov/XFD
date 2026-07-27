#!/bin/bash
# Start the in-container PE API, then run pe-reports (Fargate and local Docker).
set -euo pipefail

export PE_API_URL="${PE_API_URL:-http://127.0.0.1:8000}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-pe_reports_django.settings}"
export DJANGO_ALLOW_ASYNC_UNSAFE="${DJANGO_ALLOW_ASYNC_UNSAFE:-true}"

REPORT_DATE="${REPORT_DATE:?REPORT_DATE is required (YYYY-MM-DD)}"
OUTPUT_DIR="${REPORT_OUTPUT_DIR:-/tmp/pe-reports}"
REPORT_ORGS="${REPORT_ORGS:-all}"

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

cd /app
mkdir -p "${OUTPUT_DIR}"

EXTRA_ARGS=()
if [[ "${REPORT_FLARE:-false}" == "true" ]]; then
  EXTRA_ARGS+=(--flare)
fi
if [[ "${REPORT_SOC_MED_INCLUDED:-false}" == "true" ]]; then
  EXTRA_ARGS+=(--soc_med_included)
fi

echo "Starting pe-reports for ${REPORT_DATE} (orgs=${REPORT_ORGS})..."
exec pe-reports "${REPORT_DATE}" "${OUTPUT_DIR}" --orgs="${REPORT_ORGS}" "${EXTRA_ARGS[@]}"

#!/bin/bash
# Start the in-container PE API, then run pe-mailer (Fargate and local Docker).
set -euo pipefail

export PE_API_URL="${PE_API_URL:-http://127.0.0.1:8000}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-pe_reports_django.settings}"
export DJANGO_ALLOW_ASYNC_UNSAFE="${DJANGO_ALLOW_ASYNC_UNSAFE:-true}"

MAILER_REPORT_DATE="${MAILER_REPORT_DATE:?MAILER_REPORT_DATE is required (YYYY-MM-DD)}"
MAILER_ORGS="${MAILER_ORGS:-all}"
MAILER_LOG_LEVEL="${MAILER_LOG_LEVEL:-info}"

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

EXTRA_ARGS=()
if [ -n "${MAILER_SUMMARY_TO:-}" ]; then
  EXTRA_ARGS+=(--summary-to="${MAILER_SUMMARY_TO}")
fi
if [ -n "${MAILER_TEST_EMAILS:-}" ]; then
  EXTRA_ARGS+=(--test-emails="${MAILER_TEST_EMAILS}")
fi

echo "Starting pe-mailer for ${MAILER_REPORT_DATE} (orgs=${MAILER_ORGS})..."
exec pe-mailer "${MAILER_REPORT_DATE}" --orgs="${MAILER_ORGS}" --log-level="${MAILER_LOG_LEVEL}" "${EXTRA_ARGS[@]}"

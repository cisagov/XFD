#!/bin/bash
# Start the in-container PE API, then run pe-mailer (Fargate and local Docker).
set -euo pipefail

export PE_API_URL="${PE_API_URL:-http://127.0.0.1:8000}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-pe_reports_django.settings}"
export DJANGO_ALLOW_ASYNC_UNSAFE="${DJANGO_ALLOW_ASYNC_UNSAFE:-true}"
# Unbuffered so uvicorn's log lines interleave in real time with the health-check
# log below instead of appearing all at once when the process is later killed --
# without this, `docker logs` can make a slow-to-bind API look like it started
# instantly, which is misleading when diagnosing "PE API failed to start".
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

MAILER_REPORT_DATE="${MAILER_REPORT_DATE:?MAILER_REPORT_DATE is required (YYYY-MM-DD)}"
MAILER_ORGS="${MAILER_ORGS:-all}"
MAILER_LOG_LEVEL="${MAILER_LOG_LEVEL:-info}"

cd /app/pe_reports_django_project
PE_API_LOG="$(mktemp)"
echo "PE API log: ${PE_API_LOG}"
uvicorn pe_reports_django.asgi:app --host 127.0.0.1 --port 8000 > >(tee "${PE_API_LOG}") 2>&1 &
API_PID=$!

cleanup() {
  kill "${API_PID}" 2>/dev/null || true
}
trap cleanup EXIT

READY=""
for i in $(seq 1 30); do
  if ! kill -0 "${API_PID}" 2>/dev/null; then
    echo "PE API process (pid ${API_PID}) exited before becoming ready (attempt ${i})" >&2
    break
  fi
  http_code="$(curl -s -o /dev/null -w '%{http_code}' "${PE_API_URL}/apiv1/health" 2>/dev/null || true)"
  http_code="${http_code:-000}"
  if [ "${http_code}" = "200" ]; then
    echo "PE API is ready at ${PE_API_URL} (attempt ${i})"
    READY="1"
    break
  fi
  echo "PE API not ready yet (attempt ${i}/30, http_code=${http_code})"
  sleep 1
done

if [ -z "${READY}" ]; then
  echo "PE API failed to start after 30s; last health check:" >&2
  curl -v "${PE_API_URL}/apiv1/health" 2>&1 | sed 's/^/  /' >&2 || true
  echo "PE API process status: $(kill -0 "${API_PID}" 2>/dev/null && echo running || echo exited)" >&2
  echo "--- last 50 lines of PE API log (${PE_API_LOG}) ---" >&2
  tail -n 50 "${PE_API_LOG}" >&2 || true
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

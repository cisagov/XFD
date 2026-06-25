#!/bin/bash
# Local compose entrypoint: derive ElasticMQ queue URL from scan type, then run the worker.
set -euo pipefail

if [ -z "${SERVICE_TYPE:-}" ]; then
  echo "SERVICE_TYPE is required (e.g. dnstwist)." >&2
  exit 1
fi

PREFIX="${PE_QUEUE_PREFIX:-staging}"
ENDPOINT="${SQS_ENDPOINT_URL:-http://elasticmq:9324}"
export SERVICE_QUEUE_URL="${ENDPOINT}/000000000000/${PREFIX}-${SERVICE_TYPE}-queue"
export PE_API_URL="${PE_API_URL:-http://127.0.0.1:8000}"

echo "PE local worker: SERVICE_TYPE=${SERVICE_TYPE}"
echo "PE local worker: SERVICE_QUEUE_URL=${SERVICE_QUEUE_URL}"
echo "PE local worker: PE_API_URL=${PE_API_URL}"

exec ./worker/pe-worker-start.sh

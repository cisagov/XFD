#!/usr/bin/env bash
# Invoke the deployed peAsmSyncController Lambda (staging-cd / integration).
set -euo pipefail

STAGE="${STAGE:-staging-cd}"
FUNCTION="${PE_ASMSYNC_LAMBDA_FUNCTION:-crossfeed-${STAGE}-peAsmSyncController}"

ORGS="${ORGS:-all}"
TASK_COUNT="${TASK_COUNT:-1}"

PAYLOAD=$(jq -n \
  --arg orgs "$ORGS" \
  --argjson count "$TASK_COUNT" \
  '{
    orgs: ($orgs | split(",") | map(select(length > 0))),
    taskCount: $count,
  }')

aws lambda invoke \
  --function-name "$FUNCTION" \
  --payload "$PAYLOAD" \
  --cli-binary-format raw-in-base64-out \
  /dev/stdout

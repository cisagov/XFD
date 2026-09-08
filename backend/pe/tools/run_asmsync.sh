#!/usr/bin/env bash
# Invoke the deployed peAsmSyncController Lambda (staging-cd / integration).
set -euo pipefail

STAGE="${STAGE:-staging-cd}"
REGION="${AWS_REGION:-us-east-1}"
FUNCTION="${PE_ASMSYNC_LAMBDA_FUNCTION:-crossfeed-${STAGE}-peAsmSyncController}"

PHASE="${PHASE:?PHASE is required import_s3 or enumerate}"
ORGS="${ORGS:-all}"
TASK_COUNT="${TASK_COUNT:-1}"
OUTPUT_FILE="$(mktemp)"

cleanup() {
  rm -f "$OUTPUT_FILE"
}
trap cleanup EXIT

PAYLOAD="$(jq -n \
  --arg phase "$PHASE" \
  --arg orgs "$ORGS" \
  --argjson count "$TASK_COUNT" \
  '{
    phase: $phase,
    orgs: ($orgs | split(",") | map(select(length > 0))),
    taskCount: $count
  }')"

echo "Invoking ${FUNCTION} in ${REGION}..."
echo "Payload: ${PAYLOAD}"

# Invoke Lambda once and disable automatic AWS CLI retries
# AWS CLI auto-retrying can lead to duplicate workers/tasks being spun up.
if INVOKE_OUTPUT="$(
  AWS_RETRY_MODE=standard AWS_MAX_ATTEMPTS=1 \
    aws lambda invoke \
      --region "$REGION" \
      --function-name "$FUNCTION" \
      --cli-binary-format raw-in-base64-out \
      --output json \
      --cli-connect-timeout 10 \
      --cli-read-timeout 900 \
      --payload "$PAYLOAD" \
      "$OUTPUT_FILE" \
      2>&1
)"
then
  :
else
  # Capture any invocation errors so they can be written to the output file.
  INVOKE_EXIT_CODE=$?

  {
    echo
    echo "ERROR: Lambda invocation failed with AWS CLI exit code ${INVOKE_EXIT_CODE}."
    printf '%s\n' "$INVOKE_OUTPUT"
    echo
    echo "The AWS CLI attempted the invocation once and did not retry."
    echo "The Lambda may or may not have performed its intended work."
    echo "Inspect the Lambda logs and ECS tasks before running this command again to avoid duplication."
  } >>"$OUTPUT_FILE"

  echo "Lambda invocation error:"
  cat "$OUTPUT_FILE"
  exit "$INVOKE_EXIT_CODE"
fi

echo "Lambda response:"
cat "$OUTPUT_FILE"
echo

# Catch any Lambda function errors
FUNCTION_ERROR="$(
  printf '%s' "$INVOKE_OUTPUT" |
    jq -r '.FunctionError // empty'
)"

if [[ -n "$FUNCTION_ERROR" ]]; then
  {
    echo
    echo "ERROR: Lambda reported a function error: ${FUNCTION_ERROR}"
    echo "Inspect the Lambda response and logs before running this command again."
  } >>"$OUTPUT_FILE"

  cat "$OUTPUT_FILE"
  exit 1
fi

# Catch any non-200 status codes returned
STATUS_CODE="$(jq -r '.statusCode // empty' "$OUTPUT_FILE")"
if [[ -n "$STATUS_CODE" && "$STATUS_CODE" != "200" ]]; then
  {
    echo
    echo "ERROR: Lambda controller returned status code ${STATUS_CODE}."
    echo "Inspect the response and ECS tasks before running this command again."
  } >>"$OUTPUT_FILE"

  cat "$OUTPUT_FILE"
  exit 1
fi

#!/usr/bin/env bash
# Invoke the deployed peScanController Lambda (staging-cd / integration).
# Worker image is deployed by CI: backend.yml → npm run deploy-worker-staging
#
# Examples:
#   ./run_scans.sh --scans dnstwist --orgs DHS,DHS_CISA --count 3
#   ./run_scans.sh --scans dnstwist --orgs all-orgs --count 10
#   ./run_scans.sh --scans dnstwist --orgs-file orgs.json --queue-only
#   ./watch_queues.sh --scans dnstwist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/pe_queue_lib.sh"

STAGE="${PE_STAGE:-staging-cd}"
export PE_STAGE="$STAGE"
REGION="${AWS_REGION:-us-east-1}"
FUNCTION="${PE_LAMBDA_FUNCTION:-crossfeed-${STAGE}-peScanController}"
SCANS=""
ORGS=""
ORGS_FILE=""
COUNT=""
QUEUE_ONLY=false
TASKS_ONLY=false
IGNORE_QUEUE_DEPTH=false
PURGE_QUEUES=false
OUTPUT_FILE="$(mktemp)"

usage() {
  echo "Usage: $0 --scans SCAN[,SCAN...] [--orgs ORG[,ORG...] | --orgs-file FILE] [options]"
  echo
  echo "Options:"
  echo "  -s, --scans SCANS           Comma-separated catalog scan keys (e.g. dnstwist)"
  echo "  -o, --orgs ORGS             Comma-separated organization cyhy_db_name values"
  echo "  -f, --orgs-file FILE        JSON array of organization names"
  echo "  -c, --count N               Concurrent workers per scan (overrides catalog)"
  echo "      --queue-only            Queue SQS messages only"
  echo "      --tasks-only            Start Fargate tasks only"
  echo "      --ignore-queue-depth    Skip non-empty queue check (not recommended)"
  echo "      --purge-queues          Purge selected queues before invoke (no prompt)"
  echo "  -h, --help                  Show this help message"
  echo
  echo "If selected queues already hold messages, you will be prompted to purge,"
  echo "continue without clearing, or abort. Track progress with watch_queues.sh."
  echo
  echo "Environment: PE_STAGE (default staging-cd), PE_QUEUE_PREFIX (derived: pe-staging or pe-integration),"
  echo "             PE_LAMBDA_FUNCTION, AWS_REGION"
}

cleanup() {
  rm -f "$OUTPUT_FILE"
}
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--scans) SCANS="$2"; shift 2 ;;
    -o|--orgs) ORGS="$2"; shift 2 ;;
    -f|--orgs-file) ORGS_FILE="$2"; shift 2 ;;
    -c|--count) COUNT="$2"; shift 2 ;;
    --queue-only) QUEUE_ONLY=true; shift ;;
    --tasks-only) TASKS_ONLY=true; shift ;;
    --ignore-queue-depth) IGNORE_QUEUE_DEPTH=true; shift ;;
    --purge-queues) PURGE_QUEUES=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$SCANS" ]]; then
  echo "ERROR: --scans is required" >&2
  usage
  exit 1
fi

if [[ "$QUEUE_ONLY" == true && "$TASKS_ONLY" == true ]]; then
  echo "ERROR: --queue-only and --tasks-only cannot be used together" >&2
  exit 1
fi

if [[ -n "$ORGS_FILE" ]]; then
  [[ -f "$ORGS_FILE" ]] || { echo "ERROR: orgs file not found: $ORGS_FILE" >&2; exit 1; }
  ORGS_JSON="$(cat "$ORGS_FILE")"
elif [[ -n "$ORGS" ]]; then
  ORGS_JSON="$(printf '%s' "$ORGS" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$"; ""))')"
else
  if [[ "$TASKS_ONLY" != true ]]; then
    echo "ERROR: --orgs or --orgs-file is required unless --tasks-only is set" >&2
    exit 1
  fi
  ORGS_JSON="[]"
fi

command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required" >&2; exit 1; }

if ! pe_guard_queues_for_scans "$SCANS" "$IGNORE_QUEUE_DEPTH" "$PURGE_QUEUES"; then
  exit 1
fi

SCANS_JSON="$(printf '%s' "$SCANS" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$"; ""))')"
PAYLOAD="$(jq -n \
  --argjson scans "$SCANS_JSON" \
  --argjson orgs "$ORGS_JSON" \
  --argjson queueOnly "$QUEUE_ONLY" \
  --argjson tasksOnly "$TASKS_ONLY" \
  --arg count "$COUNT" \
  '{scans: $scans, orgs: $orgs, queueOnly: $queueOnly, tasksOnly: $tasksOnly}
   + (if $count == "" then {} else {taskCount: ($count | tonumber)} end)')"

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
    echo "The AWS CLI attempted the invocation once and did not retry"
    echo "The Lambda may or may not have performed its intended work."
    echo "Inspect the SQS queue, Lambda logs, and ECS tasks before running this command again to avoid duplication."
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
    echo "Inspect the response and AWS resources before running this command again."
  } >>"$OUTPUT_FILE"

  cat "$OUTPUT_FILE"
  exit 1
fi

echo "Track queue progress with:"
echo "  ${SCRIPT_DIR}/watch_queues.sh --scans ${SCANS}"

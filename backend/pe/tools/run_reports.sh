#!/usr/bin/env bash
# Invoke the deployed peReportController Lambda (staging-cd / integration).
set -euo pipefail

STAGE="${STAGE:-staging-cd}"
FUNCTION="${PE_REPORT_LAMBDA_FUNCTION:-crossfeed-${STAGE}-peReportController}"

REPORT_DATE="${REPORT_DATE:?REPORT_DATE required (YYYY-MM-DD)}"
ORGS="${ORGS:-all}"
TASK_COUNT="${TASK_COUNT:-1}"
SOC_MED="${SOC_MED:-false}"

PAYLOAD=$(jq -n \
  --arg date "$REPORT_DATE" \
  --arg orgs "$ORGS" \
  --argjson count "$TASK_COUNT" \
  --argjson soc "$([ "$SOC_MED" = true ] && echo true || echo false)" \
  '{
    reportDate: $date,
    orgs: ($orgs | split(",") | map(select(length > 0))),
    taskCount: $count,
    socMedIncluded: $soc
  }')

aws lambda invoke \
  --function-name "$FUNCTION" \
  --payload "$PAYLOAD" \
  --cli-binary-format raw-in-base64-out \
  /dev/stdout

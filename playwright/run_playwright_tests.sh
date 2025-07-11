#!/usr/bin/env bash

set -euo pipefail
set -x

# Get the current datetime (e.g., 2025-04-10T12:34:56)
DATETIME=$(date +%Y-%m-%dT%H:%M:%S)
echo "📅 Test timestamp: $DATETIME"
echo "📦 Bucket: $AUTOMATED_TEST_REPORTS_BUCKET_NAME"
echo "🌎 Region: $AWS_REGION"
echo "📤 Uploading to: s3://$AUTOMATED_TEST_REPORTS_BUCKET_NAME/playwright-reports/$DATETIME/"

OVERRIDES=$(
  jq -n \
    --arg datetime "$DATETIME" \
    --arg bucket "$AUTOMATED_TEST_REPORTS_BUCKET_NAME" \
    --arg region "$AWS_REGION" \
    --arg url "$PW_XFD_URL" \
    --arg username "$PW_XFD_USERNAME" \
    --arg password "$PW_XFD_PASSWORD" \
    --arg otpsecret "$PW_XFD_2FA_SECRET" \
    --arg login "$PW_XFD_LOGIN" \
    --arg git_branch "$GIT_BRANCH" \
    --arg environment "$ENVIRONMENT" \
    --arg s3HtmlPath "s3://$AUTOMATED_TEST_REPORTS_BUCKET_NAME/$ENVIRONMENT/playwright-reports/$DATETIME/html/" \
    --arg s3JsonPath "s3://$AUTOMATED_TEST_REPORTS_BUCKET_NAME/$ENVIRONMENT/playwright-reports/$DATETIME/results.json" \
    '{
    "containerOverrides": [
      {
        "name": "main",
        "environment": [
          { "name": "DATETIME", "value": $datetime },
          { "name": "AUTOMATED_TEST_REPORTS_BUCKET_NAME", "value": $bucket },
          { "name": "AWS_REGION", "value": $region },
          { "name": "PW_XFD_URL", "value": $url },
          { "name": "PW_XFD_USERNAME", "value": $username },
          { "name": "PW_XFD_PASSWORD", "value": $password },
          { "name": "PW_XFD_2FA_SECRET", "value": $otpsecret },
          { "name": "PW_XFD_LOGIN", "value": $login },
          { "name": "GIT_BRANCH", "value": $git_branch },
          { "name": "ENVIRONMENT", "value": $environment },
          { "name": "S3_HTML_PATH", "value": $s3HtmlPath },
          { "name": "S3_JSON_PATH", "value": $s3JsonPath }
        ],
      }
    ]
  }'
)

echo "Starting ECS task to run Playwright tests..."

TASK_ARN=$(aws ecs run-task \
  --cluster "$CLUSTER_NAME" \
  --task-definition "$TASK_DEFINITION" \
  --launch-type FARGATE \
  --network-configuration "{
    \"awsvpcConfiguration\":{
      \"subnets\": [\"${AWS_SUBNET}\"],
      \"securityGroups\": [\"${AWS_SECURITY_GROUP}\"],
      \"assignPublicIp\": \"ENABLED\"
    }
  }" \
  --region "${AWS_REGION}" \
  --overrides "$OVERRIDES" \
  --query 'tasks[0].taskArn' \
  --output text 2> /dev/null) || {
  echo "❌ Failed to run ECS task (aws command error)." >&2
  exit 1
}

# Sanity check: ensure the result isn't empty
if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
  echo "❌ Failed to run ECS task. No ARN returned." >&2
  exit 1
fi

echo "Started ECS Task with ARN: $TASK_ARN"
echo "Waiting for ECS task to complete..."

aws ecs wait tasks-stopped \
  --cluster "$CLUSTER_NAME" \
  --tasks "$TASK_ARN" \
  --region "${AWS_REGION}" || {
  echo "❌ Task did not complete successfully." >&2
  exit 1
}

echo "ECS task $TASK_ARN completed successfully."

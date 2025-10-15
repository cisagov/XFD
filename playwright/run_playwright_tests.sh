#!/usr/bin/env bash
set -eu
# 📅 Timestamp for report
DATETIME=$(date +%Y-%m-%dT%H:%M:%S)

# 🧾 Define S3 report paths
S3_HTML_PATH="s3://$AUTOMATED_TEST_REPORTS_BUCKET_NAME/$ENVIRONMENT/playwright-reports/$DATETIME/html/"
S3_JSON_PATH="s3://$AUTOMATED_TEST_REPORTS_BUCKET_NAME/$ENVIRONMENT/playwright-reports/$DATETIME/results.json"

echo "📅 Test timestamp: $DATETIME"
echo "📦 Upload bucket: $AUTOMATED_TEST_REPORTS_BUCKET_NAME"
echo "🌎 AWS Region: $AWS_REGION"
echo "📤 Uploading to: $S3_HTML_PATH"

# ⚙️ Prepare container environment overrides
OVERRIDES=$(jq -n \
  --arg datetime "$DATETIME" \
  --arg bucket "$AUTOMATED_TEST_REPORTS_BUCKET_NAME" \
  --arg region "$AWS_REGION" \
  --arg url "$PW_XFD_URL" \
  --arg global_admin_username "$PW_GLOBAL_ADMIN_USERNAME" \
  --arg global_admin_password "$PW_GLOBAL_ADMIN_PASSWORD" \
  --arg global_admin_2fa "$PW_GLOBAL_ADMIN_2FA_SECRET" \
  --arg regional_admin_username "$PW_REGIONAL_ADMIN_USERNAME" \
  --arg regional_admin_password "$PW_REGIONAL_ADMIN_PASSWORD" \
  --arg regional_admin_2fa "$PW_REGIONAL_ADMIN_2FA_SECRET" \
  --arg global_view_username "$PW_GLOBAL_VIEW_USERNAME" \
  --arg global_view_password "$PW_GLOBAL_VIEW_PASSWORD" \
  --arg global_view_2fa "$PW_GLOBAL_VIEW_2FA_SECRET" \
  --arg standard_username "$PW_STANDARD_USER_USERNAME" \
  --arg standard_password "$PW_STANDARD_USER_PASSWORD" \
  --arg standard_2fa "$PW_STANDARD_USER_2FA_SECRET" \
  --arg git_branch "$GIT_BRANCH" \
  --arg environment "$ENVIRONMENT" \
  --arg headless "$PW_HEADLESS" \
  --arg ci "$CI" \
  --arg s3HtmlPath "$S3_HTML_PATH" \
  --arg s3JsonPath "$S3_JSON_PATH" \
  --arg clusterName "$CLUSTER_NAME" \
  '{
    containerOverrides: [
      {
        name: "main",
        environment: [
          { "name": "DATETIME", "value": $datetime },
          { "name": "AUTOMATED_TEST_REPORTS_BUCKET_NAME", "value": $bucket },
          { "name": "AWS_REGION", "value": $region },
          { "name": "PW_XFD_URL", "value": $url },
          { "name": "PW_GLOBAL_ADMIN_USERNAME", "value": $global_admin_username },
          { "name": "PW_GLOBAL_ADMIN_PASSWORD", "value": $global_admin_password },
          { "name": "PW_GLOBAL_ADMIN_2FA_SECRET", "value": $global_admin_2fa },
          { "name": "PW_REGIONAL_ADMIN_USERNAME", "value": $regional_admin_username },
          { "name": "PW_REGIONAL_ADMIN_PASSWORD", "value": $regional_admin_password },
          { "name": "PW_REGIONAL_ADMIN_2FA_SECRET", "value": $regional_admin_2fa },
          { "name": "PW_GLOBAL_VIEW_USERNAME", "value": $global_view_username },
          { "name": "PW_GLOBAL_VIEW_PASSWORD", "value": $global_view_password },
          { "name": "PW_GLOBAL_VIEW_2FA_SECRET", "value": $global_view_2fa },
          { "name": "PW_STANDARD_USER_USERNAME", "value": $standard_username },
          { "name": "PW_STANDARD_USER_PASSWORD", "value": $standard_password },
          { "name": "PW_STANDARD_USER_2FA_SECRET", "value": $standard_2fa },
          { "name": "GIT_BRANCH", "value": $git_branch },
          { "name": "ENVIRONMENT", "value": $environment },
          { "name": "PW_HEADLESS", "value": $headless },
          { "name": "CI", "value": $ci },
          { "name": "S3_HTML_PATH", "value": $s3HtmlPath },
          { "name": "S3_JSON_PATH", "value": $s3JsonPath },
          { "name": "CLUSTER_NAME", "value": $clusterName}
        ]
      }
    ]
  }')

# 🚀 Launch ECS task
echo "🚀 Starting ECS task..."
TASK_ARN=$(aws ecs run-task \
  --cluster "$CLUSTER_NAME" \
  --task-definition "$TASK_DEFINITION" \
  --launch-type FARGATE \
  --network-configuration "{
    \"awsvpcConfiguration\":{
      \"subnets\": [\"$AWS_SUBNET\"],
      \"securityGroups\": [\"$AWS_SECURITY_GROUP\"],
      \"assignPublicIp\": \"ENABLED\"
    }
  }" \
  --region "$AWS_REGION" \
  --overrides "$OVERRIDES" \
  --query 'tasks[0].taskArn' \
  --output text) || {
  echo "❌ Failed to run ECS task." >&2
  exit 1
}

if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
  echo "❌ ECS task did not return a valid ARN." >&2
  exit 1
fi

echo "✅ ECS Task ARN: $TASK_ARN"

echo "⏳ Waiting for ECS task to finish..."
# Wait for ECS task to stop
MAX_WAIT_MINUTES=30
SLEEP_INTERVAL=10
MAX_ATTEMPTS=$((MAX_WAIT_MINUTES * 60 / SLEEP_INTERVAL))
ATTEMPT=0

echo "⏳ Waiting up to $MAX_WAIT_MINUTES minutes for ECS task to stop..."

STATUS=""
ATTEMPT=0

while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
  # Temporarily allow command failures
  STATUS=$(aws ecs describe-tasks \
    --cluster "$CLUSTER_NAME" \
    --tasks "$TASK_ARN" \
    --region "$AWS_REGION" \
    --query 'tasks[0].lastStatus' \
    --output text 2>&1)
  STATUS_EXIT_CODE=$?


  if [[ $STATUS_EXIT_CODE -ne 0 || "$STATUS" == *"error"* || "$STATUS" == *"Unable to"* || -z "$STATUS" ]]; then
    echo "⚠️  Could not fetch ECS task status (attempt $ATTEMPT): $STATUS"
    STATUS=""
  else
    echo "🔁 Task status: $STATUS (attempt $ATTEMPT)"
  fi

  if [[ "$STATUS" == "STOPPED" ]]; then
    echo "✅ ECS task has stopped."
    break
  fi

  sleep "$SLEEP_INTERVAL"
  ((ATTEMPT++))
done

if [[ "$STATUS" != "STOPPED" ]]; then
  echo "❌ ECS task did not stop within $MAX_WAIT_MINUTES minutes." >&2
  exit 1
fi



echo "✅ Task stopped. Checking exit code..."

EXIT_CODE=$(aws ecs describe-tasks \
  --cluster "$CLUSTER_NAME" \
  --tasks "$TASK_ARN" \
  --region "$AWS_REGION" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text) || EXIT_CODE=1

echo "📦 Container exit code: $EXIT_CODE"

# 📜 Fetch logs from CloudWatch
LOG_GROUP=$(aws ecs describe-task-definition \
  --task-definition "$TASK_DEFINITION" \
  --region "$AWS_REGION" \
  --query 'taskDefinition.containerDefinitions[0].logConfiguration.options."awslogs-group"' \
  --output text)

LOG_STREAM_PREFIX=$(aws ecs describe-task-definition \
  --task-definition "$TASK_DEFINITION" \
  --region "$AWS_REGION" \
  --query 'taskDefinition.containerDefinitions[0].logConfiguration.options."awslogs-stream-prefix"' \
  --output text)

TASK_ID="${TASK_ARN##*/}"
LOG_STREAM_NAME="${LOG_STREAM_PREFIX}/main/${TASK_ID}"

echo "   • Log Group: $LOG_GROUP"
echo "   • Log Stream: $LOG_STREAM_NAME"

aws logs get-log-events \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name "$LOG_STREAM_NAME" \
  --region "$AWS_REGION" \
  --output text | tee ecs-task-output.log

# ✅ Final reporting to GitHub Actions
if [[ "$EXIT_CODE" != "0" ]]; then
  echo "❌ Playwright tests failed inside ECS task (exit code: $EXIT_CODE)"
  echo "::error title=Playwright Tests Failed::One or more tests failed. See logs above or S3 report."
  exit "$EXIT_CODE"
else
  echo "✅ All Playwright tests passed."
  exit 0
fi

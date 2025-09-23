#!/usr/bin/env bash
set -euo pipefail

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
  --arg username "$PW_XFD_USERNAME" \
  --arg password "$PW_XFD_PASSWORD" \
  --arg otpsecret "$PW_XFD_2FA_SECRET" \
  --arg login "$PW_XFD_LOGIN" \
  --arg git_branch "$GIT_BRANCH" \
  --arg environment "$ENVIRONMENT" \
  --arg headless "$PW_HEADLESS" \
  --arg ci "$PW_CI" \
  --arg s3HtmlPath "$S3_HTML_PATH" \
  --arg s3JsonPath "$S3_JSON_PATH" \
  '{
    containerOverrides: [
      {
        name: "main",
        environment: [
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
          { "name": "PW_HEADLESS", "value": $headless },
          { "name": "PW_CI", "value": $ci },
          { "name": "S3_HTML_PATH", "value": $s3HtmlPath },
          { "name": "S3_JSON_PATH", "value": $s3JsonPath }
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
  --output text 2> /dev/null) || {
  echo "❌ Failed to run ECS task." >&2
  exit 1
}

if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
  echo "❌ ECS task did not return a valid ARN." >&2
  exit 1
fi

echo "✅ ECS Task ARN: $TASK_ARN"

echo "⏳ Waiting for ECS task to finish..."
# ⏱️ Custom wait for ECS task to stop
MAX_WAIT_MINUTES=30
SLEEP_INTERVAL=10
MAX_ATTEMPTS=$((MAX_WAIT_MINUTES * 60 / SLEEP_INTERVAL))
ATTEMPT=0

echo "⏳ Waiting up to $MAX_WAIT_MINUTES minutes for ECS task to stop..."

while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
  STATUS=$(aws ecs describe-tasks \
    --cluster "$CLUSTER_NAME" \
    --tasks "$TASK_ARN" \
    --region "$AWS_REGION" \
    --query 'tasks[0].lastStatus' \
    --output text)

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

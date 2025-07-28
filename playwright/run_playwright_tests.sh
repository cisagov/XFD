#!/usr/bin/env bash
set -euo pipefail
set -x

# ⏱️ Generate timestamp
DATETIME=$(date +%Y-%m-%dT%H:%M:%S)
echo "📅 Test timestamp: $DATETIME"
echo "📦 Bucket: $AUTOMATED_TEST_REPORTS_BUCKET_NAME"
echo "🌎 Region: $AWS_REGION"
echo "📤 Uploading to: s3://$AUTOMATED_TEST_REPORTS_BUCKET_NAME/playwright-reports/$DATETIME/"

# 🧩 Build ECS container overrides for task environment
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
          ]
        }
      ]
    }'
)

echo "$OVERRIDES" | jq .

echo "🚀 Starting ECS task to run Playwright tests..."

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
  --region "$AWS_REGION" \
  --overrides "$OVERRIDES" \
  --query 'tasks[0].taskArn' \
  --output text 2>/dev/null) || {
  echo "❌ Failed to run ECS task (aws command error)." >&2
  exit 1
}

# ✅ Sanity check
if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
  echo "❌ Failed to run ECS task. No ARN returned." >&2
  exit 1
fi

echo "✅ Started ECS Task with ARN: $TASK_ARN"
echo "⏳ Waiting for ECS task to complete..."

aws ecs wait tasks-stopped \
  --cluster "$CLUSTER_NAME" \
  --tasks "$TASK_ARN" \
  --region "$AWS_REGION" || {
  echo "❌ Task did not complete successfully." >&2
  exit 1
}

echo "✅ ECS task $TASK_ARN stopped. Checking container exit code..."

EXIT_CODE=$(aws ecs describe-tasks \
  --cluster "$CLUSTER_NAME" \
  --tasks "$TASK_ARN" \
  --region "$AWS_REGION" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)

echo "📦 Container exit code: $EXIT_CODE"

if [[ "$EXIT_CODE" != "0" ]]; then
  echo "❌ Container failed with exit code $EXIT_CODE. Fetching logs..."

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

  echo "📜 Fetching logs from CloudWatch:"
  echo "   • Log Group:   $LOG_GROUP"
  echo "   • Log Stream:  $LOG_STREAM_NAME"

  aws logs get-log-events \
    --log-group-name "$LOG_GROUP" \
    --log-stream-name "$LOG_STREAM_NAME" \
    --limit 50 \
    --region "$AWS_REGION" \
    --output text | tee ecs-task-error.log

  echo "❌ ECS task failed. See logs above or check ecs-task-error.log"
  exit "$EXIT_CODE"
fi

echo "🎉 ECS task completed successfully!"

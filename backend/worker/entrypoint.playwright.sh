#!/usr/bin/env bash

set -euo pipefail

# Define the cleanup function (like finally)
# shellcheck disable=SC2317
upload_reports() {
  echo "📤 Uploading results to S3..."

  if [[ -d "./playwright-report/html" ]]; then
    echo "✅ HTML report found, uploading..."
    aws s3 cp ./playwright-report/html "$S3_HTML_PATH" --recursive --region "$AWS_REGION"
    aws s3 cp ./playwright-report/html "s3://$AUTOMATED_TEST_REPORTS_BUCKET_NAME/$ENVIRONMENT/playwright-reports/latest/html/" --recursive --region "$AWS_REGION"
  else
    echo "⚠️ No HTML report found at ./playwright-report/html"
  fi

  if [[ -f "./playwright-report/results.json" ]]; then
    echo "✅ results.json found, uploading..."
    aws s3 cp ./playwright-report/results.json "$S3_JSON_PATH" --region "$AWS_REGION"
    aws s3 cp ./playwright-report/results.json "s3://$AUTOMATED_TEST_REPORTS_BUCKET_NAME/$ENVIRONMENT/playwright-reports/latest/results.json" --region "$AWS_REGION"
  else
    echo "⚠️ No results.json file found!"
  fi

  echo "📦 Uploads complete."
}

# Register the function to run on script exit (success or failure)
trap upload_reports EXIT

echo "🔁 Cloning into Crossfeed..."
rm -rf /app/xfd
mkdir -p /app/xfd

git clone --branch "$GIT_BRANCH" https://github.com/cisagov/xfd.git /app/xfd
cd /app/xfd/playwright
npm ci
npx playwright install --with-deps

echo "🔁 Running Playwright tests..."
# Don't let failure here kill the rest — trap will still run
if ! npx playwright test; then
  echo -e "\n\033[0;31m❌ Playwright tests failed!\033[0m"
  EXIT_CODE=1
else
  echo -e "\n\033[0;32m✅ All tests passed!\033[0m"
  EXIT_CODE=0
fi

exit "$EXIT_CODE"

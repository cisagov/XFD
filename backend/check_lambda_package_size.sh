#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

MAX_SIZE_KB=262000

npx serverless package --stage=staging-cd

unzip .serverless/crossfeed.zip -d crossfeed-staging-cd

# du -sk => size in KB
SIZE_KB=$(du -sk crossfeed-staging-cd | awk '{print $1}')

rm -rf crossfeed-staging-cd

if [ "$SIZE_KB" -gt "$MAX_SIZE_KB" ]; then
  echo "Directory is larger than ${MAX_SIZE_KB}KB (actual: ${SIZE_KB}KB)"
  exit 1
else
  echo "Directory is smaller or equal to ${MAX_SIZE_KB}KB (actual: ${SIZE_KB}KB)"
fi

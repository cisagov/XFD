#!/bin/bash
# Provision the CISADEV GitHub Actions runner.
# Usage: ./bootstrap.sh <RUNNER_TOKEN>
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <RUNNER_TOKEN>"
  echo "  RUNNER_TOKEN  ephemeral GitHub runner registration token (~1hr)"
  exit 1
fi

RUNNER_TOKEN="$1"

terraform init -backend-config=cisadev.config -input=false

terraform apply \
  -var-file=cisadev.tfvars \
  -var="runner_token=$RUNNER_TOKEN"

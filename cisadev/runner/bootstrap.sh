#!/bin/bash
# Provision the CISADEV GitHub Actions runner.
# Usage: ./bootstrap.sh <RUNNER_TOKEN> <CROWDSTRIKE_CID>
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <RUNNER_TOKEN> <CROWDSTRIKE_CID>"
  echo "  RUNNER_TOKEN   ephemeral GitHub runner registration token (~1hr)"
  echo "  CROWDSTRIKE_CID CrowdStrike customer ID"
  exit 1
fi

RUNNER_TOKEN="$1"
CROWDSTRIKE_CID="$2"

terraform init -backend-config=cisadev.config -input=false

terraform apply \
  -var-file=cisadev.tfvars \
  -var="runner_token=$RUNNER_TOKEN" \
  -var="crowdstrike_cid=$CROWDSTRIKE_CID"

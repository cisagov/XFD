#!/bin/bash
# Provision the CISADEV developer dev host.
# Usage: ./bootstrap.sh <DEVHOST_PASSWORD>
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <DEVHOST_PASSWORD>"
  echo "  DEVHOST_PASSWORD  initial login password (change on first login)"
  exit 1
fi

DEVHOST_PASSWORD="$1"

terraform init -backend-config=devhost.config -input=false

terraform apply \
  -var-file=devhost.tfvars \
  -var="devhost_password=$DEVHOST_PASSWORD"

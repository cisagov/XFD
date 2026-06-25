#!/bin/bash
# Build the PE Fargate/local worker image.
set -euo pipefail

PE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
docker build --platform linux/amd64 -t pe-worker -f "${PE_DIR}/Dockerfile" "${PE_DIR}"

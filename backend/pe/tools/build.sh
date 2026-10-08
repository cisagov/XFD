#!/bin/bash
# Build the PE Fargate/local worker image.
set -euo pipefail

PE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Default to host arch for local dev (avoids QEMU OOM issues on Apple Silicon/arm64)
# Set PE_WORKER_PLATFORM=linux/amd64 to match Fargate/CI.

if [ -z "${PE_WORKER_PLATFORM:-}" ]; then
  case "$(uname -m)" in
  arm64 | aarch64) PE_WORKER_PLATFORM=linux/arm64 ;;
  *) PE_WORKER_PLATFORM=linux/amd64 ;;
  esac
fi

echo "Building PE worker image for platform: ${PE_WORKER_PLATFORM}"
docker build --platform "${PE_WORKER_PLATFORM}" -t pe-worker -f "${PE_DIR}/Dockerfile" "${PE_DIR}"

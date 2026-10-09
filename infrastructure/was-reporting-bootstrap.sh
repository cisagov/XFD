#!/bin/bash
# Install only the prerequisites needed to run the reviewed WAS host manifest.

set -euo pipefail

readonly EXPECTED_OS_ID="ubuntu"
readonly EXPECTED_OS_VERSION="24.04"

# shellcheck source=/dev/null
. /etc/os-release

if [[ "${ID:-}" != "${EXPECTED_OS_ID}" || "${VERSION_ID:-}" != "${EXPECTED_OS_VERSION}" ]]; then
  echo "WAS bootstrap requires Ubuntu ${EXPECTED_OS_VERSION}." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install --yes --no-install-recommends \
  ca-certificates \
  git \
  make \
  openssh-client \
  python3 \
  sudo

echo "WAS bootstrap prerequisites installed. Clone the approved repository and run the host-software Make workflow."

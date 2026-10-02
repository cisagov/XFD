#!/bin/bash
# Create a local WAS .env from the checked-in development template.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_FILE="${WAS_ROOT}/dev.env"
TARGET_FILE="${WAS_ROOT}/.env"

if [ -f "${TARGET_FILE}" ]; then
  echo "${TARGET_FILE} already exists. Refusing to overwrite it." >&2
  exit 1
fi

cp "${SOURCE_FILE}" "${TARGET_FILE}"
chmod 600 "${TARGET_FILE}"
echo "Created ${TARGET_FILE}. Replace all placeholder values before running WAS."

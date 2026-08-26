#!/bin/bash
# Start the WAS mailer process inside the container.
set -euo pipefail

exec was-mailer "$@"

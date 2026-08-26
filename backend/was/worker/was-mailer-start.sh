#!/bin/bash
# Start the WAS mailer process inside the container.
set -euo pipefail

exec python -m was_mailer.email_reports

#!/bin/bash
# open-cti/refresh-repo.sh -- keeps a checkout of this repo at /opt/open-cti-repo current, and
# (re)installs the two systemd units from it. Run by user_data once (bootstraps the first clone),
# then every boot via open-cti-render-env.service's ExecStartPre -- so a merge to
# var.open_cti_repo_branch reaches the box on its next boot, no S3/CI push and no `terraform apply`
# required. bootstrap.sh, env.static, and docker-compose.yml/rabbitmq.conf are read straight out of
# this checkout in place, not copied elsewhere -- see open-cti/STATUS.md for the full design.
set -euo pipefail

OPEN_CTI_DIR="/opt/open-cti"
REPO_DIR="/opt/open-cti-repo"

# shellcheck source=/dev/null
source "$OPEN_CTI_DIR/env.deploy"
: "${OPEN_CTI_REPO_URL:?OPEN_CTI_REPO_URL must be set in $OPEN_CTI_DIR/env.deploy}"
: "${OPEN_CTI_REPO_BRANCH:?OPEN_CTI_REPO_BRANCH must be set in $OPEN_CTI_DIR/env.deploy}"

if [[ -d "$REPO_DIR/.git" ]]; then
  git -C "$REPO_DIR" fetch --depth 1 origin "$OPEN_CTI_REPO_BRANCH"
  git -C "$REPO_DIR" reset --hard "origin/$OPEN_CTI_REPO_BRANCH"
else
  git clone --depth 1 --branch "$OPEN_CTI_REPO_BRANCH" "$OPEN_CTI_REPO_URL" "$REPO_DIR"
fi

install -m 644 "$REPO_DIR/open-cti/systemd/open-cti-render-env.service" /etc/systemd/system/
install -m 644 "$REPO_DIR/open-cti/systemd/open-cti-compose.service" /etc/systemd/system/
systemctl daemon-reload

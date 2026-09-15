#!/bin/bash
# NOTE: intentionally NOT using 'set -x' — tracing would log the runner token.
set -euo pipefail

LOG=/var/log/bootstrap-runner.log
exec > >(tee -a "$LOG") 2>&1

echo "[$(date -Is)] Starting runner bootstrap..."

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y ca-certificates curl tar wget perl unzip dpkg

# AWS CLI v2 — GPG-verified against AWS's pinned signing key before install.
if ! command -v aws >/dev/null 2>&1; then
  echo "[$(date -Is)] Installing AWS CLI v2..."
  apt-get install -y gnupg
  TMPDIR="$(mktemp -d)"
  cd "$TMPDIR"

  AWS_CLI_FPR="FB5DB77FD5C118B80511ADA8A6310ACC4672475C"

  curl -fsSL "https://awscli.amazonaws.com/aws-cli.gpg" -o aws-cli.gpg 2>/dev/null \
    || curl -fsSL "https://awscli.amazonaws.com/awscli.pub" -o aws-cli.gpg
  gpg --import aws-cli.gpg
  if ! gpg --fingerprint "$AWS_CLI_FPR" >/dev/null 2>&1; then
    echo "ERROR: AWS CLI signing key fingerprint did not match pinned value. Aborting."
    exit 1
  fi

  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip.sig" -o awscliv2.sig
  gpg --verify awscliv2.sig awscliv2.zip
  unzip -q awscliv2.zip
  ./aws/install
  cd /
  rm -rf "$TMPDIR"
fi
aws --version

# CrowdStrike Falcon (mandatory for CISADEV compliance).
echo "[$(date -Is)] Installing CrowdStrike Falcon sensor..."
DEB_S3_URI='${crowdstrike_s3_uri}'
DEB_LOCAL='/tmp/falcon-sensor.deb'

aws s3 cp "$DEB_S3_URI" "$DEB_LOCAL"
dpkg -i "$DEB_LOCAL" || apt-get -f install -y

/opt/CrowdStrike/falconctl -s --cid=${crowdstrike_cid}
/opt/CrowdStrike/falconctl -s --tags="${crowdstrike_tags}"
systemctl enable --now falcon-sensor

echo "[$(date -Is)] Verifying falcon-sensor..."
systemctl --no-pager --full status falcon-sensor || true
ps -ef | grep -i falcon-sensor | grep -v grep || true
rm -f "$DEB_LOCAL"

# GitHub Actions Runner.
echo "[$(date -Is)] Installing GitHub Actions Runner..."
sudo -u ubuntu mkdir -p /home/ubuntu/actions-runner
cd /home/ubuntu/actions-runner

sudo -u ubuntu curl -sL \
  -o actions-runner-linux-x64-${runner_version}.tar.gz \
  https://github.com/actions/runner/releases/download/v${runner_version}/actions-runner-linux-x64-${runner_version}.tar.gz

sudo -u ubuntu tar xzf ./actions-runner-linux-x64-${runner_version}.tar.gz

if [ ! -f .runner ]; then
  sudo -u ubuntu ./config.sh \
    --unattended \
    --url ${runner_url} \
    --token ${runner_token} \
    --runner-group ${runner_group} \
    --name ${runner_name}
fi

sudo ./svc.sh install ubuntu
sudo ./svc.sh start

echo "[$(date -Is)] Runner bootstrap complete."

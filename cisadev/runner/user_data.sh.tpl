#!/bin/bash
# NOTE: intentionally NOT using 'set -x' — tracing would log the runner token.
set -euo pipefail

LOG=/var/log/bootstrap-runner.log
exec > >(tee -a "$LOG") 2>&1

echo "[$(date -Is)] Starting runner bootstrap..."

export DEBIAN_FRONTEND=noninteractive

# Ubuntu's apt-daily(-upgrade) timers can hold the dpkg lock on first boot and
# race with this script. Wait for it instead of failing outright.
wait_for_apt_lock() {
  local timeout=300
  echo "[$(date -Is)] Waiting for apt/dpkg lock (up to $${timeout}s)..."
  if ! flock -w "$timeout" /var/lib/dpkg/lock-frontend true; then
    echo "ERROR: Timed out waiting for apt/dpkg lock after $${timeout}s." >&2
    exit 1
  fi
}

apt_get() {
  wait_for_apt_lock
  apt-get "$@"
}

apt_get update -y
apt_get install -y ca-certificates curl tar wget perl unzip dpkg

# AWS CLI v2 — GPG-verified against AWS's pinned signing key before install.
if ! command -v aws >/dev/null 2>&1; then
  echo "[$(date -Is)] Installing AWS CLI v2..."
  apt_get install -y gnupg
  TMPDIR="$(mktemp -d)"
  cd "$TMPDIR"

  AWS_CLI_FPR="FB5DB77FD5C118B80511ADA8A6310ACC4672475C"

  # AWS no longer serves this key at a URL; it's published as a literal PGP
  # block in their install docs, so it's embedded here instead of curl'd.
  cat > aws-cli.gpg <<'EOF'
-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBF2Cr7UBEADJZHcgusOJl7ENSyumXh85z0TRV0xJorM2B/JL0kHOyigQluUG
ZMLhENaG0bYatdrKP+3H91lvK050pXwnO/R7fB/FSTouki4ciIx5OuLlnJZIxSzx
PqGl0mkxImLNbGWoi6Lto0LYxqHN2iQtzlwTVmq9733zd3XfcXrZ3+LblHAgEt5G
TfNxEKJ8soPLyWmwDH6HWCnjZ/aIQRBTIQ05uVeEoYxSh6wOai7ss/KveoSNBbYz
gbdzoqI2Y8cgH2nbfgp3DSasaLZEdCSsIsK1u05CinE7k2qZ7KgKAUIcT/cR/grk
C6VwsnDU0OUCideXcQ8WeHutqvgZH1JgKDbznoIzeQHJD238GEu+eKhRHcz8/jeG
94zkcgJOz3KbZGYMiTh277Fvj9zzvZsbMBCedV1BTg3TqgvdX4bdkhf5cH+7NtWO
lrFj6UwAsGukBTAOxC0l/dnSmZhJ7Z1KmEWilro/gOrjtOxqRQutlIqG22TaqoPG
fYVN+en3Zwbt97kcgZDwqbuykNt64oZWc4XKCa3mprEGC3IbJTBFqglXmZ7l9ywG
EEUJYOlb2XrSuPWml39beWdKM8kzr1OjnlOm6+lpTRCBfo0wa9F8YZRhHPAkwKkX
XDeOGpWRj4ohOx0d2GWkyV5xyN14p2tQOCdOODmz80yUTgRpPVQUtOEhXQARAQAB
tCFBV1MgQ0xJIFRlYW0gPGF3cy1jbGlAYW1hem9uLmNvbT6JAlQEEwEIAD4CGwMF
CwkIBwIGFQoJCAsCBBYCAwECHgECF4AWIQT7Xbd/1cEYuAURraimMQrMRnJHXAUC
akV0ygUJDqP4lQAKCRCmMQrMRnJHXFHjD/9eyZLYcKuQOlLvtqSDtUBiEZf6ZZjM
i3ygYH8rJNtuToUH+HvSpe819urJCquXhDrlK6N+aqW0hCLtNABJG/vsafIgvIYJ
hSGgpgtNnQyMV1jViRWqPjbouw8OkYKBThUfT1i2Y+wn58ifs6ODBCmTexWtXspA
Si+Gt49xDOW0APmbOPnI+a4HJW6tVEo6MWS0WjzpiBayR3d1A4pt4YrPfSdDgpLo
h2SLQqlRqvvVZJaWBjhkErNFpfsBA06sDcPEOb0G8LBUbR4WOcdvhe5LubJbZuxC
AG9kNPCVeQP1ixwjgjXKysaxeQ6rv0VzIQgRp6tLVLWhy6AKDNvLjFSsmXZ1Wl08
Y/RlOHXlzLuQMRE6sR1wOdRxc9TsrNWTGiBK65cvSWOy03JeBkQQ8pesqltiyxI9
U21kkgiXtTSKNGfKK8pO27D81YANhRqPK7iTp6kuFiY2WtOg90KTMNlIT+Ff85Y2
b1rHj6Z0SrCkJujhWk3IBPic/wJgz01LEc/OAdUPlby90RJZcIBhSlWhT7mXnXIO
c0HWlNQrns2s3CTyYwZSiSlYe9ApeLwhjDo8NhbFuCAy61l6O5UsR4AfZxx/rGKv
2wFb1/RN/P4gNe6vmxZAPjR0AQcwD3tc2McimOLr/22kmPz8IH3I0X7WoSFr0Biz
E91G7bb0hOb/cA==
=knv7
-----END PGP PUBLIC KEY BLOCK-----
EOF
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
wait_for_apt_lock
dpkg -i "$DEB_LOCAL" || apt_get -f install -y

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
    --runnergroup ${runner_group} \
    --name ${runner_name}
fi

sudo ./svc.sh install ubuntu
sudo ./svc.sh start

echo "[$(date -Is)] Runner bootstrap complete."

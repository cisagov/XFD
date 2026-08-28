provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "cisadev_xfd_gh_actions_runner_ec2" {
  ami                         = "ami-xxxxxxxxxxxxxxxxx"
  instance_type               = "t2.micro"
  subnet_id                   = "subnet-xxxxxxxxxxxxxxxxx"
  vpc_security_group_ids      = ["sg-xxxxxxxxxxxxxxxxx"]
  key_name                    = " "
  iam_instance_profile        = "<IAM_INSTANCE_PROFILE>"
  associate_public_ip_address = false
  tags = {
    Name        = "CyHy Dashboard GitHub Actions Runner"
    Environment = "staging"
    Owner       = "XFD Dashboard"
  }
  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail

    LOG=/var/log/bootstrap-runner.log
    exec > >(tee -a "$LOG") 2>&1

    echo "[$(date -Is)] Starting runner bootstrap..."

    export DEBIAN_FRONTEND=noninteractive

    # --- System packages ---
    apt-get update -y
    apt-get install -y ca-certificates curl tar wget perl unzip dpkg

    # --- Install AWS CLI v2 (if missing) ---
    if ! command -v aws >/dev/null 2>&1; then
      echo "[$(date -Is)] Installing AWS CLI v2..."
      TMPDIR="$(mktemp -d)"
      cd "$TMPDIR"
      curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
      unzip -q awscliv2.zip
      ./aws/install
      cd /
      rm -rf "$TMPDIR"
    fi
    aws --version

    # --- CrowdStrike Falcon (mandatory for CISADEV compliance) ---
    echo "[$(date -Is)] Installing CrowdStrike Falcon sensor..."
    DEB_S3_URI='<CROWDSTRIKE_S3_URI>'
    DEB_LOCAL='/tmp/falcon-sensor.deb'

    aws s3 cp "$DEB_S3_URI" "$DEB_LOCAL"
    dpkg -i "$DEB_LOCAL" || apt-get -f install -y

    /opt/CrowdStrike/falconctl -s --cid=<CROWDSTRIKE_CID>
    /opt/CrowdStrike/falconctl -s --tags="<CROWDSTRIKE_TAGS>"
    systemctl enable --now falcon-sensor

    echo "[$(date -Is)] Verifying falcon-sensor..."
    systemctl --no-pager --full status falcon-sensor || true
    ps -ef | grep -i falcon-sensor | grep -v grep || true
    rm -f "$DEB_LOCAL"

    # --- GitHub Actions Runner ---
    echo "[$(date -Is)] Installing GitHub Actions Runner..."
    sudo -u ubuntu mkdir -p /home/ubuntu/actions-runner
    cd /home/ubuntu/actions-runner

    sudo -u ubuntu curl -sL \
      -o actions-runner-linux-x64-2.335.1.tar.gz \
      https://github.com/actions/runner/releases/download/v2.335.1/actions-runner-linux-x64-2.335.1.tar.gz

    sudo -u ubuntu tar xzf ./actions-runner-linux-x64-2.335.1.tar.gz

    if [ ! -f .runner ]; then
      sudo -u ubuntu ./config.sh \
        --unattended \
        --url <ENTERPRISE_GITHUB_URL> \
        --token XXXXXXXXXXXXXXXXXXXXXXXXXXXXX \
        --runner-group <RUNNER_GROUP> \
        --name <RUNNER_NAME>
    fi

    sudo ./svc.sh install ubuntu
    sudo ./svc.sh start

    echo "[$(date -Is)] Runner bootstrap complete."
    EOF
}

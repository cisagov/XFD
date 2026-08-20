#!/bin/bash
# open-cti/install-deps.sh -- idempotently installs Docker Engine + Compose V2 + git if missing.
# Embedded into user_data (open_cti.tf's local.open_cti_user_data) via file()+heredoc (same as
# refresh-repo.sh -- real ${...}/$(...) bash syntax, templatefile() would misparse it), run once
# ahead of refresh-repo.sh at a genuine first boot. Full rationale/history: open-cti/STATUS.md's
# AMI section and 2026-08-20 log entries -- kept out of this file to save user_data's 16KB budget.
#
# Detects package manager at runtime (apt/dnf/yum) rather than assuming one distro -- neither
# var.open_cti_ami_id nor var.lz_open_cti_ami_id's OS should be assumed. `command -v` guards make
# reruns (incl. output.open_cti_backfill_script against the already-provisioned stage-cd box) a
# true no-op instead of risking the package manager touching a live Docker daemon.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive # apt-only; avoids tzdata's interactive prompt hanging boot

log() { echo "[install-deps.sh] $*"; }

if command -v apt-get >/dev/null 2>&1; then
  PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="dnf"
elif command -v yum >/dev/null 2>&1; then
  PKG_MANAGER="yum"
else
  log "FATAL: no supported package manager found (apt-get/dnf/yum)." >&2
  exit 1
fi
log "Detected package manager: $PKG_MANAGER"

if ! command -v git >/dev/null 2>&1; then
  log "git not found -- installing..."
  case "$PKG_MANAGER" in
    apt) apt-get update -y && apt-get install -y git ;;
    dnf) dnf install -y git ;;
    yum) yum install -y git ;;
  esac
else
  log "git already present, skipping."
fi

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  log "Docker Engine and/or Compose V2 plugin not found -- installing..."
  case "$PKG_MANAGER" in
    apt)
      apt-get update -y
      apt-get install -y ca-certificates curl gnupg
      install -m 0755 -d /etc/apt/keyrings
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
      chmod a+r /etc/apt/keyrings/docker.asc
      # shellcheck source=/dev/null
      . /etc/os-release
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null
      apt-get update -y
      apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
      ;;
    dnf)
      # AL2023 ships Docker as its own native package, no compose plugin; Docker's upstream repo
      # doesn't serve AL2023 at all (404). Native package first, upstream repo as RHEL/Fedora fallback.
      dnf install -y docker || {
        dnf install -y dnf-plugins-core
        dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
      }
      ;;
    yum)
      if command -v amazon-linux-extras >/dev/null 2>&1; then
        amazon-linux-extras install -y docker # AL2
      else
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
      fi
      ;;
  esac
  systemctl enable --now docker

  # Fallback for whichever path above didn't provide a compose-plugin package (AL2023 native
  # docker package never does) -- Docker's own documented manual install, a no-op if already present.
  if ! docker compose version >/dev/null 2>&1; then
    log "Compose V2 plugin still missing -- installing as a CLI plugin binary..."
    COMPOSE_PLUGIN_DIR="/usr/local/lib/docker/cli-plugins"
    mkdir -p "$COMPOSE_PLUGIN_DIR"
    curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" -o "$COMPOSE_PLUGIN_DIR/docker-compose"
    chmod +x "$COMPOSE_PLUGIN_DIR/docker-compose"
  fi
else
  log "Docker Engine + Compose V2 plugin already present, skipping."
fi

# bootstrap.sh needs the aws CLI (SSM secret fetch); not installed here (v2's installer is
# arch-specific, not a simple package everywhere) -- fail loudly rather than have bootstrap.sh
# fail confusingly later.
if ! command -v aws >/dev/null 2>&1; then
  log "FATAL: aws CLI not found -- confirm the base AMI ships it." >&2
  exit 1
fi

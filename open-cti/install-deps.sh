#!/bin/bash
# open-cti/install-deps.sh -- idempotently installs Docker Engine + the Compose V2 plugin + git if
# they aren't already present. Embedded into user_data (see open_cti.tf's local.open_cti_user_data)
# and run once, ahead of refresh-repo.sh, at a genuine first boot -- same delivery mechanism as
# refresh-repo.sh (file() + heredoc, not templatefile(): this is a real bash script with its own
# ${...}/$(...) syntax that Terraform's interpolation would otherwise misparse).
#
# Why this exists: open-cti-compose.service hard-requires `/usr/bin/docker` + Compose V2
# (`docker compose`), and refresh-repo.sh hard-requires `git` -- neither was ever installed
# anywhere in this pipeline; both were simply assumed present on the base AMI. Confirmed false for
# var.open_cti_ami_id (stage-cd): `aws ec2 describe-images` shows it's a stock, unmodified Canonical
# Ubuntu 20.04 focal image (owner 099720109477) -- git/Docker are on that box today only because a
# human installed them by hand, out-of-band, when it was first stood up. var.ami_id (used for a
# genuinely new LZ instance, e.g. stage) is unverified to be Ubuntu/Debian-family at all -- see
# open-cti/STATUS.md's AMI section. This script targets apt/Debian-family only and will fail loudly
# (no `apt-get` binary) rather than silently on anything else -- update it once that's confirmed.
#
# Guarded by `command -v`/version checks rather than relying on apt/package-manager idempotency
# alone: this same payload is also replayed by hand against the already-running stage-cd instance
# via output.open_cti_backfill_script, which already has both tools installed. Blindly re-running
# `apt-get install` there risks apt deciding to reconfigure/restart the live Docker daemon and
# disrupting the already-running OpenCTI stack -- the guards make this a true no-op in that case.
set -euo pipefail

log() { echo "[install-deps.sh] $*"; }

if ! command -v git >/dev/null 2>&1; then
  log "git not found -- installing..."
  apt-get update -y
  apt-get install -y git
else
  log "git already present, skipping."
fi

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  log "Docker Engine and/or Compose V2 plugin not found -- installing..."
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
  systemctl enable --now docker
else
  log "Docker Engine + Compose V2 plugin already present, skipping."
fi

# bootstrap.sh depends on the aws CLI (SSM secret fetch) but this script doesn't install it --
# AWS CLI v2's installer is arch-specific (x86_64 vs aarch64) and not a simple apt package on every
# base image. Fail loudly here rather than have bootstrap.sh fail confusingly later.
if ! command -v aws >/dev/null 2>&1; then
  log "FATAL: aws CLI not found, and this script doesn't install it -- confirm the base AMI ships it (bootstrap.sh depends on it for SSM secret fetch)." >&2
  exit 1
fi

#!/bin/bash
# open-cti/bootstrap.sh -- renders /opt/open-cti/.env from SSM + env.static/env.deploy. Run every
# boot by open-cti-render-env.service, idempotent. Comments terse on purpose: embedded whole into
# EC2 user_data (16KB limit). Full rationale: open-cti/STATUS.md.
set -euo pipefail

OPEN_CTI_DIR="/opt/open-cti"
ENV_STATIC="$OPEN_CTI_DIR/env.static"
ENV_DEPLOY="$OPEN_CTI_DIR/env.deploy"
ENV_OUT="$OPEN_CTI_DIR/.env"
ENV_TMP="$OPEN_CTI_DIR/.env.tmp"

log() { echo "[bootstrap.sh] $*"; }
fail() { echo "[bootstrap.sh] FATAL: $*" >&2; exit 1; }

[[ -f "$ENV_STATIC" ]] || fail "$ENV_STATIC not found -- bootstrapped by Terraform user_data?"
[[ -f "$ENV_DEPLOY" ]] || fail "$ENV_DEPLOY not found -- bootstrapped by Terraform user_data?"

# shellcheck source=/dev/null
source "$ENV_DEPLOY"
: "${OPEN_CTI_SSM_PATH_PREFIX:?OPEN_CTI_SSM_PATH_PREFIX must be set in $ENV_DEPLOY}"
: "${OPEN_CTI_CONFIG_BUCKET:?OPEN_CTI_CONFIG_BUCKET must be set in $ENV_DEPLOY}"

# 0) docker-compose.yml + rabbitmq.conf: too large for user_data, fetched from S3 every boot.
# Objects kept current by .github/workflows/open-cti-config-sync.yml, not Terraform.
log "Fetching docker-compose.yml + rabbitmq.conf from s3://$OPEN_CTI_CONFIG_BUCKET ..."
aws s3 cp "s3://$OPEN_CTI_CONFIG_BUCKET/docker-compose.yml" "$OPEN_CTI_DIR/docker-compose.yml"
aws s3 cp "s3://$OPEN_CTI_CONFIG_BUCKET/rabbitmq.conf" "$OPEN_CTI_DIR/rabbitmq.conf"

log "Rendering $ENV_OUT ..."
umask 077  # .env holds decrypted secrets from here on
: > "$ENV_TMP"

# 1) Static config + stable connector IDs -- never regenerate for a running instance (env.static).
if grep -q "REPLACE_ME_STABLE_UUID" "$ENV_STATIC"; then
  fail "$ENV_STATIC still has REPLACE_ME_STABLE_UUID placeholder(s)."
fi
cat "$ENV_STATIC" >> "$ENV_TMP"

# 2) Per-environment config from Terraform vars. XTM One's two values are optional (inactive on
#    stage-cd); the rest fail closed on empty.
empty_deploy_keys=()
for key in OPENCTI_HOST OPENCTI_ADMIN_EMAIL SMTP_HOSTNAME CENSYS_ORG_ID QUALYS_API_USERNAME; do
  [[ -n "${!key:-}" ]] || empty_deploy_keys+=("$key")
done
if (( ${#empty_deploy_keys[@]} > 0 )); then
  fail "empty in $ENV_DEPLOY: ${empty_deploy_keys[*]} -- set the matching open_cti_* .tfvars value."
fi
{
  echo "OPENCTI_HOST=\"${OPENCTI_HOST}\""
  echo "OPENCTI_ADMIN_EMAIL=\"${OPENCTI_ADMIN_EMAIL}\""
  echo "SMTP_HOSTNAME=\"${SMTP_HOSTNAME}\""
  echo "CENSYS_ORG_ID=\"${CENSYS_ORG_ID}\""
  echo "QUALYS_API_USERNAME=\"${QUALYS_API_USERNAME}\""
  echo "XTM_ONE_HOST=\"${XTM_ONE_HOST:-}\""
  echo "XTM_ONE_ADMIN_EMAIL=\"${XTM_ONE_ADMIN_EMAIL:-}\""
} >> "$ENV_TMP"

# 3) Secrets. Names fetched in one call (safe -- no whitespace/newlines in names), each value fetched
#    individually after that. NOT one bulk --output text call parsed by line: embedded newlines in a
#    value would silently corrupt that parse. Costs N calls instead of 1; boot-time only, fine.
# OPTIONAL_SECRET_KEYS: exempted below from the fail-closed check -- XTM One's secrets + the
# unreferenced/vestigial CONNECTOR_CENSYS_ENRICHMENT_TOKEN. Written as empty, not "REPLACE_ME".
OPTIONAL_SECRET_KEYS=(PLATFORM_REGISTRATION_TOKEN XTM_ONE_ADMIN_PASSWORD XTM_ONE_SECRET_KEY XTM_ONE_ENTERPRISE_LICENSE XTM_ONE_POSTGRES_PASSWORD CONNECTOR_CENSYS_ENRICHMENT_TOKEN)
is_optional_key() {
  local k="$1"
  for opt in "${OPTIONAL_SECRET_KEYS[@]}"; do [[ "$k" == "$opt" ]] && return 0; done
  return 1
}

log "Fetching secrets from SSM under $OPEN_CTI_SSM_PATH_PREFIX ..."
placeholder_keys=()
skipped_optional_keys=()
fetched_count=0
while read -r name; do
  [[ -z "$name" ]] && continue
  key="${name##*/}"
  value=$(aws ssm get-parameter --name "$name" --with-decryption --query 'Parameter.Value' --output text)
  if [[ "$value" == "REPLACE_ME" ]]; then
    if is_optional_key "$key"; then
      skipped_optional_keys+=("$key")
      echo "${key}=\"\"" >> "$ENV_TMP"
      fetched_count=$((fetched_count + 1))
      continue
    fi
    placeholder_keys+=("$key")
  fi
  echo "${key}=\"${value}\"" >> "$ENV_TMP"
  fetched_count=$((fetched_count + 1))
done < <(aws ssm get-parameters-by-path --path "$OPEN_CTI_SSM_PATH_PREFIX" --recursive --query 'Parameters[].Name' --output text | tr '\t' '\n')

(( fetched_count > 0 )) || fail "no SSM parameters found under $OPEN_CTI_SSM_PATH_PREFIX"

if (( ${#skipped_optional_keys[@]} > 0 )); then
  log "NOTE: still-placeholder optional (XTM One) secrets written as empty: ${skipped_optional_keys[*]}"
fi

# Fail closed rather than start the stack with placeholder credentials.
if (( ${#placeholder_keys[@]} > 0 )); then
  rm -f "$ENV_TMP"
  fail "still REPLACE_ME, real values never set: ${placeholder_keys[*]}"
fi

mv -f "$ENV_TMP" "$ENV_OUT"
chmod 600 "$ENV_OUT"
log "Wrote $ENV_OUT ($fetched_count secrets + static/per-environment config)."

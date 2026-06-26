#!/usr/bin/env bash
# Shared PE SQS queue helpers for run_scans.sh and watch_queues.sh.

pe_queue_lib_init() {
  if [[ -z "${PE_QUEUE_PREFIX:-}" ]]; then
    case "${PE_STAGE:-staging-cd}" in
      integration) PE_QUEUE_PREFIX=pe-integration ;;
      *) PE_QUEUE_PREFIX=pe-staging ;;
    esac
  fi
  PE_QUEUE_REGION="${AWS_REGION:-us-east-1}"
  if [[ -z "${PE_QUEUE_ACCOUNT_ID:-}" ]]; then
    PE_QUEUE_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
  fi
}

# Map peScanController SCAN_CATALOG keys to queue name segments (scan["scan"] values).
pe_catalog_to_scan_type() {
  case "$1" in
    asm_sync) echo asmSync ;;
    csg_alerts) echo cybersixgill-alerts ;;
    csg_creds) echo cybersixgill-credentials ;;
    csg_mentions) echo cybersixgill-mentions ;;
    csg_topcves) echo cybersixgill-topcves ;;
    dnsmonitor) echo dnsmonitor ;;
    dnstwist) echo dnstwist ;;
    intelx) echo intelx ;;
    shodan) echo shodan ;;
    shodan_test) echo shodan ;;
    *) echo "$1" ;;
  esac
}

pe_queue_name_for_catalog_key() {
  local scan_key="$1"
  local scan_type
  scan_type="$(pe_catalog_to_scan_type "$scan_key")"
  echo "${PE_QUEUE_PREFIX}-${scan_type}-queue"
}

pe_queue_url_for_catalog_key() {
  local queue_name
  queue_name="$(pe_queue_name_for_catalog_key "$1")"
  echo "https://sqs.${PE_QUEUE_REGION}.amazonaws.com/${PE_QUEUE_ACCOUNT_ID}/${queue_name}"
}

# Split comma-separated catalog keys into lines (trimmed, non-empty).
pe_split_catalog_keys() {
  local scans_csv="$1"
  printf '%s' "$scans_csv" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed '/^$/d'
}

# Print "queue_name visible in_flight" or return 1 if the queue does not exist.
pe_read_queue_depth() {
  local queue_url="$1"
  local attrs
  if ! attrs="$(aws sqs get-queue-attributes \
    --region "$PE_QUEUE_REGION" \
    --queue-url "$queue_url" \
    --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
    --output json 2>/dev/null)"; then
    return 1
  fi
  local visible in_flight
  visible="$(printf '%s' "$attrs" | jq -r '.Attributes.ApproximateNumberOfMessages // "0"')"
  in_flight="$(printf '%s' "$attrs" | jq -r '.Attributes.ApproximateNumberOfMessagesNotVisible // "0"')"
  echo "$visible $in_flight"
}

pe_print_queue_status_for_scans() {
  local scans_csv="$1"
  local scan_key queue_name queue_url depths visible in_flight
  local any=false

  while IFS= read -r scan_key; do
    queue_name="$(pe_queue_name_for_catalog_key "$scan_key")"
    queue_url="$(pe_queue_url_for_catalog_key "$scan_key")"
    if ! depths="$(pe_read_queue_depth "$queue_url")"; then
      echo "  ${queue_name}: (queue not found)"
      continue
    fi
    visible="${depths%% *}"
    in_flight="${depths#* }"
    echo "  ${queue_name}: ${visible} visible, ${in_flight} in flight"
    if [[ "$visible" != "0" || "$in_flight" != "0" ]]; then
      any=true
    fi
  done < <(pe_split_catalog_keys "$scans_csv")

  if [[ "$any" == true ]]; then
    return 0
  fi
  return 1
}

pe_queues_have_messages() {
  pe_print_queue_status_for_scans "$1" >/dev/null
}

pe_purge_queues_for_scans() {
  local scans_csv="$1"
  local scan_key queue_name queue_url
  while IFS= read -r scan_key; do
    queue_name="$(pe_queue_name_for_catalog_key "$scan_key")"
    queue_url="$(pe_queue_url_for_catalog_key "$scan_key")"
    echo "Purging ${queue_name}..."
    if ! aws sqs purge-queue --region "$PE_QUEUE_REGION" --queue-url "$queue_url"; then
      echo "ERROR: failed to purge ${queue_name}. Ensure the IAM principal has sqs:PurgeQueue." >&2
      return 1
    fi
  done < <(pe_split_catalog_keys "$scans_csv")
}

pe_confirm_queue_action() {
  local scans_csv="$1"
  local choice

  echo "The following PE scan queues already contain messages:"
  echo
  pe_print_queue_status_for_scans "$scans_csv"
  echo
  echo "Choose an action:"
  echo "  [c] Clear queues (purge) and continue"
  echo "  [C] Continue without clearing (append new messages / use existing backlog)"
  echo "  [a] Abort"
  echo

  if [[ ! -t 0 ]]; then
    echo "ERROR: queues are not empty and stdin is not a TTY." >&2
    echo "Re-run in a terminal, or pass --ignore-queue-depth / --purge-queues." >&2
    return 1
  fi

  while true; do
    read -r -p "Choice [c/C/a]: " choice
    case "$choice" in
      c|C) echo "$choice"; return 0 ;;
      a|A)
        echo "Aborted." >&2
        return 2
        ;;
      *) echo "Enter c, C, or a." ;;
    esac
  done
}

# Returns 0 when it is safe to proceed (queues empty, purged, or user chose continue).
pe_guard_queues_for_scans() {
  local scans_csv="$1"
  local ignore_depth="$2"
  local purge_first="$3"
  local action

  pe_queue_lib_init

  if [[ "$ignore_depth" == true ]]; then
    return 0
  fi

  if ! pe_queues_have_messages "$scans_csv"; then
    echo "PE scan queues are empty for: ${scans_csv}"
    return 0
  fi

  if [[ "$purge_first" == true ]]; then
    pe_purge_queues_for_scans "$scans_csv"
    echo "Waiting 5s for SQS purge to settle..."
    sleep 5
    return 0
  fi

  if ! action="$(pe_confirm_queue_action "$scans_csv")"; then
    return 1
  fi
  if [[ "$action" == "c" ]]; then
    pe_purge_queues_for_scans "$scans_csv"
    echo "Waiting 5s for SQS purge to settle..."
    sleep 5
  fi
  return 0
}

pe_all_queues_empty_for_scans() {
  local scans_csv="$1"
  ! pe_queues_have_messages "$scans_csv"
}

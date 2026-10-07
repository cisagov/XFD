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
}

pe_queue_url_for_catalog_key() {
  local queue_name err_file url
  queue_name="$(pe_queue_name_for_catalog_key "$1")"
  err_file="$(mktemp)"
  if ! url="$(aws sqs get-queue-url \
    --region "$PE_QUEUE_REGION" \
    --queue-name "$queue_name" \
    --query QueueUrl \
    --output text 2>"$err_file")"; then
    PE_LAST_QUEUE_ERROR="$(tr '\n' ' ' < "$err_file" | sed 's/  */ /g; s/^ //; s/ $//')"
    rm -f "$err_file"
    return 1
  fi
  rm -f "$err_file"
  PE_LAST_QUEUE_ERROR=""
  printf '%s' "$url"
}

pe_queue_name_for_catalog_key() {
  echo "${PE_QUEUE_PREFIX}-${1}-queue"
}

# Split comma-separated catalog keys into lines (trimmed, non-empty).
pe_split_catalog_keys() {
  local scans_csv="$1"
  printf '%s' "$scans_csv" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed '/^$/d'
}

# Print "visible in_flight" or return 1. Sets PE_LAST_QUEUE_ERROR on failure.
pe_read_queue_depth() {
  local queue_url="$1"
  local err_file attrs visible in_flight
  PE_LAST_QUEUE_ERROR=""
  err_file="$(mktemp)"
  if ! attrs="$(aws sqs get-queue-attributes \
    --region "$PE_QUEUE_REGION" \
    --queue-url "$queue_url" \
    --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
    --output json 2>"$err_file")"; then
    PE_LAST_QUEUE_ERROR="$(tr '\n' ' ' < "$err_file" | sed 's/  */ /g; s/^ //; s/ $//')"
    rm -f "$err_file"
    return 1
  fi
  rm -f "$err_file"
  visible="$(printf '%s' "$attrs" | jq -r '.Attributes.ApproximateNumberOfMessages // "0"')"
  in_flight="$(printf '%s' "$attrs" | jq -r '.Attributes.ApproximateNumberOfMessagesNotVisible // "0"')"
  PE_LAST_QUEUE_DEPTH="${visible} ${in_flight}"
  return 0
}

pe_print_queue_status_for_scans() {
  local scans_csv="$1"
  local scan_key queue_name queue_url visible in_flight
  local any=false
  local unreadable=false

  while IFS= read -r scan_key || [[ -n "$scan_key" ]]; do
    [[ -z "$scan_key" ]] && continue
    queue_name="$(pe_queue_name_for_catalog_key "$scan_key")"
    if ! queue_url="$(pe_queue_url_for_catalog_key "$scan_key")"; then
      if [[ -n "${PE_LAST_QUEUE_ERROR:-}" ]]; then
        echo "  ${queue_name}: (cannot resolve queue — ${PE_LAST_QUEUE_ERROR})"
      else
        echo "  ${queue_name}: (queue not found)"
      fi
      unreadable=true
      continue
    fi
    if ! pe_read_queue_depth "$queue_url"; then
      if [[ -n "${PE_LAST_QUEUE_ERROR:-}" ]]; then
        echo "  ${queue_name}: (cannot read queue — ${PE_LAST_QUEUE_ERROR})"
      else
        echo "  ${queue_name}: (cannot read queue)"
      fi
      unreadable=true
      continue
    fi
    visible="${PE_LAST_QUEUE_DEPTH%% *}"
    in_flight="${PE_LAST_QUEUE_DEPTH#* }"
    echo "  ${queue_name}: ${visible} visible, ${in_flight} in flight"
    if [[ "$visible" != "0" || "$in_flight" != "0" ]]; then
      any=true
    fi
  done <<EOF
$(pe_split_catalog_keys "$scans_csv")
EOF

  if [[ "$unreadable" == true ]]; then
    return 2
  fi
  if [[ "$any" == true ]]; then
    return 0
  fi
  return 1
}

pe_queues_have_messages() {
  pe_print_queue_status_for_scans "$1" >/dev/null
  return $?
}

pe_purge_queues_for_scans() {
  local scans_csv="$1"
  local scan_key queue_name queue_url
  while IFS= read -r scan_key || [[ -n "$scan_key" ]]; do
    [[ -z "$scan_key" ]] && continue
    queue_name="$(pe_queue_name_for_catalog_key "$scan_key")"
    if ! queue_url="$(pe_queue_url_for_catalog_key "$scan_key")"; then
      echo "ERROR: could not resolve queue URL for ${queue_name}" >&2
      return 1
    fi
    echo "Purging ${queue_name}..."
    if ! aws sqs purge-queue --region "$PE_QUEUE_REGION" --queue-url "$queue_url"; then
      echo "ERROR: failed to purge ${queue_name}. Ensure the IAM principal has sqs:PurgeQueue." >&2
      return 1
    fi
  done <<EOF
$(pe_split_catalog_keys "$scans_csv")
EOF
}

pe_confirm_queue_action() {
  local scans_csv="$1"
  local choice

  echo "The following PE scan queues already contain messages:" >&2
  echo >&2
  pe_print_queue_status_for_scans "$scans_csv" >&2
  echo >&2
  echo "Choose an action:" >&2
  echo "  c — Purge selected queues, then invoke the scan (visible messages only)" >&2
  echo "  C — Keep existing messages and invoke anyway (append / use backlog)" >&2
  echo "  a — Abort (do not invoke Lambda)" >&2
  echo >&2
  echo "Note: purge does not remove in-flight messages (already received by workers)." >&2
  echo "Stop running ECS tasks first if you need a fully empty queue." >&2
  echo >&2

  if [[ ! -t 0 ]]; then
    echo "ERROR: queues are not empty and stdin is not a TTY." >&2
    echo "Re-run in a terminal, or pass --ignore-queue-depth / --purge-queues." >&2
    return 1
  fi

  while true; do
    read -r -p "Enter c (purge+continue), C (continue), or a (abort): " choice
    case "$choice" in
      c|C) echo "$choice"; return 0 ;;
      a|A)
        echo "Aborted." >&2
        return 2
        ;;
      *) echo "Enter c (purge+continue), C (continue), or a (abort)." >&2 ;;
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
    status=$?
    if [[ "$status" -eq 2 ]]; then
      echo "ERROR: could not read one or more PE scan queues (check IAM sqs:GetQueueAttributes on pe-staging-*)." >&2
      return 1
    fi
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
    if pe_queues_have_messages "$scans_csv"; then
      echo "WARNING: queue still has messages after purge (in-flight messages are not purged)." >&2
      pe_print_queue_status_for_scans "$scans_csv" >&2
    fi
  fi
  return 0
}

pe_all_queues_empty_for_scans() {
  local scans_csv="$1"
  ! pe_queues_have_messages "$scans_csv"
}

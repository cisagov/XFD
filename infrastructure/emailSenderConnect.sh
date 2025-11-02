#!/bin/bash

# Configuration
AWS_PROFILE=${EMAIL_AWS_PROFILE:-"default"}
INSTANCE_ID=${EMAIL_SENDER_INSTANCE_ID:-"your-instance-id"}
AVAILABILITY_ZONE="us-east-1b"
LOCAL_PORT=9995
REMOTE_PORT=22
SSH_USER="ubuntu"
SSH_KEY_PATH=${EMAIL_SSH_KEY_PATH:-""}

function log_info() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') INFO: $1"
}

function log_error() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: $1" >&2
}

# Check if the instance is running
function get_instance_status() {
  aws ec2 describe-instance-status \
    --instance-ids "$INSTANCE_ID" \
    --profile "$AWS_PROFILE" \
    --query 'InstanceStatuses[0].InstanceState.Name' \
    --output text 2> /dev/null
}

# Start the instance if it's not running
function start_instance() {
  log_info "Starting instance $INSTANCE_ID..."
  aws ec2 start-instances \
    --instance-ids "$INSTANCE_ID" \
    --profile "$AWS_PROFILE" \
    > /dev/null

  log_info "Instance started. Waiting for initialization (2 minutes)..."
  sleep 120
}

# Inject SSH Public Key using EC2 Instance Connect
function send_ssh_public_key() {
  log_info "Sending SSH public key..."
  if ! aws ec2-instance-connect send-ssh-public-key \
    --instance-id "$INSTANCE_ID" \
    --availability-zone "$AVAILABILITY_ZONE" \
    --instance-os-user "$SSH_USER" \
    --ssh-public-key "file://$SSH_KEY_PATH" \
    --profile "$AWS_PROFILE"; then
    log_error "Failed to send SSH public key."
    exit 1
  fi
}

# Start port forwarding with AWS SSM
function start_port_forwarding() {
  log_info "Starting port forwarding via SSM..."
  aws ssm start-session \
    --target "$INSTANCE_ID" \
    --document-name AWS-StartPortForwardingSession \
    --parameters "{\"portNumber\":[\"$REMOTE_PORT\"], \"localPortNumber\":[\"$LOCAL_PORT\"]}" \
    --profile "$AWS_PROFILE"
}

# Main script logic
log_info "Starting EC2 connection process..."
if [ -z "$INSTANCE_ID" ]; then
  log_error "INSTANCE_ID is not set. Please set it as an environment variable or update the script."
  exit 1
fi

STATUS=$(get_instance_status | tr -d '\r')

log_info "Current instance status: $STATUS"

if [[ "$STATUS" == "running" ]]; then
  log_info "Instance is already running."
elif [[ "$STATUS" == "stopped" || "$STATUS" == "stopping" ]]; then
  start_instance
else
  log_error "Unexpected instance status: $STATUS"
  exit 1
fi

send_ssh_public_key
start_port_forwarding

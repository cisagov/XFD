"""PE SQS worker loop.

Drain the scan queue then exit (same pattern as crossfeed worker.py).
"""

# Standard Python Libraries
import json
import logging
import os
import shutil
import subprocess  # nosec B404
import sys
import time

# Third-Party Libraries
import boto3
from botocore.exceptions import ClientError

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

LOG_PATH = "/app/pe_reports_logging.log"
EMPTY_CONFIRM_SLEEP_SECONDS = 5
POLL_WAIT_SECONDS = 5
# Keep in sync with peScanController.VISIBILITY_TIMEOUT_SECONDS / XFD scan queues.
VISIBILITY_TIMEOUT_SECONDS = int(os.getenv("PE_SQS_VISIBILITY_TIMEOUT", "18000"))
PE_SOURCE_BIN = shutil.which("pe-source") or "/usr/local/bin/pe-source"


def resolve_command(argv: list[str]) -> list[str]:
    """Resolve the scan executable to an absolute path when possible."""
    if not argv:
        return argv
    executable = argv[0]
    if executable == "pe-source":
        return [PE_SOURCE_BIN, *argv[1:]]
    resolved = shutil.which(executable)
    if resolved:
        return [resolved, *argv[1:]]
    return argv


def run_command(argv: list[str], env: dict | None = None) -> int:
    """Run a scan subprocess with argv (no shell) and return its exit code."""
    command = resolve_command(argv)
    result = subprocess.run(command, check=False, env=env)  # nosec B603
    return result.returncode


def sqs_client():
    """Return a boto3 SQS client for ElasticMQ or AWS."""
    queue_url = os.environ.get("SERVICE_QUEUE_URL", "")
    if "elasticmq" in queue_url or "localhost" in queue_url:
        endpoint = os.getenv("SQS_ENDPOINT_URL", "http://elasticmq:9324")
        return boto3.client(
            "sqs",
            region_name=os.getenv(
                "AWS_DEFAULT_REGION", os.getenv("AWS_REGION", "elasticmq")
            ),
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "local"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
        )
    return boto3.client("sqs")


def receive_message(client, queue_url: str):
    """Receive a single message from the scan queue, or None if empty."""
    try:
        response = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=POLL_WAIT_SECONDS,
        )
        messages = response.get("Messages") or []
        return messages[0] if messages else None
    except Exception as exc:
        LOGGER.error("Error receiving message: %s", exc)
        return None


def extend_message_visibility(client, queue_url: str, receipt_handle: str) -> None:
    """Reset visibility while a long-running scan is in progress."""
    try:
        client.change_message_visibility(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle,
            VisibilityTimeout=VISIBILITY_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        LOGGER.warning("Could not extend message visibility: %s", exc)


def delete_message(client, queue_url: str, receipt_handle: str) -> bool:
    """Delete a processed message from the scan queue."""
    try:
        client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ReceiptHandleIsInvalid":
            LOGGER.warning(
                "Receipt handle expired before delete (visibility timeout too short?). "
                "Scan finished but the message may be redelivered."
            )
            return False
        LOGGER.error("Error deleting message: %s", exc)
        return False
    except Exception as exc:
        LOGGER.error("Error deleting message: %s", exc)
        return False


def queue_confirmed_empty(client, queue_url: str) -> bool:
    """Wait and poll once more before exiting (handles visibility timeouts)."""
    LOGGER.info("Queue appears empty. Double-checking before exit...")
    time.sleep(EMPTY_CONFIRM_SLEEP_SECONDS)
    message = receive_message(client, queue_url)
    if message:
        LOGGER.info("Queue had more messages, continuing drain loop.")
        return False
    LOGGER.info("Confirmed queue is empty. Exiting worker.")
    return True


def parse_org(message: dict) -> str | None:
    """Extract the organization name from an SQS message body."""
    try:
        body = json.loads(message.get("Body", "{}"))
    except json.JSONDecodeError:
        body = {"org": message.get("Body")}
    org = body.get("org")
    return org if org else None


def build_command(service_type: str, org: str) -> list[str]:
    """Build the pe-source command line for the given scan type and org."""
    if "shodan" in service_type:
        return ["pe-source", "shodan", "--soc_med_included", "--org={}".format(org)]
    if "dnstwist" in service_type:
        return ["pe-source", "dnstwist", "--orgs={}".format(org)]
    if "intelx" in service_type:
        return ["pe-source", "intelx", "--org={}".format(org), "--soc_med_included"]
    if "xpanse" in service_type:
        return ["pe-source", "xpanse", "--org={}".format(org)]
    if "asmSync" in service_type:
        asm_sync = shutil.which("pe-asm-sync") or "pe-asm-sync"
        return [asm_sync, "asm-sqs", "--org={}".format(org)]
    if "qualys" in service_type:
        return []
    raise ValueError("Unsupported SERVICE_TYPE: {}".format(service_type))


def run_qualys_scan(org: str) -> int:
    """Run Qualys WAS report pull and findings sync for an organization."""
    report = run_command(["pe-source", "was-report-pull", "--org={}".format(org)])
    if report != 0:
        return report
    return run_command(["pe-source", "was-findings-sync", "--org={}".format(org)])


def run_scan(service_type: str, org: str) -> bool:
    """Run the configured scan for an organization and return success."""
    if "qualys" in service_type:
        LOGGER.info("Running qualys was-report-pull + was-findings-sync for %s", org)
        return run_qualys_scan(org) == 0

    command = build_command(service_type, org)
    LOGGER.info("Running %s", " ".join(command))
    if "dnstwist" in service_type:
        LOGGER.info(
            "dnstwist can take several minutes per root domain (DNS fuzzing + "
            "blocklist checks); scan logs stream below until the org finishes."
        )
    scan_env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "PE_LOG_TO_STDERR": "1",
    }
    exit_code = run_command(command, env=scan_env)
    if exit_code != 0:
        LOGGER.error("Scan command exited with code %s", exit_code)
        return False

    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, encoding="utf-8") as log_file:
            sys.stdout.write(log_file.read())
        os.remove(LOG_PATH)
    return True


def main() -> None:
    """Poll the scan queue until empty, running pe-source for each org."""
    queue_url = os.getenv("SERVICE_QUEUE_URL")
    service_type = os.getenv("SERVICE_TYPE")

    if not queue_url:
        LOGGER.error("SERVICE_QUEUE_URL is not set. Exiting.")
        sys.exit(1)
    if not service_type:
        LOGGER.error("SERVICE_TYPE is not set. Exiting.")
        sys.exit(1)

    client = sqs_client()
    LOGGER.info(
        "PE worker started (pe_worker.py): SERVICE_TYPE=%s queue=%s",
        service_type,
        queue_url,
    )

    while True:
        message = receive_message(client, queue_url)
        if not message:
            if queue_confirmed_empty(client, queue_url):
                break
            continue

        org = parse_org(message)
        if not org:
            LOGGER.error("Invalid message format (missing org). Skipping.")
            continue

        LOGGER.info("Processing organization: %s", org)
        receipt_handle = message.get("ReceiptHandle")
        if receipt_handle:
            extend_message_visibility(client, queue_url, receipt_handle)
        try:
            success = run_scan(service_type, org)
        except Exception as exc:
            LOGGER.error("Error processing %s: %s", org, exc)
            success = False

        if success:
            if receipt_handle:
                delete_message(client, queue_url, receipt_handle)
                LOGGER.info("Done with %s", org)
            else:
                LOGGER.warning("No ReceiptHandle; cannot delete message for %s", org)
        else:
            LOGGER.error(
                "Scan failed for %s; leaving message on queue and "
                "continuing worker loop",
                org,
            )

        time.sleep(1)


if __name__ == "__main__":
    main()

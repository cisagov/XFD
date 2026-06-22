"""PE SQS worker loop — drain scan queue then exit (same pattern as crossfeed worker.py)."""

# Standard Python Libraries
import json
import logging
import os
import subprocess
import sys
import time

# Third-Party Libraries
import boto3

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

LOG_PATH = "/app/pe_reports_logging.log"
EMPTY_CONFIRM_SLEEP_SECONDS = 5
POLL_WAIT_SECONDS = 5


def sqs_client():
    queue_url = os.environ.get("SERVICE_QUEUE_URL", "")
    if "elasticmq" in queue_url or "localhost" in queue_url:
        endpoint = os.getenv("SQS_ENDPOINT_URL", "http://elasticmq:9324")
        return boto3.client(
            "sqs",
            region_name=os.getenv("AWS_DEFAULT_REGION", os.getenv("AWS_REGION", "elasticmq")),
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "local"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
        )
    return boto3.client("sqs")


def receive_message(client, queue_url: str):
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


def delete_message(client, queue_url: str, receipt_handle: str) -> None:
    try:
        client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    except Exception as exc:
        LOGGER.error("Error deleting message: %s", exc)


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
    try:
        body = json.loads(message.get("Body", "{}"))
    except json.JSONDecodeError:
        body = {"org": message.get("Body")}
    org = body.get("org")
    return org if org else None


def build_command(service_type: str, org: str) -> list[str]:
    if "shodan" in service_type:
        return ["pe-source", "shodan", "--soc_med_included", "--org={}".format(org)]
    if "dnstwist" in service_type:
        return ["pe-source", "dnstwist", "--orgs={}".format(org)]
    if "intelx" in service_type:
        return ["pe-source", "intelx", "--org={}".format(org), "--soc_med_included"]
    if "cybersixgill" in service_type:
        return ["pe-source", "cybersixgill", "--org={}".format(org), "--soc_med_included"]
    if "xpanse" in service_type:
        return ["pe-source", "xpanse", "--org={}".format(org)]
    if "asmSync" in service_type:
        return ["pe-asm-sync", "asm-sqs", "--org={}".format(org)]
    if "qualys" in service_type:
        return []
    raise ValueError("Unsupported SERVICE_TYPE: {}".format(service_type))


def run_qualys_scan(org: str) -> int:
    report = subprocess.run(
        ["pe-source", "was-report-pull", "--org={}".format(org)],
        check=False,
    )
    if report.returncode != 0:
        return report.returncode
    findings = subprocess.run(
        ["pe-source", "was-findings-sync", "--org={}".format(org)],
        check=False,
    )
    return findings.returncode


def run_scan(service_type: str, org: str) -> bool:
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
    result = subprocess.run(command, check=False, env=scan_env)
    if result.returncode != 0:
        LOGGER.error("Scan command exited with code %s", result.returncode)
        return False

    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, encoding="utf-8") as log_file:
            print(log_file.read(), end="")
        os.remove(LOG_PATH)
    return True


def main() -> None:
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
        try:
            success = run_scan(service_type, org)
        except Exception as exc:
            LOGGER.error("Error processing %s: %s", org, exc)
            success = False

        if success:
            receipt_handle = message.get("ReceiptHandle")
            if receipt_handle:
                delete_message(client, queue_url, receipt_handle)
                LOGGER.info("Done with %s", org)
            else:
                LOGGER.warning("No ReceiptHandle; cannot delete message for %s", org)
        else:
            LOGGER.error(
                "Scan failed for %s; leaving message on queue and continuing worker loop",
                org,
            )

        time.sleep(1)


if __name__ == "__main__":
    main()

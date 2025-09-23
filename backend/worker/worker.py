"""Worker controller."""
# Standard Python Libraries
import importlib
import json
import logging
import os
import sys
import time

# Third-Party Libraries
import boto3
import django

# Initialize Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
# Django-Dependant Imports
from xfd_api.helpers.email import ensure_zscaler_cert_downloaded
from xfd_api.schema_models.scan import SCAN_SCHEMA
from xfd_api.tasks.helpers.log_scan_result import log_scan_result

# Setup logging
LOGGER = logging.getLogger(__name__)

# ElasticMQ/SQS Configuration
QUEUE_URL = os.getenv("SERVICE_QUEUE_URL")
if not QUEUE_URL:
    LOGGER.error("QUEUE_URL environment variable is not set. Exiting.")
    sys.exit(1)

# Detect if using ElasticMQ (local) or AWS SQS (prod)
USE_ELASTICMQ = "elasticmq" in QUEUE_URL or "localhost" in QUEUE_URL

# Set correct SQS client configuration
sqs = boto3.client(
    "sqs",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=QUEUE_URL if USE_ELASTICMQ else None,
)


def get_message(queue_url):
    """Retrieve a message from the queue (ElasticMQ or AWS SQS)."""
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=5
        )
        messages = response.get("Messages", [])
        return messages[0] if messages else None
    except Exception as e:
        LOGGER.error("Error retrieving message: %s", e)
        return None


def delete_message(queue_url, receipt_handle):
    """Delete a processed message from the queue."""
    try:
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        LOGGER.info("Deleted processed message.")
    except Exception as e:
        LOGGER.error("Error deleting message: %s", e)


def process_message(message_data):
    """Extract and process the message data."""
    try:
        return json.loads(message_data.get("Body", "{}"))
    except Exception:
        LOGGER.error("Error processing message data.")
        return {"org": message_data.get("Body")}


def main():
    """Worker loop."""
    is_dmz = os.getenv("IS_DMZ")
    if str(is_dmz).lower() not in {"true", "1"}:
        zscaler_cert = ensure_zscaler_cert_downloaded()
        os.environ["AWS_CA_BUNDLE"] = zscaler_cert
        os.environ["REQUESTS_CA_BUNDLE"] = zscaler_cert
        os.environ["SSL_CERT_FILE"] = zscaler_cert
        LOGGER.info("Set Zscaler cert environment variables for outbound TLS.")
    else:
        # If not set, ensure these are not set so traffic is direct
        os.environ.pop("AWS_CA_BUNDLE", None)
        os.environ.pop("REQUESTS_CA_BUNDLE", None)
        os.environ.pop("SSL_CERT_FILE", None)
        LOGGER.info("DMZ mode enabled. Skipping Zscaler cert injection.")

    try:
        command_options = json.loads(os.getenv("CROSSFEED_COMMAND_OPTIONS", "{}"))
    except Exception:
        LOGGER.error("Error loading command options.")
        command_options = {}

    LOGGER.info("Base command options: %s", command_options)
    scan_name = command_options.get("scanName", "test")
    scan_schema = SCAN_SCHEMA.get(scan_name)
    if not scan_schema:
        LOGGER.exception("No schema found for scan name: %s", scan_name)
        raise ValueError

    try:
        task_module = importlib.import_module("xfd_api.tasks.{}".format(scan_name))
        scan_fn = getattr(task_module, "handler", None)
        if not callable(scan_fn):
            raise ValueError(
                "No handler function found for scan name: {}".format(scan_name)
            )
    except ModuleNotFoundError:
        LOGGER.exception("No task handler found for scan name: %s", scan_name)
        raise ValueError

    # If global_scan, run the scan one time and exit without queue polling.
    if getattr(scan_schema, "global_scan", False):
        LOGGER.info("Global scan detected. Running scan once without queue polling.")
        scan_fn(command_options)
        sys.exit(0)

    SERVICE_QUEUE_URL = command_options.get("SERVICE_QUEUE_URL")
    if not SERVICE_QUEUE_URL:
        LOGGER.error("SERVICE_QUEUE_URL not set in command options. Exiting.")
        sys.exit(1)

    is_local = os.getenv("IS_LOCAL")
    full_queue_path_name = (
        "http://localhost:9324/000000000000/{}-{}-queue".format("dev", scan_name)
        if is_local
        else SERVICE_QUEUE_URL
    )
    LOGGER.info("Polling queue: %s", full_queue_path_name)

    while True:
        message_data = get_message(full_queue_path_name)
        if not message_data:
            LOGGER.info("No more messages in the queue.")
            break

        message = process_message(message_data)
        org = message.get("org")
        org_id = message.get("id")
        if not org:
            LOGGER.error("Invalid message format. Skipping.")
            continue

        LOGGER.info("Processing organization: %s", org)
        task_options = dict(command_options)
        task_options.update(
            {
                "organizationName": org,
                "organizationId": org_id,
                "organizations": [],
            }
        )

        try:
            result = scan_fn(task_options)

            # Log returned http status and message body
            if isinstance(result, dict):
                http_status = result.get("status_code") or result.get("statusCode")
                message_body = result.get("body")
            else:
                http_status = None
                message_body = str(result)

            log_scan_result(
                scan_id=task_options.get("scanId"),
                organization_id=task_options.get("organizationId"),
                http_status=http_status,
                message=message_body,
            )
            # Delete message after processing
            receipt_handle = message_data.get("ReceiptHandle")
            if receipt_handle:
                delete_message(full_queue_path_name, receipt_handle)
            else:
                LOGGER.warning("No ReceiptHandle found; cannot delete message.")
        except Exception as e:
            LOGGER.error("Error processing %s: %s", org, e)
        time.sleep(1)


if __name__ == "__main__":
    main()

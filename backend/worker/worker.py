"""Worker controller."""
# Standard Python Libraries
import importlib
import json
import os
import sys
import time

# Third-Party Libraries
import boto3
import django
from xfd_api.schema_models.scan import SCAN_SCHEMA

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# ElasticMQ/SQS Configuration
QUEUE_URL = os.getenv("SERVICE_QUEUE_URL")
if not QUEUE_URL:
    print("QUEUE_URL environment variable is not set. Exiting.")
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
        print("Error retrieving message: {}".format(e))
        return None


def delete_message(queue_url, receipt_handle):
    """Delete a processed message from the queue."""
    try:
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        print("Deleted processed message.")
    except Exception as e:
        print("Error deleting message: {}".format(e))


def process_message(message_data):
    """Extract and process the message data."""
    try:
        return json.loads(message_data.get("Body", "{}"))
    except Exception:
        return {"org": message_data.get("Body")}


def main():
    """Worker loop."""
    try:
        command_options = json.loads(os.getenv("CROSSFEED_COMMAND_OPTIONS", "{}"))
    except Exception:
        command_options = {}

    print("Base command options: {}".format(command_options))
    scan_name = command_options.get("scanName", "test")
    scan_schema = SCAN_SCHEMA.get(scan_name)
    if not scan_schema:
        raise ValueError("No schema found for scan name: {}".format(scan_name))

    try:
        task_module = importlib.import_module("xfd_api.tasks.{}".format(scan_name))
        scan_fn = getattr(task_module, "handler", None)
        if not callable(scan_fn):
            raise ValueError(
                "No handler function found for scan name: {}".format(scan_name)
            )
    except ModuleNotFoundError:
        raise ValueError("No task handler found for scan name: {}".format(scan_name))

    # If global_scan, run the scan one time and exit without queue polling.
    if getattr(scan_schema, "global_scan", False):
        print("Global scan detected. Running scan once without queue polling.")
        scan_fn(command_options)
        sys.exit(0)

    SERVICE_QUEUE_URL = command_options.get("SERVICE_QUEUE_URL")
    if not SERVICE_QUEUE_URL:
        print("SERVICE_QUEUE_URL not set in command options. Exiting.")
        sys.exit(1)

    is_local = os.getenv("IS_LOCAL")
    full_queue_path_name = (
        "http://localhost:9324/000000000000/{}-{}-queue".format("dev", scan_name)
        if is_local
        else SERVICE_QUEUE_URL
    )
    print("Polling queue: {}".format(full_queue_path_name))

    while True:
        message_data = get_message(full_queue_path_name)
        if not message_data:
            print("No more messages in the queue.")
            break

        message = process_message(message_data)
        org = message.get("org")
        org_id = message.get("id")
        if not org:
            print("Invalid message format. Skipping.")
            continue

        print("Processing organization: {}".format(org))
        task_options = dict(command_options)
        task_options.update(
            {
                "organizationName": org,
                "organizationId": org_id,
                "organizations": [],
            }
        )

        try:
            scan_fn(task_options)
            # Delete message after processing
            receipt_handle = message_data.get("ReceiptHandle")
            if receipt_handle:
                delete_message(full_queue_path_name, receipt_handle)
            else:
                print("No ReceiptHandle found; cannot delete message.")
        except Exception as e:
            print("Error processing {}: {}".format(org, e))
        time.sleep(1)


if __name__ == "__main__":
    main()

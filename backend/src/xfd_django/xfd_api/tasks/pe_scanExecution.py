"""PE Scan Execution."""
# Standard Python Libraries
import json
import logging
import os

# Third-Party Libraries
import boto3
from botocore.exceptions import ClientError
import django

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
from xfd_mini_dl.models import Scan, ScanTask

LOGGER = logging.getLogger(__name__)
QUEUE_URL = os.getenv("QUEUE_URL")

if not os.getenv("IS_LOCAL"):
    ecs_client = boto3.client("ecs")


def start_desired_tasks(
    scan_type,
    desired_count,
    scan_id,
    organizations,
    shodan_api_keys=None,
):  # pylint: disable=R0913, R0915, W0613
    """Start the desired number of PE tasks on AWS ECS or local Docker."""
    scans_with_name = Scan.objects.filter(name=scan_type)
    max_concurrent = max((scan.concurrent_tasks for scan in scans_with_name), default=1)

    existing_indexes = list(
        ScanTask.objects.filter(
            scan__name=scan_type,
            status__in=["created", "queued", "requested", "started"],
        ).values_list("concurrency_index", flat=True)
    )

    available_indexes = sorted(
        set(range(1, max_concurrent + 1)) - set(existing_indexes)
    )

    this_scan_running = ScanTask.objects.filter(
        scan_id=scan_id,
        status__in=["created", "queued", "requested", "started"],
    ).count()

    remaining_for_this_scan = desired_count - this_scan_running
    shodan_api_keys = shodan_api_keys or []

    if scan_type == "shodan" and len(shodan_api_keys) < remaining_for_this_scan:
        LOGGER.warning(
            "Not enough Shodan API keys. Needed: %s, Provided: %s",
            remaining_for_this_scan,
            len(shodan_api_keys),
        )
        return

    if remaining_for_this_scan <= 0:
        LOGGER.warning(
            "Scan %s already has %s tasks running (desired: %s). Not launching more.",
            scan_id,
            this_scan_running,
            desired_count,
        )
        return

    remaining_count = min(len(available_indexes), remaining_for_this_scan)

    if remaining_count == 0:
        LOGGER.warning(
            "No available concurrency slots for scan '%s'. Max: %d, Running: %d",
            scan_type,
            max_concurrent,
            len(existing_indexes),
        )
        return

    queue_url = "{}{}-queue".format(QUEUE_URL, scan_type)
    batch_size = 1 if scan_type == "shodan" else 10

    while remaining_count > 0:
        current_batch_count = min(remaining_count, batch_size)
        shodan_api_key = (
            shodan_api_keys[available_indexes[0] - 1]
            if available_indexes and len(shodan_api_keys) >= available_indexes[0]
            else ""
        )

        if os.getenv("IS_LOCAL"):
            # Third-Party Libraries
            from pe.peScanController import (  # pylint: disable=import-outside-toplevel
                LOCAL_SCAN_CATALOG,
                start_local_docker_workers,
            )

            scan_config = dict(
                LOCAL_SCAN_CATALOG.get(scan_type, {"scan": scan_type, "count": 1})
            )
            scan_config["count"] = current_batch_count
            api_key_arg = ",".join(shodan_api_keys) if scan_type == "shodan" else ""
            start_local_docker_workers([scan_config], api_key_arg)
            remaining_count -= current_batch_count
            continue
        else:
            try:
                ecs_client.run_task(
                    cluster=os.getenv("PE_FARGATE_CLUSTER_NAME"),
                    taskDefinition=os.getenv("PE_FARGATE_TASK_DEFINITION_NAME"),
                    networkConfiguration={
                        "awsvpcConfiguration": {
                            "assignPublicIp": "ENABLED",
                            "securityGroups": [os.getenv("FARGATE_SG_ID")],
                            "subnets": [os.getenv("FARGATE_SUBNET_ID")],
                        }
                    },
                    platformVersion="1.4.0",
                    launchType="FARGATE",
                    count=current_batch_count,
                    overrides={
                        "containerOverrides": [
                            {
                                "name": "main",
                                "environment": [
                                    {"name": "SERVICE_TYPE", "value": scan_type},
                                    {
                                        "name": "SERVICE_QUEUE_URL",
                                        "value": queue_url,
                                    },
                                    {
                                        "name": "PE_SHODAN_API_KEYS",
                                        "value": shodan_api_key,
                                    },
                                ],
                            }
                        ]
                    },
                )
                LOGGER.info("Tasks started (PE): %d", current_batch_count)
            except ClientError as e:
                LOGGER.error("Error starting PE tasks: %s", e)
                raise e

        remaining_count -= current_batch_count


def handler(event, context):
    """Handle the AWS Lambda event to start PE tasks on ECS or Docker."""
    try:
        LOGGER.info("Starting PE scan execution")
        desired_count = event.get("desiredCount", 1)
        scan_type = event.get("scanType")
        scan_id = event.get("scanId", "")
        organizations = event.get("organizations", [])

        if not scan_type:
            LOGGER.error("Failed: no scanType provided.")
            return {"status_code": 400, "body": "Failed: no scanType provided."}

        if scan_type == "shodan":
            api_key_list = event.get("apiKeyList", "")
            shodan_api_keys = (
                [key.strip() for key in api_key_list.split(",")] if api_key_list else []
            )

            if len(shodan_api_keys) < desired_count:
                LOGGER.error("Failed: insufficient API keys for Shodan.")
                return {
                    "status_code": 400,
                    "body": "Failed: insufficient API keys for Shodan.",
                }

            start_desired_tasks(
                scan_type,
                desired_count,
                scan_id,
                organizations,
                shodan_api_keys=shodan_api_keys,
            )
        else:
            start_desired_tasks(
                scan_type,
                desired_count,
                scan_id,
                organizations,
            )

        return {"status_code": 200, "body": "Tasks started successfully."}
    except Exception as e:
        LOGGER.error("Error in PE handler: %s", e)
        return {"status_code": 500, "body": json.dumps(str(e))}

"""Scan Execution."""
# Standard Python Libraries
import json
import logging
import os

# Third-Party Libraries
import django

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
from xfd_api.tasks.ecs_client import ECSClient
from xfd_mini_dl.models import Scan, ScanTask

LOGGER = logging.getLogger(__name__)
QUEUE_URL = os.getenv("QUEUE_URL")


def create_scan_task(
    scan_id, scan_type, organizations, fargate_task_arn=None, concurrency_index=1
):
    """Create a ScanTask for each launched task and assign the correct fargateTaskArn."""
    scan_task = ScanTask.objects.create(
        scan_id=scan_id,
        type="fargate",
        status="created",
        fargate_task_arn=fargate_task_arn,
        concurrency_index=concurrency_index,
    )

    if organizations:
        scan_task.organizations.set(organizations)

    scan_task.save()
    return scan_task


def start_desired_tasks(
    scan_type,
    desired_count,
    scan_id,
    organizations,
    shodan_api_keys=None,
    arguments=None,
):  # pylint: disable=R0913, R0915
    """Start the desired number of tasks on AWS ECS based on configuration."""
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
    if arguments is None:
        arguments = {}

    while remaining_count > 0:
        current_batch_count = min(remaining_count, batch_size)
        shodan_api_key = (
            shodan_api_keys[available_indexes[0] - 1]
            if available_indexes and len(shodan_api_keys) >= available_indexes[0]
            else ""
        )

        LOGGER.info("Running ECS task")
        ecs = ECSClient()
        command_options = {
            "scanId": scan_id,
            "scanName": scan_type,
            "SERVICE_QUEUE_URL": queue_url,
            "SERVICE_TYPE": scan_type,
            "count": current_batch_count,
            **arguments,
        }
        if scan_type == "shodan":
            command_options["SHODAN_API_KEY"] = shodan_api_key
        else:
            command_options["SHODAN_API_KEY"] = os.getenv("SHODAN_API_KEY")

        result = ecs.run_command(command_options)

        if not result.get("tasks"):
            LOGGER.exception("Failed to start ECS task for scan %s", scan_type)
            raise Exception("Failed to start ECS task for scan {}".format(scan_type))

        for task in result["tasks"]:
            task_arn = task["taskArn"]
            if not available_indexes:
                raise Exception("Not enough available concurrency indexes")
            index_to_use = available_indexes.pop(0)
            create_scan_task(
                scan_id,
                scan_type,
                organizations,
                fargate_task_arn=task_arn,
                concurrency_index=index_to_use,
            )
            LOGGER.info(
                "Started ECS task %s with concurrency index %d",
                task_arn,
                index_to_use,
            )

        remaining_count -= current_batch_count


def handler(event, context):
    """Handle the AWS Lambda event to start tasks on ECS."""
    try:
        LOGGER.info("Starting scan execution")
        desired_count = event.get("desiredCount", 1)
        scan_type = event.get("scanType")
        scan_id = event.get("scanId", "")
        organizations = event.get("organizations", [])
        arguments = event.get("arguments", {})

        if not scan_type:
            LOGGER.error("Failed: no scanType provided.")
            return {"status_code": 400, "body": "Failed: no scanType provided."}

        if scan_type == "shodan":
            api_key_list = os.getenv("PE_SHODAN_API_KEYS", "")
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
                arguments=arguments,
            )
        else:
            start_desired_tasks(
                scan_type,
                desired_count,
                scan_id,
                organizations,
                arguments=arguments,
            )

        return {"status_code": 200, "body": "Tasks started successfully."}
    except Exception as e:
        LOGGER.error("Error in handler: %s", e)
        return {"status_code": 500, "body": json.dumps(str(e))}

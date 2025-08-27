"""Scan Execution."""
# Standard Python Libraries
import json
import logging
import os
import random
import re

# Third-Party Libraries
import boto3
from botocore.exceptions import ClientError
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

# Conditionally import Docker if in local environment
docker = None
if os.getenv("IS_LOCAL"):
    # Third-Party Libraries
    from docker import DockerClient

    docker = DockerClient(base_url="unix://var/run/docker.sock")
else:
    ecs_client = boto3.client("ecs")


def to_snake_case(input_string):
    """Convert a string to snake-case."""
    return re.sub(r"\s+", "-", input_string)


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
    scan_type, desired_count, scan_id, organizations, is_pe=False, shodan_api_keys=[]
):
    """Start the desired number of tasks on AWS ECS or local Docker based on configuration."""
    # Step 1: Get the scan instance
    scans_with_name = Scan.objects.filter(name=scan_type)

    # Step 2: Determine the max concurrent_tasks among them
    max_concurrent = max((scan.concurrent_tasks for scan in scans_with_name), default=1)

    # Step 3: Get all currently running concurrency_indexes across all scans of this type
    existing_indexes = list(
        ScanTask.objects.filter(
            scan__name=scan_type,
            status__in=["created", "queued", "requested", "started"],
        ).values_list("concurrency_index", flat=True)
    )

    available_indexes = sorted(
        set(range(1, max_concurrent + 1)) - set(existing_indexes)
    )

    # Step 4: Check how many tasks are already running for this specific scan
    this_scan_running = ScanTask.objects.filter(
        scan_id=scan_id,
        status__in=["created", "queued", "requested", "started"],
    ).count()

    # Step 5: Determine how many *this* scan is allowed to start
    remaining_for_this_scan = desired_count - this_scan_running
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

    # Step 6: Global cap applies too
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
    shodan_api_keys = shodan_api_keys or []

    while remaining_count > 0:
        current_batch_count = min(remaining_count, batch_size)
        shodan_api_key = (
            shodan_api_keys[available_indexes[0] - 1]
            if available_indexes and len(shodan_api_keys) >= available_indexes[0]
            else ""
        )

        if is_pe:
            if os.getenv("IS_LOCAL"):
                # Use local Docker environment (old method)
                LOGGER.info("Starting local containers (PE)...")
                start_local_containers(
                    current_batch_count, scan_type, queue_url, shodan_api_key
                )
            else:
                # Use AWS ECS (old method)
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
        else:
            LOGGER.info("Running ECS task")
            ecs = ECSClient()
            command_options = {
                "scanId": scan_id,
                "scanName": scan_type,
                "SERVICE_QUEUE_URL": queue_url,
                "SERVICE_TYPE": scan_type,
                "count": current_batch_count,
            }
            if scan_type == "shodan":
                command_options["SHODAN_API_KEY"] = shodan_api_key
            else:
                command_options["SHODAN_API_KEY"] = os.getenv("SHODAN_API_KEY")

            result = ecs.run_command(command_options)

            if not result.get("tasks"):
                LOGGER.exception("Failed to start ECS task for scan %s", scan_type)
                raise Exception(
                    "Failed to start ECS task for scan {}".format(scan_type)
                )

            for task in result["tasks"]:
                task_arn = task["taskArn"]
                if not available_indexes:
                    raise Exception("Not enough available concurrency indexes")
                index_to_use = available_indexes.pop(0)  # Use and remove
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


def start_local_containers(count, scan_type, queue_url, shodan_api_key=""):
    """Start the desired number of local Docker containers."""
    for i in range(count):
        try:
            container_name = to_snake_case(
                "crossfeed_worker_{}_{}_{}".format(
                    scan_type, i, random.randint(1, 10_000_000)
                )
            )
            container = docker.containers.create(
                name=container_name,
                image="pe-worker",
                network_mode="xfd_backend",
                mem_limit="4g",
                detach=True,
                environment=[
                    "DB_DIALECT={}".format(os.getenv("DB_DIALECT")),
                    "DB_HOST={}".format(os.getenv("DB_HOST")),
                    "IS_LOCAL=true",
                    "DB_PORT={}".format(os.getenv("DB_PORT")),
                    "DB_NAME={}".format(os.getenv("DB_NAME")),
                    "DB_USERNAME={}".format(os.getenv("DB_USERNAME")),
                    "DB_PASSWORD={}".format(os.getenv("DB_PASSWORD")),
                    "NIST_API_KEY={}".format(os.getenv("NIST_API_KEY")),
                    "SERVICE_QUEUE_URL={}".format(queue_url),
                    "SERVICE_TYPE={}".format(scan_type),
                    "PE_SHODAN_API_KEYS={}".format(shodan_api_key),
                    "WHOIS_XML_KEY={}".format(os.getenv("WHOIS_XML_KEY")),
                    "QUALYS_USERNAME={}".format(os.getenv("QUALYS_USERNAME")),
                    "QUALYS_PASSWORD={}".format(os.getenv("QUALYS_PASSWORD")),
                ],
            )
            container.start()
            LOGGER.info("Started container: %s", container_name)
        except Exception as e:
            LOGGER.error("Error starting local container %d: %s", i, e)


def handler(event, context):
    """Handle the AWS Lambda event to start tasks on ECS or Docker."""
    try:
        LOGGER.info("Starting scan execution")
        desired_count = event.get("desiredCount", 1)
        scan_type = event.get("scanType")
        is_pe = event.get("isPe", True)
        scan_id = event.get("scanId", "")
        organizations = event.get("organizations", [])

        if not scan_type:
            LOGGER.error("Failed: no scanType provided.")
            return {"status_code": 400, "body": "Failed: no scanType provided."}

        if scan_type == "shodan":
            if is_pe:
                api_key_list = event.get("apiKeyList", "")
            else:
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
                is_pe=is_pe,
                shodan_api_keys=shodan_api_keys,
            )

        else:
            start_desired_tasks(
                scan_type, desired_count, scan_id, organizations, is_pe=is_pe
            )

        return {"status_code": 200, "body": "Tasks started successfully."}
    except Exception as e:
        LOGGER.error("Error in handler: %s", e)
        return {"status_code": 500, "body": json.dumps(str(e))}

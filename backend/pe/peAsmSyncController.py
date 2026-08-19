"""PE ASM Sync controller Lambda.

Starts Fargate tasks that run `pe-asm-sync` (re-enumerate customer assets). Kept separate
from peScanController, peReportController, and peMailerController so scan orchestration stays unchanged.

Event payload:
    {
        "orgs": ["all"],
        "taskCount": 1,
        "local": false
    }

Orgs (comma-separated cyhy_db_name values, or one shortcut used alone):

    DHS,DHS_CISA
        Generate reports for the listed organizations.

    all
        All organizations with report_on (same as pe-reports --orgs=all).

    demo
        All demo organizations (pe-reports --orgs=demo).

    all-orgs / demo-orgs
        Expand from the PE database to a comma-separated org list (for parallel tasks).

taskCount splits a resolved comma-separated org list across multiple Fargate tasks.
Shortcuts all and demo always run as a single task.
"""
# Standard Python Libraries
import json
import logging
import os
from typing import Any, Dict, List

# Third-Party Libraries
import boto3
from pe.peScanController import (  # pylint: disable=import-error
    fetch_orgs_from_db,
    is_local_mode,
    local_worker_dev_mount,
)
from pe.worker_key_planner import api_key_label, plan_worker_keys, worker_key_env

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

ASMSYNC_BATCH_SHORTCUTS = frozenset({"all", "demo"})
ASMSYNC_EXPAND_SHORTCUTS = frozenset({"all-orgs", "demo-orgs"})


def resolve_asmsync_orgs(orgs: List[str]) -> str:
    """Return the --orgs value for pe-reports."""
    if not orgs:
        raise ValueError("orgs is required")

    if len(orgs) == 1:
        shortcut = orgs[0]
        if shortcut in ASMSYNC_EXPAND_SHORTCUTS:
            if shortcut == "all-orgs":
                names = fetch_orgs_from_db(report_on=True)
            else:
                names = fetch_orgs_from_db(demo=True)
            return ",".join(names)
        if shortcut in ASMSYNC_BATCH_SHORTCUTS:
            return shortcut
        if shortcut.upper() == "DEMO":
            return "demo"

    for org in orgs:
        if org in ASMSYNC_EXPAND_SHORTCUTS:
            raise ValueError(
                "Expand shortcuts all-orgs and demo-orgs must be used alone"
            )

    return ",".join(orgs)


def chunk_asmsync_orgs(orgs_arg: str, task_count: int) -> List[str]:
    """Split a comma-separated org list across tasks; leave batch shortcuts intact."""
    if task_count <= 1 or orgs_arg in ASMSYNC_BATCH_SHORTCUTS:
        return [orgs_arg]

    names = [part.strip() for part in orgs_arg.split(",") if part.strip()]
    if len(names) <= 1:
        return [orgs_arg]

    task_count = min(task_count, len(names))
    chunks: List[List[str]] = [[] for _ in range(task_count)]
    for index, name in enumerate(names):
        chunks[index % task_count].append(name)
    return [",".join(chunk) for chunk in chunks if chunk]


def start_fargate_asmsync_tasks(
    orgs_arg: str,
    worker_api_key: str,
) -> int:
    """Start one ECS Fargate ASM Sync task with one Shodan API key."""
    ecs_client = boto3.client("ecs")
    cluster = os.environ["PE_FARGATE_CLUSTER_NAME"]
    task_definition = os.environ["PE_FARGATE_TASK_DEFINITION_NAME"]
    security_group = os.environ["FARGATE_SG_ID"]
    subnet = os.environ["FARGATE_SUBNET_ID"]

    key_environment = worker_key_env("asmsync", worker_api_key)
    environment = [
        {"name": "ASMSYNC_ORGS", "value": orgs_arg},
        *[{"name": name, "value": value} for name, value in key_environment.items()],
    ]

    LOGGER.info(
        "Starting Fargate ASM Sync task for orgs=%s with API key %s",
        orgs_arg,
        api_key_label(worker_api_key),
    )

    response = ecs_client.run_task(
        cluster=cluster,
        taskDefinition=task_definition,
        networkConfiguration={
            "awsvpcConfiguration": {
                "assignPublicIp": "ENABLED",
                "securityGroups": [security_group],
                "subnets": [subnet],
            }
        },
        platformVersion="1.4.0",
        launchType="FARGATE",
        count=1,
        overrides={
            "containerOverrides": [
                {
                    "name": "main",
                    "command": ["./worker/pe-asmsync-start.sh"],
                    "environment": environment,
                }
            ]
        },
    )

    failures = response.get("failures", [])
    if failures:
        raise RuntimeError(
            "Failed to start ASM Sync task for {}: {}".format(
                orgs_arg,
                failures,
            )
        )

    return len(response.get("tasks", []))


def start_local_docker_asmsync_task(
    orgs_arg: str,
    worker_api_key: str,
) -> str:
    """Start a local ASM Sync container with one Shodan API key."""
    # Third-Party Libraries
    import docker

    client = docker.from_env()
    container_name = "pe_asmsync_{:x}".format(int.from_bytes(os.urandom(4), "big"))

    environment = {
        "IS_LOCAL": "true",
        "DJANGO_SETTINGS_MODULE": "pe_reports_django.settings",
        "DJANGO_ALLOW_ASYNC_UNSAFE": "true",
        "ASMSYNC_ORGS": orgs_arg,
        "DB_HOST": os.getenv(
            "PE_DB_HOST",
            os.getenv("DB_HOST", "db"),
        ),
        "PE_DB_NAME": os.getenv("PE_DB_NAME", "pe"),
        "PE_DB_USERNAME": os.getenv("PE_DB_USERNAME", "pe"),
        "PE_DB_PASSWORD": os.getenv("PE_DB_PASSWORD", ""),
        "PE_API_URL": os.getenv(
            "PE_API_URL",
            "http://127.0.0.1:8000",
        ),
        "PE_API_KEY": os.getenv("PE_API_KEY", ""),
        "WHOIS_XML_KEY": os.getenv("WHOIS_XML_KEY", ""),
    }
    environment.update(worker_key_env("asmsync", worker_api_key))

    run_kwargs: Dict[str, Any] = {
        "image": "pe-worker",
        "name": container_name,
        "network": "backend",
        "environment": environment,
        "command": ["./worker/pe-asmsync-start.sh"],
        "detach": True,
        "mem_limit": os.getenv("PE_REPORT_MEM_LIMIT", "8g"),
    }

    dev_mount = local_worker_dev_mount()
    if dev_mount:
        run_kwargs["volumes"] = dev_mount

    client.containers.run(**run_kwargs)

    LOGGER.info(
        "Started local ASM Sync container %s for orgs=%s " "with API key %s",
        container_name,
        orgs_arg,
        api_key_label(worker_api_key),
    )
    return container_name


def run(event: Dict[str, Any]) -> Dict[str, Any]:
    """Start ASM Sync on Fargate or local Docker."""
    orgs = event.get("orgs")
    task_count = int(event.get("taskCount", 1))
    local = is_local_mode(event)
    if not orgs:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "orgs is required"}),
        }
    if isinstance(orgs, str):
        org_list = [part.strip() for part in orgs.split(",") if part.strip()]
    else:
        org_list = list(orgs)

    orgs_arg = resolve_asmsync_orgs(org_list)
    requested_chunks = chunk_asmsync_orgs(orgs_arg, task_count)

    worker_api_keys = plan_worker_keys(
        "asmsync",
        len(requested_chunks),
    )
    org_chunks = chunk_asmsync_orgs(
        orgs_arg,
        len(worker_api_keys),
    )

    started = 0
    container_names: List[str] = []

    for chunk, worker_api_key in zip(
        org_chunks,
        worker_api_keys,
    ):
        if local:
            container_names.append(
                start_local_docker_asmsync_task(
                    chunk,
                    worker_api_key,
                )
            )
            started += 1
        else:
            started += start_fargate_asmsync_tasks(
                chunk,
                worker_api_key,
            )

    body = {
        "message": "PE ASM Sync started",
        "orgs": orgs_arg,
        "tasksStarted": started,
        "local": local,
    }
    if container_names:
        body["containerNames"] = container_names
    return {"statusCode": 200, "body": json.dumps(body)}


def handler(event, context):
    """AWS Lambda entrypoint."""
    try:
        return run(event)
    except ValueError as exc:
        LOGGER.error("Validation error: %s", exc)
        return {"statusCode": 400, "body": json.dumps({"error": str(exc)})}
    except Exception as exc:
        LOGGER.exception("Unhandled error in PE ASM Sync controller")
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}

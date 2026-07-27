"""PE report controller Lambda.

Starts Fargate tasks that run `pe-reports` (PDF generation + S3 upload). Kept separate
from peScanController so scan orchestration stays unchanged.

Event payload:
    {
        "reportDate": "2026-07-15",
        "orgs": ["all"],
        "taskCount": 1,
        "flare": false,
        "socMedIncluded": false,
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

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

REPORT_BATCH_SHORTCUTS = frozenset({"all", "demo"})
REPORT_EXPAND_SHORTCUTS = frozenset({"all-orgs", "demo-orgs"})
LOCAL_REPORTS_OUTPUT_PATH = "/tmp/pe-reports"  # nosec B108


def resolve_report_orgs(orgs: List[str]) -> str:
    """Return the --orgs value for pe-reports."""
    if not orgs:
        raise ValueError("orgs is required")

    if len(orgs) == 1:
        shortcut = orgs[0]
        if shortcut in REPORT_EXPAND_SHORTCUTS:
            if shortcut == "all-orgs":
                names = fetch_orgs_from_db(report_on=True)
            else:
                names = fetch_orgs_from_db(demo=True)
            return ",".join(names)
        if shortcut in REPORT_BATCH_SHORTCUTS:
            return shortcut
        if shortcut.upper() == "DEMO":
            return "demo"

    for org in orgs:
        if org in REPORT_EXPAND_SHORTCUTS:
            raise ValueError(
                "Expand shortcuts all-orgs and demo-orgs must be used alone"
            )

    return ",".join(orgs)


def chunk_report_orgs(orgs_arg: str, task_count: int) -> List[str]:
    """Split a comma-separated org list across tasks; leave batch shortcuts intact."""
    if task_count <= 1 or orgs_arg in REPORT_BATCH_SHORTCUTS:
        return [orgs_arg]

    names = [part.strip() for part in orgs_arg.split(",") if part.strip()]
    if len(names) <= 1:
        return [orgs_arg]

    task_count = min(task_count, len(names))
    chunks: List[List[str]] = [[] for _ in range(task_count)]
    for index, name in enumerate(names):
        chunks[index % task_count].append(name)
    return [",".join(chunk) for chunk in chunks if chunk]


def start_fargate_report_tasks(
    report_date: str,
    orgs_arg: str,
    *,
    flare: bool,
    soc_med_included: bool,
) -> int:
    """Start one or more ECS Fargate report-generation tasks."""
    ecs_client = boto3.client("ecs")
    cluster = os.environ["PE_FARGATE_CLUSTER_NAME"]
    task_definition = os.environ["PE_FARGATE_TASK_DEFINITION_NAME"]
    security_group = os.environ["FARGATE_SG_ID"]
    subnet = os.environ["FARGATE_SUBNET_ID"]

    reports_bucket = os.environ.get("REPORTS_BUCKET_NAME", "")
    environment = [
        {"name": "REPORT_DATE", "value": report_date},
        {"name": "REPORT_ORGS", "value": orgs_arg},
        {"name": "REPORT_FLARE", "value": "true" if flare else "false"},
        {
            "name": "REPORT_SOC_MED_INCLUDED",
            "value": "true" if soc_med_included else "false",
        },
    ]
    if reports_bucket:
        environment.append({"name": "REPORTS_BUCKET_NAME", "value": reports_bucket})

    LOGGER.info(
        "Starting Fargate report task for date=%s orgs=%s", report_date, orgs_arg
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
                    "command": ["./worker/pe-report-start.sh"],
                    "environment": environment,
                }
            ]
        },
    )
    failures = response.get("failures", [])
    if failures:
        raise RuntimeError("Failed to start report task: {}".format(failures))
    return len(response.get("tasks", []))


def start_local_docker_report_task(
    report_date: str,
    orgs_arg: str,
    *,
    flare: bool,
    soc_med_included: bool,
) -> str:
    """Start a detached pe-worker container running pe-report-start.sh locally."""
    # Third-Party Libraries
    import docker

    client = docker.from_env()
    container_name = "pe_report_{:x}".format(int.from_bytes(os.urandom(4), "big"))
    environment = {
        "IS_LOCAL": "true",
        "DJANGO_SETTINGS_MODULE": "pe_reports_django.settings",
        "DJANGO_ALLOW_ASYNC_UNSAFE": "true",
        "REPORT_DATE": report_date,
        "REPORT_ORGS": orgs_arg,
        "REPORT_OUTPUT_DIR": LOCAL_REPORTS_OUTPUT_PATH,
        "REPORT_FLARE": "true" if flare else "false",
        "REPORT_SOC_MED_INCLUDED": "true" if soc_med_included else "false",
        "REPORTS_BUCKET_NAME": os.getenv("REPORTS_BUCKET_NAME", "local-reports"),
        "DB_HOST": os.getenv("PE_DB_HOST", os.getenv("DB_HOST", "db")),
        "PE_DB_NAME": os.getenv("PE_DB_NAME", "pe"),
        "PE_DB_USERNAME": os.getenv("PE_DB_USERNAME", "pe"),
        "PE_DB_PASSWORD": os.getenv("PE_DB_PASSWORD", ""),
        "PE_API_URL": os.getenv("PE_API_URL", "http://127.0.0.1:8000"),
        "PE_API_KEY": os.getenv("PE_API_KEY", ""),
    }

    run_kwargs: Dict[str, Any] = {
        "image": "pe-worker",
        "name": container_name,
        "network": "backend",
        "environment": environment,
        "command": ["./worker/pe-report-start.sh"],
        "detach": True,
        "mem_limit": os.getenv("PE_REPORT_MEM_LIMIT", "8g"),
    }
    dev_mount = local_worker_dev_mount()
    if dev_mount:
        run_kwargs["volumes"] = dev_mount

    client.containers.run(**run_kwargs)
    LOGGER.info("Started local report container %s", container_name)
    return container_name


def run(event: Dict[str, Any]) -> Dict[str, Any]:
    """Start report generation on Fargate or local Docker."""
    report_date = event.get("reportDate")
    orgs = event.get("orgs")
    task_count = int(event.get("taskCount", 1))
    flare = bool(event.get("flare", False))
    soc_med_included = bool(event.get("socMedIncluded", False))
    local = is_local_mode(event)

    if not report_date:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "reportDate is required (YYYY-MM-DD)"}),
        }
    if not orgs:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "orgs is required"}),
        }

    if isinstance(orgs, str):
        org_list = [part.strip() for part in orgs.split(",") if part.strip()]
    else:
        org_list = list(orgs)

    orgs_arg = resolve_report_orgs(org_list)
    org_chunks = chunk_report_orgs(orgs_arg, task_count)

    started = 0
    container_names: List[str] = []
    for chunk in org_chunks:
        if local:
            container_names.append(
                start_local_docker_report_task(
                    report_date,
                    chunk,
                    flare=flare,
                    soc_med_included=soc_med_included,
                )
            )
            started += 1
        else:
            started += start_fargate_report_tasks(
                report_date,
                chunk,
                flare=flare,
                soc_med_included=soc_med_included,
            )

    body = {
        "message": "PE report generation started",
        "reportDate": report_date,
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
        LOGGER.exception("Unhandled error in PE report controller")
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}

"""PE mailer controller Lambda.

Starts a Fargate task that runs `pe-mailer` (retrieve report PDFs from S3,
encrypt them, and email them via SES). Kept separate from peScanController
and peReportController for the same reason peReportController is separate:
pe-mailer already batches every requested org -- and one end-of-run summary
email -- inside a single process, so there is no parallel-worker/queue
semantics to gain by routing it through SCAN_CATALOG/pe_worker.py.

Event payload:
    {
        "reportDate": "2026-07-30",
        "orgs": "all",
        "summaryTo": "person@example.com,other@example.com",
        "testEmails": "test@example.com",
        "local": false
    }

reportDate is required, the same as peReportController's -- pe-mailer reads
report PDFs from S3 under a per-date prefix (see pe_mailer.s3_reports), so
there is no "latest" to discover on its own; it must be told which run's
reports to mail, normally the same date passed to peReportController.

orgs is either "all" (every report_on org, matching pe-mailer --orgs=all) or
a comma-separated list of cyhy_db_name values. pe-mailer's own --orgs flag
has no "demo"/"all-orgs"/"demo-orgs" expansion (unlike pe-reports), so
neither does this controller.

summaryTo/testEmails are optional comma-separated email lists, passed
through to pe-mailer's --summary-to/--test-emails.

For local Docker runs only, setting the host env var PE_LOCAL_REPORTS_DIR
(a directory laid out the way `make run-reports`' OUTPUT_DIR is) bind-mounts
it into the container and points pe-mailer at it instead of S3 for reading
report PDFs -- see pe_mailer.local_reports. MAILER_ARN/SES sending is
unaffected; that's always real AWS regardless.
"""
# Standard Python Libraries
import json
import logging
import os
from typing import Any, Dict, List, Union

# Third-Party Libraries
import boto3
from pe.peScanController import (  # pylint: disable=import-error
    is_local_mode,
    local_worker_dev_mount,
)

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def resolve_mailer_orgs(orgs: Union[str, List[str]]) -> str:
    """Return the --orgs value for pe-mailer.

    pe-mailer's own --orgs only understands "all" or a literal
    comma-separated cyhy_db_name list -- there is no "demo"/"all-orgs"/
    "demo-orgs" expansion to replicate here (unlike pe-reports).
    """
    if isinstance(orgs, str):
        value = orgs.strip()
        if not value:
            raise ValueError("orgs is required")
        return value

    if not orgs:
        raise ValueError("orgs is required")
    return ",".join(orgs)


def start_fargate_mailer_task(
    report_date: str,
    orgs_arg: str,
    *,
    summary_to: str = "",
    test_emails: str = "",
) -> int:
    """Start an ECS Fargate task that runs pe-mailer.

    Only overrides the env vars specific to this invocation (MAILER_REPORT_DATE/
    MAILER_ORGS/MAILER_SUMMARY_TO/MAILER_TEST_EMAILS/PE_LOG_TO_STDERR) -- DB
    credentials, MAILER_ARN, REPORTS_BUCKET_NAME, and PE API creds are expected
    to already be part of the base task definition, same as peReportController
    does for pe-reports.

    PE_LOG_TO_STDERR is forced on here (rather than added to the shared
    pe_worker task definition in Terraform) specifically so it only applies to
    pe-mailer runs -- that task definition is also used by peScanController/
    peReportController, and this is the one path where email_reports.py's own
    LOGGER output (its file-only default -- see email_reports.main) needs to
    reach the awslogs driver/CloudWatch instead of vanishing with the
    container's ephemeral filesystem when the task stops. See
    start_local_docker_mailer_task, which already sets this for local runs.
    """
    ecs_client = boto3.client("ecs")
    cluster = os.environ["PE_FARGATE_CLUSTER_NAME"]
    task_definition = os.environ["PE_FARGATE_TASK_DEFINITION_NAME"]
    security_group = os.environ["FARGATE_SG_ID"]
    subnet = os.environ["FARGATE_SUBNET_ID"]

    environment = [
        {"name": "MAILER_REPORT_DATE", "value": report_date},
        {"name": "MAILER_ORGS", "value": orgs_arg},
        {"name": "PE_LOG_TO_STDERR", "value": "true"},
    ]
    if summary_to:
        environment.append({"name": "MAILER_SUMMARY_TO", "value": summary_to})
    if test_emails:
        environment.append({"name": "MAILER_TEST_EMAILS", "value": test_emails})

    LOGGER.info(
        "Starting Fargate mailer task for date=%s orgs=%s", report_date, orgs_arg
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
                    "command": ["./worker/pe-mailer-start.sh"],
                    "environment": environment,
                }
            ]
        },
    )
    failures = response.get("failures", [])
    if failures:
        raise RuntimeError("Failed to start mailer task: {}".format(failures))
    return len(response.get("tasks", []))


def start_local_docker_mailer_task(
    report_date: str,
    orgs_arg: str,
    *,
    summary_to: str = "",
    test_emails: str = "",
) -> str:
    """Start a detached pe-worker container running pe-mailer-start.sh locally."""
    # Third-Party Libraries
    import docker

    client = docker.from_env()
    container_name = "pe_mailer_{:x}".format(int.from_bytes(os.urandom(4), "big"))
    environment = {
        "IS_LOCAL": "true",
        "DJANGO_SETTINGS_MODULE": "pe_reports_django.settings",
        "DJANGO_ALLOW_ASYNC_UNSAFE": "true",
        "MAILER_REPORT_DATE": report_date,
        "MAILER_ORGS": orgs_arg,
        "REPORTS_BUCKET_NAME": os.getenv("REPORTS_BUCKET_NAME", "local-reports"),
        "MAILER_ARN": os.getenv("MAILER_ARN", ""),
        # pe-mailer's own logging.basicConfig() sends everything to a log file
        # inside the container by default (see email_reports.py:main) -- for
        # local runs, mirror it to stderr too so errors show up in `docker
        # logs` instead of only being visible via `docker cp` from a
        # container that's already exited.
        "PE_LOG_TO_STDERR": "true",
        "PE_DB_PASSWORD_KEY": os.getenv("PE_DB_PASSWORD_KEY", ""),
        "DB_HOST": os.getenv("PE_DB_HOST", os.getenv("DB_HOST", "db")),
        "PE_DB_NAME": os.getenv("PE_DB_NAME", "pe"),
        "PE_DB_USERNAME": os.getenv("PE_DB_USERNAME", "pe"),
        "PE_DB_PASSWORD": os.getenv("PE_DB_PASSWORD", ""),
        # Always the in-container loopback -- this is the same container's own
        # uvicorn process (started by pe-mailer-start.sh), not a host-configurable
        # external API. Deliberately not sourced from the host's PE_API_URL env
        # var, which commonly points elsewhere (e.g. the xfd-backend healthcheck
        # in the repo-root .env) and would silently break the in-container health
        # check if forwarded here.
        "PE_API_URL": "http://127.0.0.1:8000",
        "PE_API_KEY": os.getenv("PE_API_KEY", ""),
    }
    if summary_to:
        environment["MAILER_SUMMARY_TO"] = summary_to
    if test_emails:
        environment["MAILER_TEST_EMAILS"] = test_emails

    # MAILER_ARN assume-role and SES send are always real AWS calls -- no local
    # bypass exists for actually sending mail -- so this container needs real AWS
    # credentials regardless. Forward whatever the invoking process has (e.g.
    # exported via `aws configure export-credentials` or an SSO session) rather
    # than fabricating placeholder ones.
    for aws_var in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "AWS_PROFILE",
    ):
        value = os.getenv(aws_var)
        if value:
            environment[aws_var] = value

    volumes: Dict[str, Dict[str, str]] = {}
    dev_mount = local_worker_dev_mount()
    if dev_mount:
        volumes.update(dev_mount)

    # Optional: bypass S3 for the report PDFs themselves (only S3 -- MAILER_ARN/
    # SES above are unaffected) by pointing this at a local directory laid out
    # the same way `make run-reports`' OUTPUT_DIR is, e.g. the same path passed
    # as OUTPUT_DIR there. See pe_mailer.local_reports for the convention.
    #
    # Taken as-is, already resolved -- this process runs inside the `backend`
    # container (docker compose exec), so ~/os.path.expanduser() here would
    # resolve against *that* container's $HOME (root's), not the actual
    # Docker-daemon host's, silently producing a path the daemon can't mount
    # (e.g. /root/... instead of /Users/you/...). The Makefile's run-mailer
    # target does the real (host-side) tilde-expansion and existence check
    # before this ever runs, matching the PE_DEV_MOUNT_HOST convention above.
    local_reports_dir = os.getenv("PE_LOCAL_REPORTS_DIR")
    if local_reports_dir:
        volumes[local_reports_dir] = {"bind": "/local-reports", "mode": "ro"}
        environment["MAILER_LOCAL_REPORTS_DIR"] = "/local-reports"

    run_kwargs: Dict[str, Any] = {
        "image": "pe-worker",
        "name": container_name,
        "network": "backend",
        "environment": environment,
        "command": ["./worker/pe-mailer-start.sh"],
        "detach": True,
        "mem_limit": os.getenv("PE_MAILER_MEM_LIMIT", "2g"),
    }
    if volumes:
        run_kwargs["volumes"] = volumes

    client.containers.run(**run_kwargs)
    LOGGER.info("Started local mailer container %s", container_name)
    return container_name


def run(event: Dict[str, Any]) -> Dict[str, Any]:
    """Start pe-mailer on Fargate or local Docker."""
    report_date = event.get("reportDate")
    orgs = event.get("orgs")
    summary_to = event.get("summaryTo") or ""
    test_emails = event.get("testEmails") or ""
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

    orgs_arg = resolve_mailer_orgs(orgs)

    if local:
        container_name = start_local_docker_mailer_task(
            report_date, orgs_arg, summary_to=summary_to, test_emails=test_emails
        )
        body = {
            "message": "PE mailer started",
            "reportDate": report_date,
            "orgs": orgs_arg,
            "tasksStarted": 1,
            "local": True,
            "containerName": container_name,
        }
    else:
        started = start_fargate_mailer_task(
            report_date, orgs_arg, summary_to=summary_to, test_emails=test_emails
        )
        body = {
            "message": "PE mailer started",
            "reportDate": report_date,
            "orgs": orgs_arg,
            "tasksStarted": started,
            "local": False,
        }

    return {"statusCode": 200, "body": json.dumps(body)}


def handler(event, context):
    """AWS Lambda entrypoint."""
    try:
        return run(event)
    except ValueError as exc:
        LOGGER.error("Validation error: %s", exc)
        return {"statusCode": 400, "body": json.dumps({"error": str(exc)})}
    except Exception as exc:
        LOGGER.exception("Unhandled error in PE mailer controller")
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}

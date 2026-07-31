"""PE scan controller Lambda.

Replaces the EC2 pe_sqs.py workflow: queue org messages to SQS and start PE Fargate
workers for the requested scans.

Event payload:
    {
        "scans": ["dnstwist", "shodan", "flare_events"],
        "orgs": ["DHS", "DHS_CISA"],
        "taskCount": 3,
        "queueOnly": false,
        "tasksOnly": false,
        "messageDelaySeconds": 1,
        "local": false
    }

Keyed scans (flare_events, shodan, asmSync) validate comma-separated API keys from
SSM-injected env vars, skip invalid keys, and start one worker container per valid
key (capped by taskCount/COUNT). Each container receives a single per-worker key
env var (e.g. FLARE_API_KEY, PE_SHODAN_API_KEY). See worker_key_planner.py.

Orgs (comma-separated cyhy_db_name values, or one shortcut used alone):

    DHS,DHS_CISA
        One SQS message per org. Use COUNT>1 to drain the queue with multiple workers.

    all / DEMO  (batch mode)
        One SQS message total. The worker passes --orgs=all or --orgs=DEMO to
        pe-source, which scans every report_on or demo org inside a single worker
        process (sequential).

    all-orgs / demo-orgs  (parallel mode)
        peScanController looks up orgs in the PE database and enqueues one message per
        cyhy_db_name. Use COUNT>1 so multiple workers process orgs concurrently.

    Do not combine a shortcut with named orgs (e.g. all-orgs,DHS is invalid).

taskCount overrides the scan catalog default worker count for this invocation.
Inline scan config: {"scan": "dnstwist", "count": 10}
"""
# Standard Python Libraries
import json
import logging
import os
import time
from typing import Any, Dict, List, Union
from urllib.parse import urlparse

# Third-Party Libraries
import boto3

# Local Libraries
from pe.worker_key_planner import (
    KEYED_SCANS,
    api_key_label,
    plan_worker_keys_for_scans,
    worker_key_env,
    worker_keys_for_scan,
)

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Match XFD scan queues: dnstwist and other PE scans can run for hours.
VISIBILITY_TIMEOUT_SECONDS = 18000

SCAN_CATALOG = {
    "asmSync": {"scan": "asmSync", "count": 2},
    "dnsmonitor": {"scan": "dnsmonitor", "count": 1},
    "dnstwist": {"scan": "dnstwist", "count": 142},
    # Default high so unspecified COUNT uses all valid Flare keys (clamped later).
    "flare_events": {"scan": "flare_events", "count": 50},
    "flare_ident_prune": {"scan": "flare_ident_prune", "count": 1},
    "flare_ident_refresh": {"scan": "flare_ident_refresh", "count": 1},
    "intelx": {"scan": "intelx", "count": 10},
    "shodan": {"scan": "shodan", "count": 3, "apiKeys": ""},
    "shodan_top_cves": {"scan": "shodan_top_cves", "count": 3, "apiKeys": ""},
}

ORG_BATCH_SHORTCUTS = frozenset({"all", "DEMO"})
ORG_EXPAND_SHORTCUTS = frozenset({"all-orgs", "demo-orgs"})

SHODAN_SCANS = {"shodan", "asmSync", "shodan_top_cves"}


def is_local_mode(event: Dict[str, Any] | None = None) -> bool:
    """Return True when running against local ElasticMQ and Docker workers."""
    if event and event.get("local"):
        return True
    return os.getenv("IS_LOCAL", "").lower() in {"1", "true", "yes"}


def local_sqs_endpoint() -> str:
    """SQS endpoint reachable from pe-worker containers on the Docker network."""
    return os.getenv(
        "SQS_ENDPOINT_URL", os.getenv("QUEUE_URL", "http://elasticmq:9324")
    ).rstrip("/")


def normalize_local_queue_url(queue_url: str) -> str:
    """Normalize queue URLs that use localhost for Docker network workers."""
    path = urlparse(queue_url).path
    if not path:
        raise ValueError("Invalid queue URL: {!r}".format(queue_url))
    return "{}{}".format(local_sqs_endpoint(), path)


def host_bind_source_for_container_path(container_path: str) -> str | None:
    """Return the host path for a bind mount visible inside this container."""
    explicit = os.getenv("PE_DEV_MOUNT_HOST")
    if explicit:
        return explicit

    target = os.path.normpath(container_path)
    try:
        with open("/proc/self/mountinfo", encoding="utf-8") as mountinfo:
            for line in mountinfo:
                parts = line.strip().split()
                if "-" not in parts:
                    continue
                mountpoint = os.path.normpath(parts[4])
                if mountpoint != target:
                    continue
                dash = parts.index("-")
                if parts[dash + 1] == "bind" and dash + 2 < len(parts):
                    return parts[dash + 2]
    except OSError:
        return None
    return None


def local_worker_dev_mount() -> Dict[str, Dict[str, str]] | None:
    """Bind-mount live PE sources when peScanController runs inside compose backend."""
    pe_tree = os.getenv("PE_DEV_MOUNT_CONTAINER", "/app/pe")
    worker_py = os.path.join(pe_tree, "worker", "pe_worker.py")
    if not os.path.isfile(worker_py):
        return None

    host_path = host_bind_source_for_container_path(pe_tree)
    if not host_path:
        LOGGER.info(
            "PE dev tree found at %s but no host bind source; "
            "using pe-worker image only",
            pe_tree,
        )
        return None

    return {host_path: {"bind": "/app", "mode": "rw"}}


def sqs_endpoint_url() -> str | None:
    """Return ElasticMQ endpoint URL when running locally, else None."""
    queue_url = os.getenv("QUEUE_URL", "")
    if "elasticmq" in queue_url or "localhost" in queue_url:
        return queue_url.rstrip("/")
    return None


def sqs_client():
    """Return a boto3 SQS client configured for local ElasticMQ or AWS."""
    endpoint = sqs_endpoint_url()
    if endpoint:
        return boto3.client(
            "sqs",
            region_name=os.getenv("AWS_REGION", "elasticmq"),
            endpoint_url=endpoint,
        )
    return boto3.client("sqs")


def default_queue_prefix() -> str:
    """Return the PE SQS queue name prefix (separate from XFD scan queues)."""
    return os.environ.get("PE_QUEUE_PREFIX", "pe-staging")


def queue_name_for_scan(scan_type: str) -> str:
    """Build the SQS queue name for a scan type."""
    return "{}-{}-queue".format(default_queue_prefix(), scan_type)


def queue_url_prefix() -> str:
    """Return the prefix used to build fully qualified SQS queue URLs."""
    queue_url = os.environ.get("QUEUE_URL")
    endpoint = sqs_endpoint_url()
    if endpoint:
        prefix = default_queue_prefix()
        return "{}/000000000000/{}-".format(endpoint, prefix)
    if queue_url:
        return queue_url
    region = os.environ.get("AWS_REGION") or boto3.Session().region_name
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    prefix = os.environ["PE_QUEUE_PREFIX"]
    return "https://sqs.{}.amazonaws.com/{}/{}-".format(region, account_id, prefix)


def queue_url_for_scan(scan_type: str) -> str:
    """Return the queue URL for a scan, creating the queue if it does not exist."""
    client = sqs_client()
    queue_name = queue_name_for_scan(scan_type)
    response = client.create_queue(
        QueueName=queue_name,
        Attributes={
            "VisibilityTimeout": str(VISIBILITY_TIMEOUT_SECONDS),
            "MaximumMessageSize": "262144",
            "MessageRetentionPeriod": "604800",
        },
    )
    queue_url = response["QueueUrl"]
    if sqs_endpoint_url():
        queue_url = normalize_local_queue_url(queue_url)
    client.set_queue_attributes(
        QueueUrl=queue_url,
        Attributes={
            "VisibilityTimeout": str(VISIBILITY_TIMEOUT_SECONDS),
        },
    )
    return queue_url


def pe_db_connection_params() -> Dict[str, str]:
    """Return psycopg2 connection parameters for the PE database."""
    return {
        "host": os.getenv("PE_DB_HOST", os.getenv("DB_HOST", "localhost")),
        "dbname": os.getenv("PE_DB_NAME", "pe"),
        "user": os.getenv("PE_DB_USERNAME", "pe"),
        "password": os.getenv("PE_DB_PASSWORD", ""),
    }


# TODO: Convert to API endpoint in CRASM-4061
def fetch_orgs_from_db(*, report_on: bool = False, demo: bool = False) -> List[str]:
    """Load cyhy_db_name values from the PE organizations table."""
    # Third-Party Libraries
    import psycopg2

    if report_on:
        query = (
            "SELECT cyhy_db_name FROM organizations "
            "WHERE report_on = true AND cyhy_db_name IS NOT NULL "
            "ORDER BY cyhy_db_name"
        )
        label = "all-orgs"
    elif demo:
        query = (
            "SELECT cyhy_db_name FROM organizations "
            "WHERE demo = true AND cyhy_db_name IS NOT NULL "
            "ORDER BY cyhy_db_name"
        )
        label = "demo-orgs"
    else:
        raise ValueError("fetch_orgs_from_db requires report_on=True or demo=True")

    with psycopg2.connect(**pe_db_connection_params()) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            names = [row[0] for row in cur.fetchall()]

    if not names:
        raise ValueError("No organizations found for {!r}".format(label))
    return names


def resolve_orgs(orgs: List[str]) -> List[str]:
    """Resolve org list, expanding all-orgs/demo-orgs shortcuts from the PE database.

    Batch shortcuts (all, DEMO) pass through as a single token for pe-source.
    Expand shortcuts (all-orgs, demo-orgs) become one queue message per cyhy_db_name.
    """
    if not orgs:
        return []

    if len(orgs) == 1:
        shortcut = orgs[0]
        if shortcut in ORG_EXPAND_SHORTCUTS:
            if shortcut == "all-orgs":
                return fetch_orgs_from_db(report_on=True)
            return fetch_orgs_from_db(demo=True)
        if shortcut in ORG_BATCH_SHORTCUTS:
            return [shortcut]

    for org in orgs:
        if org in ORG_EXPAND_SHORTCUTS:
            raise ValueError(
                "Expand shortcuts all-orgs and demo-orgs must be used alone"
            )

    return orgs


def resolve_scans(
    scans: List[Union[str, Dict[str, Any]]],
    task_count: int | None = None,
) -> List[Dict[str, Any]]:
    """Resolve scan catalog entries and optional taskCount overrides."""
    resolved = []
    for scan in scans:
        if isinstance(scan, str):
            if scan not in SCAN_CATALOG:
                raise ValueError(
                    "Unknown scan {!r}. Valid keys: {}".format(
                        scan, ", ".join(sorted(SCAN_CATALOG))
                    )
                )
            config = dict(SCAN_CATALOG[scan])
            if task_count is not None:
                config["count"] = int(task_count)
            resolved.append(config)
            continue

        if "scan" not in scan or "count" not in scan:
            raise ValueError("Inline scan config requires 'scan' and 'count' fields")
        config = dict(scan)
        if task_count is not None:
            config["count"] = int(task_count)
        resolved.append(config)

    return resolved


def queue_messages(
    scan_list: List[Dict[str, Any]],
    org_list: List[str],
    delay_seconds: float,
) -> Dict[str, int]:
    """Enqueue one SQS message per org for each requested scan."""
    client = sqs_client()
    counts = {}
    for scan in scan_list:
        scan_name = scan["scan"]
        queue_url = queue_url_for_scan(scan_name)
        sent = 0
        LOGGER.info(
            "Queuing messages for %s on %d organization(s)", scan_name, len(org_list)
        )
        for org in org_list:
            response = client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({"org": org}),
            )
            sent += 1
            LOGGER.info(
                "Message sent to %s for %s (MessageId: %s)",
                scan_name,
                org,
                response["MessageId"],
            )
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        counts[scan_name] = sent
    return counts


def start_fargate_tasks(
    scan_list: List[Dict[str, Any]],
    worker_keys_by_scan: Dict[str, List[str]] | None = None,
) -> Dict[str, int]:
    """Start ECS Fargate pe-worker tasks for each scan in the list."""
    ecs_client = boto3.client("ecs")
    cluster = os.environ["PE_FARGATE_CLUSTER_NAME"]
    task_definition = os.environ["PE_FARGATE_TASK_DEFINITION_NAME"]
    security_group = os.environ["FARGATE_SG_ID"]
    subnet = os.environ["FARGATE_SUBNET_ID"]
    started = {}

    for scan in scan_list:
        scan_name = scan["scan"]
        queue_url = queue_url_for_scan(scan_name)

        if scan_name in KEYED_SCANS:
            worker_keys = worker_keys_for_scan(
                scan_name,
                int(scan["count"]),
                worker_keys_by_scan,
            )
            task_count = 0
            for index, key in enumerate(worker_keys, start=1):
                key_env = worker_key_env(scan_name, key)
                environment = [
                    {"name": "SERVICE_TYPE", "value": scan_name},
                    {"name": "SERVICE_QUEUE_URL", "value": queue_url},
                    *[{"name": k, "value": v} for k, v in key_env.items()],
                ]
                LOGGER.info(
                    "Starting 1 Fargate task for %s with API key %d/%d (%s)",
                    scan_name,
                    index,
                    len(worker_keys),
                    api_key_label(key),
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
                            {"name": "main", "environment": environment}
                        ]
                    },
                )
                failures = response.get("failures", [])
                if failures:
                    raise RuntimeError(
                        "Failed to start tasks for {}: {}".format(scan_name, failures)
                    )
                task_count += len(response.get("tasks", []))
            started[scan_name] = task_count
            LOGGER.info("Started %d task(s) for %s", task_count, scan_name)
            continue

        count = int(scan["count"])
        environment = [
            {"name": "SERVICE_TYPE", "value": scan_name},
            {"name": "SERVICE_QUEUE_URL", "value": queue_url},
        ]

        LOGGER.info("Starting %d Fargate task(s) for %s", count, scan_name)
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
            count=count,
            overrides={
                "containerOverrides": [{"name": "main", "environment": environment}]
            },
        )
        failures = response.get("failures", [])
        if failures:
            raise RuntimeError(
                "Failed to start tasks for {}: {}".format(scan_name, failures)
            )

        task_count = len(response.get("tasks", []))
        started[scan_name] = task_count
        LOGGER.info("Started %d task(s) for %s", task_count, scan_name)

    return started


def start_local_docker_workers(
    scan_list: List[Dict[str, Any]],
    worker_keys_by_scan: Dict[str, List[str]] | None = None,
) -> Dict[str, int]:
    """Start detached pe-worker containers on the local Docker network (IS_LOCAL)."""
    # Third-Party Libraries
    import docker

    client = docker.from_env()
    started: Dict[str, int] = {}

    for scan in scan_list:
        scan_name = scan["scan"]
        queue_url = queue_url_for_scan(scan_name)
        task_count = 0

        if scan_name in KEYED_SCANS:
            worker_slots: List[str | None] = list(
                worker_keys_for_scan(
                    scan_name,
                    int(scan["count"]),
                    worker_keys_by_scan,
                )
            )
        else:
            worker_slots = [None] * int(scan["count"])

        for index, worker_api_key in enumerate(worker_slots, start=1):
            container_name = "pe_worker_{}_{:x}".format(
                scan_name.replace("-", "_"),
                int.from_bytes(os.urandom(4), "big"),
            )
            environment = {
                "IS_LOCAL": "true",
                "DJANGO_SETTINGS_MODULE": "pe_reports_django.settings",
                "DJANGO_ALLOW_ASYNC_UNSAFE": "true",
                "SERVICE_TYPE": scan_name,
                "SERVICE_QUEUE_URL": queue_url,
                "SQS_ENDPOINT_URL": os.getenv(
                    "SQS_ENDPOINT_URL", "http://elasticmq:9324"
                ),
                "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID", "local"),
                "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
                "AWS_DEFAULT_REGION": os.getenv("AWS_REGION", "elasticmq"),
                "DB_HOST": os.getenv("PE_DB_HOST", os.getenv("DB_HOST", "db")),
                "PE_DB_NAME": os.getenv("PE_DB_NAME", "pe"),
                "PE_DB_USERNAME": os.getenv("PE_DB_USERNAME", "pe"),
                "PE_DB_PASSWORD": os.getenv("PE_DB_PASSWORD", ""),
                "PE_API_URL": os.getenv("PE_API_URL", "http://127.0.0.1:8000"),
                "PE_API_KEY": os.getenv("PE_API_KEY", ""),
                "PE_QUEUE_PREFIX": default_queue_prefix(),
                "DNSMONITOR_CLIENT_ID": os.getenv("DNSMONITOR_CLIENT_ID", None),
                "DNSMONITOR_CLIENT_SECRET": os.getenv("DNSMONITOR_CLIENT_SECRET", None),
                "FLARE_TENANT_ID": os.getenv("FLARE_TENANT_ID", ""),
                "SHODAN_ORG_EXCEPTION": os.getenv("SHODAN_ORG_EXCEPTION", None),
            }
            if worker_api_key is not None:
                environment.update(worker_key_env(scan_name, worker_api_key))

            run_kwargs: Dict[str, Any] = {
                "image": "pe-worker",
                "name": container_name,
                "network": "backend",
                "environment": environment,
                "detach": True,
                "mem_limit": os.getenv("PE_WORKER_MEM_LIMIT", "4g"),
            }
            dev_mount = local_worker_dev_mount()
            if dev_mount:
                run_kwargs["volumes"] = dev_mount
                LOGGER.info("Mounting live PE tree for local worker %s", container_name)

            client.containers.run(**run_kwargs)
            if worker_api_key is not None:
                LOGGER.info(
                    "Started local pe-worker container %s for %s " "(API key %d/%d %s)",
                    container_name,
                    scan_name,
                    index,
                    len(worker_slots),
                    api_key_label(worker_api_key),
                )
            else:
                LOGGER.info(
                    "Started local pe-worker container %s for %s",
                    container_name,
                    scan_name,
                )
            task_count += 1

        started[scan_name] = task_count

    return started


def start_workers(
    scan_list: List[Dict[str, Any]],
    local: bool,
    worker_keys_by_scan: Dict[str, List[str]] | None = None,
) -> Dict[str, int]:
    """Start local Docker workers or Fargate tasks depending on environment."""
    if local:
        return start_local_docker_workers(scan_list, worker_keys_by_scan)
    return start_fargate_tasks(scan_list, worker_keys_by_scan)


def run(event: Dict[str, Any]) -> Dict[str, Any]:
    """Queue PE scan work and start workers. Used by Lambda and local tooling."""
    scans = event.get("scans")
    orgs = event.get("orgs")
    queue_only = bool(event.get("queueOnly", False))
    tasks_only = bool(event.get("tasksOnly", False))
    delay_seconds = float(
        event.get("messageDelaySeconds", 0 if is_local_mode(event) else 1)
    )
    local = is_local_mode(event)

    task_count = event.get("taskCount")
    if task_count is not None:
        task_count = int(task_count)

    if not scans:
        return {"statusCode": 400, "body": json.dumps({"error": "scans is required"})}

    if not tasks_only and not orgs:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "orgs is required unless tasksOnly is true"}),
        }

    scan_list = resolve_scans(scans, task_count=task_count)
    org_list = resolve_orgs(orgs) if orgs else []

    worker_keys_by_scan: Dict[str, List[str]] | None = None
    if not queue_only and not tasks_only:
        worker_keys_by_scan = plan_worker_keys_for_scans(scan_list)

    queued = {}
    if not tasks_only:
        queued = queue_messages(scan_list, org_list, delay_seconds)

    started = {}
    if not queue_only:
        started = start_workers(scan_list, local, worker_keys_by_scan)

    body = {
        "message": "PE scans requested successfully",
        "queued": queued,
        "started": started,
        "local": local,
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
        LOGGER.exception("Unhandled error in PE scan controller")
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}

"""Scheduler method containing AWS Lambda handler."""


# Standard Python Libraries
from itertools import islice
import os

# Third-Party Libraries
from django.utils import timezone

from ..helpers.getScanOrganizations import get_scan_organizations
from ..models import Organization, Scan, ScanTask
from ..schema_models.scan import SCAN_SCHEMA
from .ecs_client import ECSClient


def chunk(iterable, size):
    """Chunk a list into a nested list."""
    it = iter(iterable)
    return iter(lambda: list(islice(it, size)), [])


class Scheduler:
    def __init__(self):
        """Initialize."""
        self.ecs = ECSClient()
        self.num_existing_tasks = 0
        self.num_launched_tasks = 0
        self.max_concurrent_tasks = int(os.getenv("FARGATE_MAX_CONCURRENCY", "10"))
        self.scans = []
        self.organizations = []
        self.queued_scan_tasks = []
        self.orgs_per_scan_task = 1

    async def initialize(
        self, scans, organizations, queued_scan_tasks, orgs_per_scan_task
    ):
        """Initialize."""
        self.scans = scans
        self.organizations = organizations
        self.queued_scan_tasks = queued_scan_tasks
        self.orgs_per_scan_task = orgs_per_scan_task
        self.num_existing_tasks = await self.ecs.get_num_tasks()

        print(f"Number of running Fargate tasks: {self.num_existing_tasks}")
        print(f"Number of queued scan tasks: {len(self.queued_scan_tasks)}")

    async def launch_single_scan_task(
        self,
        organizations=None,
        scan=None,
        chunk_number=None,
        num_chunks=None,
        scan_task=None,
    ):
        """Launch single scan."""
        organizations = organizations or []
        scan_schema = SCAN_SCHEMA.get(scan.name, {})
        task_type = getattr(scan_schema, "type", None)
        global_scan = getattr(scan_schema, "global_scan", None)

        scan_task = scan_task or ScanTask.objects.create(
            scanId=scan, type=task_type, status="created"
        )

        # Set the many-to-many relationship with organizations
        if not global_scan:
            scan_task.organizations.set(organizations)

        command_options = scan_task.input or {
            "organizations": [
                {"name": org.name, "id": str(org.id)} for org in organizations
            ],
            "scanId": str(scan.id),
            "scanName": scan.name,
            "scanTaskId": str(scan_task.id),
            "numChunks": num_chunks,
            "chunkNumber": chunk_number,
            "isSingleScan": scan.isSingleScan,
        }

        scan_task.input = command_options

        if self.reached_scan_limit():
            scan_task.status = "queued"
            if not scan_task.queuedAt:
                scan_task.queuedAt = timezone.now()
            print(f"Reached maximum concurrency, queueing scantask {scan_task.id}")
            scan_task.save()
            return

        try:
            if task_type == "fargate":
                result = await self.ecs.run_command(command_options)
                if not result.get("tasks"):
                    print(
                        f"Failed to start Fargate task for scan {scan.name}, failures: {result.get('failures')}"
                    )
                    raise Exception(
                        f"Failed to start Fargate task for scan {scan.name}"
                    )

                task_arn = result["tasks"][0]["taskArn"]
                scan_task.fargateTaskArn = task_arn
                print(
                    f"Successfully invoked scan {scan.name} with Fargate on {len(organizations)} organizations. Task ARN: {task_arn}"
                )
            else:
                raise Exception(f"Invalid task type: {task_type}")

            scan_task.status = "requested"
            scan_task.requestedAt = timezone.now()
            self.num_launched_tasks += 1
        except Exception as error:
            print(f"Error invoking {scan.name} scan: {error}")
            scan_task.output = str(error)
            scan_task.status = "failed"
            scan_task.finishedAt = timezone.now()

        scan_task.save()

    async def launch_scan_task(self, organizations=None, scan=None):
        """Launch scan task."""
        organizations = organizations or []

        scan_schema = SCAN_SCHEMA.get(scan.name, None)
        num_chunks = getattr(scan_schema, "numChunks", None)

        # If num_chunks is set, handle it; otherwise, default to launching a single task
        if num_chunks:
            # For running locally, set num_chunks to 1
            if os.getenv("IS_LOCAL"):
                num_chunks = 1

            # Sanitize num_chunks to ensure it doesn't exceed 100
            num_chunks = min(num_chunks, 100)

            for chunk_number in range(num_chunks):
                await self.launch_single_scan_task(
                    organizations=organizations,
                    scan=scan,
                    chunk_number=chunk_number,
                    num_chunks=num_chunks,
                )
        else:
            # Launch a single scan task when num_chunks is None or 0
            await self.launch_single_scan_task(organizations=organizations, scan=scan)

    def reached_scan_limit(self):
        """Check scan limit."""
        return (
            self.num_existing_tasks + self.num_launched_tasks
        ) >= self.max_concurrent_tasks

    async def run(self):
        """Run scheduler."""
        for scan in self.scans:
            prev_num_launched_tasks = self.num_launched_tasks

            if scan.name not in SCAN_SCHEMA:
                print(f"Invalid scan name: {scan.name}")
                continue

            scan_schema = SCAN_SCHEMA[scan.name]
            if scan_schema.global_scan:
                if not self.should_run_scan(scan):
                    continue
                await self.launch_scan_task(scan=scan)
            else:
                organizations = (
                    get_scan_organizations(scan)
                    if scan.isGranular
                    else self.organizations
                )
                orgs_to_launch = [
                    org
                    for org in organizations
                    if self.should_run_scan(scan=scan, organization=org)
                ]
                for org_chunk in chunk(orgs_to_launch, self.orgs_per_scan_task):
                    await self.launch_scan_task(organizations=org_chunk, scan=scan)

            if self.num_launched_tasks > prev_num_launched_tasks:
                scan.lastRun = timezone.now()
                scan.manualRunPending = False
                scan.save()

    async def run_queued(self):
        """Run queued scans."""
        for scan_task in self.queued_scan_tasks:
            await self.launch_single_scan_task(scan_task=scan_task, scan=scan_task.scan)

    def should_run_scan(self, scan, organization=None):
        """Check if the scan should run."""
        scan_schema = SCAN_SCHEMA.get(scan.name, {})
        is_passive = getattr(scan_schema, "isPassive", False)
        global_scan = getattr(scan_schema, "global_scan", False)

        # Don't run non-passive scans on passive organizations.
        if organization and organization.isPassive and not is_passive:
            return False

        # Always run scans that have manualRunPending set to True.
        if scan.manualRunPending:
            print("Manual run pending")
            return True

        # Function to filter the scan tasks based on whether it's global or organization-specific.
        def filter_scan_tasks(tasks):
            if global_scan:
                return tasks.filter(scanId=scan)
            else:
                return tasks.filter(scanId=scan).filter(
                    organizations=organization
                ) | tasks.filter(organizations__id=organization.id)

        # Check if there's a currently running or queued scan task for the given scan.
        last_running_scan_task = filter_scan_tasks(
            ScanTask.objects.filter(
                status__in=["created", "queued", "requested", "started"]
            ).order_by("-createdAt")
        ).first()

        # If there's a running or queued task, do not run another.
        if last_running_scan_task:
            print("Already running or queued")
            return False

        # Check for the last finished scan task.
        last_finished_scan_task = filter_scan_tasks(
            ScanTask.objects.filter(
                status__in=["finished", "failed"], finishedAt__isnull=False
            ).order_by("-finishedAt")
        ).first()

        # If a scan task was finished recently within the scan frequency, do not run.
        if last_finished_scan_task and last_finished_scan_task.finishedAt:
            print("Has been run since the last scan frequency")
            frequency_seconds = (
                scan.frequency * 1000
            )  # Assuming frequency is in seconds.
            if (
                timezone.now() - last_finished_scan_task.finishedAt
            ).total_seconds() < frequency_seconds:
                return False

        # If the scan is marked as a single scan and has already run once, do not run again.
        if (
            last_finished_scan_task
            and last_finished_scan_task.finishedAt
            and scan.isSingleScan
        ):
            print("Single scan")
            return False

        return True


async def handler(event):
    """Handler for manually invoking the scheduler to run scans."""
    print("Running scheduler...")

    scan_ids = event.get("scanIds", [])
    if "scanId" in event:
        scan_ids.append(event["scanId"])

    org_ids = event.get("organizationIds", [])

    # Fetch scans based on scan_ids if provided
    if scan_ids:
        scans = Scan.objects.filter(id__in=scan_ids).prefetch_related(
            "organizations", "tags"
        )
    else:
        scans = Scan.objects.all().prefetch_related("organizations", "tags")

    # Fetch organizations based on org_ids if provided
    if org_ids:
        organizations = Organization.objects.filter(id__in=org_ids)
    else:
        organizations = Organization.objects.all()

    queued_scan_tasks = (
        ScanTask.objects.filter(scanId__in=scan_ids, status="queued")
        .order_by("queuedAt")
        .select_related("scanId")
    )

    scheduler = Scheduler()
    await scheduler.initialize(
        scans=scans,
        organizations=organizations,
        queued_scan_tasks=queued_scan_tasks,
        orgs_per_scan_task=event.get("orgsPerScanTask")
        or int(os.getenv("SCHEDULER_ORGS_PER_SCANTASK", "1")),
    )

    await scheduler.run_queued()
    await scheduler.run()

    print("Finished running scheduler.")

"""Scheduler method containing AWS Lambda handler."""

# Standard Python Libraries
import json
import os

# Third-Party Libraries
import boto3
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
from xfd_api.helpers.email import _setup_proxy
from xfd_api.helpers.getScanOrganizations import get_scan_organizations
from xfd_api.schema_models.scan import SCAN_SCHEMA
from xfd_api.tasks.scanExecution import handler as scan_execution_handler

# Import Django models and helper functions
from xfd_mini_dl.models import Organization, Scan, ScanTask


class Scheduler:
    """Scheduler for executing scans by managing ScanTask records and invoking execution."""

    def __init__(self):
        """Initialize."""
        self.scans = []
        self.organizations = []

    def initialize(self, scans, organizations):
        """Initialize the scheduler with scans and organizations."""
        self.scans = scans
        self.organizations = organizations

    def launch_scan_execution(self, scan):
        """Prepare and send scan execution request."""
        # If global scan, ignore queue and start 1 concurrent task
        scan_schema = SCAN_SCHEMA.get(scan.name, {})
        global_scan = getattr(scan_schema, "global_scan", False)
        if global_scan:
            print("This is a global scan.")
            if not self.should_run_scan(scan):
                print(
                    "Skipping global scan execution due to recent activity or constraints."
                )
                return
            # Now pass organizations to scanExecution
            event_payload = {
                "scanId": str(scan.id),
                "scanType": scan.name,
                "desiredCount": 1,
                "organizations": [],
                "isPe": False,
            }
            try:
                response = scan_execution_handler(event_payload, None)
                print("scanExecution handler response: {}".format(response))

                # Set manual_run_pending to False since scan is now launched
                scan.manual_run_pending = False
                scan.last_run = timezone.now()
                scan.save()
                print("Updated scan: manual_run_pending set to False")

            except Exception as e:
                print("Error invoking scanExecution: {}".format(e))

            return

        # Get organizations to run on
        orgs = get_scan_organizations(scan) if scan.is_granular else self.organizations
        filtered_orgs = [org for org in orgs if self.should_run_scan(scan, org)]

        if not filtered_orgs:
            print(
                "Skipping scan execution for {} - No organizations to run on.".format(
                    scan.name
                )
            )
            return

        # Prepare scan specific queue
        queue_name = "{}-{}-queue".format(os.getenv("STAGE"), scan.name)
        base_queue_url = os.getenv("QUEUE_URL").rstrip("/")
        is_local = os.getenv("IS_LOCAL")
        sqs = boto3.client(
            "sqs",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=base_queue_url if is_local else None,
        )
        # Create or get queue
        response = sqs.create_queue(
            QueueName=queue_name,
            Attributes={
                "VisibilityTimeout": "18000",
                "MaximumMessageSize": "262144",
                "MessageRetentionPeriod": "604800",
            },
        )
        queue_url = response["QueueUrl"]

        # Check queue URL
        print("Queue URL: {}".format(queue_url))

        # Send organizations to the queue in batches of 10
        batch_size = 10
        org_batches = [
            filtered_orgs[i : i + batch_size]
            for i in range(0, len(filtered_orgs), batch_size)
        ]

        for batch in org_batches:
            entries = [
                {
                    "Id": str(i),  # Unique identifier for the batch request
                    "MessageBody": json.dumps({"org": org.name, "id": str(org.id)}),
                }
                for i, org in enumerate(batch)
            ]

            try:
                resp = sqs.send_message_batch(QueueUrl=queue_url, Entries=entries)
                print("Batch sent successfully")

                # Handle any failed messages
                if "Failed" in resp:
                    for failure in resp["Failed"]:
                        print(
                            "Failed to send message {}: {}".format(
                                failure["Id"], failure["Message"]
                            )
                        )
            except Exception as e:
                print("Error sending message batch: {}".format(e))

        # Now pass organizations to scanExecution
        event_payload = {
            "scanId": str(scan.id),
            "scanType": scan.name,
            "desiredCount": scan.concurrent_tasks,
            "organizations": list(filtered_orgs),
            "isPe": False,
        }
        try:
            response = scan_execution_handler(event_payload, None)
            print("scanExecution handler response: {}".format(response))

            # Set manual_run_pending to False since scan is now launched
            scan.manual_run_pending = False
            scan.last_run = timezone.now()
            scan.save()
            print("Updated scan: manual_run_pending set to False")

        except Exception as e:
            print("Error invoking scanExecution: {}".format(e))

    def should_run_scan(self, scan, organization=None):
        """
        Determine whether the scan should run for a given organization.

        This method uses several criteria:
         1. If manual_run_pending is set, always run.
         2. Check if enough time has passed since the scan last ran (using scan.last_run and frequency).
         3. Check for currently running or recently finished scan tasks.
        """
        scan_schema = SCAN_SCHEMA.get(scan.name, {})
        is_passive = getattr(scan_schema, "is_passive", False)
        global_scan = getattr(scan_schema, "global_scan", False)

        # Don't run non-passive scans on passive organizations.
        if organization and organization.is_passive and not is_passive:
            return False

        # Always run scans that have manual_run_pending set to True.
        if scan.manual_run_pending:
            return True

        # Check if the scan has run recently based on its last_run timestamp.
        if scan.last_run:
            if timezone.is_naive(scan.last_run):
                scan.last_run = timezone.make_aware(
                    scan.last_run, timezone.get_current_timezone()
                )
            # Assuming scan.frequency is expressed in days, convert to seconds.
            frequency_seconds = scan.frequency * 86400
            if (timezone.now() - scan.last_run).total_seconds() < frequency_seconds:
                return False

        def filter_scan_tasks(tasks):
            if global_scan:
                return tasks.filter(scan=scan)
            return tasks.filter(scan=scan).filter(
                organizations=organization
            ) | tasks.filter(organizations__id=organization.id)

        last_running_scan_task = filter_scan_tasks(
            ScanTask.objects.filter(
                status__in=["created", "queued", "requested", "started"]
            ).order_by("-created_at")
        ).first()
        if last_running_scan_task:
            return False

        last_finished_scan_task = filter_scan_tasks(
            ScanTask.objects.filter(
                status__in=["finished", "failed"], finished_at__isnull=False
            ).order_by("-finished_at")
        ).first()
        if last_finished_scan_task and last_finished_scan_task.finished_at:
            frequency_seconds = scan.frequency * 86400
            if timezone.is_naive(last_finished_scan_task.finished_at):
                last_finished_scan_task.finished_at = timezone.make_aware(
                    last_finished_scan_task.finished_at, timezone.get_current_timezone()
                )
            if (
                timezone.now() - last_finished_scan_task.finished_at
            ).total_seconds() < frequency_seconds:
                return False

        if (
            last_finished_scan_task
            and last_finished_scan_task.finished_at
            and scan.is_single_scan
        ):
            print("Single scan")
            return False

        return True

    def run(self):
        """Execute scans based on their configurations."""
        for scan in self.scans:
            if getattr(scan, "concurrent_tasks", 0):
                self.launch_scan_execution(scan)


# -----------------------------------------------------------------------------
# Lambda Handler
# -----------------------------------------------------------------------------
def handler(event, context):
    """Handle invoking the scheduler to run scans."""
    print("Running scheduler...")

    _setup_proxy()  # Setup proxy if LZ_PROXY_URL is defined

    scan_ids = event.get("scanIds", [])
    if "scanId" in event:
        scan_ids.append(event["scanId"])

    org_ids = event.get("organizationIds", [])

    # Fetch scans based on scan_ids if provided. Else, get all scans.
    if scan_ids:
        scans = Scan.objects.filter(id__in=scan_ids).prefetch_related(
            "organizations", "tags"
        )
    else:
        scans = Scan.objects.all().prefetch_related("organizations", "tags")

    # Fetch organizations based on org_ids if provided; otherwise, all organizations.
    if org_ids:
        organizations = Organization.objects.filter(id__in=org_ids)
    else:
        organizations = Organization.objects.all()

    scheduler = Scheduler()
    scheduler.initialize(scans, organizations)
    scheduler.run()

    print("Finished running scheduler.")

"""API methods to support scan task endpoints."""

# Standard Python Libraries
from datetime import datetime, timezone
import logging
from typing import Optional

# Third-Party Libraries
from fastapi import HTTPException, Response, status
from xfd_mini_dl.models import ScanTask

from ..auth import get_tag_organizations, is_global_view_admin, is_global_write_admin
from ..schema_models.scan_tasks import ScanTaskSearch
from ..tasks.ecs_client import ECSClient

PAGE_SIZE = 15

# Configure logging
LOGGER = logging.getLogger(__name__)


# POST: /scan-tasks/search
def list_scan_tasks(search_data: Optional[ScanTaskSearch], current_user):
    """List scans tasks based on search filter."""
    try:
        # Check if the user is a GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Unauthorized access. View logs for details."
            )

        # Ensure that search_data is not None, and set default values if it is
        if search_data is None:
            search_data = ScanTaskSearch(
                page_size=PAGE_SIZE, page=1, sort="created_at", order="DESC", filters={}
            )

        # Validate and parse the request body
        page_size = search_data.page_size or PAGE_SIZE
        page = search_data.page or 1

        # Determine the correct ordering based on the 'order' field
        ordering_field = (
            "-{}".format(search_data.sort)
            if search_data.order and search_data.order.upper() == "DESC"
            else "{}".format(search_data.sort)
        )

        # Construct query based on filters
        qs = (
            ScanTask.objects.select_related("scan")
            .prefetch_related("organizations")
            .order_by(ordering_field)
        )

        # Apply filters to queryset safely
        filters = search_data.filters
        if filters:
            if filters.get("name"):
                qs = qs.filter(scan__name__icontains=filters["name"])
            if filters.get("status"):
                qs = qs.filter(status__icontains=filters["status"])
            if filters.get("organization"):
                qs = qs.filter(organizations__id=filters["organization"])
            if filters.get("tag"):
                orgs = get_tag_organizations(current_user, filters["tag"])
                qs = qs.filter(organizations__id__in=orgs)

        # Paginate results
        if page_size != -1:
            qs = qs[(page - 1) * page_size : page * page_size]

        # Convert queryset into a serialized response
        results = []
        for task in qs:
            # Ensure scan is not None before accessing its properties
            if task.scan is None:
                LOGGER.warning("ScanTask %s has no scan associated.", task.id)
                scan_data = None
            else:
                scan_data = {
                    "id": str(task.scan.id),
                    "created_at": task.scan.created_at.isoformat(),
                    "updated_at": task.scan.updated_at.isoformat(),
                    "name": task.scan.name,
                    "arguments": task.scan.arguments,
                    "frequency": task.scan.frequency,
                    "last_run": task.scan.last_run.isoformat()
                    if task.scan.last_run
                    else None,
                    "is_granular": task.scan.is_granular,
                    "is_user_modifiable": task.scan.is_user_modifiable,
                    "is_single_scan": task.scan.is_single_scan,
                    "manual_run_pending": task.scan.manual_run_pending,
                    "concurrent_tasks": task.scan.concurrent_tasks,
                    "total_orgs": task.scan.total_orgs,
                }
            results.append(
                {
                    "id": str(task.id),
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "status": task.status,
                    "type": task.type,
                    "fargate_task_arn": task.fargate_task_arn,
                    "input": (
                        task.input.replace("None", "null")
                        .replace("True", "true")
                        .replace("False", "false")
                        .replace("'", '"')
                        if task.input is not None
                        else "null"  # Default to "null" if task.input is None
                    ),
                    "output": task.output,
                    "requested_at": task.requested_at.isoformat()
                    if task.requested_at
                    else None,
                    "started_at": task.started_at.isoformat()
                    if task.started_at
                    else None,
                    "finished_at": task.finished_at.isoformat()
                    if task.finished_at
                    else None,
                    "queued_at": task.queued_at.isoformat() if task.queued_at else None,
                    "concurrency_index": task.concurrency_index,
                    "scan": scan_data,
                    "organizations": [
                        {
                            "id": str(org.id),
                            "created_at": org.created_at.isoformat(),
                            "updated_at": org.updated_at.isoformat(),
                            "acronym": org.acronym,
                            "name": org.name,
                            "root_domains": org.root_domains,
                            "ip_blocks": org.ip_blocks,
                            "is_passive": org.is_passive,
                            "pending_domains": org.pending_domains,
                            "country": org.country,
                            "state": org.state,
                            "region_id": org.region_id,
                            "state_fips": org.state_fips,
                            "state_name": org.state_name,
                            "county": org.county,
                            "county_fips": org.county_fips,
                            "type": org.type,
                        }
                        for org in task.organizations.all()
                    ],
                }
            )

        count = qs.count()
        response = {"result": results, "count": count}
        return response

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /scan-tasks/{scan_task_id}/kill
def kill_scan_task(scan_task_id, current_user):
    """Kill a particular scan task."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Unauthorized access. View logs for details."
            )
        # Check if scan_task_id is valid
        try:
            scan_task = ScanTask.objects.get(id=scan_task_id)
        except ScanTask.DoesNotExist:
            raise HTTPException(status_code=404, detail="ScanTask not found.")

        # Check if scan task is already finished or failed
        if scan_task.status in ["failed", "finished"]:
            raise HTTPException(
                status_code=400, detail="ScanTask has already finished."
            )

        # Update scan task status to 'failed'
        utc_now = datetime.now(timezone.utc)
        scan_task.status = "failed"
        scan_task.finished_at = utc_now
        scan_task.output = "Manually stopped at {}".format(utc_now.isoformat())
        scan_task.save()

        return {"statusCode": 200, "message": "ScanTask successfully marked as failed."}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# GET: /scan-tasks/{scan_task_id}/logs
def get_scan_task_logs(scan_task_id, current_user):
    """Get scan task logs."""
    try:
        # Check if the user is a GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Unauthorized access. View logs for details."
            )

        # Check if scan_task_id is valid
        try:
            scan_task = ScanTask.objects.get(id=scan_task_id)
        except ScanTask.DoesNotExist:
            raise HTTPException(status_code=404, detail="ScanTask not found.")

        # Ensure fargateTaskArn exists
        if not scan_task.fargate_task_arn:
            raise HTTPException(
                status_code=404, detail="No logs available for this ScanTask."
            )

        # Retrieve logs from the ECSClient
        ecs_client = ECSClient()
        logs = ecs_client.get_logs(scan_task.fargate_task_arn)

        return Response(
            content=logs or "", media_type="text/plain", status_code=status.HTTP_200_OK
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

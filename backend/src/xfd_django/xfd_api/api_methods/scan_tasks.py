"""API methods to support scan task endpoints."""

# Standard Python Libraries
from datetime import datetime, timezone

# Third-Party Libraries
from fastapi import HTTPException, Response, status

from ..auth import is_global_view_admin, is_global_write_admin, get_tag_organizations
from ..models import ScanTask
from ..schema_models.scan_tasks import ScanTaskSearch
from ..tasks.ecs_client import ECSClient


PAGE_SIZE = 15;

def list_scan_tasks(search_data: ScanTaskSearch, current_user):
    """List scans tasks based on search filter."""
    try:
        # Check if the user is a GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Unauthorized access. View logs for details."
        )

        # Validate and parse the request body
        pageSize = search_data.pageSize or PAGE_SIZE

        # Determine the correct ordering based on the 'order' field
        ordering_field = f"-{search_data.sort}" if search_data.order.upper() == "DESC" else search_data.sort
        
        # Construct query based on filters
        qs = ScanTask.objects.select_related("scanId").prefetch_related("organizations").order_by(ordering_field)

        # Apply filters to queryset safely
        filters = search_data.filters
        if filters:
            if filters.get("name"):
                qs = qs.filter(scanId__name__icontains=filters["name"])
            if filters.get("status"):
                qs = qs.filter(status__icontains=filters["status"])
            if filters.get("organization"):
                qs = qs.filter(organizations__id=filters["organization"])
            if filters.get("tag"):
                print("We are in tags")
                orgs = get_tag_organizations(current_user, filters["tag"])
                print(orgs)
                qs = qs.filter(organizations__id__in=orgs)
                print(qs)

        # Paginate results
        if pageSize != -1:
            qs = qs[(search_data.page - 1) * pageSize: search_data.page * pageSize]

        # Convert queryset into a serialized response
        results = []
        for task in qs:
            # Ensure scanId is not None before accessing its properties
            if task.scanId is None:
                print(f"Warning: ScanTask {task.id} has no scanId associated.")
                scan_data = None  # or some default values, depending on how you want to handle this case
            else:
                scan_data = {
                    "id": str(task.scanId.id),
                    "createdAt": task.scanId.createdAt.isoformat() + 'Z',
                    "updatedAt": task.scanId.updatedAt.isoformat() + 'Z',
                    "name": task.scanId.name,
                    "arguments": task.scanId.arguments,
                    "frequency": task.scanId.frequency,
                    "lastRun": task.scanId.lastRun.isoformat() + 'Z' if task.scanId.lastRun else None,
                    "isGranular": task.scanId.isGranular,
                    "isUserModifiable": task.scanId.isUserModifiable,
                    "isSingleScan": task.scanId.isSingleScan,
                    "manualRunPending": task.scanId.manualRunPending
                }
            results.append({
                "id": str(task.id),
                "createdAt": task.createdAt.isoformat() + 'Z',
                "updatedAt": task.updatedAt.isoformat() + 'Z',
                "status": task.status,
                "type": task.type,
                "fargateTaskArn": task.fargateTaskArn,
                "input": task.input,
                "output": task.output,
                "requestedAt": task.requestedAt.isoformat() + 'Z' if task.requestedAt else None,
                "startedAt": task.startedAt.isoformat() + 'Z' if task.startedAt else None,
                "finishedAt": task.finishedAt.isoformat() + 'Z' if task.finishedAt else None,
                "queuedAt": task.queuedAt.isoformat() + 'Z' if task.queuedAt else None,
                "scan": scan_data,
                "organizations": [
                    {
                        "id": str(org.id),
                        "createdAt": org.createdAt.isoformat() + 'Z',
                        "updatedAt": org.updatedAt.isoformat() + 'Z',
                        "acronym": org.acronym,
                        "name": org.name,
                        "rootDomains": org.rootDomains,
                        "ipBlocks": org.ipBlocks,
                        "isPassive": org.isPassive,
                        "pendingDomains": org.pendingDomains,
                        "country": org.country,
                        "state": org.state,
                        "regionId": org.regionId,
                        "stateFips": org.stateFips,
                        "stateName": org.stateName,
                        "county": org.county,
                        "countyFips": org.countyFips,
                        "type": org.type
                    }
                    for org in task.organizations.all()
                ]
            })

        count = qs.count()
        response = {"result": results, "count": count}

        return response

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
        


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
        if scan_task.status in ['failed', 'finished']:
            raise HTTPException(status_code=400, detail="ScanTask has already finished.")

        # Update scan task status to 'failed'
        utc_now = datetime.now(timezone.utc)
        scan_task.status = 'failed'
        scan_task.finishedAt = utc_now
        scan_task.output = f"Manually stopped at {utc_now.isoformat()}"
        scan_task.save()

        return {"statusCode": 200, "message": "ScanTask successfully marked as failed."}
        
    
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    

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
        if not scan_task.fargateTaskArn:
            raise HTTPException(status_code=404, detail="No logs available for this ScanTask.")

        # Retrieve logs from the ECSClient
        ecs_client = ECSClient()
        logs = ecs_client.get_logs(scan_task.fargateTaskArn)

        return Response(content=logs or '', status_code=status.HTTP_200_OK)
        
    
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
        
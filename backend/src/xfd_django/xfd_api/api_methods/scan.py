"""API methods to support Scan endpoints."""

# Standard Python Libraries
import logging
import os

# Third-Party Libraries
from fastapi import HTTPException, status
from xfd_mini_dl.models import Organization, OrganizationTag, Scan

from ..auth import is_global_view_admin, is_global_write_admin
from ..schema_models.scan import SCAN_SCHEMA, NewScan
from ..tasks.lambda_client import LambdaClient

# Configure logging
LOGGER = logging.getLogger(__name__)


# GET: /scans
def list_scans(current_user):
    """List scans."""
    try:
        # Check if the user is a GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Fetch scans and prefetch related tags
        scans = Scan.objects.prefetch_related("tags").all()

        # Fetch all organizations
        organizations = Organization.objects.values("id", "name")

        # Convert to list of dicts with related tags
        scan_list = []
        for scan in scans:
            scan_data = {
                "id": scan.id,
                "created_at": scan.created_at,
                "updated_at": scan.updated_at,
                "name": scan.name,
                "arguments": scan.arguments,
                "frequency": scan.frequency,
                "last_run": scan.last_run,
                "is_granular": scan.is_granular,
                "is_user_modifiable": scan.is_user_modifiable,
                "is_single_scan": scan.is_single_scan,
                "manual_run_pending": scan.manual_run_pending,
                "concurrent_tasks": scan.concurrent_tasks,
                "tags": [
                    {
                        "id": tag.id,
                        "created_at": tag.created_at,
                        "updated_at": tag.updated_at,
                        "name": tag.name,
                    }
                    for tag in scan.tags.all()
                ],
            }
            scan_list.append(scan_data)

        # Return response with scans, schema, and organizations
        response = {
            "scans": scan_list,
            "schema": SCAN_SCHEMA,
            "organizations": list(organizations),
        }

        return response

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET: /granularScans
def list_granular_scans(current_user):
    """List granular scans."""
    try:
        # Check if the user is a GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Fetch scans that match the criteria (isGranular, isUserModifiable, isSingleScan)
        scans = Scan.objects.filter(
            is_granular=True, is_user_modifiable=True, is_single_scan=False
        ).values("id", "name", "is_user_modifiable")

        response = {"scans": list(scans), "schema": SCAN_SCHEMA}

        return response

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST: /scans
def create_scan(scan_data: NewScan, current_user):
    """Create a new scan."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Check if scan name is valid
        if scan_data.name not in SCAN_SCHEMA:
            raise HTTPException(status_code=400, detail="Invalid scan name")

        max_tasks = SCAN_SCHEMA[scan_data.name].max_concurrent_tasks
        if scan_data.concurrent_tasks is None:
            raise HTTPException(
                status_code=400, detail="Concurrent tasks must be provided."
            )
        if max_tasks is None:
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: max concurrent tasks not set.",
            )

        if scan_data.concurrent_tasks > max_tasks:
            raise HTTPException(
                status_code=400,
                detail="Number of concurrent tasks exceeds the max for this scan.",
            )

        # Create the scan instance
        scan_data_dict = scan_data.dict(
            exclude_unset=True, exclude={"organizations", "tags"}
        )
        scan_data_dict["created_by"] = current_user

        # Create the scan object
        scan = Scan.objects.create(**scan_data_dict)

        # Link organizations
        if scan_data.organizations:
            scan.organizations.set(scan_data.organizations)

        # Link tags
        if scan_data.tags:
            tag_ids = [tag.id for tag in scan_data.tags]
            scan.tags.set(tag_ids)

        return {
            "id": scan.id,
            "name": scan.name,
            "arguments": scan.arguments,
            "frequency": scan.frequency,
            "is_granular": scan.is_granular,
            "is_user_modifiable": scan.is_user_modifiable,
            "is_single_scan": scan.is_single_scan,
            "concurrent_tasks": scan.concurrent_tasks,
            "created_by": {"id": current_user.id, "name": current_user.full_name},
            "tags": list(scan.tags.values("id")),
            "organizations": list(scan.organizations.values("id")),
        }

    except HTTPException as http_exc:
        raise http_exc
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found")
    except OrganizationTag.DoesNotExist:
        raise HTTPException(status_code=404, detail="Tag not found")
    except Exception as e:
        LOGGER.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# GET: /scans/{scan_id}
def get_scan(scan_id: str, current_user):
    """Get a scan by its ID."""
    # Check if the user is a GlobalViewAdmin
    if not is_global_view_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    try:
        # Fetch the scan with its related organizations and tags
        scan = Scan.objects.prefetch_related("organizations", "tags").get(id=scan_id)

        # Fetch all organizations
        all_organizations = Organization.objects.values("id", "name")
    except Scan.DoesNotExist:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Get related organizations with all fields and remove unwanted fields
    related_organizations = list(scan.organizations.values())
    for org in related_organizations:
        org.pop("parent_id", None)
        org.pop("created_by_id", None)

    # Serialize scan data
    scan_data = {
        "id": str(scan.id),
        "created_at": scan.created_at,
        "updated_at": scan.updated_at,
        "name": scan.name,
        "arguments": scan.arguments,
        "last_run": scan.last_run,
        "frequency": scan.frequency,
        "is_granular": scan.is_granular,
        "is_user_modifiable": scan.is_user_modifiable,
        "is_single_scan": scan.is_single_scan,
        "manual_run_pending": scan.manual_run_pending,
        "organizations": related_organizations,
        "tags": list(scan.tags.values()),
        "concurrent_tasks": scan.concurrent_tasks,
    }

    # Return the scan details along with its related data
    return {
        "scan": scan_data,
        "schema": dict(SCAN_SCHEMA[scan.name]),
        "organizations": list(all_organizations),
    }


# POST: /update_scan/{scan_id}
def update_scan(scan_id: str, scan_data: NewScan, current_user):
    """Update a scan by its ID."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Validate scan ID
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            raise HTTPException(status_code=404, detail="Scan not found")

        # Only update the fields that are provided in the request (non-null)
        if scan_data.name is not None:
            scan.name = scan_data.name
        if scan_data.arguments is not None:
            scan.arguments = scan_data.arguments
        if scan_data.frequency is not None:
            scan.frequency = scan_data.frequency
        if scan_data.is_granular is not None:
            scan.is_granular = scan_data.is_granular
        if scan_data.is_user_modifiable is not None:
            scan.is_user_modifiable = scan_data.is_user_modifiable
        if scan_data.is_single_scan is not None:
            scan.is_single_scan = scan_data.is_single_scan

        # Update ManyToMany relationships
        if scan_data.organizations:
            scan.organizations.set(scan_data.organizations)

        if scan_data.tags:
            tag_ids = [tag.id for tag in scan_data.tags]
            scan.tags.set(tag_ids)

        # Save the updated scan
        scan.save()

        return {
            "id": scan.id,
            "name": scan.name,
            "arguments": scan.arguments,
            "frequency": scan.frequency,
            "is_granular": scan.is_granular,
            "is_user_modifiable": scan.is_user_modifiable,
            "is_single_scan": scan.is_single_scan,
            "created_by": {"id": current_user.id, "name": current_user.full_name},
            "tags": list(scan.tags.values("id")),
            "organizations": list(scan.organizations.values("id")),
            "concurrent_tasks": scan.concurrent_tasks,
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# DELETE: /scans/{scan_id}
def delete_scan(scan_id: str, current_user):
    """Delete a scan by its ID."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Validate scan ID
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            raise HTTPException(status_code=404, detail="Scan not found")

        scan.delete()

        return {
            "status": "success",
            "message": "Scan {} deleted successfully.".format(scan_id),
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST: /scans/{scan_id}/run
def run_scan(scan_id: str, current_user):
    """Mark a scan as manually triggered to run."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Validate the scan ID and check if it exists
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            raise HTTPException(status_code=404, detail="Scan not found")

        scan.manual_run_pending = True
        scan.save()
        return {
            "status": "success",
            "message": "Scan {} set to manualRunPending.".format(scan_id),
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST: /scheduler/invoke
async def invoke_scheduler(current_user):
    """Manually invoke the scan scheduler."""
    try:
        # TODO: RUN THIS ON A SCHEDULE LOCALLY LIKE DEFINED IN APP.TS
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Initialize the Lambda client
        lambda_client = LambdaClient()

        # Form the lambda function name using environment variable
        lambda_function_name = "{}-scheduler".format(os.getenv("SLS_LAMBDA_PREFIX"))
        LOGGER.info("Invoking Lambda function: %s", lambda_function_name)

        # Run the Lambda command
        response = lambda_client.run_command(name=lambda_function_name)

        return response

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.exception("Error invoking scheduler: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""API methods to support Scan enpoints."""

# cisagov Libraries
from ..auth import is_global_write_admin, is_global_view_admin
from ..models import Scan, Organization, OrganizationTag
from ..schemas import SCAN_SCHEMA, NewScan
from ..tasks.lambda_client import LambdaClient

# Standard Python Libraries
import os

# Third-Party Libraries
from fastapi import HTTPException


def list_scans(current_user):
    """List scans."""
    try:
        # Check if the user is a GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access. View logs for details.")

        # Fetch scans and prefetch related tags
        scans = Scan.objects.prefetch_related('tags').all()

        # Fetch all organizations
        organizations = Organization.objects.values('id', 'name')

        # Convert to list of dicts with related tags
        scan_list = []
        for scan in scans:
            scan_data = {
                'id': scan.id,
                'createdAt': scan.createdAt,
                'updatedAt': scan.updatedAt,
                'name': scan.name,
                'arguments': scan.arguments,
                'frequency': scan.frequency,
                'lastRun': scan.lastRun,
                'isGranular': scan.isGranular,
                'isUserModifiable': scan.isUserModifiable,
                'isSingleScan': scan.isSingleScan,
                'manualRunPending': scan.manualRunPending,
                'tags': [
                    {
                        'id': tag.id,
                        'createdAt': tag.createdAt,
                        'updatedAt': tag.updatedAt,
                        'name': tag.name
                    } for tag in scan.tags.all()
                ]
            }
            scan_list.append(scan_data)

        # Return response with scans, schema, and organizations
        response = {
            'scans': scan_list,
            'schema': SCAN_SCHEMA,
            'organizations': list(organizations)
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def list_granular_scans(current_user):
    """List granular scans."""
    try:
        # Check if the user is a GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access. View logs for details.")
        
        # Fetch scans that match the criteria (isGranular, isUserModifiable, isSingleScan)
        scans = Scan.objects.filter(
            isGranular=True,
            isUserModifiable=True,
            isSingleScan=False
        ).values('id', 'name', 'isUserModifiable')

        response = {
            'scans': list(scans),
            'schema': SCAN_SCHEMA
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_scan(scan_data: NewScan, current_user):
    """Create a new scan."""
    try:

        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access. View logs for details.")
        
        # Check if scan name is valid
        if scan_data.name not in SCAN_SCHEMA:
            raise HTTPException(status_code=400, detail="Invalid scan name")
        
        # Create the scan instance
        scan_data_dict = scan_data.dict(exclude_unset=True, exclude={"organizations", "tags"})
        scan_data_dict['createdBy'] = current_user
        print(scan_data_dict)

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
            'name': scan.name,
            'arguments': scan.arguments,
            'frequency': scan.frequency,
            'isGranular': scan.isGranular,
            'isUserModifiable': scan.isUserModifiable,
            'isSingleScan': scan.isSingleScan,
            'createdBy': {
                'id': current_user.id,
                'name': current_user.fullName
            },
            'tags': list(scan.tags.values('id')),
            'organizations': list(scan.organizations.values('id')),
        }
    
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found")
    except OrganizationTag.DoesNotExist:
        raise HTTPException(status_code=404, detail="Tag not found")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    


def get_scan(scan_id: str, current_user):
    """Get a scan by its ID. """

    # Check if the user is a GlobalViewAdmin
    if not is_global_view_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized access. View logs for details.")
    
    try:
        # Fetch the scan with its related organizations and tags
        scan = Scan.objects.prefetch_related('organizations', 'tags').get(id=scan_id)

        # Fetch all organizations
        all_organizations = Organization.objects.values('id', 'name')
    except Scan.DoesNotExist:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Get related organizations with all fields and remove unwanted fields
    related_organizations = list(scan.organizations.values())
    for org in related_organizations:
        org.pop('parentId_id', None)
        org.pop('createdById_id', None)

    # Serialize scan data
    scan_data = {
        'id': str(scan.id),
        'createdAt': scan.createdAt,
        'updatedAt': scan.updatedAt,
        'name': scan.name,
        'arguments': scan.arguments,
        'lastRun': scan.lastRun,
        'frequency': scan.frequency,
        'isGranular': scan.isGranular,
        'isUserModifiable': scan.isUserModifiable,
        'isSingleScan': scan.isSingleScan,
        'manualRunPending': scan.manualRunPending,
        'organizations': related_organizations,
        'tags': list(scan.tags.values())
    }

    # Return the scan details along with its related data
    return {
        'scan': scan_data,
        'schema': dict(SCAN_SCHEMA[scan.name]),
        'organizations': list(all_organizations)
    }



def update_scan(scan_id: str, scan_data: NewScan, current_user):
    """Update a scan by its ID."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access. View logs for details.")
        
        # Validate scan ID
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Update the scan's fields with the new data
        scan.name = scan_data.name
        scan.arguments = scan_data.arguments
        scan.frequency = scan_data.frequency
        scan.isGranular = scan_data.isGranular
        scan.isUserModifiable = scan_data.isUserModifiable
        scan.isSingleScan = scan_data.isSingleScan

        # Update ManyToMany relationships
        if scan_data.organizations:
            scan.organizations.set(scan_data.organizations)

        if scan_data.tags:
            tag_ids = [tag.id for tag in scan_data.tags]
            scan.tags.set(tag_ids)
    
        # Save the updated scan
        scan.save()

        return {
            'name': scan.name,
            'arguments': scan.arguments,
            'frequency': scan.frequency,
            'isGranular': scan.isGranular,
            'isUserModifiable': scan.isUserModifiable,
            'isSingleScan': scan.isSingleScan,
            'createdBy': {
                'id': current_user.id,
                'name': current_user.fullName
            },
            'tags': list(scan.tags.values('id')),
            'organizations': list(scan.organizations.values('id')),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def delete_scan(scan_id: str, current_user):
    """Delete a scan by its ID."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access. View logs for details.")
        
        # Validate scan ID
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        scan.delete()

        return {"status": "success", "message": f"Scan {scan_id} deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_scan(scan_id: str, current_user):
    """Mark a scan as manually triggered to run."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access. View logs for details.")
        
        # Validate the scan ID and check if it exists
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        scan.manualRunPending = True
        scan.save()
        return {"status": "success", "message": f"Scan {scan_id} deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def invoke_scheduler(current_user):
    """Manually invoke the scan scheduler."""
    try:
        #TODO: RUN THIS ON A SCHEDULE LOCALLY LIKE DEFINED IN APP.TS
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")
        
        # Initialize the Lambda client
        lambda_client = LambdaClient()

        # Form the lambda function name using environment variable
        lambda_function_name = f"{os.getenv('SLS_LAMBDA_PREFIX')}-scheduler"
        print(lambda_function_name)

        # Run the Lambda command
        response = await lambda_client.run_command(name=lambda_function_name)

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

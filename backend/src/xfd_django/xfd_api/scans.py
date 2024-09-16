from .models import Scan, Organization, OrganizationTag, ScanTagsOrganizationTag, ScanOrganizationsOrganization
from .schemas import ScanSchema
from django.db import transaction
from fastapi import HTTPException
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.core.serializers.json import DjangoJSONEncoder


SCAN_SCHEMA = {
    "amass": ScanSchema(
        type="fargate",
        isPassive=False,
        global_scan=False,
        description="Open source tool that integrates passive APIs and active subdomain enumeration in order to discover target subdomains",
    ),
    "censys": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        description="Passive discovery of subdomains from public certificates",
    ),
    "censysCertificates": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        cpu="2048",
        memory="6144",
        numChunks=20,
        description="Fetch TLS certificate data from censys certificates dataset",
    ),
    "censysIpv4": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        cpu="2048",
        memory="6144",
        numChunks=20,
        description="Fetch passive port and banner data from censys ipv4 dataset",
    ),
    "cve": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Matches detected software versions to CVEs from NIST NVD and CISA's Known Exploited Vulnerabilities Catalog.",
    ),
    "vulnScanningSync": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in vulnerability data from VSs Vulnerability database",
    ),
    "cveSync": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Matches detected software versions to CVEs from NIST NVD and CISA's Known Exploited Vulnerabilities Catalog.",
    ),
    "dnstwist": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        cpu="2048",
        memory="16384",
        description="Domain name permutation engine for detecting similar registered domains.",
    ),
    "dotgov": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        description='Create organizations based on root domains from the dotgov registrar dataset. All organizations are created with the "dotgov" tag and have a " (dotgov)" suffix added to their name.',
    ),
    "findomain": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        description="Open source tool that integrates passive APIs in order to discover target subdomains",
    ),
    "hibp": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        cpu="2048",
        memory="16384",
        description="Finds emails that have appeared in breaches related to a given domain",
    ),
    "intrigueIdent": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        cpu="1024",
        memory="4096",
        description="Open source tool that fingerprints web technologies based on HTTP responses",
    ),
    "lookingGlass": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        description="Finds vulnerabilities and malware from the LookingGlass API",
    ),
    "portscanner": ScanSchema(
        type="fargate",
        isPassive=False,
        global_scan=False,
        description="Active port scan of common ports",
    ),
    "rootDomainSync": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        description="Creates domains from root domains by doing a single DNS lookup for each root domain.",
    ),
    "rscSync": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        description="Retrieves and saves assessments from ReadySetCyber mission instance.",
    ),
    "savedSearch": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        description="Performs saved searches to update their search results",
    ),
    "searchSync": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        cpu="1024",
        memory="4096",
        description="Syncs records with Elasticsearch so that they appear in search results.",
    ),
    "shodan": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Fetch passive port, banner, and vulnerability data from shodan",
    ),
    "sslyze": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        description="SSL certificate inspection",
    ),
    "test": ScanSchema(
        type="fargate",
        isPassive=False,
        global_scan=True,
        description="Not a real scan, used to test",
    ),
    "trustymail": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        description="Evaluates SPF/DMARC records and checks MX records for STARTTLS support",
    ),
    "vulnSync": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in vulnerability data from PEs Vulnerability database",
    ),
    "wappalyzer": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=False,
        cpu="1024",
        memory="4096",
        description="Open source tool that fingerprints web technologies based on HTTP responses",
    ),
    "xpanseSync": ScanSchema(
        type="fargate",
        isPassive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in xpanse vulnerability data from PEs Vulnerability database",
    ),
}


def list_scans():
    """List scans."""
    try:
        # Fetch scans
        scans = Scan.objects.all().values()

        # Convert scans and related tags to dict format
        scan_list = []
        for scan in scans:
            related_tags = OrganizationTag.objects.filter(
                scantagsorganizationtag__scanId=scan['id']
            ).values()

            # Add tags to each scan
            scan['tags'] = list(related_tags)
            scan_list.append(scan)

        # Fetch all organizations
        organizations = list(Organization.objects.values('id', 'name'))

        # Return everything as a JSON response
        response = {
            'scans': scan_list,
            'schema': SCAN_SCHEMA,  # Add your predefined SCAN_SCHEMA here
            'organizations': organizations
        }
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def list_granular_scans():
    """
    List all granular scans that can be modified by users.
    """
    try:
        scans = Scan.objects.filter(
            isGranular=True, isUserModifiable=True, isSingleScan=False
        )
        return {"scans": list(scans), 'schema': SCAN_SCHEMA}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_scan(scan_data: Scan, current_user):
    """
    Create a new scan.
    """
    try:
        # Create the scan instance using **scan_data.dict()
        scan_data_dict = scan_data.dict(exclude_unset=True, exclude={"organizations", "frequencyUnit", "tags"})
        scan_data_dict['createdBy'] = current_user
        print(scan_data_dict)
        
        # Create scan using the dictionary unpacking
        scan = Scan.objects.create(**scan_data_dict)

        print("added Scan")
        print(scan)
        # Link organizations
        if scan_data.organizations:
            for org_id in scan_data.organizations:
                organization, created = Organization.objects.get_or_create(id=org_id)
                print(f"Linked Organization {organization}")
                ScanOrganizationsOrganization.objects.create(
                    scanId=scan,
                    organizationId=organization
                )
        
        # Link tags
        if scan_data.tags:
            for tag_data in scan_data.tags:
                tag, created = OrganizationTag.objects.get_or_create(id=tag_data.id)
                print(f"Linked Tag {tag}")
                ScanTagsOrganizationTag.objects.create(
                    scanId=scan,
                    organizationTagId=tag
                )

        # Return the saved scan
        return scan
    
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found")
    except OrganizationTag.DoesNotExist:
        raise HTTPException(status_code=404, detail="Tag not found")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    


def get_scan(scan_id: str):
    """
    Retrieve a scan by its ID.

    Parameters:
    - scan_id: The ID of the scan to retrieve.

    Returns:
    - The scan object with the specified ID.
    """
    try:
        scan = Scan.objects.get(id=scan_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        return scan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def update_scan(scan_id: str, scan_data: Scan):
    """
    Update a scan by its ID.

    Parameters:
    - scan_id: The ID of the scan to update.
    - scan_data: The new data to update the scan with.

    Returns:
    - The updated scan object.
    """
    try:
        scan = Scan.objects.get(id=scan_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        for key, value in scan_data.dict().items():
            setattr(scan, key, value)
        scan.save()
        return scan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def delete_scan(scan_id: str):
    """
    Delete a scan by its ID.

    Parameters:
    - scan_id: The ID of the scan to delete.

    Returns:
    - A message confirming the deletion.
    """
    try:
        scan = Scan.objects.get(id=scan_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        scan.delete()
        return {"message": "Scan deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_scan(scan_id: str):
    """
    Mark a scan as manually triggered to run.

    Parameters:
    - scan_id: The ID of the scan to run.

    Returns:
    - A message confirming that the scan has been triggered.
    """
    try:
        scan = Scan.objects.get(id=scan_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        scan.manualRunPending = True
        scan.save()
        return {"message": "Scan manually run"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def invoke_scheduler():
    """
    Manually invoke the scan scheduler.

    Returns:
    - A message confirming that the scheduler has been invoked.
    """
    try:
        # Implement logic to invoke the scheduler manually
        # This could be an external service call or AWS Lambda invocation
        return {"message": "Scheduler invoked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

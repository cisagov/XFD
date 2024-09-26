"""Schemas to support Scan endpoints."""

# cisagov Libraries
from .organization_tag import OrganizationalTags
from.organization import Organization

# Standard Python Libraries
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

class Scan(BaseModel):
    """Scan schema reflecting model."""
    id: UUID
    createdAt: datetime
    updatedAt: datetime
    name: str
    arguments: Any
    frequency: int
    lastRun: Optional[datetime]
    isGranular: bool
    isUserModifiable: Optional[bool]
    isSingleScan: bool
    manualRunPending: bool
    tags: Optional[List[OrganizationalTags]] = []
    organizations: Optional[List[Organization]] = []

class ScanSchema(BaseModel):
    """Scan type schema."""
    
    type: str = 'fargate' # Only 'fargate' is supported
    description: str

    # Whether scan is passive (not allowed to hit the domain).
    isPassive: bool

    # Whether scan is global. Global scans run once for all organizations, as opposed
    # to non-global scans, which are run for each organization.
    global_scan: bool

    # CPU and memory for the scan. See this page for more information:
    # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html
    cpu: Optional[str] = None
    memory: Optional[str] = None

    # A scan is "chunked" if its work is divided and run in parallel by multiple workers.
    # To make a scan chunked, make sure it is a global scan and specify the "numChunks" variable,
    # which corresponds to the number of workers that will be created to run the task.
    # Chunked scans can only be run on scans whose implementation takes into account the
    # chunkNumber and numChunks parameters specified in commandOptions.
    numChunks: Optional[int] = None

class GranularScan(BaseModel):
    """Granular scan model."""
    id: UUID
    name: str
    isUserModifiable: Optional[bool]

class GetScansResponseModel(BaseModel):
    """Get Scans response model."""
    scans: List[Scan]
    schema: Dict[str, Any]
    organizations: List[Dict[str, Any]]

class GetGranularScansResponseModel(BaseModel):
    """Get Scans response model."""
    scans: List[GranularScan]
    schema: Dict[str, Any]

class IdSchema(BaseModel):
    """Schema for ID objects."""
    id: UUID

class NewScan(BaseModel):
    """Create Scan Schema."""
    name: str
    arguments: Any
    organizations: Optional[List[UUID]]
    tags: Optional[List[IdSchema]]
    frequency: int
    isGranular: bool
    isUserModifiable: Optional[bool]
    isSingleScan: bool

class CreateScanResponseModel(BaseModel):
    """Create Scan Schema."""
    name: str
    arguments: Any
    frequency: int
    isGranular: bool
    isUserModifiable: Optional[bool]
    isSingleScan: bool
    createdBy: Optional[Any]
    tags: Optional[List[IdSchema]]
    organizations: Optional[List[IdSchema]]

class GetScanResponseModel(BaseModel):
    """Get Scans response model."""
    scan: Scan
    schema: Dict[str, Any]
    organizations: List[Dict[str, Any]]

class GenericMessageResponseModel(BaseModel):
    """Get Scans response model."""
    status: str
    message: str


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

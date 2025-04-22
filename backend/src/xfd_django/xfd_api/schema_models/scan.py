"""Schemas to support Scan endpoints."""

# Standard Python Libraries
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

from .organization_schema import Organization
from .organization_tag import OrganizationalTags


class Scan(BaseModel):
    """Scan schema reflecting model."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    arguments: Any
    frequency: int
    last_run: Optional[datetime]
    is_granular: bool
    is_user_modifiable: Optional[bool]
    is_single_scan: bool
    manual_run_pending: bool
    concurrent_tasks: Optional[int]
    tags: Optional[List[OrganizationalTags]] = []
    organizations: Optional[List[Organization]] = []


class ScanSchema(BaseModel):
    """Scan type schema."""

    type: str = "fargate"  # Only 'fargate' is supported
    description: str

    # Whether scan is passive (not allowed to hit the domain).
    is_passive: bool

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
    num_chunks: Optional[int] = None

    max_concurrent_tasks: Optional[int] = 500


class GranularScan(BaseModel):
    """Granular scan model."""

    id: UUID
    name: str
    is_user_modifiable: Optional[bool]


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
    organizations: Optional[List[UUID]] = []
    tags: Optional[List[IdSchema]] = []
    frequency: Optional[int] = None
    is_granular: Optional[bool] = None
    is_user_modifiable: Optional[bool] = None
    is_single_scan: Optional[bool] = None
    concurrent_tasks: Optional[int] = 1


class CreateScanResponseModel(BaseModel):
    """Create Scan Schema."""

    id: UUID
    name: str
    arguments: Any
    frequency: int
    is_granular: bool
    is_user_modifiable: Optional[bool]
    is_single_scan: bool
    created_by: Optional[Any]
    tags: Optional[List[IdSchema]]
    organizations: Optional[List[IdSchema]]
    concurrent_tasks: Optional[int]


class GetScanResponseModel(BaseModel):
    """Get Scans response model."""

    scan: Scan
    schema: Dict[str, Any]
    organizations: List[Dict[str, Any]]


class GenericMessageResponseModel(BaseModel):
    """Generic response model."""

    status: str
    message: str


SCAN_SCHEMA = {
    "amass": ScanSchema(
        type="fargate",
        is_passive=False,
        global_scan=False,
        description="Open source tool that integrates passive APIs and active subdomain enumeration in order to discover target subdomains",
    ),
    "censys": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        description="Passive discovery of subdomains from public certificates",
        max_concurrent_tasks=5,
    ),
    "censysCertificates": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="2048",
        memory="6144",
        num_chunks=20,
        description="Fetch TLS certificate data from censys certificates dataset",
    ),
    "censysIpv4": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="2048",
        memory="6144",
        num_chunks=20,
        description="Fetch passive port and banner data from censys ipv4 dataset",
    ),
    "cve": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Matches detected software versions to CVEs from NIST NVD and CISA's Known Exploited Vulnerabilities Catalog.",
    ),
    "credential_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in Credential breach and exposure data from commercial mdl",
    ),
    "vulnScanningSync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in vulnerability data from VSs Vulnerability database",
    ),
    "cveSync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Matches detected software versions to CVEs from NIST NVD and CISA's Known Exploited Vulnerabilities Catalog.",
    ),
    "dnstwist": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="2048",
        memory="16384",
        description="Domain name permutation engine for detecting similar registered domains.",
    ),
    "dotgov": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        description='Create organizations based on root domains from the dotgov registrar dataset. All organizations are created with the "dotgov" tag and have a " (dotgov)" suffix added to their name.',
    ),
    "findomain": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        description="Open source tool that integrates passive APIs in order to discover target subdomains",
    ),
    "hibp": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="2048",
        memory="16384",
        description="Finds emails that have appeared in breaches related to a given domain",
    ),
    "intel_x_identity": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Identify credential exposures via IntelX.",
    ),
    "intrigueIdent": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="4096",
        description="Open source tool that fingerprints web technologies based on HTTP responses",
    ),
    "lookingGlass": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        description="Finds vulnerabilities and malware from the LookingGlass API",
    ),
    "portscanner": ScanSchema(
        type="fargate",
        is_passive=False,
        global_scan=False,
        description="Active port scan of common ports",
    ),
    "rootDomainSync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        description="Creates domains from root domains by doing a single DNS lookup for each root domain.",
    ),
    "savedSearch": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        description="Performs saved searches to update their search results",
    ),
    "searchSync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="4096",
        description="Syncs records with Elasticsearch so that they appear in search results.",
    ),
    "shodan": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Fetch passive port, banner, and vulnerability data from shodan",
        max_concurrent_tasks=10,
    ),
    "shodan_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in Shodan asset and vulnerability data from commercial mdl",
    ),
    "sslyze": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        description="SSL certificate inspection",
    ),
    "test": ScanSchema(
        type="fargate",
        is_passive=False,
        global_scan=True,
        description="Not a real scan, used to test",
    ),
    "trustymail": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        description="Evaluates SPF/DMARC records and checks MX records for STARTTLS support",
    ),
    "vulnSync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in vulnerability data from PEs Vulnerability database",
    ),
    "wappalyzer": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="4096",
        description="Open source tool that fingerprints web technologies based on HTTP responses",
    ),
    "flagFloatingIps": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="2048",
        memory="16384",
        description="Loops through all domains and determines if their associated IP can be found in a report Cidr block.",
    ),
    "updateBlocklist": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        numChunks=0,
        cpu="1024",
        memory="8192",
        description="Updates blocked ip records against blocklist.de global IP blocklist",
    ),
    "was_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in WAS finding data from commercial mdl",
    ),
    "xpanse_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in Xpanse alert data from commercial mdl",
    ),
    "asm_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Enumerate and sync org assets.",
        max_concurrent_tasks=1,
    ),
}

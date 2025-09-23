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
    cpu: Optional[str] = "1024"
    memory: Optional[str] = "8192"

    # A scan is "chunked" if its work is divided and run in parallel by multiple workers.
    # To make a scan chunked, make sure it is a global scan and specify the "num_chunks" variable,
    # which corresponds to the number of workers that will be created to run the task.
    # Chunked scans can only be run on scans whose implementation takes into account the
    # chunk_number and num_chunks parameters specified in commandOptions.
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
    "asm_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Enumerate and sync org assets.",
        max_concurrent_tasks=3,
    ),
    "censys": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        description="Passive discovery of subdomains from public certificates",
        max_concurrent_tasks=5,
    ),
    "censys_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Pull in Censys asset and vulnerability data from commercial mdl",
        max_concurrent_tasks=10,
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
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Pull in Credential breach and exposure data from commercial mdl",
        max_concurrent_tasks=5,
    ),
    "vulnScanningSync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="16384",
        memory="65536",
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
    "dns_twist": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="2048",
        memory="16384",
        description="Domain name permutation engine for detecting similar registered domains.",
        max_concurrent_tasks=10000,
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
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Identify credential exposures via IntelX.",
        max_concurrent_tasks=1,
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
    "nist": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Update CVE data using the NIST API",
    ),
    "nist_lz_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in NIST cve data from commercial mdl",
    ),
    "cybersix_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in Cybersixgill data from commercial mdl",
    ),
    "cybersix_lz_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in Cybersixgill cve data from commercial mdl",
    ),
    "portscanner": ScanSchema(
        type="fargate",
        is_passive=False,
        global_scan=False,
        description="Active port scan of common ports",
    ),
    "redshift_cve_scan": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        description="Creates cve redshift scan.",
        cpu="2048",
        memory="16384",
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
        cpu="16384",
        memory="65536",
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
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Pull in Shodan asset and vulnerability data from commercial mdl",
        max_concurrent_tasks=10,
    ),
    "sslyze": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        description="SSL certificate inspection",
    ),
    "sync_asm_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Pull synced assets from DMZ.",
        max_concurrent_tasks=10,
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
    "update_blocklist": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        num_chunks=0,
        cpu="1024",
        memory="8192",
        description="Updates blocked ip records against blocklist.de global IP blocklist",
    ),
    "was": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Populate was info at commercial mdl",
    ),
    "was_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in WAS finding data from commercial mdl",
    ),
    "was_lz_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in WAS data from commercial mdl and sync to LZ MDL",
    ),
    "xpanse_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in Xpanse alert data from commercial mdl",
    ),
    "refresh_vs_summaries": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Rerun VS Summary fills.",
    ),
    "refresh_material_views": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="2048",
        memory="16384",
        description="Task to refresh or create all views/materialized views in mini_data_lake.",
    ),
    "cisakev": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="4096",
        description="Fetches and stores the latest CISA Known Exploited Vulnerabilities catalog into the Mini Data Lake and flags relevant CVEs.",
    ),
    "xpanse_alert_pull": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Pull in Xpanse alert data from Xpanse API",
        max_concurrent_tasks=3,
    ),
    "xpanse_org_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull in Xpanse business units and link them to organizations",
    ),
    "xpanse_data_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Pull all Xpanse data and push to /xpanse-sync in DMZ",
    ),
    "cybersixgill": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Collect alerts, mentions, credentials, and top CVEs from Cybersixgill dark web monitoring.",
    ),
    "dns_twist_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Pull DomainPermutation data and push them to the DMZ sync endpoint.",
        max_concurrent_tasks=10000,
    ),
    "pshtt_scan": ScanSchema(
        type="fargate",
        is_passive=False,
        global_scan=False,
        cpu="1024",
        memory="8192",
        description="Performs HTTPS security checks on domains using the pshtt tool.",
        max_concurrent_tasks=10,
    ),
    "pshtt_scan_sync": ScanSchema(
        type="fargate",
        is_passive=True,
        global_scan=True,
        cpu="1024",
        memory="8192",
        description="Syncs pshtt scan results with the database and Elasticsearch.",
    ),
}

"""Django ORM models."""


# Standard Python Libraries
from datetime import datetime, timezone
import uuid

# Third-Party Libraries
from django.contrib.postgres.fields import ArrayField
from django.db import models


class ApiKey(models.Model):
    """The ApiKey model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="created_at")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updated_at")
    lastUsed = models.DateTimeField(db_column="last_used", blank=True, null=True)
    hashedKey = models.TextField(db_column="hashed_key")
    lastFour = models.TextField(db_column="last_four")
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="user_id",
        blank=True,
        null=True,
        related_name="api_keys",
    )

    class Meta:
        """Meta class for ApiKey."""

        managed = True
        db_table = "api_key"


class Cpe(models.Model):
    """The Cpe model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=255)
    vendor = models.CharField(max_length=255)
    lastSeenAt = models.DateTimeField(db_column="last_seen_at")

    class Meta:
        """The Meta class for Cpe."""

        db_table = "cpe"
        managed = True  # This ensures Django does not manage the table
        unique_together = (("name", "version", "vendor"),)  # Unique constraint


class Cve(models.Model):
    """The Cve model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, blank=True, null=True)
    publishedAt = models.DateTimeField(db_column="published_at", blank=True, null=True)
    modifiedAt = models.DateTimeField(db_column="modified_at", blank=True, null=True)
    status = models.CharField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    cvssV2Source = models.CharField(db_column="cvss_v2_source", blank=True, null=True)
    cvssV2Type = models.CharField(db_column="cvss_v2_type", blank=True, null=True)
    cvssV2Version = models.CharField(db_column="cvss_v2_version", blank=True, null=True)
    cvssV2VectorString = models.CharField(
        db_column="cvss_v2_vector_string", blank=True, null=True
    )
    cvssV2BaseScore = models.CharField(
        db_column="cvss_v2_base_score", blank=True, null=True
    )
    cvssV2BaseSeverity = models.CharField(
        db_column="cvss_v2_base_severity", blank=True, null=True
    )
    cvssV2ExploitabilityScore = models.CharField(
        db_column="cvss_v2_exploitability_score", blank=True, null=True
    )
    cvssV2ImpactScore = models.CharField(
        db_column="cvss_v2_impact_score", blank=True, null=True
    )
    cvssV3Source = models.CharField(db_column="cvss_v3_source", blank=True, null=True)
    cvssV3Type = models.CharField(db_column="cvss_v3_type", blank=True, null=True)
    cvssV3Version = models.CharField(db_column="cvss_v3_version", blank=True, null=True)
    cvssV3VectorString = models.CharField(
        db_column="cvss_v3_vector_string", blank=True, null=True
    )
    cvssV3BaseScore = models.CharField(
        db_column="cvss_v3_base_score", blank=True, null=True
    )
    cvssV3BaseSeverity = models.CharField(
        db_column="cvss_v3_base_severity", blank=True, null=True
    )
    cvssV3ExploitabilityScore = models.CharField(
        db_column="cvss_v3_exploitability_score", blank=True, null=True
    )
    cvssV3ImpactScore = models.CharField(
        db_column="cvss_v3_impact_score", blank=True, null=True
    )
    cvssV4Source = models.CharField(db_column="cvss_v4_source", blank=True, null=True)
    cvssV4Type = models.CharField(db_column="cvss_v4_type", blank=True, null=True)
    cvssV4Version = models.CharField(db_column="cvss_v4_version", blank=True, null=True)
    cvssV4VectorString = models.CharField(
        db_column="cvss_v4_vector_string", blank=True, null=True
    )
    cvssV4BaseScore = models.CharField(
        db_column="cvss_v4_base_score", blank=True, null=True
    )
    cvssV4BaseSeverity = models.CharField(
        db_column="cvss_v4_base_severity", blank=True, null=True
    )
    cvssV4ExploitabilityScore = models.CharField(
        db_column="cvss_v4_exploitability_score", blank=True, null=True
    )
    cvssV4ImpactScore = models.CharField(
        db_column="cvss_v4_impact_score", blank=True, null=True
    )
    weaknesses = models.TextField(blank=True, null=True)
    references = models.TextField(blank=True, null=True)

    cpes = models.ManyToManyField(
        "Cpe",
        related_name="cves",
        db_table="cve_cpes_cpe",
    )

    class Meta:
        """The Meta class for Cve."""

        managed = True
        db_table = "cve"


class Domain(models.Model):
    """The Domain model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    syncedAt = models.DateTimeField(db_column="syncedAt", blank=True, null=True)
    ip = models.CharField(max_length=255, blank=True, null=True)
    fromRootDomain = models.CharField(
        max_length=255, db_column="fromRootDomain", blank=True, null=True
    )
    subdomainSource = models.CharField(
        db_column="subdomainSource", max_length=255, blank=True, null=True
    )
    ipOnly = models.BooleanField(db_column="ipOnly", default=False)

    reverseName = models.CharField(db_column="reverseName", max_length=512)
    name = models.CharField(max_length=512)

    screenshot = models.CharField(max_length=512, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    asn = models.CharField(max_length=255, blank=True, null=True)
    cloudHosted = models.BooleanField(db_column="cloudHosted", default=False)
    fromCidr = models.BooleanField(db_column="fromCidr", default=False)
    isFceb = models.BooleanField(db_column="isFceb", default=False)

    ssl = models.JSONField(blank=True, null=True)
    censysCertificatesResults = models.JSONField(
        db_column="censysCertificatesResults", default=dict
    )
    trustymailResults = models.JSONField(db_column="trustymailResults", default=dict)

    discoveredBy = models.ForeignKey(
        "Scan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="discoveredById",
    )
    organization = models.ForeignKey(
        "Organization", on_delete=models.CASCADE, db_column="organizationId"
    )

    class Meta:
        """The meta class for Domain."""

        db_table = "domain"
        managed = True  # This ensures Django does not manage the table
        unique_together = (("name", "organization"),)  # Unique constraint

    def save(self, *args, **kwargs):
        """Save domain ith reverseName."""
        self.name = self.name.lower()
        self.reverseName = ".".join(reversed(self.name.split(".")))
        super().save(*args, **kwargs)


class Log(models.Model):
    """The Log model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payload = models.TextField()
    createdAt = models.DateTimeField(db_column="created_at", auto_now_add=True)
    eventType = models.CharField(
        db_column="event_type", max_length=255, null=True, blank=True
    )
    result = models.CharField(max_length=255)

    class Meta:
        """The Meta class for Log."""

        managed = True
        db_table = "log"


class Notification(models.Model):
    """The Notification model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="created_at")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updated_at")
    startDatetime = models.DateTimeField(
        db_column="start_datetime", blank=True, null=True
    )
    endDatetime = models.DateTimeField(db_column="end_datetime", blank=True, null=True)
    maintenanceType = models.CharField(
        db_column="maintenance_type", blank=True, null=True
    )
    status = models.CharField(blank=True, null=True)
    updatedBy = models.CharField(db_column="updated_by", blank=True, null=True)
    message = models.CharField(blank=True, null=True)

    class Meta:
        """The Meta class for Notification."""

        managed = True
        db_table = "notification"


class Organization(models.Model):
    """The Organization model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(db_column="created_at", auto_now_add=True)
    updatedAt = models.DateTimeField(db_column="updated_at", auto_now=True)

    acronym = models.CharField(unique=True, blank=True, null=True, max_length=255)
    name = models.CharField(max_length=255)
    rootDomains = ArrayField(models.CharField(max_length=255), db_column="root_domains")
    ipBlocks = ArrayField(models.CharField(max_length=255), db_column="ip_blocks")
    isPassive = models.BooleanField(db_column="is_passive", default=False)

    pendingDomains = models.TextField(
        db_column="pending_domains", default="[]"
    )  # ******* Had to change this from JSON TO TEXT**********
    country = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    regionId = models.CharField(
        max_length=255, db_column="region_id", blank=True, null=True
    )
    stateFips = models.IntegerField(db_column="state_fips", blank=True, null=True)
    stateName = models.CharField(
        max_length=255, db_column="state_name", blank=True, null=True
    )
    county = models.CharField(max_length=255, blank=True, null=True)
    countyFips = models.IntegerField(db_column="county_fips", blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)

    parent = models.ForeignKey(
        "self",
        db_column="parent_id",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )

    createdBy = models.ForeignKey(
        "User",
        db_column="created_by_id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        """The meta class for Organization."""

        managed = True
        db_table = "organization"


class OrganizationTag(models.Model):
    """The OrganizationTag model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(db_column="created_at", auto_now_add=True)
    updatedAt = models.DateTimeField(db_column="updated_at", auto_now=True)

    name = models.CharField(max_length=255, unique=True)
    organizations = models.ManyToManyField(
        "Organization",
        related_name="tags",
        db_table="organization_tag_organizations_organization",
    )

    class Meta:
        """The Meta class for OrganizationTag."""

        managed = True
        db_table = "organization_tag"


class QueryResultCache(models.Model):
    """The QueryResultCache model."""

    identifier = models.CharField(blank=True, null=True)
    time = models.BigIntegerField()
    duration = models.IntegerField()
    query = models.TextField()
    result = models.TextField()

    class Meta:
        """The Meta class for QueryResultCache."""

        managed = True
        db_table = "query-result-cache"


class Role(models.Model):
    """The Role model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="created_at")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updated_at")

    role = models.CharField(max_length=10, default="user")
    approved = models.BooleanField(default=False)

    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, db_column="user_id", related_name="roles"
    )
    createdBy = models.ForeignKey(
        "User",
        models.DO_NOTHING,
        db_column="created_by_id",
        related_name="created_roles",
        blank=True,
        null=True,
    )
    approvedBy = models.ForeignKey(
        "User",
        models.DO_NOTHING,
        db_column="approved_by_id",
        related_name="approved_roles",
        blank=True,
        null=True,
    )

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization_id",
        related_name="user_roles",
        blank=True,
        null=True,
    )

    class Meta:
        """The Meta class for Role."""

        managed = True
        db_table = "role"
        unique_together = (("user", "organization"),)


class SavedSearch(models.Model):
    """The SavedSearch model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(db_column="created_at", auto_now_add=True)
    updatedAt = models.DateTimeField(db_column="updated_at", auto_now=True)

    name = models.CharField()
    searchTerm = models.CharField(db_column="search_term")
    sortDirection = models.CharField(db_column="sort_direction")
    sortField = models.CharField(db_column="sort_field")
    count = models.IntegerField()
    filters = models.JSONField()
    searchPath = models.CharField(db_column="search_path")
    createdById = models.ForeignKey(
        "User", models.DO_NOTHING, db_column="created_by_id", blank=True, null=True
    )

    class Meta:
        """The Meta class for SavedSearch."""

        managed = True
        db_table = "saved_search"


class Scan(models.Model):
    """The Scan model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(db_column="createdAt", auto_now_add=True)
    updatedAt = models.DateTimeField(db_column="updatedAt", auto_now=True)

    name = models.CharField()
    arguments = models.TextField(
        default="{}"
    )  # JSON in the database but fails: the JSON object must be str, bytes or bytearray, not dict
    frequency = models.IntegerField()

    lastRun = models.DateTimeField(db_column="lastRun", blank=True, null=True)
    isGranular = models.BooleanField(db_column="isGranular", default=False)
    isUserModifiable = models.BooleanField(
        db_column="isUserModifiable", blank=True, null=True, default=False
    )
    isSingleScan = models.BooleanField(db_column="isSingleScan", default=False)
    manualRunPending = models.BooleanField(db_column="manualRunPending", default=False)
    concurrentTasks = models.IntegerField(db_column="concurrentTasks", default=1)

    createdBy = models.ForeignKey(
        "User", models.SET_NULL, db_column="createdById", blank=True, null=True
    )
    tags = models.ManyToManyField(
        "OrganizationTag", related_name="scans", db_table="scan_tags_organization_tag"
    )
    organizations = models.ManyToManyField(
        "Organization",
        related_name="granularScans",
        db_table="scan_organizations_organization",
    )

    class Meta:
        """The Meta class for Scan."""

        managed = True
        db_table = "scan"


class ScanTask(models.Model):
    """The ScanTask model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(db_column="createdAt", auto_now_add=True)
    updatedAt = models.DateTimeField(db_column="updatedAt", auto_now=True)
    status = models.TextField()
    type = models.TextField()
    fargateTaskArn = models.TextField(db_column="fargateTaskArn", blank=True, null=True)
    input = models.TextField(blank=True, null=True)
    output = models.TextField(blank=True, null=True)
    requestedAt = models.DateTimeField(db_column="requestedAt", blank=True, null=True)
    startedAt = models.DateTimeField(db_column="startedAt", blank=True, null=True)
    finishedAt = models.DateTimeField(db_column="finishedAt", blank=True, null=True)
    queuedAt = models.DateTimeField(db_column="queuedAt", blank=True, null=True)
    concurrencyIndex = models.IntegerField(db_column="concurrencyIndex", default=1)

    scan = models.ForeignKey(
        Scan, on_delete=models.SET_NULL, db_column="scanId", blank=True, null=True
    )
    organizations = models.ManyToManyField(
        "Organization",
        related_name="allScanTasks",
        db_table="scan_task_organizations_organization",
    )

    class Meta:
        """The Meta class for ScanTask."""

        managed = True
        db_table = "scan_task"


class Service(models.Model):
    """The Service model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    serviceSource = models.TextField(db_column="serviceSource", blank=True, null=True)
    port = models.IntegerField()
    service = models.CharField(blank=True, null=True)
    lastSeen = models.DateTimeField(db_column="lastSeen", blank=True, null=True)
    banner = models.TextField(blank=True, null=True)

    products = models.JSONField(default=list)
    censysMetadata = models.JSONField(
        db_column="censysMetadata", null=True, blank=True, default=dict
    )
    censysIpv4Results = models.JSONField(db_column="censysIpv4Results", default=dict)
    intrigueIdentResults = models.JSONField(
        db_column="intrigueIdentResults", default=dict
    )
    shodanResults = models.JSONField(
        db_column="shodanResults", null=True, blank=True, default=dict
    )
    wappalyzerResults = models.JSONField(db_column="wappalyzerResults", default=list)

    domain = models.ForeignKey(
        Domain, db_column="domainId", on_delete=models.CASCADE, related_name="services"
    )
    discoveredBy = models.ForeignKey(
        Scan,
        db_column="discoveredById",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="services",
    )

    class Meta:
        """The Meta class for Service."""

        managed = True
        db_table = "service"
        unique_together = (("port", "domain"),)


class TypeormMetadata(models.Model):
    """The TypeormMetadata model."""

    type = models.CharField()
    database = models.CharField(blank=True, null=True)
    schema = models.CharField(blank=True, null=True)
    table = models.CharField(blank=True, null=True)
    name = models.CharField(blank=True, null=True)
    value = models.TextField(blank=True, null=True)

    class Meta:
        """The Meta class for TypeormMetadata."""

        managed = True
        db_table = "typeorm_metadata"


class UserType(models.TextChoices):
    """User type definition."""

    GLOBAL_ADMIN = "globalAdmin"
    GLOBAL_VIEW = "globalView"
    REGIONAL_ADMIN = "regionalAdmin"
    STANDARD = "standard"


class User(models.Model):
    """The User model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cognitoId = models.CharField(
        max_length=255, db_column="cognitoId", unique=True, blank=True, null=True
    )
    oktaId = models.CharField(
        max_length=255, db_column="okta_id", null=True, blank=True, unique=True
    )
    loginGovId = models.CharField(
        max_length=255, db_column="login_gov_id", unique=True, blank=True, null=True
    )
    createdAt = models.DateTimeField(auto_now_add=True, db_column="created_at")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updated_at")

    firstName = models.CharField(max_length=255, db_column="first_name")
    lastName = models.CharField(max_length=255, db_column="last_name")
    fullName = models.CharField(max_length=255, db_column="full_name")
    email = models.CharField(unique=True)

    invitePending = models.BooleanField(db_column="invite_pending", default=False)
    loginBlockedByMaintenance = models.BooleanField(
        db_column="login_blocked_by_maintenance", default=False
    )
    dateAcceptedTerms = models.DateTimeField(
        db_column="date_accepted_terms", blank=True, null=True
    )
    acceptedTermsVersion = models.TextField(
        db_column="accepted_terms_version", blank=True, null=True
    )

    lastLoggedIn = models.DateTimeField(
        db_column="last_logged_in", blank=True, null=True
    )
    userType = models.CharField(
        db_column="user_type",
        max_length=50,
        choices=UserType.choices,
        default=UserType.STANDARD,
    )

    regionId = models.CharField(
        db_column="region_id", blank=True, null=True, max_length=255
    )
    state = models.CharField(blank=True, null=True, max_length=255)

    def save(self, *args, **kwargs):
        """Save user with fullName."""
        self.fullName = "{} {}".format(self.firstName, self.lastName)
        super().save(*args, **kwargs)

    class Meta:
        """The Meta class for User."""

        managed = True
        db_table = "user"


class Vulnerability(models.Model):
    """The Vulnerability model."""

    class SeverityChoices(models.TextChoices):
        """Severity choices."""

        NONE = "None"
        LOW = "Low"
        MEDIUM = "Medium"
        HIGH = "High"
        CRITICAL = "Critical"

    class StateChoices(models.TextChoices):
        """State choices."""

        OPEN = "open"
        CLOSED = "closed"

    class SubstateChoices(models.TextChoices):
        """Substate choices."""

        UNCONFIRMED = "unconfirmed"
        EXPLOITABLE = "exploitable"
        FALSE_POSITIVE = "false-positive"
        ACCEPTED_RISK = "accepted-risk"
        REMEDIATED = "remediated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")
    lastSeen = models.DateTimeField(db_column="lastSeen", blank=True, null=True)
    title = models.CharField()
    cve = models.TextField(blank=True, null=True)
    cwe = models.TextField(blank=True, null=True)
    cpe = models.TextField(blank=True, null=True)
    description = models.CharField()
    references = models.JSONField(default=list)
    cvss = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    severity = models.CharField(
        max_length=10, choices=SeverityChoices.choices, blank=True, null=True
    )
    needsPopulation = models.BooleanField(db_column="needsPopulation", default=False)
    state = models.CharField(
        max_length=10, choices=StateChoices.choices, default=StateChoices.OPEN
    )
    substate = models.CharField(
        max_length=15,
        choices=SubstateChoices.choices,
        default=SubstateChoices.UNCONFIRMED,
    )
    source = models.CharField()
    notes = models.CharField()
    actions = models.JSONField(default=list)
    structuredData = models.JSONField(db_column="structuredData", default=dict)
    isKev = models.BooleanField(db_column="isKev", blank=True, null=True, default=False)
    kevResults = models.JSONField(
        db_column="kevResults", blank=True, null=True, default=dict
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        db_column="domainId",
        blank=True,
        null=True,
        related_name="vulnerabilities",
    )
    service = models.ForeignKey(
        Service, models.DO_NOTHING, db_column="serviceId", blank=True, null=True
    )

    def setState(self, substate, automatic, user=None):
        """Set the state and update actions."""
        self.substate = substate
        self.state = "open" if substate in ["unconfirmed", "exploitable"] else "closed"
        self.actions.insert(
            0,
            {
                "type": "state-change",
                "state": self.state,
                "substate": self.substate,
                "automatic": automatic,
                "userId": user.id if user else None,
                "userName": user.fullName if user else None,
                "date": datetime.now(timezone.utc),
            },
        )

    def save(self, *args, **kwargs):
        """Override save to set severity based on cvss."""
        if self.cvss is not None:
            if self.cvss == 0:
                self.severity = self.SeverityChoices.NONE
            elif self.cvss < 4:
                self.severity = self.SeverityChoices.LOW
            elif self.cvss < 7:
                self.severity = self.SeverityChoices.MEDIUM
            elif self.cvss < 9:
                self.severity = self.SeverityChoices.HIGH
            else:
                self.severity = self.SeverityChoices.CRITICAL
        super().save(*args, **kwargs)

    class Meta:
        """The Meta class for Vulnerability."""

        managed = True
        db_table = "vulnerability"
        indexes = [
            models.Index(fields=["createdAt"]),
            models.Index(fields=["updatedAt"]),
        ]
        unique_together = (("domain", "title"),)


class Webpage(models.Model):
    """The Webpage model."""

    id = models.UUIDField(primary_key=True)
    createdAt = models.DateTimeField(db_column="created_at")
    updatedAt = models.DateTimeField(db_column="updated_at")
    syncedAt = models.DateTimeField(db_column="synced_at", blank=True, null=True)
    lastSeen = models.DateTimeField(db_column="last_seen", blank=True, null=True)
    s3key = models.CharField(db_column="s3Key", blank=True, null=True)
    url = models.CharField()
    status = models.DecimalField(max_digits=1000, decimal_places=1000)
    responseSize = models.DecimalField(
        db_column="response_size",
        max_digits=1000,
        decimal_places=1000,
        blank=True,
        null=True,
    )
    headers = models.JSONField()
    domainId = models.ForeignKey(
        Domain,
        models.DO_NOTHING,
        db_column="domain_id",
        blank=True,
        null=True,
        related_name="webpages",
    )
    discoveredById = models.ForeignKey(
        Scan, models.DO_NOTHING, db_column="discovered_by_id", blank=True, null=True
    )

    class Meta:
        """The Meta class for Webpage."""

        managed = True
        db_table = "webpage"
        unique_together = (("url", "domainId"),)

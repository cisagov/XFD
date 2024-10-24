""" Django ORM models."""


# Standard Python Libraries
import uuid

# Third-Party Libraries
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models


class ApiKey(models.Model):
    """The ApiKey model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")
    lastUsed = models.DateTimeField(db_column="lastUsed", blank=True, null=True)
    hashedKey = models.TextField(db_column="hashedKey")
    lastFour = models.TextField(db_column="lastFour")
    userId = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="userId",
        blank=True,
        null=True,
        related_name="apiKeys",
    )

    class Meta:
        """Meta class for ApiKey."""

        managed = False
        db_table = "api_key"


class Assessment(models.Model):
    """The Assessment model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")
    rscId = models.CharField(max_length=255, db_column="rscId", unique=True)
    type = models.CharField(max_length=255)

    user = models.ForeignKey(
        "User",
        db_column="userId",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="assessments",
    )

    class Meta:
        """The Meta class for Assessment."""

        managed = False
        db_table = "assessment"


class Category(models.Model):
    """The Category model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=255, unique=True)
    shortName = models.CharField(
        db_column="shortName", max_length=255, blank=True, null=True
    )

    class Meta:
        """The Meta class for Category model."""

        managed = False
        db_table = "category"


class Cpe(models.Model):
    """The Cpe model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=255)
    vendor = models.CharField(max_length=255)
    lastSeenAt = models.DateTimeField(db_column="lastSeenAt")

    class Meta:
        """The Meta class for Cpe."""

        db_table = "cpe"
        managed = False  # This ensures Django does not manage the table
        unique_together = (("name", "version", "vendor"),)  # Unique constraint


class Cve(models.Model):
    """The Cve model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, blank=True, null=True)
    publishedAt = models.DateTimeField(db_column="publishedAt", blank=True, null=True)
    modifiedAt = models.DateTimeField(db_column="modifiedAt", blank=True, null=True)
    status = models.CharField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    cvssV2Source = models.CharField(db_column="cvssV2Source", blank=True, null=True)
    cvssV2Type = models.CharField(db_column="cvssV2Type", blank=True, null=True)
    cvssV2Version = models.CharField(db_column="cvssV2Version", blank=True, null=True)
    cvssV2VectorString = models.CharField(
        db_column="cvssV2VectorString", blank=True, null=True
    )
    cvssV2BaseScore = models.CharField(
        db_column="cvssV2BaseScore", blank=True, null=True
    )
    cvssV2BaseSeverity = models.CharField(
        db_column="cvssV2BaseSeverity", blank=True, null=True
    )
    cvssV2ExploitabilityScore = models.CharField(
        db_column="cvssV2ExploitabilityScore", blank=True, null=True
    )
    cvssV2ImpactScore = models.CharField(
        db_column="cvssV2ImpactScore", blank=True, null=True
    )
    cvssV3Source = models.CharField(db_column="cvssV3Source", blank=True, null=True)
    cvssV3Type = models.CharField(db_column="cvssV3Type", blank=True, null=True)
    cvssV3Version = models.CharField(db_column="cvssV3Version", blank=True, null=True)
    cvssV3VectorString = models.CharField(
        db_column="cvssV3VectorString", blank=True, null=True
    )
    cvssV3BaseScore = models.CharField(
        db_column="cvssV3BaseScore", blank=True, null=True
    )
    cvssV3BaseSeverity = models.CharField(
        db_column="cvssV3BaseSeverity", blank=True, null=True
    )
    cvssV3ExploitabilityScore = models.CharField(
        db_column="cvssV3ExploitabilityScore", blank=True, null=True
    )
    cvssV3ImpactScore = models.CharField(
        db_column="cvssV3ImpactScore", blank=True, null=True
    )
    cvssV4Source = models.CharField(db_column="cvssV4Source", blank=True, null=True)
    cvssV4Type = models.CharField(db_column="cvssV4Type", blank=True, null=True)
    cvssV4Version = models.CharField(db_column="cvssV4Version", blank=True, null=True)
    cvssV4VectorString = models.CharField(
        db_column="cvssV4VectorString", blank=True, null=True
    )
    cvssV4BaseScore = models.CharField(
        db_column="cvssV4BaseScore", blank=True, null=True
    )
    cvssV4BaseSeverity = models.CharField(
        db_column="cvssV4BaseSeverity", blank=True, null=True
    )
    cvssV4ExploitabilityScore = models.CharField(
        db_column="cvssV4ExploitabilityScore", blank=True, null=True
    )
    cvssV4ImpactScore = models.CharField(
        db_column="cvssV4ImpactScore", blank=True, null=True
    )
    weaknesses = models.TextField(blank=True, null=True)
    references = models.TextField(blank=True, null=True)

    class Meta:
        """The Meta class for Cve."""

        managed = False
        db_table = "cve"


class CveCpesCpe(models.Model):
    """The CveCpesCpe model."""

    cveId = models.ForeignKey(Cve, on_delete=models.CASCADE, db_column="cveId")
    cpeId = models.ForeignKey(Cpe, on_delete=models.CASCADE, db_column="cpeId")

    class Meta:
        """The Meta class for CveCpesCpe model."""

        db_table = "cve_cpes_cpe"
        managed = False  # This ensures Django does not manage the table
        unique_together = (("cve", "cpe"),)  # Unique constraint


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

    ssl = models.JSONField(blank=True, null=True)
    censysCertificatesResults = models.JSONField(
        db_column="censysCertificatesResults", default=dict
    )
    trustymailResults = models.JSONField(db_column="trustymailResults", default=dict)

    discoveredBy = models.ForeignKey(
        "Scan", on_delete=models.SET_NULL, null=True, blank=True
    )
    organization = models.ForeignKey(
        "Organization", on_delete=models.CASCADE, db_column="organizationId"
    )

    class Meta:
        """The meta class for Domain."""

        db_table = "domain"
        managed = False  # This ensures Django does not manage the table
        unique_together = (("name", "organization"),)  # Unique constraint

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        self.reverseName = ".".join(reversed(self.name.split(".")))
        super().save(*args, **kwargs)


class Notification(models.Model):
    """The Notification model."""

    id = models.UUIDField(primary_key=True)
    createdAt = models.DateTimeField(db_column="createdAt")
    updatedAt = models.DateTimeField(db_column="updatedAt")
    startDatetime = models.DateTimeField(
        db_column="startDatetime", blank=True, null=True
    )
    endDatetime = models.DateTimeField(db_column="endDatetime", blank=True, null=True)
    maintenanceType = models.CharField(
        db_column="maintenanceType", blank=True, null=True
    )
    status = models.CharField(blank=True, null=True)
    updatedBy = models.CharField(db_column="updatedBy", blank=True, null=True)
    message = models.CharField(blank=True, null=True)

    class Meta:
        """The Meta class for Notification."""

        managed = False
        db_table = "notification"


class Organization(models.Model):
    """The Organization model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(db_column="createdAt", auto_now_add=True)
    updatedAt = models.DateTimeField(db_column="updatedAt", auto_now=True)

    acronym = models.CharField(unique=True, blank=True, null=True, max_length=255)
    name = models.CharField(max_length=255)
    rootDomains = ArrayField(models.CharField(max_length=255), db_column="rootDomains")
    ipBlocks = ArrayField(models.CharField(max_length=255), db_column="ipBlocks")
    isPassive = models.BooleanField(db_column="isPassive", default=False)

    pendingDomains = models.TextField(
        db_column="pendingDomains", default="[]"
    )  # ******* Had to change this from JSON TO TEXT**********
    country = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    regionId = models.CharField(
        max_length=255, db_column="regionId", blank=True, null=True
    )
    stateFips = models.IntegerField(db_column="stateFips", blank=True, null=True)
    stateName = models.CharField(
        max_length=255, db_column="stateName", blank=True, null=True
    )
    county = models.CharField(max_length=255, blank=True, null=True)
    countyFips = models.IntegerField(db_column="countyFips", blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)

    parent = models.ForeignKey(
        "self",
        db_column="parentId",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )

    createdBy = models.ForeignKey(
        "User",
        db_column="createdById",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        """The meta class for Organization."""

        managed = False
        db_table = "organization"


class OrganizationTag(models.Model):
    """The OrganizationTag model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(db_column="createdAt", auto_now_add=True)
    updatedAt = models.DateTimeField(db_column="updatedAt", auto_now=True)

    name = models.CharField(max_length=255, unique=True)
    organizations = models.ManyToManyField(
        "Organization",
        related_name="tags",
        db_table="organization_tag_organizations_organization",
    )
    scans = models.ManyToManyField(
        "Scan", related_name="tags", db_table="scan_tags_organization_tag"
    )

    class Meta:
        """The Meta class for OrganizationTag."""

        managed = False
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

        managed = False
        db_table = "query-result-cache"


class Question(models.Model):
    """The Question model."""

    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.CharField(blank=True, null=True)
    longForm = models.CharField(db_column="longForm")
    number = models.CharField(max_length=255)
    categoryId = models.ForeignKey(
        Category, models.DO_NOTHING, db_column="categoryId", blank=True, null=True
    )

    class Meta:
        """The Meta class for Question."""

        db_table = "question"
        managed = False
        unique_together = (("category", "number"),)


# Question and Resource many-to-many
class QuestionResourcesResource(models.Model):
    """The QuestionResourcesResource model."""

    questionId = models.ForeignKey(
        "Question", on_delete=models.CASCADE, db_column="questionId"
    )
    resourceId = models.ForeignKey(
        "Resource", on_delete=models.CASCADE, db_column="resourceId"
    )

    class Meta:
        """The Meta class for QuestionResourcesResource."""

        db_table = "question_resources_resource"
        managed = False
        unique_together = (("question", "resource"),)


class Resource(models.Model):
    """The Resource model."""

    id = models.UUIDField(primary_key=True)
    description = models.CharField()
    name = models.CharField()
    type = models.CharField()
    url = models.CharField(unique=True)

    class Meta:
        """The Meta class for Resource."""

        managed = False
        db_table = "resource"


class Response(models.Model):
    """The Response model."""

    id = models.UUIDField(primary_key=True)
    selection = models.CharField()
    assessmentId = models.ForeignKey(
        Assessment, models.DO_NOTHING, db_column="assessmentId", blank=True, null=True
    )
    questionId = models.ForeignKey(
        Question, models.DO_NOTHING, db_column="questionId", blank=True, null=True
    )

    class Meta:
        """The Meta class for Resource."""

        managed = False
        db_table = "response"
        unique_together = (("assessmentId", "questionId"),)


class Role(models.Model):
    """The Role model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    role = models.CharField(max_length=10, default="user")
    approved = models.BooleanField(default=False)

    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, db_column="userId", related_name="roles"
    )
    createdBy = models.ForeignKey(
        "User",
        models.DO_NOTHING,
        db_column="createdById",
        related_name="createdRoles",
        blank=True,
        null=True,
    )
    approvedBy = models.ForeignKey(
        "User",
        models.DO_NOTHING,
        db_column="approvedById",
        related_name="approvedRoles",
        blank=True,
        null=True,
    )

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organizationId",
        related_name="userRoles",
        blank=True,
        null=True,
    )

    class Meta:
        """The Meta class for Role."""

        managed = False
        db_table = "role"
        unique_together = (("user", "organization"),)


class SavedSearch(models.Model):
    """The SavedSearch model."""

    id = models.UUIDField(primary_key=True)
    createdAt = models.DateTimeField(db_column="createdAt")
    updatedAt = models.DateTimeField(db_column="updatedAt")
    name = models.CharField()
    searchTerm = models.CharField(db_column="searchTerm")
    sortDirection = models.CharField(db_column="sortDirection")
    sortField = models.CharField(db_column="sortField")
    count = models.IntegerField()
    filters = models.JSONField()
    searchPath = models.CharField(db_column="searchPath")
    createVulnerabilities = models.BooleanField(db_column="createVulnerabilities")
    vulnerabilityTemplate = models.JSONField(db_column="vulnerabilityTemplate")
    createdById = models.ForeignKey(
        "User", models.DO_NOTHING, db_column="createdById", blank=True, null=True
    )

    class Meta:
        """The Meta class for SavedSearch."""

        managed = False
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

        managed = False
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

        managed = False
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

        managed = False
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

        managed = False
        db_table = "typeorm_metadata"


class UserType(models.TextChoices):
    GLOBAL_ADMIN = "globalAdmin"
    GLOBAL_VIEW = "globalView"
    REGIONAL_ADMIN = "regionalAdmin"
    READY_SET_CYBER = "readySetCyber"
    STANDARD = "standard"


class User(models.Model):
    """The User model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cognitoId = models.CharField(
        max_length=255, db_column="cognitoId", unique=True, blank=True, null=True
    )
    oktaId = models.CharField(
        max_length=255, db_column="oktaId", null=True, blank=True, unique=True
    )
    loginGovId = models.CharField(
        max_length=255, db_column="loginGovId", unique=True, blank=True, null=True
    )
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    firstName = models.CharField(max_length=255, db_column="firstName")
    lastName = models.CharField(max_length=255, db_column="lastName")
    fullName = models.CharField(max_length=255, db_column="fullName")
    email = models.CharField(unique=True)

    invitePending = models.BooleanField(db_column="invitePending", default=False)
    loginBlockedByMaintenance = models.BooleanField(
        db_column="loginBlockedByMaintenance", default=False
    )
    dateAcceptedTerms = models.DateTimeField(
        db_column="dateAcceptedTerms", blank=True, null=True
    )
    acceptedTermsVersion = models.TextField(
        db_column="acceptedTermsVersion", blank=True, null=True
    )

    lastLoggedIn = models.DateTimeField(db_column="lastLoggedIn", blank=True, null=True)
    userType = models.CharField(
        db_column="userType",
        max_length=50,
        choices=UserType.choices,
        default=UserType.STANDARD,
    )

    regionId = models.CharField(
        db_column="regionId", blank=True, null=True, max_length=255
    )
    state = models.CharField(blank=True, null=True, max_length=255)

    def save(self, *args, **kwargs):
        self.fullName = f"{self.firstName} {self.lastName}"
        super().save(*args, **kwargs)

    class Meta:
        """The Meta class for User."""

        managed = False
        db_table = "user"


class Vulnerability(models.Model):
    """The Vulnerability model."""

    id = models.UUIDField(primary_key=True)
    createdAt = models.DateTimeField(db_column="createdAt")
    updatedAt = models.DateTimeField(db_column="updatedAt")
    lastSeen = models.DateTimeField(db_column="lastSeen", blank=True, null=True)
    title = models.CharField()
    cve = models.TextField(blank=True, null=True)
    cwe = models.TextField(blank=True, null=True)
    cpe = models.TextField(blank=True, null=True)
    description = models.CharField()
    references = models.JSONField()
    cvss = models.DecimalField(
        max_digits=65535, decimal_places=65535, blank=True, null=True
    )
    severity = models.TextField(blank=True, null=True)
    needsPopulation = models.BooleanField(db_column="needsPopulation")
    state = models.CharField()
    substate = models.CharField()
    source = models.CharField()
    notes = models.CharField()
    actions = models.JSONField()
    structuredData = models.JSONField(db_column="structuredData")
    isKev = models.BooleanField(db_column="isKev", blank=True, null=True)
    kevResults = models.JSONField(db_column="kevResults", blank=True, null=True)
    domainId = models.ForeignKey(
        Domain, models.DO_NOTHING, db_column="domainId", blank=True, null=True
    )
    serviceId = models.ForeignKey(
        Service, models.DO_NOTHING, db_column="serviceId", blank=True, null=True
    )

    class Meta:
        """The Meta class for Vulnerability."""

        managed = False
        db_table = "vulnerability"
        unique_together = (("domainId", "title"),)


class Webpage(models.Model):
    """The Webpage model."""

    id = models.UUIDField(primary_key=True)
    createdAt = models.DateTimeField(db_column="createdAt")
    updatedAt = models.DateTimeField(db_column="updatedAt")
    syncedAt = models.DateTimeField(db_column="syncedAt", blank=True, null=True)
    lastSeen = models.DateTimeField(db_column="lastSeen", blank=True, null=True)
    s3key = models.CharField(db_column="s3Key", blank=True, null=True)
    url = models.CharField()
    status = models.DecimalField(max_digits=65535, decimal_places=65535)
    responseSize = models.DecimalField(
        db_column="responseSize",
        max_digits=65535,
        decimal_places=65535,
        blank=True,
        null=True,
    )
    headers = models.JSONField()
    domainId = models.ForeignKey(
        Domain, models.DO_NOTHING, db_column="domainId", blank=True, null=True
    )
    discoveredById = models.ForeignKey(
        Scan, models.DO_NOTHING, db_column="discoveredById", blank=True, null=True
    )

    class Meta:
        """The Meta class for Webpage."""

        managed = False
        db_table = "webpage"
        unique_together = (("url", "domainId"),)

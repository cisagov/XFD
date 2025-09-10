"""Django ORM models."""
# Standard Python Libraries
import logging
import socket
import uuid

# Third-Party Libraries
from django.contrib.postgres.fields import ArrayField
from django.db import models
from netfields import InetAddressField

manage_db = True
app_label_name = "xfd_mini_dl"

LOGGER = logging.getLogger(__name__)


class AutoLengthCheckModel(models.Model):
    """Extend base model functionality to validate CharField."""

    class Meta:
        """Meta class."""

        abstract = True

    def save(self, *args, **kwargs):
        """Log warnings and trim input that is too big for CharField."""
        for field in self._meta.fields:
            if isinstance(field, models.CharField):
                value = getattr(self, field.name)
                if (
                    isinstance(value, str)
                    and field.max_length
                    and len(value) > field.max_length
                ):
                    LOGGER.warning(
                        "[%s] Auto-truncating field '%s': %s → %s chars",
                        self.__class__.__name__,
                        field.name,
                        len(value),
                        field.max_length,
                    )
                    setattr(self, field.name, value[: field.max_length])
        super().save(*args, **kwargs)


class ApiKey(models.Model):
    """The ApiKey model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for an API key object.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_column="created_at",
        help_text="Date and time the API key object was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_column="updated_at",
        help_text="Date and time the API key object was last updated.",
    )
    last_used = models.DateTimeField(
        db_column="last_used",
        blank=True,
        null=True,
        help_text="Last date and time the API key was used.",
    )
    hashed_key = models.TextField(
        db_column="hashed_key", help_text="Cryptographic hash of the API key"
    )
    last_four = models.TextField(
        db_column="last_four", help_text="Last for characters of the API key"
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="user_id",
        blank=True,
        null=True,
        related_name="api_keys",
        help_text="FK: foreign key relationship to the user who owns the API key.",
    )

    class Meta:
        """Meta class for ApiKey."""

        app_label = app_label_name
        managed = manage_db
        db_table = "api_key"


class Cpe(AutoLengthCheckModel):
    """The Cpe model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for a CPE Product object.",
    )
    name = models.TextField(help_text="Name of the product.")
    version = models.CharField(max_length=255, help_text="Version of the product.")
    vendor = models.CharField(
        max_length=255, help_text="Vendor who created the product."
    )
    last_seen_at = models.DateTimeField(
        db_column="last_seen_at", help_text="Last datetime the CPE was seen."
    )

    class Meta:
        """The Meta class for Cpe."""

        app_label = app_label_name
        db_table = "cpe"
        managed = manage_db  # This ensures Django does not manage the table
        unique_together = (("name", "version", "vendor"),)  # Unique constraint


class Cve(AutoLengthCheckModel):
    """The Cve model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for a CVE object.",
    )
    name = models.CharField(
        unique=True, blank=True, null=True, max_length=255, help_text="Name of the CVE."
    )
    published_at = models.DateTimeField(
        db_column="published_at",
        blank=True,
        null=True,
        help_text="Date the CVE was published by NIST.",
    )
    modified_at = models.DateTimeField(
        db_column="modified_at",
        blank=True,
        null=True,
        help_text="Datte the CVE was modified.",
    )
    status = models.CharField(
        blank=True, null=True, max_length=255, help_text="Status of the CVE."
    )
    description = models.TextField(
        blank=True, null=True, help_text="Description of the CVE."
    )
    cvss_v2_source = models.CharField(
        db_column="cvss_v2_source",
        blank=True,
        null=True,
        max_length=255,
        help_text="Organization or entity that assigned a CVSS v2 (Common Vulnerability Scoring System version 2) score to a particular vulnerability.",
    )
    cvss_v2_type = models.CharField(
        db_column="cvss_v2_type",
        blank=True,
        null=True,
        max_length=255,
        help_text="Type of CVVS v2 score. (Primary, Secondary)",
    )
    cvss_v2_version = models.CharField(
        db_column="cvss_v2_version",
        blank=True,
        null=True,
        max_length=255,
        help_text="Version of the CVSS v2 score.",
    )
    cvss_v2_vector_string = models.CharField(
        db_column="cvss_v2_vector_string",
        blank=True,
        null=True,
        max_length=255,
        help_text="Textual representation of the specific metrics used to calculate the CVSS v2 score.",
    )
    cvss_v2_base_score = models.CharField(
        db_column="cvss_v2_base_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the severity of the vulnerability.",
    )
    cvss_v2_base_severity = models.CharField(
        db_column="cvss_v2_base_severity",
        blank=True,
        null=True,
        max_length=255,
        help_text="Qualitative categorization of a vulnerability's Base Score that helps assess its overall risk level in a more human-readable way.",
    )
    cvss_v2_exploitability_score = models.CharField(
        db_column="cvss_v2_exploitability_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the exploitability of the vulnerability.",
    )
    cvss_v2_impact_score = models.CharField(
        db_column="cvss_v2_impact_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the potential impact of the vulnerability.",
    )
    cvss_v3_source = models.CharField(
        db_column="cvss_v3_source",
        blank=True,
        null=True,
        max_length=255,
        help_text="Organization or entity that has provided or published the CVSS v3 score for a given vulnerability.",
    )
    cvss_v3_type = models.CharField(
        db_column="cvss_v3_type",
        blank=True,
        null=True,
        max_length=255,
        help_text="Type of CVVS v3 score. (Primary, Secondary)",
    )
    cvss_v3_version = models.CharField(
        db_column="cvss_v3_version",
        blank=True,
        null=True,
        max_length=255,
        help_text="Version of the CVSS v3 score.",
    )
    cvss_v3_vector_string = models.CharField(
        db_column="cvss_v3_vector_string",
        blank=True,
        null=True,
        max_length=255,
        help_text="Textual representation of the specific metrics used to calculate the CVSS v3 score.",
    )
    cvss_v3_base_score = models.CharField(
        db_column="cvss_v3_base_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the severity of the vulnerability.",
    )
    cvss_v3_base_severity = models.CharField(
        db_column="cvss_v3_base_severity",
        blank=True,
        null=True,
        max_length=255,
        help_text="Qualitative categorization of a vulnerability's Base Score that helps assess its overall risk level in a more human-readable way.",
    )
    cvss_v3_exploitability_score = models.CharField(
        db_column="cvss_v3_exploitability_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the exploitability of the vulnerability.",
    )
    cvss_v3_impact_score = models.CharField(
        db_column="cvss_v3_impact_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the potential impact of the vulnerability.",
    )
    cvss_v4_source = models.CharField(
        db_column="cvss_v4_source",
        blank=True,
        null=True,
        max_length=255,
        help_text="Organization or entity that has provided or published the CVSS v4 score for a given vulnerability.",
    )
    cvss_v4_type = models.CharField(
        db_column="cvss_v4_type",
        blank=True,
        null=True,
        max_length=255,
        help_text="Type of CVVS v4 score. (Primary, Secondary)",
    )
    cvss_v4_version = models.CharField(
        db_column="cvss_v4_version",
        blank=True,
        null=True,
        max_length=255,
        help_text="Version of the CVSS v4 score.",
    )
    cvss_v4_vector_string = models.CharField(
        db_column="cvss_v4_vector_string",
        blank=True,
        null=True,
        max_length=255,
        help_text="Textual representation of the specific metrics used to calculate the CVSS v4 score.",
    )
    cvss_v4_base_score = models.CharField(
        db_column="cvss_v4_base_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the severity of the vulnerability.",
    )
    cvss_v4_base_severity = models.CharField(
        db_column="cvss_v4_base_severity",
        blank=True,
        null=True,
        max_length=255,
        help_text="Qualitative categorization of a vulnerability's Base Score that helps assess its overall risk level in a more human-readable way.",
    )
    cvss_v4_exploitability_score = models.CharField(
        db_column="cvss_v4_exploitability_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the exploitability of the vulnerability.",
    )
    cvss_v4_impact_score = models.CharField(
        db_column="cvss_v4_impact_score",
        blank=True,
        null=True,
        max_length=255,
        help_text="Numerical value that quantifies the potential impact of the vulnerability.",
    )
    weaknesses = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    reference_urls = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    cpe_list = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    dve_score = models.DecimalField(
        max_digits=1000,
        decimal_places=1000,
        blank=True,
        null=True,
        help_text="CyberSixGill's Dynamic Vulnerability Exploit (DVE) Score, this state-of-the-art machine learning model automatically predicts the probability of a CVE being exploited.",
    )

    cpes = models.ManyToManyField(
        Cpe,
        related_name="cves",
        blank=True,
        help_text="Many to many relationship to list of affected Products (CPE).",
    )
    source_attribution = models.CharField(
        blank=True,
        null=True,
        max_length=64,
        help_text="Origin of this CVE record (e.g., 'AE/Redshift').",
    )

    assigner = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="Short name of the CVE assigner (e.g., 'CISA-ADP', 'AMD').",
    )

    title = models.TextField(
        blank=True,
        null=True,
        help_text="Short title from CNA/ADP when available.",
    )

    cna_source_json = models.JSONField(
        blank=True, null=True, help_text="Raw CNA 'source' object."
    )
    cna_affected_json = models.JSONField(
        blank=True, null=True, help_text="Raw CNA 'affected' array/object."
    )
    cna_problem_types_json = models.JSONField(
        blank=True, null=True, help_text="Raw CNA 'problemTypes' structure."
    )

    class Meta:
        """The Meta class for Cve."""

        app_label = app_label_name
        managed = manage_db
        indexes = [
            models.Index(fields=["name"]),
        ]
        db_table = "cve"


class CveSsvc(models.Model):
    """SSVC triplet + ADP provenance, flattened from AE/Redshift."""

    cve = models.OneToOneField("Cve", on_delete=models.CASCADE, related_name="ssvc")

    exploitation = models.CharField(max_length=32, blank=True, null=True, db_index=True)
    automatable = models.CharField(max_length=32, blank=True, null=True, db_index=True)
    technical_impact = models.CharField(
        max_length=32, blank=True, null=True, db_index=True
    )

    adp_provider = models.CharField(
        max_length=128, blank=True, null=True, db_index=True
    )
    adp_title = models.TextField(blank=True, null=True)
    ssvc_version = models.CharField(max_length=16, blank=True, null=True)
    ssvc_timestamp = models.DateTimeField(blank=True, null=True, db_index=True)
    adp_date_updated = models.DateTimeField(blank=True, null=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        """Meta class for CveSsvc."""

        app_label = app_label_name
        managed = manage_db
        db_table = "adp_ssvc"
        indexes = [
            models.Index(fields=["exploitation"]),
            models.Index(fields=["automatable"]),
            models.Index(fields=["technical_impact"]),
            models.Index(fields=["adp_provider"]),
            models.Index(fields=["adp_date_updated"]),
        ]


class Notification(AutoLengthCheckModel):
    """The Notification model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for a notification object.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Datetime the notification object was created.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Datetime the notification object was last updated in the database.",
    )
    start_datetime = models.DateTimeField(
        db_column="start_datetime",
        blank=True,
        null=True,
        help_text="Datetime the notification should start being displayed on the cyhy dashboard.",
    )
    end_datetime = models.DateTimeField(
        db_column="end_datetime",
        blank=True,
        null=True,
        help_text="Datetime the notification should stop being displayed on the cyhy dashboard.",
    )
    maintenance_type = models.CharField(
        db_column="maintenance_type",
        blank=True,
        null=True,
        max_length=255,
        help_text="Type of maintenance being done. (Major, Minor)",
    )
    status = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="Status of the notification. (Active, Inactive)",
    )
    updated_by = models.CharField(
        db_column="updated_by",
        blank=True,
        null=True,
        max_length=255,
        help_text="User who updated the notification",
    )
    message = models.TextField(
        blank=True,
        null=True,
        help_text="Message to be displayed on the cyhy dashboard.",
    )

    class Meta:
        """The Meta class for Notification."""

        app_label = app_label_name
        managed = manage_db
        db_table = "notification"


class Organization(AutoLengthCheckModel):
    """The Organization model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a stakeholder Organization.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Date and time the organization object was created in the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Last date and time the organization object was updated.",
    )
    acronym = models.CharField(
        unique=True,
        blank=True,
        null=True,
        max_length=255,
        help_text="Short name used to identify the organization. This should match ServiceNow and the cyhy mongo database org id.",
    )
    retired = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean field to flag organizations that have been retired a",
    )
    name = models.CharField(max_length=255, help_text="Full name of the organization")
    root_domains = ArrayField(
        models.CharField(max_length=255),
        default=list,
        db_column="root_domains",
        help_text="List of root domains attributed to the organization",
    )
    ip_blocks = ArrayField(
        models.CharField(max_length=255),
        default=list,
        db_column="ip_blocks",
        help_text="IP blocks attributed to or provided by a stakeholder.",
    )
    is_passive = models.BooleanField(
        db_column="is_passive",
        help_text="Boolean to flag if only passive data collection can be used on the stakeholder's assets.",
        null=True,
    )
    pending_domains = ArrayField(
        models.TextField(blank=True, null=True),
        blank=True,
        null=True,
        db_column="pending_domains",
        help_text="List of domains that have not yet been run through the setup/enumeration process.",
    )  # This field type is a guess
    date_pe_first_reported = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date that PE first delivered reports to this stakeholder",
    )
    country = models.TextField(
        blank=True,
        null=True,
        help_text="Abbreviation of the country the organization is based in.",
    )
    country_name = models.TextField(
        blank=True,
        null=True,
        help_text="Full name of the country the organization is based in.",
    )
    state = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="Abbreviation of the US state the organization is based in.",
    )
    region_id = models.CharField(
        db_column="region_id",
        blank=True,
        null=True,
        max_length=255,
        help_text="Region number that the organization is found in.",
    )
    state_fips = models.IntegerField(
        db_column="state_fips",
        blank=True,
        null=True,
        help_text="Federal Information Processing Standards code for the US state where the organization is found.",
    )
    state_name = models.CharField(
        db_column="state_name",
        blank=True,
        null=True,
        max_length=255,
        help_text="Full name of the US state the organization is based in.",
    )
    county = models.TextField(
        blank=True,
        null=True,
        help_text="Full name of the county the organization is found in.",
    )
    county_fips = models.IntegerField(
        db_column="county_fips",
        blank=True,
        null=True,
        help_text="Federal Information Processing Standards code for the US county where the organization is found.",
    )
    type = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="The type of organization, brought over from legacy crossfeed, but not sure if currently used.",
    )
    pe_report_on = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean to flag if the organization receives PE reports.",
    )
    pe_premium = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean to flag if an organization receives a premium PE report.",
    )
    pe_demo = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean to flag if an organization is in demo status for PE. This means that scans are run for the organization, but reports are not delivered.",
    )
    agency_type = models.TextField(
        blank=True,
        null=True,
        help_text="Type of organization pulled from the Cyhy mongo database (Federal, State, Local, Private).",
    )
    is_parent = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean to flag if an organization has children organizations associated with it.",
    )
    pe_run_scans = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean field to determine if pe scans should be run an organization's assets.",
    )
    stakeholder = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean to flag if an organization is a cyhy stakeholder.",
    )
    election = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean to flag if the organization is an election entity.",
    )
    was_stakeholder = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean to flag if an organization is a WAS customer.",
    )
    vs_stakeholder = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean to flag if an organization is a VS customer.",
    )
    pe_stakeholder = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Boolean to flag if an organization is a PE customer.",
    )
    receives_cyhy_report = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean to flag if the organization receives a cyhy report.",
    )
    receives_bod_report = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean to flag if the organization receives a cyhy bod report.",
    )
    receives_cybex_report = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean to flag if the organization receives a cyhy cybex report.",
    )
    init_stage = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="First scan run in the VS scan process.",
    )
    scheduler = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Type of scheduler the VS scan uses when running VS scans.",
    )
    enrolled_in_vs_timestamp = models.DateTimeField(
        db_column="enrolled_in_vs_timestamp",
        null=True,
        blank=True,
        help_text="Date the stakeholder enrolled in VS.",
    )
    period_start_vs_timestamp = models.DateTimeField(
        db_column="period_start_vs_timestamp",
        null=True,
        blank=True,
        help_text="Period start for the last report period VS ran.?????",
    )
    report_types = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text="List of types of CyHy reports the stakeholder receives ",
    )
    scan_types = models.JSONField(
        null=True, blank=True, default=list, help_text="Types of scans run by Cyhy."
    )
    scan_windows = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text="List of time windows when VS can scan a stakeholder's assets.",
    )
    scan_limits = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text="Limits placed on a VS scan by the stakeholder.",
    )
    password = models.TextField(
        blank=True,
        null=True,
        help_text="Encrypted password used to encrypt and decrypt reports sent to the stakeholder.",
    )
    cyhy_period_start = models.DateField(
        blank=True,
        null=True,
        help_text="Timestamp when scanning can begin for this organization.",
    )
    location = models.ForeignKey(
        "Location",
        related_name="organizations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Foreign Key linking to a related Location object.",
    )
    parent = models.ForeignKey(
        "self",
        models.DO_NOTHING,
        db_column="parent_id",
        related_name="children",
        blank=True,
        null=True,
        help_text="Foreign Key linking to a related organization parent object.",
    )
    created_by = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="created_by_id",
        blank=True,
        null=True,
        help_text="Foreign Key linking to the user who create the organization.",
    )
    org_type = models.ForeignKey(
        "OrgType",
        on_delete=models.CASCADE,
        db_column="org_type_id",
        blank=True,
        null=True,
        help_text="Foreign Key to the related orgType object. ",
    )

    class Meta:
        """The meta class for Organization."""

        app_label = app_label_name
        managed = manage_db
        db_table = "organization"


class OrganizationTag(AutoLengthCheckModel):
    """The OrganizationTag model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for an Organization tag object.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Date the organization tag was added to the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Last date the organization tag object was updated in the database.",
    )
    name = models.CharField(
        unique=True,
        max_length=255,
        help_text="The name of the tag used to link common organizations.",
    )
    organization = models.ManyToManyField(
        "Organization",
        related_name="tags",
        blank=True,
        help_text="Many to many relationship to link a tag to many organizations",
    )

    class Meta:
        """The Meta class for OrganizationTag."""

        app_label = app_label_name
        managed = manage_db
        db_table = "organization_tag"


class QueryResultCache(AutoLengthCheckModel):
    """The QueryResultCache model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for the query result object being cached.",
    )
    identifier = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="Another identifier for the query being cached.",
    )
    time = models.BigIntegerField(
        help_text="Time the query was run against the database."
    )
    duration = models.IntegerField(help_text="How long the query took to run.")
    query = models.TextField(
        help_text="The Query run against the database to be cached."
    )
    result = models.TextField(help_text="Result from the query performed in Crossfeed.")

    class Meta:
        """The Meta class for QueryResultCache."""

        app_label = app_label_name
        managed = manage_db
        db_table = "query-result-cache"


class Role(models.Model):
    """The Role model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for the role object.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Date the role object was added to the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Last date the role object was updated in the database.",
    )
    role = models.CharField(
        max_length=255,
        help_text="A role that a user can be assigned to, granting them specific access on the crossfeed platform.",
    )
    approved = models.BooleanField(
        default=False,
        help_text="A boolean flag to determine if the user has been approved to have the assigned role.",
    )
    created_by = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="created_by_id",
        blank=True,
        null=True,
        help_text="Foreign key linking to the user who created the role in the database.",
    )
    approved_by = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="approved_by_id",
        related_name="approved_roles",
        blank=True,
        null=True,
        help_text="Foreign key to the user who approved the role assignation.",
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="user_id",
        related_name="roles",
        blank=True,
        null=True,
        help_text="Foreign key to the user being assigned the role.",
    )
    organization = models.ForeignKey(
        Organization,
        models.CASCADE,
        db_column="organization_id",
        related_name="user_roles",
        blank=True,
        null=True,
        help_text="Foreign key to the organization the user is aligned to and whos data the user can access via their role.",
    )

    class Meta:
        """The Meta class for Role."""

        app_label = app_label_name
        managed = manage_db
        db_table = "role"
        unique_together = (("user_id", "organization_id"),)


class SavedSearch(AutoLengthCheckModel):
    """The SavedSearch model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for the Saved Search object",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Date the saved search object was added to the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Last date the saved search object was updated in the database.",
    )
    name = models.CharField(
        max_length=255,
        help_text="User provided name of the saved search provided in the cyhy dashboard.",
    )
    search_term = models.CharField(
        db_column="search_term",
        max_length=255,
        help_text="The term being searched for in the cyhy dashboard.",
    )
    sort_direction = models.CharField(
        db_column="sort_direction",
        max_length=255,
        help_text="Direction of the sort (asc or desc).",
    )
    sort_field = models.CharField(
        db_column="sort_field", max_length=255, help_text="The field to sort based on."
    )
    count = models.IntegerField(
        help_text="Number of results returned when the search was run."
    )
    filters = models.JSONField(help_text="Filters applied in the search.")
    search_path = models.CharField(
        db_column="search_path",
        max_length=255,
        help_text="Search path used to call create the search against the ORM.",
    )
    created_by = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="created_by_id",
        blank=True,
        null=True,
        help_text="Foreign key linking to the user who created the saved search in the dashboard.",
    )

    class Meta:
        """The Meta class for SavedSearch."""

        app_label = app_label_name
        managed = manage_db
        db_table = "saved_search"


class Scan(models.Model):
    """The Scan model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a cyhy dashboard scan object.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Date the scan object was added to the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Last date the scan object was updated in the database.",
    )
    name = models.CharField(
        max_length=255, help_text="The name of the cyhy dashboard scan."
    )
    arguments = models.TextField(
        default="{}", help_text="A dictionary of arguments to pass to the scan."
    )  # JSON in the database but fails: the JSON object must be str, bytes or bytearray, not dict
    frequency = models.IntegerField(
        help_text="How often the scan should run in seconds."
    )
    last_run = models.DateTimeField(
        db_column="last_run",
        blank=True,
        null=True,
        help_text="Last day the scan was run.",
    )
    is_granular = models.BooleanField(
        db_column="is_granular",
        default=False,
        help_text="A boolean flag to specify if the scan is granular. Granular scans are only run on specified organizations. Global scans cannot be granular scans.",
    )
    is_user_modifiable = models.BooleanField(
        db_column="is_user_modifiable",
        blank=True,
        null=True,
        help_text="Whether the scan is user-modifiable. User-modifiable scans are granular scans that can be viewed and toggled on/off by organization admins themselves.",
    )
    is_single_scan = models.BooleanField(
        db_column="is_single_scan",
        default=False,
        help_text="A boolean to flag scans that should only be run once and not on a reoccuring basis.",
    )
    manual_run_pending = models.BooleanField(
        db_column="manual_run_pending",
        default=False,
        help_text="A boolean to flag if a manually called scan is still waiting to be run.",
    )
    concurrent_tasks = models.IntegerField(db_column="concurrent_tasks", default=1)
    total_orgs = models.IntegerField(
        db_column="total_orgs",
        default=0,
        help_text="Total number of organizations the scan is run on.",
    )
    created_by = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="created_by",
        blank=True,
        null=True,
        help_text="A foreign key linking to the user who created the scan.",
    )
    organizations = models.ManyToManyField(
        Organization,
        blank=True,
        related_name="granular_scans",
        help_text="A many to many relationship linking to all the organizations the scan should be run on.",
    )
    tags = models.ManyToManyField(
        OrganizationTag,
        related_name="scans",
        blank=True,
        db_table="scan_tags_organization_tag",
        help_text="A many to many relationship linking to all the organization tags that should be run on.",
    )

    class Meta:
        """The Meta class for Scan."""

        app_label = app_label_name
        managed = manage_db
        db_table = "scan"


class ScanResult(models.Model):
    """Timestamp of latest result for each scan/organization pair."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a scan result object.",
    )
    scanned_at = models.DateTimeField(
        db_column="scanned_at",
        help_text="Timestamp when scan result was observed",
    )
    http_status = models.IntegerField(
        db_column="http_status",
        help_text="HTTP status code of the scan result.",
    )
    message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message and exception returned from the scan result.",
    )
    scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        db_column="scan_id",
        related_name="scan_results",
        help_text="Foreign key to the scan that generated the scan result.",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_column="organization_id",
        related_name="scan_results",
        help_text="Foreign key to the organization that the scan result is for.",
    )

    class Meta:
        """The Meta class for ScanResult."""

        app_label = app_label_name
        managed = manage_db
        db_table = "scan_result"
        indexes = [
            models.Index(
                fields=["scanned_at", "scan", "http_status", "organization"],
                name="logtime_scan_status_org_idx",
            ),
        ]


class ScanTask(models.Model):
    """The ScanTask model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a scan task object.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Date the scan task object was added to the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Last date the scan task object was updated in the database.",
    )
    status = models.TextField(
        help_text="The scan task's status. ('created', 'queued', 'requested', 'started', 'failed','finished')"
    )
    type = models.TextField(help_text="Type of scan task. ('fargate', 'lambda')")
    fargate_task_arn = models.TextField(
        db_column="fargate_task_arn",
        blank=True,
        null=True,
        help_text="Unique identifier for the fargate container running the task.",
    )
    input = models.TextField(
        blank=True,
        null=True,
        help_text="All data necessary to run the scan task. (organizations, scan_id, scanName, scanTaskId, isSingleScan)",
    )
    output = models.TextField(
        blank=True,
        null=True,
        help_text="All the data returned from the scan task, dependant on the type of scan.",
    )
    requested_at = models.DateTimeField(
        db_column="requested_at",
        blank=True,
        null=True,
        help_text="Date and time the scan task was requested.",
    )
    started_at = models.DateTimeField(
        db_column="started_at",
        blank=True,
        null=True,
        help_text="Date and time the scan task was started.",
    )
    finished_at = models.DateTimeField(
        db_column="finished_at",
        blank=True,
        null=True,
        help_text="Date and time the scan task finished.",
    )
    queued_at = models.DateTimeField(
        db_column="queued_at",
        blank=True,
        null=True,
        help_text="Date and time the scan task was added to the queue.",
    )
    concurrency_index = models.IntegerField(db_column="concurrency_index", default=1)
    organizations = models.ManyToManyField(
        Organization,
        related_name="scan_tasks",
        help_text="Many to many relationship to the organizations the scan is being run on.",
    )
    scan = models.ForeignKey(
        Scan,
        on_delete=models.SET_NULL,
        db_column="scan_id",
        blank=True,
        null=True,
        help_text="Foreign key to the scan the scan task was based off of.",
    )

    class Meta:
        """The Meta class for ScanTask."""

        app_label = app_label_name
        managed = manage_db
        db_table = "scan_task"


class Service(models.Model):
    """The Service View."""

    id = models.TextField(
        primary_key=True,
        help_text="Unique identifier for the service object.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        help_text="Date the service object was added to the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        help_text="Last date the service object was updated in the database.",
    )
    service_source = models.TextField(
        db_column="service_source",
        blank=True,
        null=True,
        help_text="The source of the service, which scan identified the service.",
    )
    port = models.IntegerField(help_text="The port the service is running on.")
    service = models.TextField(blank=True, null=True, help_text="Name of the service.")
    last_seen = models.DateTimeField(
        db_column="last_seen",
        blank=True,
        null=True,
        help_text="Late date the service was seen running on the asset.",
    )
    banner = models.TextField(
        blank=True,
        null=True,
        help_text="Text that is automatically sent back to a client when they connect to the service.",
    )
    products = models.JSONField(help_text="Products identified running on the port.")
    censys_metadata = models.JSONField(
        db_column="censys_metadata",
        help_text="Metadata provided from the Censys scan of the service.",
    )
    censys_ipv4_results = models.JSONField(
        db_column="censys_ipv4_results",
        help_text="IPv4 results provided from the Censys scan of the service.",
    )
    intrigue_ident_results = models.JSONField(
        db_column="intrigue_ident_results",
        help_text="Additional details about the service provided by Intrigue scans.",
    )
    shodan_results = models.JSONField(
        db_column="shodan_results",
        help_text="Details about the service identified through the Shodan scan.",
    )
    wappalyzer_results = models.JSONField(
        db_column="wappalyzer_results",
        help_text="Details about the service identified by the wappalyzer scan.",
    )
    domain = models.ForeignKey(
        "Domain",
        models.DO_NOTHING,
        db_column="domain_id",
        blank=True,
        null=True,
        related_name="services",
        help_text="Foreign key relationship to the domain the service is running on.",
    )
    discovered_by = models.ForeignKey(
        Scan,
        models.DO_NOTHING,
        db_column="discovered_by_id",
        blank=True,
        null=True,
        help_text="Foreign key to the scan that discovered the service.",
    )

    class Meta:
        """The Meta class for Service."""

        app_label = app_label_name
        managed = False
        db_table = "mat_vw_service"
        unique_together = (("port", "domain"),)


class UserType(models.TextChoices):
    """User type definition."""

    GLOBAL_ADMIN = "globalAdmin"
    GLOBAL_VIEW = "globalView"
    REGIONAL_ADMIN = "regionalAdmin"
    STANDARD = "standard"


class User(AutoLengthCheckModel):
    """The User model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a user object.",
    )
    cognito_id = models.CharField(
        db_column="cognito_id",
        unique=True,
        blank=True,
        null=True,
        max_length=255,
        help_text="Identifier for the user in the cognito system. This is necessary to log into the cyhy dashboard application.",
    )
    cognito_username = models.CharField(
        max_length=255,
        db_column="cognito_username",
        blank=True,
        null=True,
        help_text="Username returned from Cognito decoded token.",
    )
    cognito_use_case_description = models.TextField(
        db_column="cognito_use_case_description",
        blank=True,
        null=True,
        help_text="Use case description for specified user from Cognito.",
    )
    cognito_email_verified = models.BooleanField(
        db_column="cognito_email_verified",
        default=False,
        blank=True,
        null=True,
        help_text="Email verified boolean returned from cognito token.",
    )
    cognito_groups = models.JSONField(
        db_column="cognitoGroups",
        null=True,
        blank=True,
        help_text="Cognito groups the user is a part of.",
    )
    login_gov_id = models.CharField(
        db_column="login_gov_id",
        unique=True,
        blank=True,
        null=True,
        max_length=255,
        help_text="Identifier  for the user in the login.gov system. This is also used to log in to the cyhy dashboard.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Date the user object was added to the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Last date the user object was updated in the database.",
    )
    first_name = models.CharField(
        db_column="first_name", max_length=255, help_text="First name of the user."
    )
    last_name = models.CharField(
        db_column="last_name", max_length=255, help_text="Last name of the user."
    )
    full_name = models.CharField(
        db_column="full_name", max_length=255, help_text="Full name of the user."
    )
    email = models.CharField(
        unique=True, max_length=255, help_text="User's email address."
    )
    invite_pending = models.BooleanField(
        db_column="invite_pending",
        default=False,
        help_text="A boolean field flagging if the user's invite is pending.",
    )
    first_login = models.BooleanField(
        db_column="first_login",
        default=True,
        help_text="A boolean field identifying a users first approved login for prompts.",
    )
    can_select_own_state = models.BooleanField(
        db_column="can_select_own_state",
        default=False,
        help_text="A boolean field identifying if a user has select their state/region.",
    )
    date_approved = models.DateTimeField(
        db_column="date_approved",
        blank=True,
        null=True,
        help_text="Date the user was approved to have access to the cyhy dashboard.",
    )
    approved_by = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="approved_by_id",
        blank=True,
        null=True,
        help_text="Foreign key to the user who approved the user.",
    )
    login_blocked_by_maintenance = models.BooleanField(
        db_column="login_blocked_by_maintenance",
        default=False,
        help_text="A boolean flag identifying whether the user is blocked by maintenance to login",
    )
    date_accepted_terms = models.DateTimeField(
        db_column="date_accepted_terms",
        blank=True,
        null=True,
        help_text="Date the user accepted the cyhy dashboard terms of service.",
    )
    accepted_terms_version = models.TextField(
        db_column="accepted_terms_version",
        blank=True,
        null=True,
        help_text="The version of the the terms of service the user accepted.",
    )
    last_logged_in = models.DateTimeField(
        db_column="last_logged_in",
        blank=True,
        null=True,
        help_text="Datetime the last time the user logged in.",
    )
    region_id = models.CharField(
        db_column="region_id",
        blank=True,
        null=True,
        max_length=255,
        help_text="What region the user belongs to.",
    )
    state = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="The state the user resides in.",
    )
    okta_id = models.CharField(
        db_column="okta_id",
        unique=True,
        blank=True,
        null=True,
        max_length=255,
        help_text="The Okta id associated with the user.",
    )
    user_type = models.CharField(
        db_column="user_type",
        max_length=50,
        choices=UserType.choices,
        default=UserType.STANDARD,
    )

    def save(self, *args, **kwargs):
        """Save user with full_name."""
        self.full_name = "{} {}".format(self.first_name, self.last_name)
        super().save(*args, **kwargs)

    class Meta:
        """The Meta class for User."""

        app_label = app_label_name
        managed = manage_db
        db_table = "user"


class Webpage(models.Model):
    """The Webpage model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for the webpage object.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        help_text="Date the webpage object was added to the database.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        help_text="Last date the webpage object was updated in the database.",
    )
    synced_at = models.DateTimeField(
        db_column="synced_at",
        blank=True,
        null=True,
        help_text="When this model was last synced with Elasticsearch.",
    )
    last_seen = models.DateTimeField(
        db_column="last_seen",
        blank=True,
        null=True,
        help_text="Last time the webpage was seen.",
    )
    s3_key = models.TextField(
        db_column="s3_key",
        blank=True,
        null=True,
        help_text="The AWS S3 key that corresponds to this webpage's contents.",
    )
    url = models.TextField(help_text="URL to the webpage.")
    status = models.DecimalField(
        max_digits=100, decimal_places=5, help_text="The status of the HTTP response."
    )
    response_size = models.DecimalField(
        db_column="response_size",
        max_digits=100,
        decimal_places=5,
        blank=True,
        null=True,
        help_text="The size of the url response.",
    )
    headers = models.JSONField(help_text="The header returned from the url response.")
    domain = models.ForeignKey(
        "SubDomains",
        models.DO_NOTHING,
        db_column="domain_id",
        blank=True,
        null=True,
        related_name="webpages",
        help_text="The domain associated with the webpage.",
    )
    discovered_by = models.ForeignKey(
        Scan,
        models.DO_NOTHING,
        db_column="discovered_by_id",
        blank=True,
        null=True,
        help_text="The scan that discovered the webpage.",
    )

    class Meta:
        """The Meta class for Webpage."""

        app_label = app_label_name
        managed = manage_db
        db_table = "webpage"
        unique_together = (("url", "domain"),)


# ########  VS Models  #########
class TicketEvent(models.Model):
    """The TicketEvent model."""

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="Unique id for a ticket event object in the database.",
    )
    reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="The identifier for the vulnerability scan related to the event",
    )
    vuln_scan = models.ForeignKey(
        "VulnScan",
        on_delete=models.CASCADE,
        db_column="vuln_scan_id",
        null=True,
        blank=True,
        related_name="ticket_events",
        help_text="A foreign key relationship to the Vuln scan related to the event.",
    )
    port_scan = models.ForeignKey(
        "PortScan",
        on_delete=models.CASCADE,
        db_column="port_scan_id",
        null=True,
        blank=True,
        related_name="ticket_events",
        help_text="A foreign key relationship to the Vuln scan related to the event.",
    )
    action = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Event action type. (OPENED, VERIFIED, CHANGED, CLOSED, REOPENED, UNVERIFIED)",
    )
    reason = models.TextField(
        null=True,
        blank=True,
        help_text="Short description of the event",
    )
    event_timestamp = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp indicating when the event occurred"
    )
    delta = models.JSONField(
        default=list, help_text="List of what changed; only applies to 'CHANGED' events"
    )
    ticket = models.ForeignKey(
        "Ticket",
        on_delete=models.CASCADE,
        db_column="ticket_id",
        null=True,
        blank=True,
        related_name="ticket_events",
        help_text="Foreign key relationship to the ticket the event references.",
    )

    class Meta:
        """The Meta class for TicketEvent."""

        app_label = app_label_name
        managed = manage_db
        indexes = [
            models.Index(fields=["ticket"]),
            models.Index(fields=["port_scan"]),
            models.Index(fields=["vuln_scan"]),
            models.Index(fields=["ticket", "port_scan"]),
            models.Index(fields=["ticket", "vuln_scan"]),
            models.Index(fields=["ticket", "-event_timestamp", "id"]),
        ]
        db_table = "ticket_event"
        unique_together = ("event_timestamp", "ticket", "action")


class VulnScan(AutoLengthCheckModel):
    """The VS Vuln Scan model."""

    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="Unique identifier for the webpage object.",
    )
    cert_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Id to look up a vulnerability int the CERT Vulnerability Notes Database. https://www.kb.cert.org/vuls/",
    )
    cpe = models.TextField(
        blank=True,
        null=True,
        help_text="Common Platform Enumeration (CPE) id for the product the vulnerability was found on.",
    )
    cve_string = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="CVE (Common Vulnerabilities and Exposures) id for the vulnerability.",
    )
    cve = models.ForeignKey(
        Cve,
        related_name="vuln_scans",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Foreign key relationship to the related CVE object.",
    )
    cvss_base_score = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Numerical value that measures the severity of a vulnerability using the Common Vulnerability Scoring System (CVSS)",
    )
    cvss_temporal_score = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Score representing a vulnerabilities urgency at specific points in time.",
    )
    cvss_temporal_vector = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="A textual representation of the metric values used to determine the temporal score.",
    )
    cvss_vector = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="A textual representation of the set of CVSS metrics.",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the vulnerability, according to the vulnerability scanner.",
    )
    exploit_available = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="A boolean field flagging whether or not an exploit is available, according to the vulnerability scanner.",
    )
    exploitability_ease = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Ease of exploitation, according to the vulnerability scanner.",
    )
    ip_string = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="IPv4 or IPv6 address where the vulnerability was identified.",
    )
    ip = models.ForeignKey(
        "Ip",
        related_name="vuln_scans",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Foreign key relationship to the related IP object.",
    )
    latest = models.BooleanField(
        default=False,
        help_text="A boolean field flagging if this is the latest vulnerability scan of this port/protocol/host.",
    )
    owner = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Acronym of the organization that claims the IP address associated with this vulnerability scan.",
    )
    osvdb_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Open Source Vulnerability Database identifier for the detected vulnerability.",
    )
    organization = models.ForeignKey(
        Organization,
        related_name="vuln_scans",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Foreign key relationship linking to the related Organization object.",
    )
    patch_publication_timestamp = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when a patch was published for this vulnerability",
    )
    cisa_known_exploited = models.DateTimeField(blank=True, null=True, help_text="????")
    port = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of the port that was vulnerability scanned",
    )
    port_protocol = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Protocol for the vulnerable port in this scan ('tcp' or 'udp')",
    )
    risk_factor = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Risk factor of the detected vulnerability according to the vulnerability scanner",
    )
    script_version = models.CharField(
        max_length=255, blank=True, null=True, help_text="Script version string"
    )
    see_also = models.TextField(
        blank=True,
        null=True,
        help_text="Additional reference(s) for this vulnerability provided by the vulnerability scanner",
    )
    service = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Service detected at the vulnerable port in this scan",
    )
    severity = models.IntegerField(
        blank=True,
        null=True,
        help_text="CVSS v2.0 severity rating from the vulnerability scanner.",
    )
    solution = models.TextField(
        blank=True,
        null=True,
        help_text="Solution to mitigate the detected vulnerability, according to the vulnerability scanner",
    )
    source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Source of the vulnerability scan (e.g. 'nessus').",
    )
    synopsis = models.TextField(
        blank=True,
        null=True,
        help_text="Brief overview of the vulnerability.",
    )
    vuln_detection_timestamp = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp indicating when the vulnerability was detected.",
    )
    vuln_publication_timestamp = models.DateTimeField(
        blank=True, null=True, help_text="Vulnerability publication date."
    )
    xref = models.TextField(blank=True, null=True, help_text="External reference.")
    cwe = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Common Weakness Enumeration (CWE) id for the weakness or vulnerability.",
    )
    bid = models.CharField(
        max_length=255, blank=True, null=True, help_text="Bugtraq ID"
    )
    exploited_by_malware = models.BooleanField(
        default=False,
        help_text="A boolean field to flag if the vuln type has been exploited by a known malware.",
    )
    thorough_tests = models.BooleanField(
        default=False,
        help_text="Boolean field to flag if more thorough tests have been run on the vulnerability for confirmation.",
    )
    cvss_score_rationale = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Rationale for the cvss score given to the vulnerability.",
    )
    cvss_score_source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The source that determined the cvss score for this vulnerability.",
    )
    cvss3_base_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="CVSS version 3 base score.",
    )
    cvss3_vector = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="A textual representation of the set of CVSS version 3 metrics.",
    )
    cvss3_temporal_vector = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="A textual representation of the metric values used to determine the temporal score.",
    )
    cvss3_temporal_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Score representing a vulnerabilities urgency at specific points in time.",
    )
    asset_inventory = models.BooleanField(default=False, help_text="????")
    plugin_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="ID of the plugin."
    )
    plugin_modification_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Latest modification date of the vulnerability scanner plugin that detected this vulnerability.",
    )
    plugin_publication_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Publication date of the vulnerability scanner plugin that detected this vulnerability.",
    )
    plugin_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the vulnerability scanner plugin that detected this vulnerability.",
    )
    plugin_type = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Vulnerability scanner plugin type.",
    )
    plugin_family = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Family of the plugin run by the vulnerability scanner that detected this vulnerability.",
    )
    f_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Filename of the vulnerability scanner plugin that detected this vulnerability.",
    )
    cisco_bug_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="??????"
    )
    cisco_sa = models.CharField(
        max_length=255, blank=True, null=True, help_text="??????"
    )
    plugin_output = models.TextField(
        blank=True,
        null=True,
        help_text="Plugin-specific output from the vulnerability scanner",
    )
    other_findings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data collected by the VS vuln scan that is not commonly seen.",
    )
    nmi_service_group = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the service group associated with this ticket (e.g. 'NMI')",
    )
    risky_service_group = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        """The Meta class for VulnScan."""

        app_label = app_label_name
        managed = manage_db
        db_table = "vuln_scan"


class VulnScanSummary(models.Model):
    """The VulnScanSummary Model."""

    summary_date = models.DateField(
        help_text="Date this summary represents (usually the date it was generated)."
    )
    start_date = models.DateTimeField(
        help_text="Timestamp of the earliest last_change in the collection",
        null=True,
        blank=True,
    )
    end_date = models.DateTimeField(
        help_text="Timestamp of the latest last_change in the collection",
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        Organization,
        related_name="vuln_scan_summaries",
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the organization the summary is built for.",
    )
    enrolled_in_vs_timestamp = models.DateTimeField(
        db_column="enrolled_in_vs_timestamp",
        null=True,
        blank=True,
        help_text="Date the stakeholder enrolled in VS.",
    )
    assets_owned_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of Ip addresses found within an organizations reported CIDR blocks.",
    )
    false_positive_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of tickets marked as false positive.",
    )
    vulnerable_host_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of Ip addresses that have an open ticket associated with them.",
    )
    unique_service_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of Ip addresses that have been scanned",
    )
    unique_low_severity_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of vulnerabilities with a severity of 1",
    )
    unique_medium_severity_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of vulnerabilities with a severity of 2",
    )
    unique_high_severity_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of vulnerabilities with a severity of 3",
    )
    unique_critical_severity_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of vulnerabilities with a severity of 4",
    )
    risky_services_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count risky services by port",
    )
    unsupported_software_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of hosts with unsupported software",
    )
    unique_os_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of unique operating systems identified running on org assets.",
    )
    low_severity_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of vulnerabilities with a severity of 1",
    )
    medium_severity_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of vulnerabilities with a severity of 2",
    )
    high_severity_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of vulnerabilities with a severity of 3",
    )
    critical_severity_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of vulnerabilities with a severity of 4",
    )
    critical_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open critical ticket.",
    )
    high_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open high ticket.",
    )
    medium_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open medium ticket.",
    )
    low_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open low ticket.",
    )
    low_kev_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of KEVs with a severity of low.",
    )
    medium_kev_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of KEVs with a severity of medium.",
    )
    high_kev_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of KEVs with a severity of high.",
    )
    critical_kev_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of KEVs with a severity of critical.",
    )
    kev_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open KEV ticket.",
    )
    critical_kev_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open critical KEV ticket.",
    )
    high_kev_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open high KEV ticket.",
    )
    medium_kev_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open medium KEV ticket.",
    )
    low_kev_max_age = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age of the longest open low KEV ticket.",
    )
    one_to_five_vulns_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of hosts that have 1 to 5 vulns.",
    )
    six_to_nine_vulns_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of hosts that have 6 to 9 vulns.",
    )
    ten_plus_vulns_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of hosts that have 10+ vulns.",
    )
    top_5_occurring_cves = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="Dictionary containing top 5 occuring CVEs vulns",
    )
    top_5_occurring_kevs = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="Dictionary containing top 5 KEV CVEs.",
    )
    included_tickets = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dictionary of ticket IDs to metadata (e.g., severity, is_kev) at the time of summary.",
    )
    top_5_risky_hosts = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dictionary containing top 5 risky hosts based on severity and the count number of tickets at each severity level.",
    )

    class Meta:
        """The Meta class for VulnScan."""

        app_label = app_label_name
        managed = manage_db
        db_table = "vuln_scan_summary"
        unique_together = (("summary_date", "organization"),)


class Cidr(models.Model):
    """The Cidr Model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique idenifier for the Cidr object.",
    )
    created_date = models.DateTimeField(
        auto_now_add=True, help_text="Date the cidr object was added to the database."
    )
    network = InetAddressField(
        null=True, blank=True, unique=True, help_text="The cidr block"
    )  # models.TextField()  # This field type is a guess.
    start_ip = InetAddressField(
        null=True, blank=True, help_text="The first IP address in the cidr block."
    )
    end_ip = InetAddressField(
        null=True, blank=True, help_text="The last IP address in the cidr block."
    )
    retired = models.BooleanField(
        null=True,
        blank=True,
        help_text="A boolean field flagging if the cidr has been retired.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="The last time the cidr object was updated in the database.",
    )
    insert_alert = models.TextField(
        blank=True,
        null=True,
        help_text="An alert message specifying any conflicts when inserting the cidr into the database.",
    )
    live_ips = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="A list of live IP addresses associated with this CIDR block.",
    )
    data_source = models.ForeignKey(
        "DataSource",
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        blank=True,
        null=True,
        help_text="Foreign key relationship to the data source that inserted the cidr object.",
    )
    organizations = models.ManyToManyField(
        Organization,
        through="CidrOrgs",
        related_name="cidrs",
        blank=True,
        help_text="Foreign key relationship to the organization that owns the cidr object.",
    )

    class Meta:
        """The Meta class for Cidr."""

        app_label = app_label_name
        managed = manage_db
        db_table = "cidr"
        indexes = [models.Index(fields=["network"])]


class CidrOrgs(models.Model):
    """Define CidrOrgs model."""

    cidr_orgs_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    cidr = models.ForeignKey(
        Cidr,
        on_delete=models.CASCADE,
        help_text="FK: Foreign key to the Cidr associated with the organization.",
        related_name="cidrorgs",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        help_text="FK: Foreign key to the Organization associated with the Cidr.",
        related_name="cidrorgs",
    )
    first_seen = models.DateField(
        blank=True,
        null=True,
        help_text="First date and time the cidr was associated with the organization.",
        auto_now_add=True,
    )
    last_seen = models.DateField(
        blank=True,
        null=True,
        help_text="Last date and time the cidr was associated with the organization.",
    )
    current = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field flagging if the cidr organization relationship has been recently seen",
    )

    class Meta:
        """Set CidrOrgs model metadata."""

        managed = manage_db
        db_table = "cidr_orgs"
        unique_together = (("cidr", "organization"),)


class Location(AutoLengthCheckModel):
    """The Location model."""

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="Unique identifier for a location object.",
    )
    name = models.CharField(
        max_length=255, null=True, blank=True, help_text="Name of the location."
    )
    country_abrv = models.CharField(
        max_length=255, null=True, blank=True, help_text="Country abbreviation."
    )
    country = models.CharField(
        max_length=255, null=True, blank=True, help_text="Full name of the country."
    )
    county = models.CharField(
        max_length=255, null=True, blank=True, help_text="Name of the county."
    )
    county_fips = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Federal Information Processing Standards code for the US county where the organization is found.",
    )
    gnis_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        help_text="(Geographic Names Information System ID) is a unique identifier assigned to geographic features in the GNIS database.",
    )
    state_abrv = models.CharField(
        max_length=255, null=True, blank=True, help_text="State abbreviation."
    )
    state_fips = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Federal Information Processing Standards code for the US state where the organization is found.",
    )
    state = models.CharField(
        max_length=255, null=True, blank=True, help_text="Full name of the state."
    )

    class Meta:
        """The Meta class for Location."""

        app_label = app_label_name
        managed = manage_db
        db_table = "location"
        indexes = [models.Index(fields=["gnis_id"])]


class Sector(models.Model):
    """The Sector model."""

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="Unique identifier for a sector object in the database.",
    )
    name = models.CharField(
        max_length=255, null=True, blank=True, help_text="The name of the sector."
    )
    acronym = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        help_text="The short name of the sector.",
    )
    retired = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field flagging if the sector has been retired.",
    )

    organizations = models.ManyToManyField(
        Organization,
        related_name="sectors",
        blank=True,
        help_text="Many to many relationship between sectors and organizations.",
    )

    class Meta:
        """The Meta class for Sector."""

        app_label = app_label_name
        managed = manage_db
        db_table = "sector"
        indexes = [models.Index(fields=["acronym"])]


class Host(models.Model):
    """The Host model."""

    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="Unique identifier for a host object in the database.",
    )
    ip_string = models.CharField(
        max_length=255, null=True, blank=True, help_text="The IP address of the host."
    )
    ip = models.ForeignKey(
        "Ip",
        related_name="hosts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Foreign key relationship to the related model.",
    )
    updated_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last time the host object was updated.",
    )
    latest_netscan_1_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamps indicating last time host completed the NETSCAN1.",
    )
    latest_netscan_2_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamps indicating last time host completed the NETSCAN2.",
    )
    latest_vulnscan_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamps indicating last time host completed the PORTSCAN.",
    )
    latest_portscan_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamps indicating last time host completed the VULNSCAN.",
    )
    latest_scan_completion_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamps indicating last time host completed all scans.",
    )
    location_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude of host, according to geolocation database",
    )
    location_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude of host, according to geolocation database",
    )
    priority = models.IntegerField(
        null=True,
        blank=True,
        help_text="Scan priority of this host document, from -16 (most urgent) to 1 (least urgent)",
    )
    next_scan_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp indicating when this host document is scheduled to be scanned next; a value of null indicates that the host document has a status other than 'DONE' (i.e. currently queued up for a scan or running a scan)",
    )
    rand = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="A random number between 0 and 1 used to randomize scan order",
    )
    curr_stage = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Current scan stage for this host document",
    )
    host_live = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether or not a live host was detected at this host document’s IP address by the port scanner",
    )
    host_live_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Reason given by the port scanner as to whether or not this host document represents a live host",
    )
    status = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Current scan status for this host document. (WAITING, READY, RUNNING, DONE)",
    )
    organization = models.ForeignKey(
        Organization,
        related_name="hosts",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Foreign key relationship to the organization that owns the host.",
    )

    class Meta:
        """The Meta class for Host."""

        app_label = app_label_name
        managed = manage_db
        db_table = "host"
        indexes = [
            models.Index(fields=["ip_string"]),
        ]


class HostSummary(models.Model):
    """Define HostSummary model."""

    summary_date = models.DateField(
        help_text="Date this summary represents (usually the date it was generated)."
    )
    start_date = models.DateTimeField(
        help_text="Timestamp of the earliest last_change in the collection",
    )
    end_date = models.DateTimeField(
        help_text="Timestamp of the latest last_change in the collection",
    )
    organization = models.ForeignKey(
        Organization,
        related_name="host_summaries",
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the organization the summary is built for.",
    )
    host_done_count = models.IntegerField(
        null=True, blank=True, help_text="Number of the hosts with a status of DONE."
    )
    host_waiting_count = models.IntegerField(
        null=True, blank=True, help_text="Number of the hosts with a status of WAITING."
    )
    host_running_count = models.IntegerField(
        null=True, blank=True, help_text="Number of the hosts with a status of RUNNING."
    )
    host_ready_count = models.IntegerField(
        null=True, blank=True, help_text="Number of the hosts with a status of READY."
    )
    up_host_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of the hosts that were live in the last scan.",
    )
    down_host_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of the hosts that were down in the last scan.",
    )
    scanned_asset_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Count of Ip addresses that have been scanned",
    )
    port_scan_min_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the oldest port_scan run on a host owned by the org.",
    )
    port_scan_max_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent port_scan run on a host owned by the org.",
    )
    vuln_scan_min_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the oldest vuln_scan run on a host owned by the org.",
    )
    vuln_scan_max_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent vuln_scan run on a host owned by the org.",
    )
    net_scan1_min_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the oldest net_scan1 run on a host owned by the org.",
    )
    net_scan1_max_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent net_scan1 run on a host owned by the org.",
    )
    net_scan2_min_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the oldest net_scan2 run on a host owned by the org.",
    )
    net_scan2_max_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent net_scan2 run on a host owned by the org.",
    )

    class Meta:
        """The Meta class for HostSummary."""

        app_label = app_label_name
        managed = manage_db
        db_table = "host_summary"
        unique_together = (("organization", "summary_date"),)


class Ip(models.Model):
    """The Ip model."""

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="Unique identifier for an IP object in the database.",
    )
    ip_hash = models.TextField(
        help_text="A hash of the IP used as a unique identifier."
    )
    organization = models.ForeignKey(
        Organization,
        related_name="ips",
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the organization that owns the IP.",
    )
    created_timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp the cidr object was added to the database.",
    )
    updated_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=True,
        help_text="Timestamp of the last time the IP object was updated.",
    )
    last_seen_timestamp = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of the last time the IP was seen."
    )
    ip = models.GenericIPAddressField(
        null=True, blank=True, help_text="The IP address."
    )
    ip_version = models.CharField(
        max_length=4,  # max_length of 'IPv4' or 'IPv6'
        choices=[("IPv4", "IPv4"), ("IPv6", "IPv6")],
        default="IPv4",  # Optional, you can set a default if you'd like
    )
    live = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if the IP is live as of the last scan.",
    )
    false_positive = models.BooleanField(
        null=True,
        blank=True,
        help_text="A boolean field that marks if the IP was incorrectly attributed to the stakeholder.",
    )
    retired = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if the IP is no longer owned by the organization.",
    )
    last_reverse_lookup = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last time a reverse lookup was run against the IP.",
    )
    from_cidr = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field that flags if the IP came from a stakeholder provided cidr.",
    )
    origin_cidr = models.ForeignKey(
        Cidr,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Foreign key relationship to the cidr from which the ip was enumerated.",
    )
    sub_domains = models.ManyToManyField(
        "SubDomains",
        through="IpsSubs",
        help_text="Many to many linking ips to the sub domain table.",
    )
    has_shodan_results = models.BooleanField(
        blank=True,
        null=True,
        help_text="A boolean field that flags if shodan has findings for the givenn IP",
    )
    current = models.BooleanField(
        blank=True,
        null=True,
        help_text="A boolean field that flags if the IP is current.",
    )
    conflict_alerts = models.JSONField(
        blank=True, null=True, default=list, help_text="List of cidr conflict alerts."
    )
    synced_at = models.DateTimeField(db_column="synced_at", blank=True, null=True)

    def save(self, *args, **kwargs):
        """Save ip_version based on the saved ip."""
        # Automatically set ip_version based on ip_address
        if self.ip:
            # Check if the IP is IPv4 or IPv6
            try:
                socket.inet_pton(socket.AF_INET, self.ip)
                self.ip_version = "IPv4"
            except OSError:
                try:
                    socket.inet_pton(socket.AF_INET6, self.ip)
                    self.ip_version = "IPv6"
                except OSError:
                    LOGGER.exception("Invalid IP address: %s", self.ip)
                    raise ValueError

        super().save(*args, **kwargs)

    class Meta:
        """The Meta class for Ip."""

        app_label = app_label_name
        managed = manage_db
        db_table = "ip"
        indexes = [models.Index(fields=["ip", "organization"])]
        unique_together = ["ip", "organization"]


class IpsSubs(models.Model):
    """Define IpsSubs model."""

    ips_subs_uid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ip = models.ForeignKey(
        Ip, on_delete=models.CASCADE, db_column="ip_id", related_name="ipssubs"
    )
    sub_domain = models.ForeignKey(
        "SubDomains",
        on_delete=models.CASCADE,
        db_column="sub_domain_id",
        related_name="ipssubs",
    )
    first_seen = models.DateTimeField(
        blank=True,
        null=True,
        help_text="First date and time the ip was associated with the subdomain.",
        auto_now_add=True,
    )
    last_seen = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last date and time the ip was associated with the subdomain.",
    )
    current = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field flagging if the ip subdomain relationship has been recently seen",
    )

    class Meta:
        """Set IpsSubs model metadata."""

        managed = manage_db
        db_table = "ips_subs"
        unique_together = (("ip", "sub_domain"),)


class Ticket(models.Model):
    """The Ticket model."""

    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="Unique identifier for a ticket object in the database.",
    )  # Assuming the UUID is represented as a string
    cve_string = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="CVE (Common Vulnerabilities and Exposures) id for the vulnerability.",
    )
    cve = models.ForeignKey(
        Cve,
        related_name="tickets",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the related CVE object.",
    )
    cvss_base_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="CVSS base score](https://nvd.nist.gov/vuln-metrics)",
    )
    cvss_version = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="CVSS version used for the CVSS base score",
    )
    vuln_name = models.CharField(
        max_length=255, null=True, blank=True, help_text="Vulnerability name"
    )
    cvss_score_source = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Source of the CVSS base score (e.g. 'nvd' or 'nessus')",
    )
    cvss_severity = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="[CVSS severity rating](https://nvd.nist.gov/vuln-metrics)",
    )
    vpr_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tenable [Vulnerability Priority Rating](https://docs.tenable.com/nessus/Content/RiskMetrics.htm)",
    )
    false_positive = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if this ticket is marked as a false positive?",
    )
    ip_string = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="IP address of the host that was vulnerability scanned",
    )
    ip = models.ForeignKey(
        Ip,
        related_name="tickets",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the related IP object.",
    )
    updated_timestamp = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of when the ticket was last updated"
    )
    location_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude of host (according to geolocation database) associated with this ticket",
    )
    location_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude of host (according to geolocation database) associated with this ticket",
    )
    found_in_latest_host_scan = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if this vulnerability was detected in the latest scan of the associated host?",
    )
    organization = models.ForeignKey(
        Organization,
        related_name="tickets",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the organization that owns the asset that was scanned.",
    )
    vuln_port = models.IntegerField(
        null=True, blank=True, help_text="Number of the vulnerable port in this ticket."
    )
    port_protocol = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Protocol for the vulnerable port in this ticket ('tcp' or 'udp')",
    )
    snapshots_bool = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if there are snapshots that include this ticket",
    )
    vuln_source = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Source of the vulnerability scan (e.g. 'nessus' or 'nmap')",
    )
    vuln_source_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Source-specific identifier for the vulnerability scan (e.g. the scanner plugin identifier that detected the vulnerability)",
    )
    closed_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this ticket was closed (vulnerability was no longer detected); value of null indicates that this ticket is currently open",
    )
    opened_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this ticket was opened (vulnerability was first detected)",
    )
    is_open = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if this ticket open or closed   ",
    )
    is_kev = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if this ticket is a KEV (Known Exploited Vulnerability) ticket",
    )
    is_kev_ransomware = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if this ticket is a KEV and known to be ransomware.",
    )
    is_risky = models.BooleanField(
        null=True,
        blank=True,
        help_text="Boolean field that flags if this ticket is a risky ticket",
    )
    service_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the service associated with this ticket",
    )
    nmi_service_group = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the service group associated with this ticket (e.g. 'NMI')",
    )
    risky_service_group = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    operating_system = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of operating system identified by port scan for the ip of the ticket.",
    )

    class Meta:
        """The Meta class for Ticket."""

        app_label = app_label_name
        managed = manage_db
        indexes = [
            # 1. Ensure fast lookup by ticket id for upserts
            models.Index(fields=["id"], name="tickets_id_idx"),
            # 2. Optional: fast filtering on IP (if you query per IP)
            models.Index(fields=["ip_string"], name="tickets_ip_idx"),
            # 3. Optional: cover “open” tickets if you often filter by is_open
            models.Index(fields=["is_open"], name="tickets_is_open_idx"),
        ]
        db_table = "ticket"
        unique_together = ["id"]


class CisaKevCatalog(models.Model):
    """Define CISA KEV Catalog model."""

    cisa_kev_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for each KEV record.",
    )
    cve_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="CVE ID of the known exploited vulnerability.",
    )
    vendor_project = models.CharField(
        max_length=255,
        help_text="Name of the vendor or project associated with the vulnerability.",
    )
    product = models.CharField(
        max_length=255, help_text="Name of the affected product."
    )
    vulnerability_name = models.CharField(
        max_length=255, help_text="Name or brief title of the vulnerability."
    )
    date_added = models.DateField(
        help_text="Date the vulnerability was added to the KEV catalog."
    )
    short_description = models.TextField(
        help_text="Brief description of the vulnerability."
    )
    required_action = models.TextField(
        help_text="Recommended remediation or mitigation action."
    )
    due_date = models.DateField(
        null=True, blank=True, help_text="Due date for action if provided."
    )
    notes = models.TextField(
        null=True, blank=True, help_text="Additional notes or remarks."
    )
    cwe_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Common Weakness Enumeration (CWE) ID related to the CVE.",
    )
    known_ransomware_campaign_use = models.BooleanField(
        default=False,
        help_text="Flag indicating if the CVE is known to be used in ransomware campaigns.",
    )
    vulnerability_publish_date = models.DateField(
        null=True, blank=True, help_text="Original publish date of the vulnerability."
    )

    class Meta:
        """Set model metadata for Mini Data Lake."""

        app_label = app_label_name
        managed = manage_db
        db_table = "cisa_kev_catalog"


class PortScan(AutoLengthCheckModel):
    """The PortScan model."""

    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="Unique identifier for the port scan object.",
    )  # Assuming UUIDs are stored as strings
    ip_string = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="IP address of the host that was port scanned",
    )
    ip = models.ForeignKey(
        Ip,
        related_name="port_scans",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the related IP.",
    )
    latest = models.BooleanField(
        default=False,
        help_text="Booolean field that flags if this is the latest scan of this port.",
    )
    port = models.IntegerField(
        null=True, blank=True, help_text="Number of the port that was scanned."
    )
    protocol = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Protocol for this port scan ('tcp' or 'udp').",
    )
    reason = models.TextField(
        null=True,
        blank=True,
        help_text="Why this port is determined to be open, as reported by the port scanner.",
    )
    service = models.JSONField(
        default=dict, help_text="Details about this port, as reported by the scanner"
    )  # Use JSONField to store JSON objects
    service_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Source of the scan (e.g. 'nmap')",
    )
    service_confidence = models.IntegerField(
        null=True, blank=True, help_text="Level of confidence the service is running."
    )
    service_method = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="The method that was used to identify the service on the port.",
    )
    service_cpe = models.TextField(
        null=True,
        blank=True,
        help_text="The cpe of the product associated with the service on the port.",
    )
    service_hostname = models.TextField(
        null=True,
        blank=True,
        help_text="The hostname running the service on the port.",
    )
    service_extra_info = models.TextField(
        null=True,
        blank=True,
        help_text="Additional info provided by the port scanner.",
    )
    service_os_type = models.TextField(
        null=True,
        blank=True,
        help_text="OS identified running the service",
    )
    service_product = models.TextField(
        null=True,
        blank=True,
        help_text="Product identified by service scanner.",
    )
    service_version = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Version of the product identified.",
    )
    service_tunnel = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Additional info provided by the port scanner.",
    )
    service_device_type = models.TextField(
        null=True,
        blank=True,
        help_text="Product identified by service scanner.",
    )
    source = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Source of the scan (e.g. 'nmap')",
    )
    state = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="State of the port, as reported by the scanner; see nmap states",
    )
    time_scanned = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when the port was scanned"
    )
    organization = models.ForeignKey(
        Organization,
        related_name="port_scans",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the organization that owns the scanned IP.",
    )
    nmi_service_group = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the service group associated with this ticket (e.g. 'NMI')",
    )
    risky_service_group = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        """The Meta class for PortScan."""

        app_label = app_label_name
        managed = manage_db
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["time_scanned"]),
            models.Index(
                fields=["organization", "ip_string", "port", "-time_scanned"],
                name="portscan_latest_lookup_idx",
            ),
            models.Index(
                fields=["organization", "ip_string", "port", "latest"],
                name="portscan_latest_idx",
            ),
            models.Index(
                fields=["organization", "ip_string", "port", "time_scanned"],
                name="portscan_latest_true_idx",
                condition=models.Q(latest=True),
            ),
        ]
        db_table = "port_scan"


class PortScanSummary(models.Model):
    """Define PortScanSummary model."""

    start_date = models.DateTimeField(
        help_text="Timestamp of the earliest vuln_detection timestamp",
    )
    end_date = models.DateTimeField(
        help_text="Timestamp of the latest vuln_detection timestamp",
    )
    summary_date = models.DateField(
        help_text="Date this summary represents (usually the date it was generated)."
    )
    organization = models.ForeignKey(
        Organization,
        related_name="port_scan_summaries",
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the organization the port scan summary is built for.",
    )
    open_port_count = models.IntegerField(
        null=True, blank=True, help_text="Number of open ports."
    )
    risky_port_count = models.IntegerField(
        null=True, blank=True, help_text="Number of risky ports."
    )
    nmi_service_count = models.IntegerField(
        null=True, blank=True, help_text="Number of NMI services."
    )
    unique_ip_count = models.IntegerField(
        null=True, blank=True, help_text="Number of unique ips."
    )
    unique_service_count = models.IntegerField(
        null=True, blank=True, help_text="Number of unique services."
    )
    risky_service_group_counts = models.JSONField(
        null=True,
        blank=True,
        help_text="Dictionary of risky_service_group values and their counts",
    )

    class Meta:
        """The Meta class for PortScanSummary."""

        app_label = app_label_name
        managed = manage_db
        db_table = "port_scan_summary"
        unique_together = (
            ("organization", "summary_date"),
        )  # datetime_pulled_from_redshift


class PortScanServiceSummary(models.Model):
    """Define PortScanServiceSummary model."""

    start_date = models.DateTimeField(
        help_text="Timestamp of the earliest vuln_detection timestamp",
    )
    end_date = models.DateTimeField(
        help_text="Timestamp of the latest vuln_detection timestamp",
    )
    summary_date = models.DateField(
        help_text="Date this summary represents (usually the date it was generated)."
    )
    organization = models.ForeignKey(
        Organization,
        related_name="port_scan_service_summaries",
        on_delete=models.CASCADE,
        help_text="Foreign key relationship to the organization the port scan summary is built for.",
    )
    service_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the service the summary row is tracking.",
    )
    risky_ports = models.JSONField(
        blank=True,
        null=True,
        default=dict,  # or list
        help_text="Dictionary or list of risky ports running the service.",
    )
    unique_ip_count = models.IntegerField(
        null=True, blank=True, help_text="Number of unique ips."
    )
    unique_service_count = models.IntegerField(
        null=True, blank=True, help_text="Number of unique services."
    )

    class Meta:
        """The Meta class for PortScanServiceSummary."""

        app_label = app_label_name
        managed = manage_db
        db_table = "port_scan_service_summary"
        unique_together = (
            ("organization", "summary_date", "service_name"),
        )  # datetime_pulled_from_redshift


class WasTrackerCustomerdata(models.Model):
    """Define WasTrackerCustomerdata model."""

    customer_id = models.UUIDField(
        db_column="customer_id",
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a Was customer.",
    )
    tag = models.TextField(
        help_text="Short name of the customer used to query reports, ideally shoulud match ServiceNow, PE and VS."
    )
    customer_name = models.TextField(help_text="Full name of the WAS customer.")
    testing_sector = models.TextField(help_text="The sector the customer falls under.")
    ci_type = models.TextField(help_text="Critical infrastructure classification.")
    jira_ticket = models.TextField(help_text="???")
    ticket = models.TextField(help_text="???")
    next_scheduled = models.TextField(
        help_text="The next date and time the customer's webapps will be scanned."
    )
    last_scanned = models.TextField(
        help_text="The last date and time the customer's webapps were scanned."
    )
    frequency = models.TextField(help_text="The frequency the WAS reports are run.")
    comments_notes = models.TextField(
        help_text="Additional comments and notes about how and when to run the report."
    )
    was_report_poc = models.TextField(help_text="Customer's point of contact.")
    was_report_email = models.TextField(
        help_text="Email address(es) that WAS reports are delivered to."
    )
    onboarding_date = models.TextField(
        help_text="Date that the customer was added to the WAS service."
    )
    no_of_web_apps = models.IntegerField(
        help_text="Number of webapps the customer has submitted to be scanned."
    )
    no_web_apps_last_updated = models.TextField(
        blank=True,
        null=True,
        help_text="The last datetime that the number of apps was updated.",
    )
    elections = models.BooleanField(
        blank=False,
        null=False,
        help_text="Boolean field that flags if the customer is an election entity.",
    )
    fceb = models.BooleanField(
        blank=False,
        null=False,
        help_text="Boolean field that flags if the customer is an FCEB entity.",
    )
    special_report = models.BooleanField(
        blank=False,
        null=False,
        help_text="Boolean field that flags if the customer receives a special report.",
    )
    report_password = models.TextField(
        help_text="The password used to encrypt the WAS report."
    )
    child_tags = models.TextField(help_text="List of tags of any child customers.")

    class Meta:
        """Set WasTrackerCustomerdata model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "was_tracker_customer_data"


class WasFindings(models.Model):
    """Define WasFindings model."""

    finding_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a WAS finding object.",
    )
    finding_type = models.TextField(
        blank=True,
        null=True,
        help_text="Type of WAS finding. (INFORMATION_GATHERED, SENSITIVE_CONTENT, VULNERABILITY)",
    )
    webapp_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="Identifier for the webapp on which the finding was found.",
    )
    was_org_id = models.TextField(
        blank=True,
        null=True,
        help_text="Acronym of the customer who owns the scanned webapp.",
    )
    owasp_category = models.TextField(
        blank=True,
        null=True,
        help_text="OWASP (Open Web Application Security Project) categorization of the finding.",
    )
    severity = models.TextField(
        blank=True, null=True, help_text="Severity of the finding, rated 1-5."
    )
    times_detected = models.IntegerField(
        blank=True, null=True, help_text="How many times the finding has been seen."
    )
    base_score = models.FloatField(
        blank=True, null=True, help_text="Base CVSS score for the finding."
    )
    temporal_score = models.FloatField(
        blank=True, null=True, help_text="Temporal CVSS score for the finding."
    )
    fstatus = models.TextField(
        blank=True,
        null=True,
        help_text="Status of finding. (NEW, ACTIVE, REOPENED, FIXED)",
    )
    last_detected = models.DateField(
        blank=True, null=True, help_text="The last time the finding was seen."
    )
    first_detected = models.DateField(
        blank=True, null=True, help_text="The first time the finding was seen."
    )
    is_remediated = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field flagging if the fiding has been remediated.",
    )
    potential = models.BooleanField(blank=True, null=True, help_text="???")
    webapp_url = models.TextField(
        blank=True,
        null=True,
        help_text="URL of the webapp where the finding was identified.",
    )
    webapp_name = models.TextField(
        blank=True,
        null=True,
        help_text="Name of the webapp where the finding was identified.",
    )
    name = models.TextField(blank=True, null=True, help_text="Name of the finding.")
    cvss_v3_attack_vector = models.TextField(
        blank=True,
        null=True,
        help_text="Vector of the attack. (Adjacent Network, Local Access, Network, None)",
    )
    cwe_list = ArrayField(
        models.IntegerField(blank=True, null=True),
        blank=True,
        null=True,
        help_text="List of CWEs identified in the finding.",
    )
    wasc_list = models.JSONField(
        blank=True,
        null=True,
        help_text="List of dictionaries containing links to relevant WASC (Web Application Security Consortium) references.",
    )
    last_tested = models.DateField(
        blank=True, null=True, help_text="Last time the finding was tested."
    )
    fixed_date = models.DateField(
        blank=True, null=True, help_text="Date the finding was remediated."
    )
    is_ignored = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field flagging if the customer has decided to ignore the finding.",
    )
    url = models.TextField(
        blank=True, null=True, help_text="URL where the finding was identified."
    )
    qid = models.IntegerField(
        blank=True, null=True, help_text="Qualys id for the finding."
    )
    response = models.TextField(
        blank=True, null=True, help_text="The returned response from the webapp."
    )
    sub_domain = models.ForeignKey(
        "SubDomains",
        on_delete=models.CASCADE,
        db_column="sub_domain_id",
        blank=True,
        null=True,
        help_text="FK: Foreign Key to the linked subdomain",
    )
    cve = models.ForeignKey(
        "Cve",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="was_findings",
        help_text="FK: CVE linked to this finding.",
    )

    class Meta:
        """Set WasFindings model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "was_findings"


class WasHistory(models.Model):
    """Define WasHistory model."""

    was_org_id = models.TextField(
        blank=True, null=True, help_text="Unique identifier for the WAS history object."
    )
    date_scanned = models.DateField(
        help_text="The date a customers webapps were scanned."
    )
    vuln_cnt = models.IntegerField(
        blank=True,
        null=True,
        help_text="A count of how many vulnerabilities were identified.",
    )
    vuln_webapp_cnt = models.IntegerField(
        blank=True, null=True, help_text="The count of how many webapps are vulnerable."
    )
    web_app_cnt = models.IntegerField(
        blank=True,
        null=True,
        help_text="Count of how many webapps were scanned for the customer.",
    )
    high_rem_time = models.IntegerField(
        blank=True,
        null=True,
        help_text="Average time it took to remediate vulnerabilities with a high severity.",
    )
    crit_rem_time = models.IntegerField(
        blank=True,
        null=True,
        help_text="Average time it took to remediate vulnerabilities with a critical severity.",
    )
    crit_vuln_cnt = models.IntegerField(
        blank=True,
        null=True,
        help_text="A count of how many vulnerabilites have a critical severity.",
    )
    high_vuln_cnt = models.IntegerField(
        blank=True,
        null=True,
        help_text="A count of how many vulnerabilites have a high severity.",
    )
    report_period = models.DateField(
        blank=True,
        null=True,
        help_text="The report period these findings were identified within.",
    )
    high_rem_cnt = models.IntegerField(
        blank=True,
        null=True,
        help_text="A count of how many high severity vulnerabiliteis were remediated.",
    )
    crit_rem_cnt = models.IntegerField(
        blank=True,
        null=True,
        help_text="A count of how many critical severity vulnerabiliteis were remediated.",
    )
    total_potential = models.IntegerField(
        blank=True,
        null=True,
        help_text="A count of all potential vulnerabilities there are across a customer's webapps.",
    )

    class Meta:
        """Set WasHistory model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "was_history"
        unique_together = (("was_org_id", "date_scanned"),)


class WasMap(models.Model):
    """Define WasMap model."""

    was_org_id = models.TextField(
        blank=True, primary_key=True, help_text="WAS customer acronym."
    )
    pe_org_id = models.UUIDField(
        blank=True, null=True, help_text="Corresponding PE organization acronym"
    )
    report_on = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field flagging if the organization receives a report???",
    )  # Not sure if this is a PE or WAS report.
    last_scanned = models.DateField(
        blank=True,
        null=True,
        help_text="Last time the organization was scanned by WAS.",
    )

    class Meta:
        """Set WasMap model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "was_map"


class WasReport(models.Model):
    """The WasReport model."""

    org_name = models.TextField(
        blank=True, null=True, help_text="Name of the WAS customer."
    )
    date_pulled = models.DateTimeField(
        blank=True, null=True, help_text="Date the was report wasw pulled from Qualys."
    )
    last_scan_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last time WAS ran a Qualys scan on the organization's webapps.",
    )
    security_risk = models.TextField(
        blank=True, null=True, help_text="Security risk the customer's webapps face."
    )
    total_info = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of findings found across the customer's webapps.???",
    )
    num_apps = models.IntegerField(
        blank=True, null=True, help_text="Number of webapps scanned in this report."
    )
    risk_color = models.TextField(
        blank=True,
        null=True,
        help_text="Color code for the risk level presented in the reports.",
    )
    sensitive_count = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of sensitive findings included inn the report.???",
    )
    sensitive_color = models.TextField(
        blank=True,
        null=True,
        help_text="Color code for the sensitivity level presented in the report.",
    )
    max_days_open_urgent = models.IntegerField(
        blank=True,
        null=True,
        help_text="The maximum days an urgent finding has remained open.",
    )
    max_days_open_critical = models.IntegerField(
        blank=True,
        null=True,
        help_text="The maximum days a critical finding has remained open.",
    )
    urgent_color = models.TextField(
        blank=True,
        null=True,
        help_text="Color code used to display urgent details in the report.",
    )
    critical_color = models.TextField(
        blank=True,
        null=True,
        help_text="Color code used to display critical details in the report.",
    )
    org_was_acronym = models.TextField(
        blank=True,
        null=True,
        help_text="Acronym or short name of the organization receiving the report.",
    )
    name_len = models.TextField(
        blank=True,
        null=True,
        help_text="Number of characters in the organization's name.",
    )
    vuln_csv_dict = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dictionary containing counts of each type of vulnerability for each webapp",
    )
    ssn_cc_dict = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dictionary containing counts of credit card and social security data found on the customer's webapps.",
    )
    app_overview_csv_dict = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dictionary containing an overview of the apps urls and findings.",
    )
    details_csv = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of additional details regarding the findings in the report.???",
    )
    info_csv = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of Finding information for each of the findings in the report.",
    )
    links_crawled = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of links crawled including duration of time and depth of the crawl.",
    )
    links_rejected = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of rejecting links and which webapp they were from.???",
    )
    emails_found = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of emails found in each webapp.",
    )
    owasp_count_dict = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dictionary that counts each of the OWASP categories for each webapp.???",
    )
    group_count_dict = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dictionary counting the sums of each OWASP category for all webapps.",
    )
    fixed = models.IntegerField(
        blank=True,
        null=True,
        help_text="Count of fixed vulns in all webapps owned by the organization.",
    )
    total = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total vulnerability count across all webapps owned by the organization.",
    )
    vulns_monthly_dict = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Dictionary summing each of the findings by month they were found.",
    )
    path_disc = models.IntegerField(blank=True, null=True, help_text="???")
    info_disc = models.IntegerField(blank=True, null=True, help_text="???")
    cross_site = models.IntegerField(
        blank=True,
        null=True,
        help_text="Count of cross site scripting vulnerabilities.",
    )
    burp = models.IntegerField(
        blank=True, null=True, help_text="Vulnerabilities detected by BURP.???"
    )
    sql_inj = models.IntegerField(
        blank=True, null=True, help_text="Count of SQL injection vulnerabilities."
    )
    bugcrowd = models.IntegerField(
        blank=True, null=True, help_text="Vulnerabilities detected by Bugcrowd."
    )
    reopened = models.IntegerField(
        blank=True, null=True, help_text="Count of reopened vulnerabilities."
    )
    reopened_color = models.TextField(
        blank=True, null=True, help_text="Color used to display the reopened count."
    )
    new_vulns = models.IntegerField(
        blank=True, null=True, help_text="Count of new vulnerablities"
    )
    new_vulns_color = models.TextField(
        blank=True,
        null=True,
        help_text="Color code used to display count of new vulnerabilities.",
    )
    tot_vulns = models.IntegerField(
        blank=True, null=True, help_text="Total count of vulnerabilities."
    )
    tot_vulns_color = models.TextField(
        blank=True,
        null=True,
        help_text="Color code used to display count of new vulnerabilities.",
    )
    lev1 = models.IntegerField(
        blank=True, null=True, help_text="Count of level 1 vulnerabilities."
    )
    lev2 = models.IntegerField(
        blank=True, null=True, help_text="Count of level 2 vulnerabilities."
    )
    lev3 = models.IntegerField(
        blank=True, null=True, help_text="Count of level 3 vulnerabilities."
    )
    lev4 = models.IntegerField(
        blank=True, null=True, help_text="Count of level 4 vulnerabilities."
    )
    lev5 = models.IntegerField(
        blank=True, null=True, help_text="Count of level 5 vulnerabilities."
    )
    severities = ArrayField(
        models.IntegerField(),
        blank=True,
        null=True,
        default=list,
        help_text="List of the severities assigned to each of the vulnerabilities.",
    )
    ages = ArrayField(
        models.IntegerField(),
        blank=True,
        null=True,
        default=list,
        help_text="List of ages of all the vulnerabilities.",
    )
    pdf_obj = models.BinaryField(
        blank=True,
        null=True,
        help_text="PDF binary or the full pdf generated by Qualys.",
    )

    class Meta:
        """The Meta class for WasReport."""

        db_table = "was_report"
        unique_together = ("last_scan_date", "org_was_acronym")
        app_label = app_label_name
        managed = manage_db


class WasScanSummary(models.Model):
    """Holds a 24-hour summary of WAS scan data for an organization."""

    summary_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for this WAS scan summary.",
    )
    start_date = models.DateField(
        null=False,
        help_text="Start of the 24-hour summary period (based on vuln_detection timestamp).",
    )
    end_date = models.DateField(
        null=False,
        help_text="End of the 24-hour summary period (based on vuln_detection timestamp).",
    )

    scan_identifier = models.JSONField(
        default=list,
        blank=True,
        help_text="The list of finding_uid values used to build this summary.",
    )
    was_org_id = models.CharField(
        max_length=50, help_text="Acronym of the customer who owns the scan."
    )
    assets_scanned_count = models.IntegerField(
        null=False, default=0, help_text="Number of assets scanned (unique IPs)."
    )
    unique_services_count = models.IntegerField(
        null=False, default=0, help_text="Count of unique services (port count)."
    )
    unique_vulnerabilities_critical = models.IntegerField(
        null=False, default=0, help_text="Number of unique critical vulnerabilities."
    )
    unique_vulnerabilities_high = models.IntegerField(
        null=False, default=0, help_text="Number of unique high vulnerabilities."
    )
    unique_vulnerabilities_medium = models.IntegerField(
        null=False, default=0, help_text="Number of unique medium vulnerabilities."
    )
    unique_vulnerabilities_low = models.IntegerField(
        null=False, default=0, help_text="Number of unique low vulnerabilities."
    )
    unique_vulnerabilities_info = models.IntegerField(
        null=False,
        default=0,
        help_text="Number of unique informational vulnerabilities.",
    )
    risky_services_host_count = models.IntegerField(
        null=False, default=0, help_text="Count of hosts with risky services."
    )
    total_vulnerabilities_critical = models.IntegerField(
        null=False, default=0, help_text="Total count of critical vulnerabilities."
    )
    total_vulnerabilities_high = models.IntegerField(
        null=False, default=0, help_text="Total count of high vulnerabilities."
    )
    total_vulnerabilities_medium = models.IntegerField(
        null=False, default=0, help_text="Total count of medium vulnerabilities."
    )
    total_vulnerabilities_low = models.IntegerField(
        null=False, default=0, help_text="Total count of low vulnerabilities."
    )
    total_vulnerabilities_info = models.IntegerField(
        null=False, default=0, help_text="Total count of informational vulnerabilities."
    )
    max_age_days_critical = models.IntegerField(
        null=True,
        help_text="Maximum age in days of critical vulnerabilities (from firstDetected).",
    )
    max_age_days_high = models.IntegerField(
        null=True,
        help_text="Maximum age in days of high vulnerabilities (from firstDetected).",
    )
    median_age_days_by_severity = models.JSONField(
        null=True,
        help_text="Median age in days of current vulnerabilities, keyed by severity.",
    )
    kev_counts_by_severity = models.JSONField(
        null=True,
        help_text="Counts of KEVs (Known Exploited Vulnerabilities), keyed by severity.",
    )
    max_age_days_kevs = models.IntegerField(
        null=True, help_text="Maximum age in days of any KEV (from firstDetected)."
    )
    hosts_with_1_to_5_vulns_count = models.IntegerField(
        null=False, default=0, help_text="Count of hosts with 1 to 5 vulnerabilities."
    )
    hosts_with_6_to_9_vulns_count = models.IntegerField(
        null=False, default=0, help_text="Count of hosts with 6 to 9 vulnerabilities."
    )
    hosts_with_10_or_more_vulns_count = models.IntegerField(
        null=False,
        default=0,
        help_text="Count of hosts with 10 or more vulnerabilities.",
    )
    hosts_with_vulnerability_above_info_count = models.IntegerField(
        null=False,
        default=0,
        help_text="Count of hosts with vulnerabilities above informational severity.",
    )
    owasp_category_counts = models.JSONField(
        null=True, help_text="Dictionary of vulnerability counts by OWASP category."
    )
    vulnerability_type_counts = models.JSONField(
        null=True, help_text="Dictionary of vulnerability counts by type."
    )
    information_gathered_count = models.IntegerField(
        null=False, default=0, help_text="Count of 'INFORMATION_GATHERED' findings."
    )
    sensitive_content_count = models.IntegerField(
        null=False, default=0, help_text="Count of 'SENSITIVE_CONTENT' findings."
    )

    class Meta:
        """Set WasScanSummary model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "was_scan_summary"


# ######## PE Models #########
class PeUsers(AutoLengthCheckModel):
    """Define Users model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a PE user object.",
    )
    email = models.CharField(
        unique=True,
        max_length=64,
        blank=True,
        null=True,
        help_text="Email address of the user.",
    )
    username = models.CharField(
        unique=True,
        max_length=64,
        blank=True,
        null=True,
        help_text="Username of the user.",
    )
    admin = models.IntegerField(
        blank=True,
        null=True,
        help_text="Django generated field that determines the admin permissions for the user.",
    )
    role = models.IntegerField(
        blank=True,
        null=True,
        help_text="Django generated field that determines the role permissions for the user.",
    )
    password_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Cryptographic hash of the user's password.",
    )
    api_key = models.CharField(
        unique=True,
        max_length=128,
        blank=True,
        null=True,
        help_text="The user's API key.",
    )

    class Meta:
        """Set User model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "pe_users"


# ?????? not sure if we use this anywhere
class AlembicVersion(models.Model):
    """Define AlembicVersion model."""

    version_num = models.CharField(
        primary_key=True,
        max_length=32,
        help_text="A unique identifier assigned to each database migration script in Alembic, this may not be used currently.",
    )

    class Meta:
        """Set AlembicVersion model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "alembic_version"


class SixgillAlerts(models.Model):
    """Define Alerts model."""

    alerts_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for the cyber sixgill alert object.",
    )
    alert_name = models.TextField(
        blank=True, null=True, help_text="Name of the alert provided by Cybersixgill."
    )
    content = models.TextField(
        blank=True,
        null=True,
        help_text="Content of the post or website that triggered the alert.",
    )
    date = models.DateField(
        blank=True, null=True, help_text="Date the alert was created."
    )
    sixgill_id = models.TextField(
        unique=True,
        blank=True,
        null=True,
        help_text="Cybersixgill ID associated with alert.",
    )
    read = models.TextField(
        blank=True,
        null=True,
        help_text="Boolean field that flags if the alert was read in the Cybersixgill portal.",
    )
    severity = models.TextField(
        blank=True, null=True, help_text="Severity ranking of alert from 1 - 10."
    )
    site = models.TextField(
        blank=True, null=True, help_text="Site associated with the alert."
    )
    threat_level = models.TextField(
        blank=True,
        null=True,
        help_text="Threat level of alert either 'imminent' or 'emerging'.",
    )
    threats = models.TextField(
        blank=True, null=True, help_text="Type of threat for alert"
    )
    title = models.TextField(blank=True, null=True, help_text="Title of alert post")
    user_id = models.TextField(
        blank=True, null=True, help_text="Id of user that made the API call"
    )
    category = models.TextField(blank=True, null=True, help_text="Category of alert")
    lang = models.TextField(
        blank=True, null=True, help_text="Language of alert content"
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="Foreign Key to the related organization",
    )
    data_source = models.ForeignKey(
        "DataSource",
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        help_text="Foreign Key to the data_source.",
    )
    content_snip = models.TextField(
        blank=True,
        null=True,
        help_text="100 character snippet of the post content. 50 characters before/after the specific mention",
    )
    asset_mentioned = models.TextField(
        blank=True, null=True, help_text="Asset mentioned in alert"
    )
    asset_type = models.TextField(
        blank=True, null=True, help_text="Type of asset mentioned in alert"
    )

    class Meta:
        """Set Alerts model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "sixgill_alerts"


class Alias(models.Model):
    """Define Alias model."""

    alias_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for an alias.",
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="FK: Foreign Key to organizations",
    )
    alias = models.TextField(unique=True, help_text="Alias for an organization")

    class Meta:
        """Set Alias model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "alias"


# ??????
class AssetHeaders(models.Model):
    """Define AssetHeaders model."""

    field_id = models.UUIDField(
        db_column="_id",
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for the asset header object.",
    )  # Field renamed because it started with '_'.
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="Foreign key relationship to the organization that owns the asset.",
    )
    sub_url = models.TextField(help_text="URL to the subdomain that was scanned.")
    tech_detected = models.TextField(
        help_text="List of technologies identified running on the subdomain."
    )  # This field type is a guess.
    interesting_header = models.TextField(
        help_text="List of headers that potentially have relevant findings."
    )  # This field type is a guess.
    ssl2 = models.TextField(
        blank=True,
        null=True,
        help_text="Evidence that the subdomain is running the outdateed SSL2 protocol",
    )  # This field type is a guess.
    tls1 = models.TextField(
        blank=True,
        null=True,
        help_text="Evidence that the subdomain is running the outdateed TLS1 protocol",
    )  # This field type is a guess.
    certificate = models.TextField(
        blank=True, null=True, help_text="Certificate details of the subdomain."
    )  # This field type is a guess.
    scanned = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field flagging if the suubdomain has been scanned.",
    )
    ssl_scanned = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field flagging if an SSL scan has been run against the subdomain.",
    )

    class Meta:
        """Set AssetHeaders model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "asset_headers"
        unique_together = (("organization", "sub_url"),)


class CredentialBreaches(models.Model):
    """Define CredentialBreaches model."""

    credential_breaches_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for credential_breaches.",
    )
    breach_name = models.TextField(unique=True, help_text="Name of breach.")
    description = models.TextField(
        blank=True, null=True, help_text="Description of breach."
    )
    exposed_cred_count = models.BigIntegerField(
        blank=True, null=True, help_text="Number of credentials exposed in breach."
    )
    breach_date = models.DateField(
        blank=True, null=True, help_text="Date when breach occured."
    )
    added_date = models.DateTimeField(
        blank=True, null=True, help_text="Date breach was added by the source."
    )
    modified_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date breach information was last modified/updated.",
    )
    data_classes = ArrayField(
        models.TextField(blank=True, null=True),
        blank=True,
        null=True,
        help_text="List of types of data identified in the breach.",
    )  # This field type is a guess.
    password_included = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F Were passwords included with the credentials?",
    )
    is_verified = models.BooleanField(
        blank=True, null=True, help_text="T/F Is breach verified?"
    )
    is_fabricated = models.BooleanField(
        blank=True, null=True, help_text="T/F Is the breach fabricated?"
    )
    is_sensitive = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F Does the breach contain sensitive content?",
    )
    is_retired = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F Has the breach been retired? (I believe the means it is no longer posted",
    )
    is_spam_list = models.BooleanField(
        blank=True, null=True, help_text="T/F Is the breach a spam list?"
    )
    data_source = models.ForeignKey(
        "DataSource",
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        blank=True,
        null=True,
        help_text="FK: Foreign Key to data_source",
    )

    class Meta:
        """Set CredentialBreaches model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "credential_breaches"


class CredentialExposures(models.Model):
    """Define CredentialExposures model."""

    credential_exposures_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for credential_exposures",
    )
    email = models.TextField(help_text="Email found in the breach")
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization_id",
        help_text="FK: Foreign Key to organization",
    )
    root_domain = models.TextField(
        blank=True,
        null=True,
        help_text="The root domain for the email found in the breach",
    )
    sub_domain_string = models.TextField(
        blank=True,
        null=True,
        help_text="The sub domain for thee email found in the breach",
    )
    sub_domain = models.ForeignKey(
        "SubDomains",
        on_delete=models.CASCADE,
        db_column="sub_domain_id",
        blank=True,
        null=True,
        help_text="FK: Foreign Key to the linked subdomain",
    )
    breach_name = models.TextField(
        blank=True, null=True, help_text="Name of breach where credentials were exposed"
    )
    modified_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date credential exposure information was last modified/updated",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_column="created_at",
        help_text="Date and time the Credential Exposure object was created.",
    )
    credential_breach = models.ForeignKey(
        CredentialBreaches,
        on_delete=models.CASCADE,
        db_column="credential_breach_id",
        related_name="exposures",
        help_text="FK: Foreign Key to credential_breaches",
    )
    data_source = models.ForeignKey(
        "DataSource",
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        blank=True,
        null=True,
        help_text="FK: Foreign Key to data_source",
    )
    name = models.TextField(
        blank=True, null=True, help_text="Name of person whose credentials were exposed"
    )
    login_id = models.TextField(
        blank=True,
        null=True,
        help_text="Login ID of person whose credentials were exposed",
    )
    phone = models.TextField(
        blank=True,
        null=True,
        help_text="Phone number of person whose credentials were exposed",
    )
    password = models.TextField(
        blank=True,
        null=True,
        help_text="Password of person whose credentials were exposed",
    )
    hash_type = models.TextField(
        blank=True, null=True, help_text="The method used to hash the password"
    )
    intelx_system_id = models.TextField(
        blank=True, null=True, help_text="Id of the Exposure in the intelx system."
    )

    class Meta:
        """Set CredentialExposures model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "credential_exposures"
        unique_together = (("breach_name", "email", "organization"),)


class CyhyContacts(models.Model):
    """Define CyhyContacts model."""

    field_id = models.UUIDField(
        db_column="_id",
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for cyhy contacts",
    )  # Field renamed because it started with '_'.
    org_id = models.TextField(help_text="Organization abbreviated name")
    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
        db_column="organization_uid",
        help_text="FK: Foreign key to the organization",
    )
    org_name = models.TextField(help_text="Organization full name")
    phone = models.TextField(
        blank=True, null=True, help_text="Phone number for organization contact"
    )
    contact_type = models.TextField(help_text="Type of contact")
    email = models.TextField(
        blank=True, null=True, help_text="Email for organization contact"
    )
    name = models.TextField(
        blank=True, null=True, help_text="Name of organization contact"
    )
    date_pulled = models.DateField(
        blank=True,
        null=True,
        help_text="The date we pulled the contact from the cyhy database more recently",
    )

    class Meta:
        """Set CyhyContacts model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "cyhy_contacts"
        unique_together = (("org_id", "contact_type", "email", "name"),)


class CyhyDbAssets(models.Model):
    """Define CyhyDbAssets model."""

    field_id = models.UUIDField(
        db_column="_id",
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for cyhy db assets",
    )  # Field renamed because it started with '_'.
    org_id = models.TextField(
        blank=True, null=True, help_text="Organization abbreviated name"
    )
    organization = models.ForeignKey(
        "Organization",
        models.DO_NOTHING,
        db_column="organization_uid",
        help_text="FK: Foreign key to the organization",
    )
    org_name = models.TextField(
        blank=True, null=True, help_text="Organization full name"
    )
    contact = models.TextField(
        blank=True, null=True, help_text="Organization contact information"
    )
    network = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="Cidr range or IP address owned by the organization",
    )
    type = models.TextField(blank=True, null=True, help_text="Network type")
    first_seen = models.DateField(
        blank=True,
        null=True,
        help_text="First date and time the asset was associated with the cyhy customer.",
    )
    last_seen = models.DateField(
        blank=True,
        null=True,
        help_text="Last date and time the asset was associated with the cyhy customer.",
    )
    currently_in_cyhy = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field flagging if the cidr was seen in the last pull from cyhy",
    )

    class Meta:
        """Set CyhyDbAssets model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "cyhy_db_assets"
        unique_together = (("org_id", "network"),)


# TODO determine if we want user logic on both databases


class DataSource(models.Model):
    """Define DataSource model."""

    data_source_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for data_sources",
    )
    name = models.TextField(unique=True, help_text="Name of data source")
    description = models.TextField(help_text="Description of data source")
    last_run = models.DateField(help_text="Date that data source was last ran")

    class Meta:
        """Set DataSource model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "data_source"


class DnsRecords(models.Model):
    """Define DnsRecords model."""

    dns_record_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a DNS record.",
    )
    domain_name = models.TextField(blank=True, null=True, help_text="")
    domain_type = models.TextField(blank=True, null=True, help_text="")
    created_date = models.DateTimeField(blank=True, null=True, help_text="")
    updated_date = models.DateTimeField(blank=True, null=True, help_text="")
    expiration_date = models.DateTimeField(blank=True, null=True, help_text="")
    name_servers = models.TextField(
        blank=True, null=True, help_text=""
    )  # This field type is a guess.
    whois_server = models.TextField(blank=True, null=True, help_text="")
    registrar_name = models.TextField(blank=True, null=True, help_text="")
    status = models.TextField(blank=True, null=True, help_text="")
    clean_text = models.TextField(blank=True, null=True, help_text="")
    raw_text = models.TextField(blank=True, null=True, help_text="")
    registrant_name = models.TextField(blank=True, null=True, help_text="")
    registrant_organization = models.TextField(blank=True, null=True, help_text="")
    registrant_street = models.TextField(blank=True, null=True, help_text="")
    registrant_city = models.TextField(blank=True, null=True, help_text="")
    registrant_state = models.TextField(blank=True, null=True, help_text="")
    registrant_post_code = models.TextField(blank=True, null=True, help_text="")
    registrant_country = models.TextField(blank=True, null=True, help_text="")
    registrant_email = models.TextField(blank=True, null=True, help_text="")
    registrant_phone = models.TextField(blank=True, null=True, help_text="")
    registrant_phone_ext = models.TextField(blank=True, null=True, help_text="")
    registrant_fax = models.TextField(blank=True, null=True, help_text="")
    registrant_fax_ext = models.TextField(blank=True, null=True, help_text="")
    registrant_raw_text = models.TextField(blank=True, null=True, help_text="")
    administrative_name = models.TextField(blank=True, null=True, help_text="")
    administrative_organization = models.TextField(blank=True, null=True, help_text="")
    administrative_street = models.TextField(blank=True, null=True, help_text="")
    administrative_city = models.TextField(blank=True, null=True, help_text="")
    administrative_state = models.TextField(blank=True, null=True, help_text="")
    administrative_post_code = models.TextField(blank=True, null=True, help_text="")
    administrative_country = models.TextField(blank=True, null=True, help_text="")
    administrative_email = models.TextField(blank=True, null=True, help_text="")
    administrative_phone = models.TextField(blank=True, null=True, help_text="")
    administrative_phone_ext = models.TextField(blank=True, null=True, help_text="")
    administrative_fax = models.TextField(blank=True, null=True, help_text="")
    administrative_fax_ext = models.TextField(blank=True, null=True, help_text="")
    administrative_raw_text = models.TextField(blank=True, null=True, help_text="")
    technical_name = models.TextField(blank=True, null=True, help_text="")
    technical_organization = models.TextField(blank=True, null=True, help_text="")
    technical_street = models.TextField(blank=True, null=True, help_text="")
    technical_city = models.TextField(blank=True, null=True, help_text="")
    technical_state = models.TextField(blank=True, null=True, help_text="")
    technical_post_code = models.TextField(blank=True, null=True, help_text="")
    technical_country = models.TextField(blank=True, null=True, help_text="")
    technical_email = models.TextField(blank=True, null=True, help_text="")
    technical_phone = models.TextField(blank=True, null=True, help_text="")
    technical_phone_ext = models.TextField(blank=True, null=True, help_text="")
    technical_fax = models.TextField(blank=True, null=True, help_text="")
    technical_fax_ext = models.TextField(blank=True, null=True, help_text="")
    technical_raw_text = models.TextField(blank=True, null=True, help_text="")
    billing_name = models.TextField(blank=True, null=True, help_text="")
    billing_organization = models.TextField(blank=True, null=True, help_text="")
    billing_street = models.TextField(blank=True, null=True, help_text="")
    billing_city = models.TextField(blank=True, null=True, help_text="")
    billing_state = models.TextField(blank=True, null=True, help_text="")
    billing_post_code = models.TextField(blank=True, null=True, help_text="")
    billing_country = models.TextField(blank=True, null=True, help_text="")
    billing_email = models.TextField(blank=True, null=True, help_text="")
    billing_phone = models.TextField(blank=True, null=True, help_text="")
    billing_phone_ext = models.TextField(blank=True, null=True, help_text="")
    billing_fax = models.TextField(blank=True, null=True, help_text="")
    billing_fax_ext = models.TextField(blank=True, null=True, help_text="")
    billing_raw_text = models.TextField(blank=True, null=True, help_text="")
    zone_name = models.TextField(blank=True, null=True, help_text="")
    zone_organization = models.TextField(blank=True, null=True, help_text="")
    zone_street = models.TextField(blank=True, null=True, help_text="")
    zone_city = models.TextField(blank=True, null=True, help_text="")
    zone_state = models.TextField(blank=True, null=True, help_text="")
    zone_post_code = models.TextField(blank=True, null=True, help_text="")
    zone_country = models.TextField(blank=True, null=True, help_text="")
    zone_email = models.TextField(blank=True, null=True, help_text="")
    zone_phone = models.TextField(blank=True, null=True, help_text="")
    zone_phone_ext = models.TextField(blank=True, null=True, help_text="")
    zone_fax = models.TextField(blank=True, null=True, help_text="")
    zone_fax_ext = models.TextField(blank=True, null=True, help_text="")
    zone_raw_text = models.TextField(blank=True, null=True, help_text="")

    class Meta:
        """Set DnsRecords model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "dns_records"


# Possibly shodan
class DomainAlerts(models.Model):
    """Define DomainAlerts model."""

    domain_alert_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for domain_alerts",
    )
    sub_domain = models.ForeignKey(
        "SubDomains",
        on_delete=models.CASCADE,
        db_column="sub_domain_uid",
        help_text="FK: Foreign Key to sub_domains",
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        help_text="FK: Foreign Key to data_source",
    )
    organization_uid = models.UUIDField(help_text="FK: Foreign Key to organizations")
    alert_type = models.TextField(
        blank=True, null=True, help_text="Type of domain alert"
    )
    message = models.TextField(
        blank=True, null=True, help_text="Message description associated with alert"
    )
    previous_value = models.TextField(
        blank=True, null=True, help_text="Previous value associated with alert"
    )
    new_value = models.TextField(
        blank=True, null=True, help_text="New updated value associated with alert"
    )
    date = models.DateField(blank=True, null=True, help_text="Date of alert")

    class Meta:
        """Set DomainAlerts model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "domain_alerts"
        unique_together = (("alert_type", "sub_domain", "date", "new_value"),)


class DomainPermutations(models.Model):
    """Define DomainPermutations model."""

    suspected_domain_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for a DNSTwist domain permutation.",
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="Foreign Key for a linked Organization",
    )
    domain_permutation = models.TextField(
        blank=True,
        null=True,
        help_text="Domain that has been flagged as a possible spoof of a domain owned by the stakeholder.",
    )
    ipv4 = models.TextField(
        blank=True, null=True, help_text="IPv4 associated with the identified domain"
    )
    ipv6 = models.TextField(
        blank=True, null=True, help_text="IPv6 associated with the identified domain"
    )
    mail_server = models.TextField(
        blank=True, null=True, help_text="Mail server seen on the domain."
    )
    name_server = models.TextField(
        blank=True, null=True, help_text="Name server seen on the domain."
    )
    fuzzer = models.TextField(blank=True, null=True, help_text="Fuzzing technique used")
    date_observed = models.DateField(
        blank=True, null=True, help_text="Date domain permutation was observed"
    )
    ssdeep_score = models.TextField(
        blank=True, null=True, help_text="HTML similarity with fuzzy hashes"
    )
    malicious = models.BooleanField(
        blank=True, null=True, help_text="T/F Is subdomain malicious?"
    )
    blocklist_attack_count = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of attacks reported in the Blocklist.de database",
    )
    blocklist_report_count = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of reports reported in the Blocklist.de database",
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        help_text="FK: Foreign Key to data_source",
    )
    sub_domain = models.ForeignKey(
        "SubDomains",
        on_delete=models.CASCADE,
        db_column="sub_domain_uid",
        blank=True,
        null=True,
        help_text="FK: Foreign Key to sub_domains",
    )
    dshield_record_count = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of records reported in the DSheild database",
    )
    dshield_attack_count = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of attacks reported in the DSHeild databse",
    )
    date_active = models.DateField(
        blank=True, null=True, help_text="Last known date permutation was active"
    )

    class Meta:
        """Set DomainPermutations model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "domain_permutations"
        unique_together = (("domain_permutation", "organization"),)


class Domain(models.Model):
    """The Domain view of subs/ips."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_column="created_at")
    updated_at = models.DateTimeField(auto_now=True, db_column="updated_at")

    synced_at = models.DateTimeField(db_column="synced_at", blank=True, null=True)
    ip = models.CharField(max_length=255, blank=True, null=True)
    from_root_domain = models.CharField(
        max_length=255, db_column="from_root_domain", blank=True, null=True
    )
    subdomain_source = models.CharField(
        db_column="subdomain_source", max_length=255, blank=True, null=True
    )
    ip_only = models.BooleanField(db_column="ip_only", default=False)

    reverse_name = models.CharField(db_column="reverse_name", max_length=512)
    name = models.CharField(max_length=512)

    screenshot = models.CharField(max_length=512, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    asn = models.CharField(max_length=255, blank=True, null=True)
    cloud_hosted = models.BooleanField(db_column="cloud_hosted", default=False)
    from_cidr = models.BooleanField(db_column="from_cidr", default=False)
    ssl = models.JSONField(blank=True, null=True)
    censys_certificates_results = models.JSONField(
        db_column="censys_certificates_results", default=dict
    )
    trustymail_results = models.JSONField(db_column="trustymail_results", default=dict)

    discovered_by = models.ForeignKey(
        "Scan",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_column="discovered_by_id",
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.DO_NOTHING,
        db_column="organization_id",
        related_name="domains",
    )
    source = models.CharField(max_length=20)

    class Meta:
        """The meta class for Domain."""

        db_table = "mat_vw_domain"
        managed = False
        unique_together = (("name", "organization"),)  # Unique constraint

    def save(self, *args, **kwargs):
        """Save domain ith reverse_name."""
        self.name = self.name.lower()
        self.reverse_name = ".".join(reversed(self.name.split(".")))
        super().save(*args, **kwargs)


class DomainSearchView(models.Model):
    """Domain Search Material View Model."""

    domain_id = models.UUIDField(primary_key=True)
    name = models.TextField()
    ip = models.TextField()
    organization_id = models.UUIDField()
    organization_name = models.TextField()
    source = models.TextField()
    country = models.TextField(null=True)
    cloud_hosted = models.BooleanField(null=True)
    reverse_name = models.TextField(null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    ports_preview = models.TextField(null=True)
    services_preview = models.TextField(null=True)
    services_count = models.IntegerField(null=True)
    vulnerabilities_count = models.IntegerField(null=True)

    class Meta:
        """Set DomainSearchView metadata."""

        managed = False
        db_table = "mat_vw_domain_search"


class DotgovDomains(models.Model):
    """Define DotgovDomains model."""

    dotgov_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for dotgov_domains",
    )
    domain_name = models.TextField(unique=True, help_text="Name of the dotgov domain")
    domain_type = models.TextField(
        blank=True, null=True, help_text="Branch of govt. for dotgov domain"
    )
    agency = models.TextField(
        blank=True, null=True, help_text="Name of agency domain is associated with"
    )
    organization = models.TextField(
        blank=True,
        null=True,
        help_text="Name of organization domain is associated with",
    )
    city = models.TextField(blank=True, null=True, help_text="City of organization")
    state = models.TextField(blank=True, null=True, help_text="State of organization")
    security_contact_email = models.TextField(
        blank=True, null=True, help_text="Email of organization's security contact"
    )

    class Meta:
        """Set DotgovDomains model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "dotgov_domains"


class Executives(models.Model):
    """Define Executives model."""

    executives_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for executives",
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization",
        help_text="FK: Foreign Key to organizations",
    )
    executives = models.TextField(help_text="Executive's name")

    class Meta:
        """Set Executives model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "executives"


class Mentions(models.Model):
    """Define Mentions model."""

    mentions_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for cyber sixgill mentions",
    )
    category = models.TextField(blank=True, null=True, help_text="Category of mention")
    collection_date = models.TextField(
        blank=True, null=True, help_text="Date that mention was recorded"
    )
    content = models.TextField(
        blank=True, null=True, help_text="Content of mention incident"
    )
    creator = models.TextField(
        blank=True, null=True, help_text="User who created the mention"
    )
    date = models.DateField(
        blank=True, null=True, help_text="Date the mention was posted"
    )
    sixgill_mention_id = models.TextField(
        unique=True,
        blank=True,
        null=True,
        help_text="Cybersixgill mention ID associated with mention incident",
    )
    post_id = models.TextField(
        blank=True,
        null=True,
        help_text="Cybersixgill post ID associated with mention incident",
    )
    lang = models.TextField(
        blank=True, null=True, help_text="Language of the mention post"
    )
    rep_grade = models.TextField(
        blank=True,
        null=True,
        help_text="Threat actors reputation score determined by cyber sixgill",
    )
    site = models.TextField(
        blank=True, null=True, help_text="Site were the mention occured"
    )
    site_grade = models.TextField(
        blank=True, null=True, help_text="Grade of site where mention occured 0 - 5"
    )
    title = models.TextField(
        blank=True, null=True, help_text="Title of post where mention occured"
    )
    type = models.TextField(
        blank=True, null=True, help_text="Type of post where mention occured"
    )
    url = models.TextField(blank=True, null=True, help_text="URL of mention post")
    comments_count = models.TextField(
        blank=True, null=True, help_text="Number of comments on the mention post"
    )
    sub_category = models.TextField(
        blank=True, null=True, help_text="Subcategory of mention"
    )
    tags = models.TextField(
        blank=True, null=True, help_text="Tags associated with mention alert"
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="Foreign Key to the related organization",
    )
    data_source = models.ForeignKey(
        "DataSource",
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        help_text="Foreign Key to the data_source.",
    )
    title_translated = models.TextField(
        blank=True, null=True, help_text="Title of mention post translated to english"
    )
    content_translated = models.TextField(
        blank=True, null=True, help_text="Content of mention post translated to english"
    )
    detected_lang = models.TextField(
        blank=True, null=True, help_text="Detected language of metion post"
    )

    class Meta:
        """Set Mentions model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "mentions"


# Likely can be removed
class OrgIdMap(models.Model):
    """Define OrgIdMap model."""

    cyhy_id = models.TextField(
        blank=True, null=True, help_text="Cyber Hygiene organization ID"
    )
    pe_org_id = models.TextField(
        blank=True, null=True, help_text="Posture & Exposure organization ID"
    )
    merge_orgs = models.BooleanField(
        blank=True,
        null=True,
        help_text="Boolean field to flag if the orgs should be merged",
    )

    class Meta:
        """Set OrgIdMap model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "org_id_map"
        unique_together = (("cyhy_id", "pe_org_id"),)


class OrgType(models.Model):
    """Define OrgType model."""

    org_type_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for organization type object.",
    )
    org_type = models.TextField(blank=True, null=True, help_text="Organization type.")

    class Meta:
        """Set OrgType model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "org_type"


class PshttResults(models.Model):
    """Define PshttResults model."""

    pshtt_results_uid = models.UUIDField(
        primary_key=True, default=uuid.uuid4, help_text=""
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="",
    )
    sub_domain = models.ForeignKey(
        "SubDomains", on_delete=models.CASCADE, db_column="sub_domain_uid", help_text=""
    )
    data_source = models.ForeignKey(
        "DataSource",
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        help_text="",
    )
    date_scanned = models.DateField(blank=True, null=True, help_text="")
    base_domain = models.TextField(blank=True, null=True, help_text="")
    base_domain_hsts_preloaded = models.BooleanField(
        blank=True, null=True, help_text=""
    )
    canonical_url = models.TextField(blank=True, null=True, help_text="")
    defaults_to_https = models.BooleanField(blank=True, null=True, help_text="")
    domain = models.TextField(blank=True, null=True, help_text="")
    domain_enforces_https = models.BooleanField(blank=True, null=True, help_text="")
    domain_supports_https = models.BooleanField(blank=True, null=True, help_text="")
    domain_uses_strong_hsts = models.BooleanField(blank=True, null=True, help_text="")
    downgrades_https = models.BooleanField(blank=True, null=True, help_text="")
    hsts = models.BooleanField(blank=True, null=True, help_text="")
    hsts_entire_domain = models.BooleanField(blank=True, null=True, help_text="")
    hsts_header = models.TextField(blank=True, null=True, help_text="")
    hsts_max_age = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        blank=True,
        null=True,
        help_text="Max age for HSTS in seconds",
    )
    hsts_preload_pending = models.BooleanField(blank=True, null=True, help_text="")
    hsts_preload_ready = models.BooleanField(blank=True, null=True, help_text="")
    hsts_preloaded = models.BooleanField(blank=True, null=True, help_text="")
    https_bad_chain = models.BooleanField(blank=True, null=True, help_text="")
    https_bad_hostname = models.BooleanField(blank=True, null=True, help_text="")
    https_cert_chain_length = models.IntegerField(blank=True, null=True, help_text="")
    https_client_auth_required = models.BooleanField(
        blank=True, null=True, help_text=""
    )
    https_custom_truststore_trusted = models.BooleanField(
        blank=True, null=True, help_text=""
    )
    https_expired_cert = models.BooleanField(blank=True, null=True, help_text="")
    https_full_connection = models.BooleanField(blank=True, null=True, help_text="")
    https_live = models.BooleanField(blank=True, null=True, help_text="")
    https_probably_missing_intermediate_cert = models.BooleanField(
        blank=True, null=True, help_text=""
    )
    https_publicly_trusted = models.BooleanField(blank=True, null=True, help_text="")
    https_self_signed_cert = models.BooleanField(blank=True, null=True, help_text="")
    https_leaf_cert_expiration_date = models.DateField(
        blank=True, null=True, help_text=""
    )
    https_leaf_cert_issuer = models.TextField(blank=True, null=True, help_text="")
    https_leaf_cert_subject = models.TextField(blank=True, null=True, help_text="")
    https_root_cert_issuer = models.TextField(blank=True, null=True, help_text="")
    ip = models.GenericIPAddressField(blank=True, null=True, help_text="")
    live = models.BooleanField(blank=True, null=True, help_text="")
    notes = models.TextField(blank=True, null=True, help_text="")
    redirect = models.BooleanField(blank=True, null=True, help_text="")
    redirect_to = models.TextField(blank=True, null=True, help_text="")
    server_header = models.TextField(blank=True, null=True, help_text="")
    server_version = models.TextField(blank=True, null=True, help_text="")
    strictly_forces_https = models.BooleanField(blank=True, null=True, help_text="")
    unknown_error = models.BooleanField(blank=True, null=True, help_text="")
    valid_https = models.BooleanField(blank=True, null=True, help_text="")
    ep_http_headers = models.JSONField(
        blank=True, null=True, help_text=""
    )  # This field type is a guess.
    ep_http_server_header = models.TextField(blank=True, null=True, help_text="")
    ep_http_server_version = models.TextField(blank=True, null=True, help_text="")
    ep_https_headers = models.JSONField(
        blank=True, null=True, help_text=""
    )  # This field type is a guess.
    ep_https_hsts_header = models.TextField(blank=True, null=True, help_text="")
    ep_https_server_header = models.TextField(blank=True, null=True, help_text="")
    ep_https_server_version = models.TextField(blank=True, null=True, help_text="")
    ep_httpswww_headers = models.JSONField(
        blank=True, null=True, help_text=""
    )  # This field type is a guess.
    ep_httpswww_hsts_header = models.TextField(blank=True, null=True, help_text="")
    ep_httpswww_server_header = models.TextField(blank=True, null=True, help_text="")
    ep_httpswww_server_version = models.TextField(blank=True, null=True, help_text="")
    ep_httpwww_headers = models.JSONField(
        blank=True, null=True, help_text=""
    )  # This field type is a guess.
    ep_httpwww_server_header = models.TextField(blank=True, null=True, help_text="")
    ep_httpwww_server_version = models.TextField(blank=True, null=True, help_text="")

    class Meta:
        """Set PshttResults model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "pshtt_results"
        unique_together = (("organization", "sub_domain"),)


class PeReportSummaryStats(models.Model):
    """Define ReportSummaryStats model."""

    report_uid = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="")
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="",
    )
    start_date = models.DateField(help_text="")
    end_date = models.DateField(blank=True, null=True, help_text="")
    ip_count = models.IntegerField(blank=True, null=True, help_text="")
    root_count = models.IntegerField(blank=True, null=True, help_text="")
    sub_count = models.IntegerField(blank=True, null=True, help_text="")
    ports_count = models.IntegerField(blank=True, null=True, help_text="")
    creds_count = models.IntegerField(blank=True, null=True, help_text="")
    breach_count = models.IntegerField(blank=True, null=True, help_text="")
    cred_password_count = models.IntegerField(blank=True, null=True, help_text="")
    domain_alert_count = models.IntegerField(blank=True, null=True, help_text="")
    suspected_domain_count = models.IntegerField(blank=True, null=True, help_text="")
    insecure_port_count = models.IntegerField(blank=True, null=True, help_text="")
    verified_vuln_count = models.IntegerField(blank=True, null=True, help_text="")
    suspected_vuln_count = models.IntegerField(blank=True, null=True, help_text="")
    suspected_vuln_addrs_count = models.IntegerField(
        blank=True, null=True, help_text=""
    )
    threat_actor_count = models.IntegerField(blank=True, null=True, help_text="")
    dark_web_alerts_count = models.IntegerField(blank=True, null=True, help_text="")
    dark_web_mentions_count = models.IntegerField(blank=True, null=True, help_text="")
    dark_web_executive_alerts_count = models.IntegerField(
        blank=True, null=True, help_text=""
    )
    dark_web_asset_alerts_count = models.IntegerField(
        blank=True, null=True, help_text=""
    )
    pe_number_score = models.TextField(blank=True, null=True, help_text="")
    pe_letter_grade = models.TextField(blank=True, null=True, help_text="")
    pe_percent_score = models.DecimalField(
        max_digits=1000, decimal_places=1000, blank=True, null=True, help_text=""
    )
    cidr_count = models.IntegerField(blank=True, null=True, help_text="")
    port_protocol_count = models.IntegerField(blank=True, null=True, help_text="")
    software_count = models.IntegerField(blank=True, null=True, help_text="")
    foreign_ips_count = models.IntegerField(blank=True, null=True, help_text="")

    class Meta:
        """Set ReportSummaryStats model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "pe_report_summary_stats"
        unique_together = (("organization", "start_date"),)


class PeTeamMembers(models.Model):
    """Define TeamMembers model."""

    team_member_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for a PE Team Member object.",
    )
    team_member_fname = models.TextField(
        blank=False, null=False, help_text="First name."
    )
    team_member_lname = models.TextField(blank=False, null=False, help_text="Last Name")
    team_member_email = models.TextField(
        blank=False, null=False, help_text="Team member's email address."
    )
    team_member_ghID = models.TextField(
        blank=False, null=False, help_text="Team member's github ID."
    )
    team_member_phone = models.TextField(
        blank=True, null=True, help_text="Team member's phone number."
    )
    team_member_role = models.TextField(
        blank=True, null=True, help_text="Team member's role."
    )
    team_member_notes = models.TextField(
        blank=True, null=True, help_text="Notes about the team member."
    )

    class Meta:
        """Set TeamMembers model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "pe_team_members"


class ShodanAssets(models.Model):
    """Define ShodanAssets model."""

    shodan_asset_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for shodan assets",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the asset was first created",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_column="organization_uid",
        blank=True,
        null=True,
        help_text="FK: Foreign Key to organizations",
    )
    # If you still need to store the organization name or acronym, use a separate field for that
    organization_name = models.TextField(
        blank=True, null=True, help_text="Organization name"
    )  # New field to store the name or acronym
    ip_string = models.TextField(blank=True, null=True, help_text="IP address")
    port = models.IntegerField(blank=True, null=True, help_text="Port number")
    protocol = models.TextField(
        blank=True, null=True, help_text="Protocol running on the port"
    )
    timestamp = models.DateTimeField(
        blank=True, null=True, help_text="Time the asset was last seen by Shodan"
    )
    product = models.TextField(
        blank=True, null=True, help_text="What product is running on the asset"
    )
    server = models.TextField(
        blank=True, null=True, help_text="What server is running on the asset"
    )
    tags = models.JSONField(
        blank=True,
        null=True,
        help_text="shodan tags associated with the asset (ex. self-signed, vpn, starttls, cloud, etc.)",
    )  # Store tags as a list (JSON format)
    domains = models.JSONField(
        blank=True, null=True, help_text="domains associated with the asset"
    )  # Store domains as a list (JSON format)
    hostnames = models.JSONField(
        blank=True, null=True, help_text="hostnames associated with the asset"
    )  # Store hostnames as a list (JSON format)
    isp = models.TextField(blank=True, null=True, help_text="Internet service provider")
    asn = models.IntegerField(
        blank=True, null=True, help_text="Autonomous system number"
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        blank=True,
        null=True,
        help_text="FK: Foreign Key to data_source",
    )
    country_code = models.TextField(
        blank=True, null=True, help_text="Country code where the IP was located."
    )
    location = models.TextField(
        blank=True, null=True, help_text="Location where the IP hosted."
    )
    ip = models.ForeignKey(
        Ip,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="FK: Reference to resolved IP object",
        db_column="ip_uid",
    )

    class Meta:
        """Set ShodanAssets model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "shodan_assets"
        unique_together = (("organization", "ip", "port", "protocol"),)


class ShodanVulns(models.Model):
    """Define ShodanVulns model."""

    shodan_vuln_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for a shodan vulnerability object.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the asset was first created",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="FK: Foreign Key to organization",
    )
    organization_name = models.TextField(
        blank=True, null=True, help_text="Organization name"
    )
    ip_string = models.TextField(blank=True, null=True, help_text="IP address")
    port = models.TextField(blank=True, null=True, help_text="Port number")
    protocol = models.TextField(blank=True, null=True, help_text="Protocol")
    timestamp = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when unverified vulnerability was found",
    )
    cve = models.TextField(
        blank=True, null=True, help_text="CVE associated with vulnerability"
    )
    severity = models.TextField(
        blank=True,
        null=True,
        help_text="Severity of vulnerability (medium, high, critical)",
    )
    cvss = models.IntegerField(
        blank=True,
        null=True,
        help_text="Common Vulnerability Scoring System Score",
    )
    summary = models.TextField(
        blank=True, null=True, help_text="Summary of vulnerability"
    )
    product = models.TextField(
        blank=True, null=True, help_text="Product associated with vulnerability"
    )
    attack_vector = models.TextField(
        blank=True, null=True, help_text="Attack vector of vulnerability"
    )
    av_description = models.TextField(
        blank=True, null=True, help_text="Description of attack vector"
    )
    attack_complexity = models.TextField(
        blank=True, null=True, help_text="Complexity of attack (low, medium, high)"
    )
    ac_description = models.TextField(
        blank=True, null=True, help_text="Description of attack complexity"
    )
    confidentiality_impact = models.TextField(
        blank=True,
        null=True,
        help_text="Impact on confidentiality (none, partial, complete)",
    )
    ci_description = models.TextField(
        blank=True, null=True, help_text="Description of confidentiality impact"
    )
    integrity_impact = models.TextField(
        blank=True, null=True, help_text="Impact on integrity (none, partial complete)"
    )
    ii_description = models.TextField(
        blank=True, null=True, help_text="Description of integrity impact"
    )
    availability_impact = models.TextField(
        blank=True,
        null=True,
        help_text="Impact on availability (none, partial, complete)",
    )
    ai_description = models.TextField(
        blank=True, null=True, help_text="Description of availability impact"
    )
    tags = ArrayField(
        models.TextField(blank=True, null=True),
        blank=True,
        null=True,
        help_text="List of tags associated with vulnerability",
    )  # This field type is a guess.
    domains = ArrayField(
        models.TextField(blank=True, null=True),
        blank=True,
        null=True,
        help_text="List of domains associated with vulnerability",
    )  # This field type is a guess.
    hostnames = ArrayField(
        models.TextField(blank=True, null=True),
        blank=True,
        null=True,
        help_text="Host names associated with vulnerability",
    )  # This field type is a guess.
    isp = models.TextField(blank=True, null=True, help_text="Internet service provider")
    asn = models.IntegerField(
        blank=True, null=True, help_text="Autonomous system number"
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        null=True,
        db_column="data_source_uid",
        help_text="FK: Foreign Key to data_source",
    )
    type = models.TextField(blank=True, null=True, help_text="Type of vulnerability")
    name = models.TextField(blank=True, null=True, help_text="Name of vulnerability")
    potential_vulns = ArrayField(
        models.TextField(blank=True, null=True),
        blank=True,
        null=True,
        help_text="List of potential vulnerabilities associated with vulnerability",
    )  # This field type is a guess.
    mitigation = models.TextField(
        blank=True, null=True, help_text="Information on how to mitigate vulnerability"
    )
    server = models.TextField(
        blank=True, null=True, help_text="Server associated with vulnerability"
    )
    is_verified = models.BooleanField(
        blank=True, null=True, help_text="T/F Is this a verified vulnerability?"
    )
    banner = models.TextField(
        blank=True,
        null=True,
        help_text="Snippet of information retrieved by Shodan about a service or device, typically revealing details like the software, version, and configuration of a system exposed to the internet.",
    )
    version = models.TextField(
        blank=True, null=True, help_text="Version of the server running.???"
    )
    cpe = ArrayField(
        models.TextField(blank=True, null=True),
        blank=True,
        null=True,
        help_text="Common Platform Enumeration (CPE) id for the product the vulnerability was found on.",
    )
    ip = models.ForeignKey(
        Ip,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="FK: Reference to resolved IP object",
        db_column="ip_uid",
    )

    class Meta:
        """Set ShodanVulns model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "shodan_vulns"
        unique_together = (("organization", "ip", "port", "protocol"),)


class SubDomains(AutoLengthCheckModel):
    """Define SubDomains model."""

    sub_domain_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for subdomains",
    )
    sub_domain = models.TextField(
        help_text="Subdomain name"
    )  # Crossfeed Domains name field
    root_domain = models.ForeignKey(
        "self",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_column="root_domain_id",
        help_text="FK: Foreign Key to root domains",
    )
    is_root_domain = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F: Boolean field flagging if the subdomain is a root.???",
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        help_text="FK: Foreign Key to data_source",
    )
    dns_record = models.ForeignKey(
        DnsRecords,
        on_delete=models.CASCADE,
        db_column="dns_record_uid",
        blank=True,
        null=True,
        help_text="FK: Foreign Key to dns record",
    )
    status = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F: Boolean field flagging if the status is active.???",
    )
    first_seen = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time of the first time the subdomain was seen.",
    )
    last_seen = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date of the last time the subdomain was seen.",
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        auto_now_add=True,
        help_text="Datetime the subdomain object was created.",
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        auto_now=True,
        help_text="Datetime the subdomain was last updated.",
    )
    current = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F is this sub domain still live and linked to the organization",
    )
    identified = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F was this subdomain identified via an IP lookup.???",
    )
    ip_address = models.TextField(
        blank=True, null=True, help_text="IP address linked to the subdomain"
    )  # XFD column
    synced_at = models.DateTimeField(
        db_column="synced_at",
        blank=True,
        null=True,
        help_text="Date the subdomain was last synced",
    )  # XFD column
    from_root_domain = models.TextField(
        db_column="from_root_domain",
        blank=True,
        null=True,
        help_text="Root domain associated with the subdomain",
    )  # XFD column
    enumerate_subs = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F should we identify subdomains for this root domain? (We don't enumerate for Cloud provider roots)",
    )
    subdomain_source = models.TextField(
        db_column="subdomain_source",
        max_length=255,
        blank=True,
        null=True,
        help_text="Where the subdomain originated from.",
    )  # XFD column
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_column="organization_uid",
        related_name="sub_domains",
        help_text="FK: Foreign Key to organization",
    )
    ip_only = models.BooleanField(
        db_column="ip_only",
        default=False,
        help_text="T/F if there is no subdomain but just an IP",
    )  # XFD column
    reverse_name = models.CharField(
        db_column="reverse_name",
        max_length=512,
        help_text="DNS reverse lookup of a subdomain",
    )  # XFD column
    screenshot = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        help_text="link to the screenshot of the subdomain site.???",
    )  # XFD Crossfeed Domains screenshot field
    country = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Country where the subdomain is hosted.",
    )  # XFD column
    asn = models.CharField(
        max_length=255, blank=True, null=True, help_text="Autonomous system number"
    )  # XFD column
    cloud_hosted = models.BooleanField(
        db_column="cloud_hosted",
        default=False,
        help_text="T/F is this subdomain cloud hosted",
    )  # XFD column
    ssl = models.JSONField(
        blank=True,
        null=True,
        help_text="SSL (Secure Sockets Layer) or TLS (Transport Layer Security) connection, certificate, or related security features.",
    )  # XFD columnv
    censys_certificates_results = models.JSONField(
        db_column="censys_certificates_results",
        default=dict,
        help_text="Results from the censys certificate scan.",
    )  # XFD column
    trustymail_results = models.JSONField(
        db_column="trustymail_results",
        default=dict,
        help_text="Results from the trustymail scan.",
    )  # XFD column

    class Meta:
        """Set SubDomains model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "sub_domains"
        unique_together = (("sub_domain", "organization"),)

    def save(self, *args, **kwargs):
        """Format the model before saving."""
        self.sub_domain = self.sub_domain.lower()
        self.reverse_name = ".".join(reversed(self.sub_domain.split(".")))
        super().save(*args, **kwargs)


class TopCves(models.Model):
    """Define TopCves model."""

    top_cves_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: unique identifier for top cves",
    )
    cve_id = models.TextField(
        blank=True, null=True, help_text="CVE identifier ex. CVE-202-20038"
    )
    dynamic_rating = models.TextField(
        blank=True,
        null=True,
        help_text="CyberSixGill’s Dynamic Vulnerability Exploit (DVE) Score",
    )
    nvd_base_score = models.TextField(
        blank=True,
        null=True,
        help_text="Base CVE score from National vulnerability Databse",
    )
    date = models.DateField(
        blank=True,
        null=True,
        help_text="Date the CVE was fetched from the Cybersixgill API",
    )
    summary = models.TextField(blank=True, null=True, help_text="Summary of the CVE")
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        help_text="FK: Foreign Key to data_source",
    )

    class Meta:
        """Set TopCves model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "top_cves"
        unique_together = (("cve_id", "date"),)


# Not sure if this is still used
class TopicTotals(models.Model):
    """Define TopicTotals model."""

    count_uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for topic_totals",
    )
    organization_uid = models.UUIDField(help_text="FK: Foreign Key to organizations")
    content_count = models.IntegerField(
        help_text="Number dark web mentions that fit into a NLP topic"
    )
    count_date = models.TextField(
        blank=True, null=True, help_text="Date the count was taken"
    )

    class Meta:
        """Set TopicTotals model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "topic_totals"


# Not sure if this is still used
class UniqueSoftware(models.Model):
    """Define UniqueSoftware model."""

    field_id = models.UUIDField(
        db_column="_id",
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for a unique software object.",
    )  # Field renamed because it started with '_'.
    software_name = models.TextField(
        blank=False, null=False, help_text="Name of the software."
    )

    class Meta:
        """Set UniqueSoftware model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "unique_software"


class WebAssets(models.Model):
    """Define WebAssets model."""

    asset_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifer for a web asset object.",
    )
    asset_type = models.TextField(help_text="Type of web asset.")
    asset = models.TextField(help_text="The web asset owned by the organization.")
    ip_type = models.TextField(
        blank=True, null=True, help_text="Type of IP if the asset is an IP"
    )
    verified = models.BooleanField(
        blank=True, null=True, help_text="T/F if the asset is verified or not."
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_column="organization_uid",
        help_text="FK: Foreign Key to the organization",
    )
    asset_origin = models.TextField(
        blank=True, null=True, help_text="Where the asset originated from."
    )
    report_on = models.BooleanField(
        blank=True,
        null=True,
        help_text="Whetherr or not PE should report on findings related to this asset.",
    )
    last_scanned = models.DateTimeField(
        blank=True, null=True, help_text="Last date the asset was scanned."
    )
    report_status_reason = models.TextField(
        blank=True, null=True, help_text="Reason the asset is not being reported on."
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        help_text="FK: Foreign Key to the data source that created the web asset object.",
    )

    class Meta:
        """Set WebAssets model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "web_assets"
        unique_together = (("asset", "organization"),)


class WeeklyStatusesMdl(models.Model):
    """Define WeeklyStatusesMdl model."""

    weekly_status_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier to the weekly status object",
    )
    user_status = models.TextField(blank=True, help_text="Name of the user.???")
    key_accomplishments = models.TextField(
        blank=True,
        null=True,
        help_text="Key accomplishments the user has made this week.",
    )
    ongoing_task = models.TextField(help_text="Ongoing tasks the user is working on.")
    upcoming_task = models.TextField(
        help_text="Tasks the user has planned on starting."
    )
    obstacles = models.TextField(
        blank=True,
        null=True,
        help_text="Obstacles that the user is currently facing in accomplishing their tasks.",
    )
    non_standard_meeting = models.TextField(
        blank=True,
        null=True,
        help_text="Any non standard meetings during the last week.",
    )
    deliverables = models.TextField(
        blank=True, null=True, help_text="Key deliverables turned in by the user."
    )
    pto = models.TextField(blank=True, null=True, help_text="Any upcoming PTO.")
    week_ending = models.DateField(help_text="Last day of the week.")
    notes = models.TextField(blank=True, null=True, help_text="additional notes")
    statusComplete = models.IntegerField(
        blank=True,
        null=True,
        help_text="T/F if the user has completed the status report.",
    )

    class Meta:
        """Set WeeklyStatusesMdl model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "weekly_statuses_mdl"


# cyhy_kevs table model (needed for kev_list endpoint)
class CyhyKevs(models.Model):
    """Define CyhyKevs model."""

    cyhy_kevs_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier of the cyhy kev object.",
    )
    kev = models.CharField(
        blank=True, null=True, max_length=255, help_text="CVE id of the KEV."
    )
    first_seen = models.DateField(
        blank=True, null=True, help_text="First time the KEV was seen."
    )
    last_seen = models.DateField(
        blank=True, null=True, help_text="Last time the KEV was seen."
    )

    class Meta:
        """Set CyhyKevs model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "cyhy_kevs"


class XpanseBusinessUnits(models.Model):
    """Define XpanseBusinessUnits model."""

    xpanse_business_unit_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for a xpanse business unit object.",
    )
    entity_name = models.TextField(
        unique=True, blank=True, null=True, help_text="Name of the business unit."
    )
    cyhy_db_name = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        db_column="cyhy_db_name",
        to_field="acronym",
        null=True,  # Allow NULL values
        blank=True,
        help_text="Acronym of the organization associated with the business unit.",
    )
    state = models.TextField(
        blank=True, null=True, help_text="State where the business unit is based."
    )
    county = models.TextField(
        blank=True, null=True, help_text="County where the business unit is based."
    )
    city = models.TextField(
        blank=True, null=True, help_text="City where the business unit is based."
    )
    sector = models.TextField(
        blank=True, null=True, help_text="Business unit's sector."
    )
    entity_type = models.TextField(
        blank=True, null=True, help_text="Type of business unit."
    )
    region = models.TextField(
        blank=True, null=True, help_text="Region where the business unit is based."
    )
    rating = models.IntegerField(
        blank=True, null=True, help_text="Xpanse rating of the business unit."
    )

    class Meta:
        """Set XpanseBusinessUnits metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "xpanse_business_units"


class XpanseAssetsMdl(models.Model):
    """Define XpanseAssetsMdl model."""

    xpanse_asset_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for an Xpanse Asset object.",
    )
    asm_id = models.TextField(
        unique=True, blank=False, null=False, help_text="Xpanse ID for the asset"
    )
    asset_name = models.TextField(blank=True, null=True, help_text="Name of the asset")
    asset_type = models.TextField(blank=True, null=True, help_text="Type of asset")
    last_observed = models.DateTimeField(
        blank=True, null=True, help_text="Last datetime that the asset was observed"
    )
    first_observed = models.DateTimeField(
        blank=True, null=True, help_text="First datetime the asset was observed"
    )
    externally_detected_providers = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of externally detected providers.",
    )
    created = models.DateTimeField(
        blank=True, null=True, help_text="Datetime the asset was created"
    )
    ips = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of Ips associated with the asset.",
    )
    active_external_services_types = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of active external services running on the asset.",
    )
    domain = models.TextField(
        blank=True, null=True, help_text="Domain associated with the asset."
    )
    certificate_issuer = models.TextField(
        blank=True, null=True, help_text="Certificate issuer."
    )
    certificate_algorithm = models.TextField(
        blank=True, null=True, help_text="Certificate algorithm"
    )
    certificate_classifications = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of certificate classifications",
    )
    resolves = models.BooleanField(
        blank=True, null=True, help_text="T/F does the domain resolve to an live site."
    )
    # details
    top_level_asset_mapper_domain = models.TextField(
        blank=True, null=True, help_text="The top level domain the subdomain maps to"
    )
    domain_asset_type = models.JSONField(
        blank=True, null=True, help_text="Type of the domain asset"
    )
    is_paid_level_domain = models.BooleanField(
        blank=True, null=True, help_text="T/F is the asset a paid level domain"
    )
    domain_details = models.JSONField(
        blank=True, null=True, help_text="Details about the domain"
    )
    dns_zone = models.TextField(
        blank=True, null=True, help_text="What zone does the dns resolve to."
    )
    latest_sampled_ip = models.IntegerField(
        blank=True, null=True, help_text="Latest IP seen on the domain"
    )

    recent_ips = models.JSONField(
        blank=True, null=True, help_text="List of recent IPs linked to the domain"
    )
    external_services = models.JSONField(
        blank=True, null=True, help_text="External services running on the asset"
    )
    externally_inferred_vulnerability_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Externally inferred vulnerability score",
    )
    externally_inferred_cves = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="Externally inferred CVEs",
    )
    explainers = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="Explainer text",
    )
    tags = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="Tags associated with the asset",
    )

    class Meta:
        """Set XpanseAssetsMdl metdata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "xpanse_assets_mdl"


class XpanseCvesMdl(models.Model):
    """Define XpanseCvesMdl model."""

    xpanse_cve_uid = models.UUIDField(
        unique=True,
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for an Xpanse CVE objct.",
    )
    cve_id = models.TextField(
        unique=True, blank=True, null=True, help_text="CVE identifier."
    )
    cvss_score_v2 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="CVVS Score version 2",
    )
    cve_severity_v2 = models.TextField(
        blank=True, null=True, help_text="CVSS Severity Score version 2"
    )
    cvss_score_v3 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="CVSS Score version 3",
    )
    cve_severity_v3 = models.TextField(
        blank=True, null=True, help_text="CVSS Severity Score version 3"
    )

    class Meta:
        """Set XpanseCvesMdl metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "xpanse_cves_mdl"


class XpanseAlerts(models.Model):
    """Define XpanseAlerts model."""

    xpanse_alert_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for an Xpanse alert object.",
    )
    time_pulled_from_xpanse = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Time the alert was pulled from the Xpanse API.",
    )
    alert_id = models.TextField(
        unique=True, blank=False, null=False, help_text="Xpanse alert id."
    )
    detection_timestamp = models.DateTimeField(
        blank=True, null=True, help_text="Datetime the alert was detected by Xpanse."
    )
    alert_name = models.TextField(blank=True, null=True, help_text="Name of the alert.")
    # endpoint_id ???,
    description = models.TextField(
        blank=True, null=True, help_text="Description of the alert."
    )
    host_name = models.TextField(
        blank=True, null=True, help_text="IP or domain where the alert points."
    )
    alert_action = models.TextField(
        blank=True,
        null=True,
        help_text="a specific response or remediation step that is automatically taken when an alert is triggered.",
    )
    # user_name ??? null,
    # mac_addresses ??? null,
    # source ??? null,
    action_pretty = models.TextField(
        blank=True, null=True, help_text="Human readable version of the alert action."
    )
    # category ??? null,
    # project ??? null,
    # cloud_provider ??? null,
    # resource_sub_type ??? null,
    # resource_type ??? null,
    action_country = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="Country where the action was performed, if applicable.",
    )
    # event_type ??? null,
    # is_whitelisted ??? null,
    # image_name ??? null,
    # action_local_ip ??? null,
    # action_local_port ??? null,
    # action_external_hostname ??? null,
    # action_remote_ip ??? null,
    action_remote_port = ArrayField(
        models.IntegerField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="Port number.",
    )
    # "matching_service_rule_id ??? null,
    starred = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F if the user has starred the alert in the Xpanse system.",
    )
    external_id = models.TextField(
        blank=True,
        null=True,
        help_text="unique identifier that is used to reference a specific asset or record from the Xpanse system",
    )
    related_external_id = models.TextField(
        blank=True,
        null=True,
        help_text="Alert external id of the same alert being issued multiple times in the Xpanse system",
    )
    alert_occurrence = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of times the alert has been made in the Xpanse system for the same entity.",
    )
    severity = models.TextField(
        blank=True, null=True, help_text="Severity of the alert."
    )
    matching_status = models.TextField(
        blank=True, null=True, help_text="Status of the matching attempt."
    )
    # end_match_attempt_ts ??? null,
    local_insert_ts = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Datetime the alert was inserted into the mini data lake",
    )
    last_modified_ts = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Datetime the alert was modified in the Xpanse system",
    )
    case_id = models.IntegerField(
        blank=True, null=True, help_text="Case id in the Xpanse system."
    )
    # deduplicate_tokens ??? null,
    # filter_rule_id ??? null,
    # event_id ??? null,
    event_timestamp = ArrayField(
        models.DateTimeField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of event timestamps associated with the alert.",
    )
    # action_local_ip_v6 ??? null,
    # action_remote_ip_v6 ??? null,
    alert_type = models.TextField(blank=True, null=True, help_text="Type of alert")
    resolution_status = models.TextField(
        blank=True, null=True, help_text="Current resolution status of the alert."
    )
    resolution_comment = models.TextField(
        blank=True, null=True, help_text="Comment about the resolution."
    )
    # dynamic_fields ??? null,
    tags = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of tags associated with the alert.",
    )
    # malicious_urls ??? null,
    last_observed = models.DateTimeField(
        blank=True, null=True, help_text="Last time the issue was observed"
    )
    country_codes = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="Country code associated with the alert",
    )
    cloud_providers = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of cloud providers associated with the assets in the alert.",
    )
    ipv4_addresses = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of IPs associated with the alert.",
    )
    # ipv6_addresses ??? null,
    domain_names = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of domains associated with the alert",
    )
    service_ids = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of services ids associated with the alert",
    )
    website_ids = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of websites associated with the alert.",
    )
    asset_ids = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of asset's ids that are associated with the alert.",
    )
    certificate = models.JSONField(
        blank=True,
        null=True,
        help_text="Dictionary containing certificate data assocated with the alert.",
    )
    port_protocol = models.TextField(
        blank=True, null=True, help_text="Port protocol associated with the alert."
    )
    # business_unit_hierarchies
    attack_surface_rule_name = models.TextField(
        blank=True,
        null=True,
        help_text="Attack surface rule that was triggered to create the alert",
    )
    remediation_guidance = models.TextField(
        blank=True, null=True, help_text="Guidance to remediate the alert."
    )
    asset_identifiers = models.JSONField(
        blank=True,
        null=True,
        help_text="List of dictionaries containg asset data associated with the alert",
    )

    business_units = models.ManyToManyField(
        XpanseBusinessUnits,
        related_name="alerts",
        help_text="Many to many relationship to the related business units.",
    )
    assets = models.ManyToManyField(
        XpanseAssetsMdl,
        related_name="alerts",
        help_text="Many to many relationship to the assets associated with the alert.",
    )

    class Meta:
        """Set XpanseAlerts model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "xpanse_alerts_mdl"


class XpanseServicesMdl(models.Model):
    """Define XpanseServicesMdl model."""

    xpanse_service_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for a Xpanse Service object.",
    )
    service_id = models.TextField(
        unique=True,
        blank=True,
        null=True,
        help_text="Xpanse Identifier for the service.",
    )
    service_name = models.TextField(
        blank=True, null=True, help_text="Name of the service."
    )
    service_type = models.TextField(blank=True, null=True, help_text="Type of service")
    ip_address = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of IP addresses where the service is hosted, if applicable.",
    )
    domain = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of domains where the service is hosted, if applicable.",
    )
    externally_detected_providers = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="List of externally detected providers.",
    )
    is_active = models.TextField(
        blank=True, null=True, help_text="State of the service (Active, Inactive)."
    )
    first_observed = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Datetime the service was first observed by Xpanse",
    )
    last_observed = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Datetime the service was last observed by Xpanse",
    )
    port = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of the port where the service is running.",
    )
    protocol = models.TextField(
        blank=True, null=True, help_text="Protocol running on the port."
    )
    active_classifications = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="Current, actively detected and recognized software, technologies, or behaviors observed on a service based on the most recent data collected",
    )
    inactive_classifications = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="previously detected and recognized software, technologies, or behaviors observed on a service previously, but not on the most recent data collected",
    )
    discovery_type = models.TextField(
        blank=True, null=True, help_text="How the service was detected."
    )
    externally_inferred_vulnerability_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="vulnerability score assigned to a service based on publicly available information about its product name and version, compared against known vulnerabilities in the National Vulnerability Database (NVD)",
    )
    externally_inferred_cves = ArrayField(
        models.TextField(blank=True, null=False),
        blank=True,
        null=True,
        help_text="potential vulnerabilities identified by comparing the publicly visible version information of a service discovered on an organization's external attack surface with known vulnerabilities listed in the National Vulnerability Database (NVD)",
    )
    service_key = models.TextField(
        blank=True,
        null=True,
        help_text="identifier associated with a specific service that allows for access and interaction with that service within the Xpanse environment",
    )
    service_key_type = models.TextField(
        blank=True, null=True, help_text="Type of service key."
    )
    cves = models.ManyToManyField(
        XpanseCvesMdl,
        through="XpanseCveServiceMdl",
        help_text="Many to many linking table to the cve table.",
    )
    sub_domains = models.ManyToManyField(
        SubDomains,
        related_name="XpanseServicesMdl",
        help_text="Many to many linking to sub domains",
    )
    alert = models.ForeignKey(
        XpanseAlerts, on_delete=models.CASCADE, db_column="xpanse_alert_uid", null=True
    )

    class Meta:
        """Set XpanseServicesMdl metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "xpanse_services_mdl"


class XpanseCveServiceMdl(models.Model):
    """Define XpanseCves-Service linking table model."""

    xpanse_inferred_cve = models.ForeignKey(
        XpanseCvesMdl,
        on_delete=models.CASCADE,
        help_text="FK: Foreign key to the CVE associated with the service.",
    )
    xpanse_service = models.ForeignKey(
        XpanseServicesMdl,
        on_delete=models.CASCADE,
        help_text="FK: Foreign key to the service associated with the CVEs.",
    )
    inferred_cve_match_type = models.TextField(
        blank=True,
        null=True,
        help_text="If the match between service and CVE is approximate or exact.",
    )
    product = models.TextField(
        blank=True,
        null=True,
        help_text="Vulnerable product on the service that triggered the finding.",
    )
    confidence = models.TextField(
        blank=True,
        null=True,
        help_text="How confident Xpanse is the vulnerability is present.",
    )
    vendor = models.TextField(
        blank=True, null=True, help_text="Vendor who makes the compromised product."
    )
    version_number = models.TextField(
        blank=True, null=True, help_text="Version number of the compromised product."
    )
    activity_status = models.TextField(
        blank=True,
        null=True,
        help_text="Current activity status of the vulnerable product. (Inactive, Active)",
    )
    first_observed = models.DateTimeField(
        blank=True,
        null=True,
        help_text="First time the vulnerable product was seen running on the service.",
    )
    last_observed = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last time the vulnerable product was seen running on the service.",
    )

    class Meta:
        """Set XpanseCveServiceMdl metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "xpanse_cve_services_mdl"
        unique_together = (("xpanse_inferred_cve", "xpanse_service"),)


class CpeVender(models.Model):
    """Define CpeVender model."""

    cpe_vender_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique ID of the vender object",
    )
    vender_name = models.TextField(
        unique=True, blank=True, null=True, help_text="Vender name"
    )

    class Meta:
        """Set CpeVender model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "cpe_vender"


class CpeProduct(models.Model):
    """Define CpeProduct model."""

    cpe_product_uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="PK: Unique identifier for the Product (CPE)",
    )
    cpe_product_name = models.TextField(
        blank=True, null=True, help_text="Name of the product"
    )
    version_number = models.TextField(
        blank=True, null=True, help_text="Version of the product"
    )
    cpe_vender = models.ForeignKey(
        "CpeVender",
        on_delete=models.CASCADE,
        db_column="cpe_vender_uid",
        default=None,
        help_text="FK: Foreign key to the related vender object.",
    )

    # Create linking table for many to many relationship
    cves = models.ManyToManyField(
        Cve,
        related_name="products",
        help_text="Many to many relationship to the CVEs associated with the product",
    )

    class Meta:
        """Set CpeProduct model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "cpe_product_mdl"
        unique_together = (("cpe_product_name", "version_number"),)


class Blocklist(models.Model):
    """Define Blocklist Model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip = InetAddressField(null=False, blank=False, unique=True)
    created_at = models.DateTimeField(auto_now=False)
    updated_at = models.DateTimeField(auto_now=True)
    malicious = models.BooleanField(default=False)
    attacks = models.IntegerField(
        help_text="Number of attacks recorded for this IP.", null=True
    )
    reports = models.IntegerField(
        help_text="Number of reports recorded for this IP.", null=True
    )

    class Meta:
        """Set Blocklist model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "blocklist"
        indexes = [
            models.Index(fields=["ip"]),  # Reinforces index on 'ip' field
            models.Index(fields=["created_at"]),  # Speeds up sorting by 'updated_at'
        ]


class RiskyServiceGroup(models.Model):
    """Define RiskyServiceGroup Model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_name = models.CharField(
        max_length=255, null=False, blank=False, unique=True
    )
    group = models.CharField(
        max_length=255, null=False, blank=False, help_text="Group name"
    )

    class Meta:
        """Set RiskyServiceGroup model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "riskyservicegroup"


class NMIServiceGroup(models.Model):
    """Define NMIService Model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_name = models.CharField(
        max_length=255, null=False, blank=False, unique=True
    )
    group = models.CharField(
        max_length=255, null=False, blank=False, help_text="Group name"
    )

    class Meta:
        """Set NMIServiceGroup model metadata."""

        app_label = app_label_name
        managed = manage_db
        db_table = "nmiservicegroup"


class Log(models.Model):
    """The Log model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payload = models.TextField()
    created_at = models.DateTimeField(db_column="created_at", auto_now_add=True)
    event_type = models.CharField(
        db_column="event_type", max_length=255, null=True, blank=True
    )
    result = models.CharField(max_length=255)

    class Meta:
        """The Meta class for Log."""

        managed = True
        db_table = "log"


class DataPullTracker(models.Model):
    """Define DataPullTracker Model."""

    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    data_source = models.CharField(max_length=255)  # Store data source as a string
    last_queried_at = models.DateTimeField()  # Explicitly controlled timestamp

    class Meta:
        """Set DataPullTracker model metadata."""

        unique_together = ("org", "data_source")  # Ensure unique org-data_source pairs
        app_label = app_label_name
        managed = manage_db
        db_table = "data_pull_tracker"


# # THese are all views, so they shouldn't be generated via the ORM


class Vulnerability(models.Model):
    """Define VwCombinedVulns model."""

    id = models.TextField(
        primary_key=True,
        unique=True,
        help_text="Id of the vulnerability",
        db_column="vuln_id",
    )
    scan_source = models.TextField(
        blank=True, null=True, help_text="Scan that identified the data."
    )
    created_at = models.DateTimeField(
        help_text="Date and time the vulnerability was first seen",
    )
    updated_at = models.DateTimeField(
        help_text="Date and time the vulnerability was last updated",
    )
    last_seen = models.DateTimeField(
        help_text="Date and time the vulnerability was last seen",
    )
    cve = models.CharField(blank=True, null=True, max_length=255)
    title = models.TextField(blank=True, null=True)
    product = models.CharField(blank=True, null=True, max_length=255)
    domain_string = models.TextField(blank=True, null=True)
    domain = models.ForeignKey(
        Domain,
        models.DO_NOTHING,
        db_column="domain_id",
        blank=True,
        null=True,
        help_text="Foreign key to the domain or IP where the vulnerablily was found.",
        related_name="vulnerabilities",
    )
    protocol = models.CharField(blank=True, null=True, max_length=255)
    port = models.CharField(blank=True, null=True, max_length=255)
    cvss = models.DecimalField(
        max_digits=100,
        decimal_places=5,
        blank=True,
        null=True,
        db_column="cvss_base_score",
        help_text="CVSS (Common Vulnerability Scoring System) is the score reperesenting the severity of the vulnerability from 0 (None) to 10 (Critical)",
    )
    severity = models.CharField(blank=True, null=True, max_length=255)
    organization = models.ForeignKey(
        Organization,
        models.DO_NOTHING,
        db_column="organization_id",
        blank=True,
        null=True,
        related_name="vulnerabilities",
        help_text="Foreign key to the organization that owns the vulnerable asset.",
    )
    state = models.CharField(blank=True, null=True, max_length=255)
    source = models.CharField(
        blank=True, null=True, max_length=255, db_column="data_source"
    )
    description = models.TextField(blank=True, null=True)
    false_positive = models.BooleanField(
        db_column="false_positive",
        blank=True,
        null=True,
        help_text="A boolean field to flag if a vulnerability has been reported as a false positive.",
    )
    is_kev = models.BooleanField(
        db_column="is_kev",
        blank=True,
        null=True,
        help_text="A boolean field to flag if a vulnerability has been on the CISA Known Exploited Vulnerability (KEV) list.",
    )
    is_kev_ransomware = models.BooleanField(
        db_column="is_kev_ransomware",
        blank=True,
        null=True,
        help_text="A boolean field to flag if a vulnerability is linked to a known ransomware exploit.",
    )
    service_string = models.CharField(blank=True, null=True, max_length=255)
    is_risky_service = models.BooleanField(
        blank=True,
        null=True,
        help_text="T/F if the vulnerability is a known risky service.",
    )
    os = models.CharField(blank=True, null=True, max_length=255)
    cwe = models.CharField(blank=True, null=True, max_length=255)
    cpe = models.TextField(
        blank=True,
        null=True,
        help_text="Common Platform Enumeration (CPE) id for the product the vulnerability was found on.",
    )
    references = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional links to references and sources associates with the vulnerability.",
    )
    substate = models.TextField(
        blank=True,
        null=True,
        help_text="Substate of the vulnerability ('unconfirmed', 'exploitable', 'false-positive', 'accepted-risk', 'remediated')",
    )
    needs_population = models.BooleanField(
        blank=True,
        null=True,
        db_column="needs_population",
        help_text="A boolean field to flag vulnerabilities that need to be populated additional findings.",
    )
    actions = models.JSONField(
        blank=True,
        null=True,
        help_text="A list of state changes of the vulnerability, tracking its status from intially created to closed.",
    )
    structured_data = models.JSONField(
        blank=True,
        null=True,
        db_column="structured_data",
        help_text="Any additional data that does not fit into the vulnerability table pertinent to the end user.",
    )
    kev_results = models.JSONField(
        db_column="kev_results",
        blank=True,
        null=True,
        help_text="The CISA provided KEV information assocaited with KEV vulnerabilities.",
    )
    ip_string = models.CharField(max_length=255, blank=True, null=True)
    cvss_vector = models.TextField(blank=True, null=True)
    severity_int = models.IntegerField(blank=True, null=True)
    plugin_id = models.TextField(blank=True, null=True)
    solution = models.TextField(blank=True, null=True)
    synopsis = models.TextField(blank=True, null=True)
    results = models.TextField(blank=True, null=True)

    class Meta:
        """Set Vulnerability model metadata."""

        app_label = app_label_name
        managed = False
        db_table = "mat_vw_combined_vulns"

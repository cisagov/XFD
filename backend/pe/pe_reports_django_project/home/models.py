"""Django Models."""
# Create your models here.
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the
#     desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create,
#     modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.

# Standard Python Libraries
import uuid

# Third-Party Libraries
from django.contrib.auth.models import User

# from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class Users(models.Model):
    """Define Users model."""

    id = models.UUIDField(primary_key=True)
    email = models.CharField(unique=True, max_length=64, blank=True, null=True)
    username = models.CharField(unique=True, max_length=64, blank=True, null=True)
    admin = models.IntegerField(blank=True, null=True)
    role = models.IntegerField(blank=True, null=True)
    password_hash = models.CharField(max_length=128, blank=True, null=True)
    api_key = models.CharField(unique=True, max_length=128, blank=True, null=True)

    class Meta:
        """Set User model metadata."""

        managed = False
        db_table = "Users"


class AlembicVersion(models.Model):
    """Define AlembicVersion model."""

    version_num = models.CharField(primary_key=True, max_length=32)

    class Meta:
        """Set AlembicVersion model metadata."""

        managed = False
        db_table = "alembic_version"


class Alerts(models.Model):
    """Define Alerts model."""

    alerts_uid = models.UUIDField(primary_key=True)
    alert_name = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    sixgill_id = models.TextField(unique=True, blank=True, null=True)
    read = models.TextField(blank=True, null=True)
    severity = models.TextField(blank=True, null=True)
    site = models.TextField(blank=True, null=True)
    threat_level = models.TextField(blank=True, null=True)
    threats = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    user_id = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    lang = models.TextField(blank=True, null=True)
    organizations_uid = models.ForeignKey(
        "Organizations", on_delete=models.CASCADE, db_column="organizations_uid"
    )
    data_source_uid = models.ForeignKey(
        "DataSource", on_delete=models.CASCADE, db_column="data_source_uid"
    )
    content_snip = models.TextField(blank=True, null=True)
    asset_mentioned = models.TextField(blank=True, null=True)
    asset_type = models.TextField(blank=True, null=True)

    class Meta:
        """Set Alerts model metadata."""

        managed = False
        db_table = "alerts"


class Alias(models.Model):
    """Define Alias model."""

    alias_uid = models.UUIDField(primary_key=True)
    organizations_uid = models.ForeignKey(
        "Organizations", on_delete=models.CASCADE, db_column="organizations_uid"
    )
    alias = models.TextField(unique=True)

    class Meta:
        """Set Alias model metadata."""

        managed = False
        db_table = "alias"


class apiUser(models.Model):
    """apiUser class."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    apiKey = models.CharField(max_length=200, null=True)
    refresh_token = models.CharField(max_length=200, null=True)


class AssetHeaders(models.Model):
    """Define AssetHeaders model."""

    field_id = models.UUIDField(
        db_column="_id", primary_key=True
    )  # Field renamed because it started with '_'.
    organizations_uid = models.UUIDField()
    sub_url = models.TextField()
    tech_detected = models.TextField()  # This field type is a guess.
    interesting_header = models.TextField()  # This field type is a guess.
    ssl2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    tls1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    certificate = models.TextField(blank=True, null=True)  # This field type is a guess.
    scanned = models.BooleanField(blank=True, null=True)
    ssl_scanned = models.BooleanField(blank=True, null=True)

    class Meta:
        """Set AssetHeaders model metadata."""

        managed = False
        db_table = "asset_headers"
        unique_together = (("organizations_uid", "sub_url"),)


class AuthGroup(models.Model):
    """Define AuthGroup model."""

    name = models.CharField(unique=True, max_length=150)

    class Meta:
        """Set AuthGroup model metadata."""

        managed = False
        db_table = "auth_group"


class AuthGroupPermissions(models.Model):
    """Define AuthGroupPermissions model."""

    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, on_delete=models.CASCADE)
    permission = models.ForeignKey("AuthPermission", on_delete=models.CASCADE)

    class Meta:
        """Set AuthGroupPermissions model metadata."""

        managed = False
        db_table = "auth_group_permissions"
        unique_together = (("group", "permission"),)


class AuthPermission(models.Model):
    """Define AuthPermission model."""

    name = models.CharField(max_length=255)
    content_type = models.ForeignKey("DjangoContentType", on_delete=models.CASCADE)
    codename = models.CharField(max_length=100)

    class Meta:
        """Set AuthPermission model metadata."""

        managed = False
        db_table = "auth_permission"
        unique_together = (("content_type", "codename"),)


class AuthUser(models.Model):
    """Define AuthUser model."""

    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        """Set AuthUser model metadata."""

        managed = False
        db_table = "auth_user"


class AuthUserGroups(models.Model):
    """Define AuthUserGroups model."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    group = models.ForeignKey(AuthGroup, on_delete=models.CASCADE)

    class Meta:
        """Set AuthUserGroups model metadata."""

        managed = False
        db_table = "auth_user_groups"
        unique_together = (("user", "group"),)


class AuthUserUserPermissions(models.Model):
    """Define AuthUserUserPermissions model."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    permission = models.ForeignKey(AuthPermission, on_delete=models.CASCADE)

    class Meta:
        """Set AuthUserUserPermissions model metadata."""

        managed = False
        db_table = "auth_user_user_permissions"
        unique_together = (("user", "permission"),)


class Cidrs(models.Model):
    """Define Cidrs model."""

    cidr_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    network = models.TextField()  # This field type is a guess.
    organizations_uid = models.ForeignKey(
        "Organizations",
        on_delete=models.CASCADE,
        db_column="organizations_uid",
        blank=True,
        null=True,
    )
    data_source_uid = models.ForeignKey(
        "DataSource",
        on_delete=models.CASCADE,
        db_column="data_source_uid",
        blank=True,
        null=True,
    )
    insert_alert = models.TextField(blank=True, null=True)
    first_seen = models.DateField(blank=True, null=True)
    last_seen = models.DateField(blank=True, null=True)
    current = models.BooleanField(blank=True, null=True)

    class Meta:
        """Set Cidrs model metadata."""

        managed = False
        db_table = "cidrs"
        unique_together = (("organizations_uid", "network"),)


class CredentialBreaches(models.Model):
    """Define CredentialBreaches model."""

    credential_breaches_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    breach_name = models.TextField(unique=True)
    description = models.TextField(blank=True, null=True)
    exposed_cred_count = models.BigIntegerField(blank=True, null=True)
    breach_date = models.DateField(blank=True, null=True)
    added_date = models.DateTimeField(blank=True, null=True)
    modified_date = models.DateTimeField(blank=True, null=True)
    data_classes = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    password_included = models.BooleanField(blank=True, null=True)
    is_verified = models.BooleanField(blank=True, null=True)
    is_fabricated = models.BooleanField(blank=True, null=True)
    is_sensitive = models.BooleanField(blank=True, null=True)
    is_retired = models.BooleanField(blank=True, null=True)
    is_spam_list = models.BooleanField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        "DataSource", on_delete=models.CASCADE, db_column="data_source_uid"
    )

    class Meta:
        """Set CredentialBreaches model metadata."""

        managed = False
        db_table = "credential_breaches"


class CredentialExposures(models.Model):
    """Define CredentialExposures model."""

    credential_exposures_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    email = models.TextField()
    organizations_uid = models.ForeignKey(
        "Organizations", on_delete=models.CASCADE, db_column="organizations_uid"
    )
    root_domain = models.TextField(blank=True, null=True)
    sub_domain = models.TextField(blank=True, null=True)
    breach_name = models.TextField(blank=True, null=True)
    modified_date = models.DateTimeField(blank=True, null=True)
    credential_breaches_uid = models.ForeignKey(
        CredentialBreaches,
        on_delete=models.CASCADE,
        db_column="credential_breaches_uid",
    )
    data_source_uid = models.ForeignKey(
        "DataSource", on_delete=models.CASCADE, db_column="data_source_uid"
    )
    name = models.TextField(blank=True, null=True)
    login_id = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    password = models.TextField(blank=True, null=True)
    hash_type = models.TextField(blank=True, null=True)
    intelx_system_id = models.TextField(blank=True, null=True)
    login_url = models.TextField(blank=True, null=True)

    class Meta:
        """Set CredentialExposures model metadata."""

        managed = False
        db_table = "credential_exposures"
        unique_together = (("breach_name", "email"),)


class CveInfo(models.Model):
    """Define CveInfo model."""

    cve_uuid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    cve_name = models.TextField(unique=True, blank=True, null=True)
    cvss_2_0 = models.DecimalField(
        max_digits=1000, decimal_places=1000, blank=True, null=True
    )
    cvss_2_0_severity = models.TextField(blank=True, null=True)
    cvss_2_0_vector = models.TextField(blank=True, null=True)
    cvss_3_0 = models.DecimalField(
        max_digits=1000, decimal_places=1000, blank=True, null=True
    )
    cvss_3_0_severity = models.TextField(blank=True, null=True)
    cvss_3_0_vector = models.TextField(blank=True, null=True)
    dve_score = models.DecimalField(
        max_digits=1000, decimal_places=1000, blank=True, null=True
    )

    class Meta:
        """Set CveInfo model metadata."""

        managed = False
        db_table = "cve_info"


class CyhyContacts(models.Model):
    """Define CyhyContacts model."""

    field_id = models.UUIDField(
        db_column="_id", primary_key=True, default=uuid.uuid1
    )  # Field renamed because it started with '_'.
    org_id = models.TextField()
    org_name = models.TextField()
    phone = models.TextField(blank=True, null=True)
    contact_type = models.TextField()
    email = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    date_pulled = models.DateField(blank=True, null=True)

    class Meta:
        """Set CyhyContacts model metadata."""

        managed = False
        db_table = "cyhy_contacts"
        unique_together = (("org_id", "contact_type", "email", "name"),)


class CyhyDbAssets(models.Model):
    """Define CyhyDbAssets model."""

    field_id = models.UUIDField(
        db_column="_id", primary_key=True, default=uuid.uuid1
    )  # Field renamed because it started with '_'.
    org_id = models.TextField(blank=True, null=True)
    org_name = models.TextField(blank=True, null=True)
    contact = models.TextField(blank=True, null=True)
    network = models.GenericIPAddressField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    first_seen = models.DateField(blank=True, null=True)
    last_seen = models.DateField(blank=True, null=True)
    currently_in_cyhy = models.BooleanField(blank=True, null=True)

    class Meta:
        """Set CyhyDbAssets model metadata."""

        managed = False
        db_table = "cyhy_db_assets"
        unique_together = (("org_id", "network"),)


class CyhyPortScans(models.Model):
    """Define CyhyPortScans model."""

    cyhy_port_scans_uid = models.UUIDField(primary_key=True)
    organizations_uid = models.ForeignKey(
        "Organizations", models.DO_NOTHING, db_column="organizations_uid"
    )
    cyhy_id = models.TextField(unique=True, blank=True, null=True)
    cyhy_time = models.DateTimeField(blank=True, null=True)
    service_name = models.TextField(blank=True, null=True)
    port = models.TextField(blank=True, null=True)
    product = models.TextField(blank=True, null=True)
    cpe = models.TextField(blank=True, null=True)
    first_seen = models.DateField(blank=True, null=True)
    last_seen = models.DateField(blank=True, null=True)
    ip = models.TextField(blank=True, null=True)
    state = models.TextField(blank=True, null=True)
    agency_type = models.TextField(blank=True, null=True)

    class Meta:
        """Set CyhyPortScans model metadata."""

        managed = False
        db_table = "cyhy_port_scans"


class DataapiApiuser(models.Model):
    """Define DataapiApiuser model."""

    id = models.BigAutoField(primary_key=True)
    apikey = models.CharField(
        db_column="apiKey", max_length=200, blank=True, null=True
    )  # Field name made lowercase.
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)
    refresh_token = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        """Set DataapiApiuser model metadata."""

        managed = False
        db_table = "dataAPI_apiuser"


class DataSource(models.Model):
    """Define DataSource model."""

    data_source_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    name = models.TextField()
    description = models.TextField()
    last_run = models.DateField()

    class Meta:
        """Set DataSource model metadata."""

        managed = False
        db_table = "data_source"


class DjangoAdminLog(models.Model):
    """Define DjangoAdminLog model."""

    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey(
        "DjangoContentType", on_delete=models.CASCADE, blank=True, null=True
    )
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)

    class Meta:
        """Set DjangoAdminLog model metadata."""

        managed = False
        db_table = "django_admin_log"


class DjangoContentType(models.Model):
    """Define DjangoContentType model."""

    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        """Set DjangoContentType model metadata."""

        managed = False
        db_table = "django_content_type"
        unique_together = (("app_label", "model"),)


class DjangoMigrations(models.Model):
    """Define DjangoMigrations model."""

    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        """Set DjangoMigrations model metadata."""

        managed = False
        db_table = "django_migrations"


class DjangoSession(models.Model):
    """Define DjangoSession model."""

    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        """Set DjangoSession model metadata."""

        managed = False
        db_table = "django_session"


class DNSMonitorDomainMap(models.Model):
    """Define dnsmonitor_domain_map model."""

    dnsmonitor_domain_map_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    domain = models.TextField(blank=True, null=True)
    organization = models.TextField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        """Set DNSMonitorDomainMap model metadata."""

        managed = False
        db_table = "dnsmonitor_domain_map"


class DnsRecords(models.Model):
    """Define DnsRecords model."""

    dns_record_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    domain_name = models.TextField(blank=True, null=True)
    domain_type = models.TextField(blank=True, null=True)
    created_date = models.DateTimeField(blank=True, null=True)
    updated_date = models.DateTimeField(blank=True, null=True)
    expiration_date = models.DateTimeField(blank=True, null=True)
    name_servers = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    whois_server = models.TextField(blank=True, null=True)
    registrar_name = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    clean_text = models.TextField(blank=True, null=True)
    raw_text = models.TextField(blank=True, null=True)
    registrant_name = models.TextField(blank=True, null=True)
    registrant_organization = models.TextField(blank=True, null=True)
    registrant_street = models.TextField(blank=True, null=True)
    registrant_city = models.TextField(blank=True, null=True)
    registrant_state = models.TextField(blank=True, null=True)
    registrant_post_code = models.TextField(blank=True, null=True)
    registrant_country = models.TextField(blank=True, null=True)
    registrant_email = models.TextField(blank=True, null=True)
    registrant_phone = models.TextField(blank=True, null=True)
    registrant_phone_ext = models.TextField(blank=True, null=True)
    registrant_fax = models.TextField(blank=True, null=True)
    registrant_fax_ext = models.TextField(blank=True, null=True)
    registrant_raw_text = models.TextField(blank=True, null=True)
    administrative_name = models.TextField(blank=True, null=True)
    administrative_organization = models.TextField(blank=True, null=True)
    administrative_street = models.TextField(blank=True, null=True)
    administrative_city = models.TextField(blank=True, null=True)
    administrative_state = models.TextField(blank=True, null=True)
    administrative_post_code = models.TextField(blank=True, null=True)
    administrative_country = models.TextField(blank=True, null=True)
    administrative_email = models.TextField(blank=True, null=True)
    administrative_phone = models.TextField(blank=True, null=True)
    administrative_phone_ext = models.TextField(blank=True, null=True)
    administrative_fax = models.TextField(blank=True, null=True)
    administrative_fax_ext = models.TextField(blank=True, null=True)
    administrative_raw_text = models.TextField(blank=True, null=True)
    technical_name = models.TextField(blank=True, null=True)
    technical_organization = models.TextField(blank=True, null=True)
    technical_street = models.TextField(blank=True, null=True)
    technical_city = models.TextField(blank=True, null=True)
    technical_state = models.TextField(blank=True, null=True)
    technical_post_code = models.TextField(blank=True, null=True)
    technical_country = models.TextField(blank=True, null=True)
    technical_email = models.TextField(blank=True, null=True)
    technical_phone = models.TextField(blank=True, null=True)
    technical_phone_ext = models.TextField(blank=True, null=True)
    technical_fax = models.TextField(blank=True, null=True)
    technical_fax_ext = models.TextField(blank=True, null=True)
    technical_raw_text = models.TextField(blank=True, null=True)
    billing_name = models.TextField(blank=True, null=True)
    billing_organization = models.TextField(blank=True, null=True)
    billing_street = models.TextField(blank=True, null=True)
    billing_city = models.TextField(blank=True, null=True)
    billing_state = models.TextField(blank=True, null=True)
    billing_post_code = models.TextField(blank=True, null=True)
    billing_country = models.TextField(blank=True, null=True)
    billing_email = models.TextField(blank=True, null=True)
    billing_phone = models.TextField(blank=True, null=True)
    billing_phone_ext = models.TextField(blank=True, null=True)
    billing_fax = models.TextField(blank=True, null=True)
    billing_fax_ext = models.TextField(blank=True, null=True)
    billing_raw_text = models.TextField(blank=True, null=True)
    zone_name = models.TextField(blank=True, null=True)
    zone_organization = models.TextField(blank=True, null=True)
    zone_street = models.TextField(blank=True, null=True)
    zone_city = models.TextField(blank=True, null=True)
    zone_state = models.TextField(blank=True, null=True)
    zone_post_code = models.TextField(blank=True, null=True)
    zone_country = models.TextField(blank=True, null=True)
    zone_email = models.TextField(blank=True, null=True)
    zone_phone = models.TextField(blank=True, null=True)
    zone_phone_ext = models.TextField(blank=True, null=True)
    zone_fax = models.TextField(blank=True, null=True)
    zone_fax_ext = models.TextField(blank=True, null=True)
    zone_raw_text = models.TextField(blank=True, null=True)

    class Meta:
        """Set DnsRecords model metadata."""

        managed = False
        db_table = "dns_records"


class DomainAlerts(models.Model):
    """Define DomainAlerts model."""

    domain_alert_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    sub_domain_uid = models.ForeignKey(
        "SubDomains", on_delete=models.CASCADE, db_column="sub_domain_uid"
    )
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )
    organizations_uid = models.ForeignKey(
        "Organizations", on_delete=models.CASCADE, db_column="organizations_uid"
    )
    alert_type = models.TextField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    previous_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        """Set DomainAlerts model metadata."""

        managed = False
        db_table = "domain_alerts"
        unique_together = (("alert_type", "sub_domain_uid", "date", "new_value"),)


class DomainPermutations(models.Model):
    """Define DomainPermutations model."""

    suspected_domain_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    organizations_uid = models.ForeignKey(
        "Organizations", on_delete=models.CASCADE, db_column="organizations_uid"
    )
    domain_permutation = models.TextField(blank=True, null=True)
    ipv4 = models.TextField(blank=True, null=True)
    ipv6 = models.TextField(blank=True, null=True)
    mail_server = models.TextField(blank=True, null=True)
    name_server = models.TextField(blank=True, null=True)
    fuzzer = models.TextField(blank=True, null=True)
    date_observed = models.DateField(blank=True, null=True)
    ssdeep_score = models.TextField(blank=True, null=True)
    malicious = models.BooleanField(blank=True, null=True)
    blocklist_attack_count = models.IntegerField(blank=True, null=True)
    blocklist_report_count = models.IntegerField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )
    sub_domain_uid = models.ForeignKey(
        "SubDomains",
        on_delete=models.CASCADE,
        db_column="sub_domain_uid",
        blank=True,
        null=True,
    )
    dshield_record_count = models.IntegerField(blank=True, null=True)
    dshield_attack_count = models.IntegerField(blank=True, null=True)
    date_active = models.DateField(blank=True, null=True)

    class Meta:
        """Set DomainPermutations model metadata."""

        managed = False
        db_table = "domain_permutations"
        unique_together = (("domain_permutation", "organizations_uid"),)


class FlareEvents(models.Model):
    """Define FlareEvents model."""

    flare_events_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    organizations_uid = models.ForeignKey(
        "Organizations", on_delete=models.CASCADE, db_column="organizations_uid"
    )
    flare_uid = models.TextField(blank=True, null=True)
    event_type = models.TextField(blank=True, null=True)
    event_date = models.DateField(blank=True, null=True)
    collection_date = models.DateField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    content_hash = models.TextField(blank=True, null=True)
    actor = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    source = models.TextField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    risk_scores = models.TextField(blank=True, null=True)
    related_identifiers = ArrayField(
        models.TextField(), blank=True, null=True, default=list
    )
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )
    severity = models.TextField(blank=True, null=True)
    related_identifiers_txt = ArrayField(
        models.TextField(), blank=True, null=True, default=list
    )

    class Meta:
        """Set FlareEvents model metadata."""

        managed = False
        db_table = "flare_events"
        unique_together = (("organizations_uid", "flare_uid"),)


class FlareEventTypes(models.Model):
    """Flare event type definitions used in dark-web report exports."""

    flare_event_type_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    event_type = models.TextField(unique=True)
    definition = models.TextField()
    used_in_report = models.BooleanField()

    class Meta:
        """Set FlareEventTypes model metadata."""

        managed = True
        db_table = "flare_event_types"


class DotgovDomains(models.Model):
    """Define DotgovDomains model."""

    dotgov_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    domain_name = models.TextField(unique=True)
    domain_type = models.TextField(blank=True, null=True)
    agency = models.TextField(blank=True, null=True)
    organization = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    state = models.TextField(blank=True, null=True)
    security_contact_email = models.TextField(blank=True, null=True)

    class Meta:
        """Set DotgovDomains model metadata."""

        managed = False
        db_table = "dotgov_domains"


class Executives(models.Model):
    """Define Executives model."""

    executives_uid = models.UUIDField(primary_key=True)
    organizations_uid = models.ForeignKey(
        "Organizations", on_delete=models.CASCADE, db_column="organizations_uid"
    )
    executives = models.TextField()

    class Meta:
        """Set Executives model metadata."""

        managed = False
        db_table = "executives"


class Ips(models.Model):
    """Define Ips model."""

    ip_hash = models.TextField(primary_key=True)
    ip = models.GenericIPAddressField(unique=True)
    origin_cidr = models.ForeignKey(
        Cidrs, on_delete=models.CASCADE, db_column="origin_cidr", blank=True, null=True
    )
    shodan_results = models.BooleanField(blank=True, null=True)
    live = models.BooleanField(blank=True, null=True)
    date_last_live = models.DateTimeField(blank=True, null=True)
    last_reverse_lookup = models.DateTimeField(blank=True, null=True)
    first_seen = models.DateField(blank=True, null=True)
    last_seen = models.DateField(blank=True, null=True)
    current = models.BooleanField(blank=True, null=True)
    from_cidr = models.BooleanField(blank=True, null=True)  # varchar type in db???
    organizations_uid = models.UUIDField(blank=True, null=True)

    class Meta:
        """Set Ips model metadata."""

        managed = False
        db_table = "ips"


class IpsSubs(models.Model):
    """Define IpsSubs model."""

    ips_subs_uid = models.UUIDField(primary_key=True)
    ip_hash = models.ForeignKey(Ips, on_delete=models.CASCADE, db_column="ip_hash")
    sub_domain_uid = models.ForeignKey(
        "SubDomains", on_delete=models.CASCADE, db_column="sub_domain_uid"
    )

    class Meta:
        """Set IpsSubs model metadata."""

        managed = False
        db_table = "ips_subs"
        unique_together = (("ip_hash", "sub_domain_uid"),)


class Mentions(models.Model):
    """Define Mentions model."""

    mentions_uid = models.UUIDField(primary_key=True)
    category = models.TextField(blank=True, null=True)
    collection_date = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    creator = models.TextField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    sixgill_mention_id = models.TextField(unique=True, blank=True, null=True)
    post_id = models.TextField(blank=True, null=True)
    lang = models.TextField(blank=True, null=True)
    rep_grade = models.TextField(blank=True, null=True)
    site = models.TextField(blank=True, null=True)
    site_grade = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    comments_count = models.TextField(blank=True, null=True)
    sub_category = models.TextField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)
    organizations_uid = models.UUIDField()
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )
    title_translated = models.TextField(blank=True, null=True)
    content_translated = models.TextField(blank=True, null=True)
    detected_lang = models.TextField(blank=True, null=True)

    class Meta:
        """Set Mentions model metadata."""

        managed = False
        db_table = "mentions"


class OrgIdMap(models.Model):
    """Define OrgIdMap model."""

    cyhy_id = models.TextField(blank=True, null=True)
    pe_org_id = models.TextField(blank=True, null=True)
    merge_orgs = models.BooleanField(blank=True, null=True)

    class Meta:
        """Set OrgIdMap model metadata."""

        managed = False
        db_table = "org_id_map"
        unique_together = (("cyhy_id", "pe_org_id"),)


class OrgType(models.Model):
    """Define OrgType model."""

    org_type_uid = models.UUIDField(primary_key=True, default=uuid.uuid1())
    org_type = models.TextField(blank=True, null=True)

    class Meta:
        """Set OrgType model metadata."""

        managed = False
        db_table = "org_type"


class Organizations(models.Model):
    """Define Organizations model."""

    organizations_uid = models.UUIDField(primary_key=True)
    name = models.TextField()
    cyhy_db_name = models.TextField(unique=True, blank=True, null=True)
    org_type_uid = models.ForeignKey(
        OrgType,
        on_delete=models.CASCADE,
        db_column="org_type_uid",
        blank=True,
        null=True,
    )
    report_on = models.BooleanField(blank=True, null=True)
    password = models.TextField(blank=True, null=True)
    date_first_reported = models.DateTimeField(blank=True, null=True)
    parent_org_uid = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        db_column="parent_org_uid",
        blank=True,
        null=True,
    )
    premium_report = models.BooleanField(blank=True, null=True)
    agency_type = models.TextField(blank=True, null=True)
    demo = models.BooleanField(blank=True, null=True)
    scorecard = models.BooleanField(blank=True, null=True)
    fceb = models.BooleanField(blank=True, null=True)
    receives_cyhy_report = models.BooleanField(blank=True, null=True)
    receives_bod_report = models.BooleanField(blank=True, null=True)
    receives_cybex_report = models.BooleanField(blank=True, null=True)
    run_scans = models.BooleanField(blank=True, null=True)
    is_parent = models.BooleanField(blank=True, null=True)
    ignore_roll_up = models.BooleanField(blank=True, null=True)
    retired = models.BooleanField(blank=True, null=True)
    cyhy_period_start = models.DateTimeField(blank=True, null=True)
    fceb_child = models.BooleanField(blank=True, null=True)
    election = models.BooleanField(blank=True, null=True)
    scorecard_child = models.BooleanField(blank=True, null=True)
    location_name = models.TextField(blank=True, null=True)
    county = models.TextField(blank=True, null=True)
    county_fips = models.DecimalField(
        max_digits=10, decimal_places=0, blank=True, null=True
    )
    state_abbreviation = models.TextField(blank=True, null=True)
    state_fips = models.DecimalField(
        max_digits=10, decimal_places=0, blank=True, null=True
    )
    state_name = models.TextField(blank=True, null=True)
    country = models.TextField(blank=True, null=True)
    country_name = models.TextField(blank=True, null=True)
    exec_url = models.TextField(blank=True, null=True)

    class Meta:
        """Set Organizations model metadata."""

        managed = False
        db_table = "organizations"


class PshttResults(models.Model):
    """Define PshttResults model."""

    pshtt_results_uid = models.UUIDField(primary_key=True, default=uuid.uuid1())
    organizations_uid = models.ForeignKey(
        "Organizations", on_delete=models.CASCADE, db_column="organizations_uid"
    )
    sub_domain_uid = models.ForeignKey(
        "SubDomains", on_delete=models.CASCADE, db_column="sub_domain_uid"
    )
    data_source_uid = models.ForeignKey(
        "DataSource", on_delete=models.CASCADE, db_column="data_source_uid"
    )
    sub_domain = models.TextField()
    date_scanned = models.DateField(blank=True, null=True)
    base_domain = models.TextField(blank=True, null=True)
    base_domain_hsts_preloaded = models.BooleanField(blank=True, null=True)
    canonical_url = models.TextField(blank=True, null=True)
    defaults_to_https = models.BooleanField(blank=True, null=True)
    domain = models.TextField(blank=True, null=True)
    domain_enforces_https = models.BooleanField(blank=True, null=True)
    domain_supports_https = models.BooleanField(blank=True, null=True)
    domain_uses_strong_hsts = models.BooleanField(blank=True, null=True)
    downgrades_https = models.BooleanField(blank=True, null=True)
    htss = models.BooleanField(blank=True, null=True)
    hsts_entire_domain = models.BooleanField(blank=True, null=True)
    hsts_header = models.TextField(blank=True, null=True)
    hsts_max_age = models.DecimalField(
        max_digits=1000, decimal_places=1000, blank=True, null=True
    )
    hsts_preload_pending = models.BooleanField(blank=True, null=True)
    hsts_preload_ready = models.BooleanField(blank=True, null=True)
    hsts_preloaded = models.BooleanField(blank=True, null=True)
    https_bad_chain = models.BooleanField(blank=True, null=True)
    https_bad_hostname = models.BooleanField(blank=True, null=True)
    https_cert_chain_length = models.IntegerField(blank=True, null=True)
    https_client_auth_required = models.BooleanField(blank=True, null=True)
    https_custom_truststore_trusted = models.BooleanField(blank=True, null=True)
    https_expired_cert = models.BooleanField(blank=True, null=True)
    https_full_connection = models.BooleanField(blank=True, null=True)
    https_live = models.BooleanField(blank=True, null=True)
    https_probably_missing_intermediate_cert = models.BooleanField(
        blank=True, null=True
    )
    https_publicly_trusted = models.BooleanField(blank=True, null=True)
    https_self_signed_cert = models.BooleanField(blank=True, null=True)
    https_leaf_cert_expiration_date = models.DateField(blank=True, null=True)
    https_leaf_cert_issuer = models.TextField(blank=True, null=True)
    https_leaf_cert_subject = models.TextField(blank=True, null=True)
    https_root_cert_issuer = models.TextField(blank=True, null=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    live = models.BooleanField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    redirect = models.BooleanField(blank=True, null=True)
    redirect_to = models.TextField(blank=True, null=True)
    server_header = models.TextField(blank=True, null=True)
    server_version = models.TextField(blank=True, null=True)
    strictly_forces_https = models.BooleanField(blank=True, null=True)
    unknown_error = models.BooleanField(blank=True, null=True)
    valid_https = models.BooleanField(blank=True, null=True)
    ep_http_headers = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    ep_http_server_header = models.TextField(blank=True, null=True)
    ep_http_server_version = models.TextField(blank=True, null=True)
    ep_https_headers = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    ep_https_hsts_header = models.TextField(blank=True, null=True)
    ep_https_server_header = models.TextField(blank=True, null=True)
    ep_https_server_version = models.TextField(blank=True, null=True)
    ep_httpswww_headers = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    ep_httpswww_hsts_header = models.TextField(blank=True, null=True)
    ep_httpswww_server_header = models.TextField(blank=True, null=True)
    ep_httpswww_server_version = models.TextField(blank=True, null=True)
    ep_httpwww_headers = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    ep_httpwww_server_header = models.TextField(blank=True, null=True)
    ep_httpwww_server_version = models.TextField(blank=True, null=True)

    class Meta:
        """Set PshttResults model metadata."""

        managed = False
        db_table = "pshtt_results"
        unique_together = (("organizations_uid", "sub_domain_uid"),)


class VwPshttDomainsToRun(models.Model):
    """Define VwPshttDomainsToRun model."""

    sub_domain_uid = models.UUIDField(primary_key=True)
    sub_domain = models.TextField(blank=True, null=True)
    organizations_uid = models.UUIDField()
    name = models.TextField(blank=True, null=True)

    class Meta:
        """Set VwPshttDomainsToRun model metadata."""

        managed = False
        db_table = "vw_pshtt_domains_to_run"


class ReportSummaryStats(models.Model):
    """Define ReportSummaryStats model."""

    report_uid = models.UUIDField(primary_key=True, default=uuid.uuid1())
    organizations_uid = models.ForeignKey(
        Organizations, on_delete=models.CASCADE, db_column="organizations_uid"
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    ip_count = models.IntegerField(blank=True, null=True)
    root_count = models.IntegerField(blank=True, null=True)
    sub_count = models.IntegerField(blank=True, null=True)
    ports_count = models.IntegerField(blank=True, null=True)
    creds_count = models.IntegerField(blank=True, null=True)
    breach_count = models.IntegerField(blank=True, null=True)
    cred_password_count = models.IntegerField(blank=True, null=True)
    domain_alert_count = models.IntegerField(blank=True, null=True)
    suspected_domain_count = models.IntegerField(blank=True, null=True)
    insecure_port_count = models.IntegerField(blank=True, null=True)
    verified_vuln_count = models.IntegerField(blank=True, null=True)
    suspected_vuln_count = models.IntegerField(blank=True, null=True)
    suspected_vuln_addrs_count = models.IntegerField(blank=True, null=True)
    threat_actor_count = models.IntegerField(blank=True, null=True)
    dark_web_alerts_count = models.IntegerField(blank=True, null=True)
    dark_web_mentions_count = models.IntegerField(blank=True, null=True)
    dark_web_executive_alerts_count = models.IntegerField(blank=True, null=True)
    dark_web_asset_alerts_count = models.IntegerField(blank=True, null=True)
    pe_number_score = models.TextField(blank=True, null=True)
    pe_letter_grade = models.TextField(blank=True, null=True)
    pe_percent_score = models.DecimalField(
        max_digits=1000, decimal_places=1000, blank=True, null=True
    )
    cidr_count = models.IntegerField(blank=True, null=True)
    port_protocol_count = models.IntegerField(blank=True, null=True)
    software_count = models.IntegerField(blank=True, null=True)
    foreign_ips_count = models.IntegerField(blank=True, null=True)

    class Meta:
        """Set ReportSummaryStats model metadata."""

        managed = True
        db_table = "report_summary_stats"
        unique_together = (("organizations_uid", "start_date"),)


class RootDomains(models.Model):
    """Define RootDomains model."""

    root_domain_uid = models.UUIDField(primary_key=True, default=uuid.uuid1())
    organizations_uid = models.ForeignKey(
        Organizations, on_delete=models.CASCADE, db_column="organizations_uid"
    )
    root_domain = models.TextField()
    ip_address = models.TextField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )
    enumerate_subs = models.BooleanField(blank=True, null=True)

    class Meta:
        """Set RootDomains model metadata."""

        managed = False
        db_table = "root_domains"
        unique_together = (("root_domain", "organizations_uid"),)


class TeamMembers(models.Model):
    """Define TeamMembers model."""

    team_member_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    team_member_fname = models.TextField()
    team_member_lname = models.TextField()
    team_member_email = models.TextField()
    team_member_ghID = models.TextField(blank=False, null=False)
    team_member_phone = models.TextField(blank=True, null=True)
    team_member_role = models.TextField(blank=True, null=True)
    team_member_notes = models.TextField(blank=True, null=True)

    class Meta:
        """Set TeamMembers model metadata."""

        managed = True
        db_table = "team_members"


class ShodanAssets(models.Model):
    """Define ShodanAssets model."""

    shodan_asset_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    organizations_uid = models.ForeignKey(
        Organizations, on_delete=models.CASCADE, db_column="organizations_uid"
    )
    organization = models.TextField(blank=True, null=True)
    ip = models.TextField(blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    protocol = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)
    product = models.TextField(blank=True, null=True)
    server = models.TextField(blank=True, null=True)
    tags = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    domains = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    hostnames = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    isn = models.TextField(blank=True, null=True)
    asn = models.IntegerField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )
    country_code = models.TextField(blank=True, null=True)
    location = models.TextField(blank=True, null=True)

    class Meta:
        """Set ShodanAssets model metadata."""

        managed = False
        db_table = "shodan_assets"
        unique_together = (
            ("organizations_uid", "ip", "port", "protocol", "timestamp"),
        )


class ShodanInsecureProtocolsUnverifiedVulns(models.Model):
    """Define ShodanInsecureProtocolsUnverifiedVulns model."""

    insecure_product_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    organizations_uid = models.ForeignKey(
        Organizations, on_delete=models.CASCADE, db_column="organizations_uid"
    )
    organization = models.TextField(blank=True, null=True)
    ip = models.TextField(blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    protocol = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    potential_vulns = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    mitigation = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)
    product = models.TextField(blank=True, null=True)
    server = models.TextField(blank=True, null=True)
    tags = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    domains = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    hostnames = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    isn = models.TextField(blank=True, null=True)
    asn = models.IntegerField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )

    class Meta:
        """Set ShodanInsecureProtocolsUnverifiedVulns model metadata."""

        managed = False
        db_table = "old_shodan_insecure_protocols_unverified_vulns"
        unique_together = (
            ("organizations_uid", "ip", "port", "protocol", "timestamp"),
        )


class ShodanVulns(models.Model):
    """Define ShodanVulns model."""

    shodan_vuln_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    organizations_uid = models.ForeignKey(
        Organizations, on_delete=models.CASCADE, db_column="organizations_uid"
    )
    organization = models.TextField(blank=True, null=True)
    ip = models.TextField(blank=True, null=True)
    port = models.TextField(blank=True, null=True)
    protocol = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)
    cve = models.TextField(blank=True, null=True)
    severity = models.TextField(blank=True, null=True)
    cvss = models.DecimalField(
        max_digits=1000, decimal_places=1000, blank=True, null=True
    )
    summary = models.TextField(blank=True, null=True)
    product = models.TextField(blank=True, null=True)
    attack_vector = models.TextField(blank=True, null=True)
    av_description = models.TextField(blank=True, null=True)
    attack_complexity = models.TextField(blank=True, null=True)
    ac_description = models.TextField(blank=True, null=True)
    confidentiality_impact = models.TextField(blank=True, null=True)
    ci_description = models.TextField(blank=True, null=True)
    integrity_impact = models.TextField(blank=True, null=True)
    ii_description = models.TextField(blank=True, null=True)
    availability_impact = models.TextField(blank=True, null=True)
    ai_description = models.TextField(blank=True, null=True)
    tags = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    domains = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    hostnames = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    isn = models.TextField(blank=True, null=True)
    asn = models.IntegerField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )
    type = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    potential_vulns = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    mitigation = models.TextField(blank=True, null=True)
    server = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(blank=True, null=True)
    banner = models.TextField(blank=True, null=True)
    version = models.TextField(blank=True, null=True)
    mitigation = models.TextField(blank=True, null=True)
    cpe = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)

    class Meta:
        """Set ShodanVulns model metadata."""

        managed = False
        db_table = "shodan_vulns"
        unique_together = (
            ("organizations_uid", "ip", "port", "protocol", "timestamp"),
        )


class SubDomains(models.Model):
    """Define SubDomains model."""

    sub_domain_uid = models.UUIDField(primary_key=True, default=uuid.uuid1())
    sub_domain = models.TextField()
    root_domain_uid = models.ForeignKey(
        RootDomains, on_delete=models.CASCADE, db_column="root_domain_uid"
    )
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )
    dns_record_uid = models.ForeignKey(
        DnsRecords,
        on_delete=models.CASCADE,
        db_column="dns_record_uid",
        blank=True,
        null=True,
    )
    status = models.BooleanField(blank=True, null=True)
    first_seen = models.DateField(blank=True, null=True)
    last_seen = models.DateField(blank=True, null=True)
    current = models.BooleanField(blank=True, null=True)
    identified = models.BooleanField(blank=True, null=True)

    class Meta:
        """Set SubDomains model metadata."""

        managed = False
        db_table = "sub_domains"
        unique_together = (("sub_domain", "root_domain_uid"),)


class TopCves(models.Model):
    """Define TopCves model."""

    top_cves_uid = models.UUIDField(primary_key=True, default=uuid.uuid1())
    cve_id = models.TextField(blank=True, null=True)
    dynamic_rating = models.TextField(blank=True, null=True)
    nvd_base_score = models.TextField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )

    class Meta:
        """Set TopCves model metadata."""

        managed = False
        db_table = "top_cves"
        unique_together = (("cve_id", "date"),)


class TopCvesShodan(models.Model):
    """Shodan EPSS-ranked CVEs used by Flare dark-web report tables."""

    top_cves_shodan_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    cve_id = models.TextField()
    epss_score = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    nvd_base_score = models.TextField(blank=True, null=True)
    collection_date = models.DateField()
    summary = models.TextField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )

    class Meta:
        """Set TopCvesShodan model metadata."""

        managed = True
        db_table = "top_cves_shodan"
        unique_together = (("cve_id", "collection_date"),)


class TopicTotals(models.Model):
    """Define TopicTotals model."""

    cound_uuid = models.UUIDField(primary_key=True, default=uuid.uuid1())
    organizations_uid = models.UUIDField()
    content_count = models.IntegerField()
    count_date = models.TextField(blank=True, null=True)

    class Meta:
        """Set TopicTotals model metadata."""

        managed = False
        db_table = "topic_totals"


class UniqueSoftware(models.Model):
    """Define UniqueSoftware model."""

    field_id = models.UUIDField(
        db_column="_id", primary_key=True, default=uuid.uuid1()
    )  # Field renamed because it started with '_'.
    software_name = models.TextField()

    class Meta:
        """Set UniqueSoftware model metadata."""

        managed = False
        db_table = "unique_software"


class WasTrackerCustomerdata(models.Model):
    """Define WasTrackerCustomerdata model."""

    customer_id = models.UUIDField(
        db_column="customer_id", primary_key=True, default=uuid.uuid1
    )
    tag = models.TextField()
    customer_name = models.TextField()
    testing_sector = models.TextField()
    ci_type = models.TextField()
    jira_ticket = models.TextField()
    ticket = models.TextField()
    next_scheduled = models.TextField()
    last_scanned = models.TextField()
    frequency = models.TextField()
    comments_notes = models.TextField()
    was_report_poc = models.TextField()
    was_report_email = models.TextField()
    onboarding_date = models.TextField()
    no_of_web_apps = models.IntegerField()
    no_web_apps_last_updated = models.TextField(blank=True, null=True)
    elections = models.BooleanField(blank=False, null=False)
    fceb = models.BooleanField(blank=False, null=False)
    special_report = models.BooleanField(blank=False, null=False)
    report_password = models.TextField()
    child_tags = models.TextField()

    class Meta:
        """Set WasTrackerCustomerdata model metadata."""

        managed = False
        db_table = "was_tracker_customerdata"


class WebAssets(models.Model):
    """Define WebAssets model."""

    asset_uid = models.UUIDField(primary_key=True, default=uuid.uuid1())
    asset_type = models.TextField()
    asset = models.TextField()
    ip_type = models.TextField(blank=True, null=True)
    verified = models.BooleanField(blank=True, null=True)
    organizations_uid = models.ForeignKey(
        Organizations, on_delete=models.CASCADE, db_column="organizations_uid"
    )
    asset_origin = models.TextField(blank=True, null=True)
    report_on = models.BooleanField(blank=True, null=True)
    last_scanned = models.DateTimeField(blank=True, null=True)
    report_status_reason = models.TextField(blank=True, null=True)
    data_source_uid = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, db_column="data_source_uid"
    )

    class Meta:
        """Set WebAssets model metadata."""

        managed = False
        db_table = "web_assets"
        unique_together = (("asset", "organizations_uid"),)


class WeeklyStatuses(models.Model):
    """Define WeeklyStatuses model."""

    weekly_status_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    user_status = models.TextField(blank=True)
    key_accomplishments = models.TextField(blank=True, null=True)
    ongoing_task = models.TextField()
    upcoming_task = models.TextField()
    obstacles = models.TextField(blank=True, null=True)
    non_standard_meeting = models.TextField(blank=True, null=True)
    deliverables = models.TextField(blank=True, null=True)
    pto = models.TextField(blank=True, null=True)
    week_ending = models.DateField()
    notes = models.TextField(blank=True, null=True)
    statusComplete = models.IntegerField(blank=True, null=True)

    class Meta:
        """Set WeeklyStatuses model metadata."""

        # unique_together = (('week_ending', 'user_status'),)

        managed = True
        db_table = "weekly_statuses"


class VwBreachcompCredsbydate(models.Model):
    """Define VwBreachcompCredsbydate model."""

    organizations_uid = models.UUIDField(primary_key=True)
    mod_date = models.DateField(blank=True, null=True)
    no_password = models.BigIntegerField(blank=True, null=True)
    password_included = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwBreachcompCredsbydate model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_breachcomp_credsbydate"


class VwDarkwebMentionsbydate(models.Model):
    """Define VwDarkwebMentionsbydate model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    count = models.BigIntegerField(
        db_column="Count", blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        """Set VwDarkwebMentionsbydate model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_mentionsbydate"


class VwShodanvulnsSuspected(models.Model):
    """Define VwShodanvulnsSuspected model."""

    organizations_uid = models.UUIDField(primary_key=True)
    organization = models.TextField(blank=True, null=True)
    ip = models.TextField(blank=True, null=True)
    port = models.TextField(blank=True, null=True)
    protocol = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    potential_vulns = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    mitigation = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)
    product = models.TextField(blank=True, null=True)
    server = models.TextField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)  # This field type is a guess.
    domains = models.TextField(blank=True, null=True)  # This field type is a guess.
    hostnames = models.TextField(blank=True, null=True)  # This field type is a guess.
    isn = models.TextField(blank=True, null=True)
    asn = models.IntegerField(blank=True, null=True)
    data_source = models.TextField(blank=True, null=True)

    class Meta:
        """Set VwShodanvulnsSuspected model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_shodanvulns_suspected"


class VwShodanvulnsVerified(models.Model):
    """Define VwShodanvulnsVerified model."""

    organizations_uid = models.UUIDField(primary_key=True)
    organization = models.TextField(blank=True, null=True)
    ip = models.TextField(blank=True, null=True)
    port = models.TextField(blank=True, null=True)
    protocol = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)
    cve = models.TextField(blank=True, null=True)
    severity = models.TextField(blank=True, null=True)
    cvss = models.DecimalField(
        max_digits=1000, decimal_places=1000, blank=True, null=True
    )
    summary = models.TextField(blank=True, null=True)
    product = models.TextField(blank=True, null=True)
    attack_vector = models.TextField(blank=True, null=True)
    av_description = models.TextField(blank=True, null=True)
    attack_complexity = models.TextField(blank=True, null=True)
    ac_description = models.TextField(blank=True, null=True)
    confidentiality_impact = models.TextField(blank=True, null=True)
    ci_description = models.TextField(blank=True, null=True)
    integrity_impact = models.TextField(blank=True, null=True)
    ii_description = models.TextField(blank=True, null=True)
    availability_impact = models.TextField(blank=True, null=True)
    ai_description = models.TextField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)  # This field type is a guess.
    domains = models.TextField(blank=True, null=True)  # This field type is a guess.
    hostnames = models.TextField(blank=True, null=True)  # This field type is a guess.
    isn = models.TextField(blank=True, null=True)
    asn = models.IntegerField(blank=True, null=True)
    data_source = models.TextField(blank=True, null=True)
    banner = models.TextField(blank=True, null=True)
    version = models.TextField(blank=True, null=True)
    cpe = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)

    class Meta:
        """Set VwShodanvulnsVerified model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_shodanvulns_verified"


class VwBreachcompBreachdetails(models.Model):
    """Define VwBreachcompBreachdetails model."""

    organizations_uid = models.UUIDField(primary_key=True)
    breach_name = models.TextField(blank=True, null=True)
    mod_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    breach_date = models.DateField(blank=True, null=True)
    password_included = models.BooleanField(blank=True, null=True)
    number_of_creds = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwBreachcompBreachdetails model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_breachcomp_breachdetails"


class VwDarkwebSocmediaMostactposts(models.Model):
    """Define VwDarkwebSocmediaMostactposts model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    title = models.TextField(
        db_column="Title", blank=True, null=True
    )  # Field name made lowercase.
    comments_count = models.IntegerField(
        db_column="Comments Count", blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        """Set VwDarkwebSocmediaMostactposts model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_socmedia_mostactposts"


class VwDarkwebMostactposts(models.Model):
    """Define VwDarkwebMostactposts model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    title = models.TextField(
        db_column="Title", blank=True, null=True
    )  # Field name made lowercase.
    comments_count = models.IntegerField(
        db_column="Comments Count", blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        """Set VwDarkwebMostactposts model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_mostactposts"


class VwDarkwebAssetalerts(models.Model):
    """Define VwDarkwebAssetalerts model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    site = models.TextField(
        db_column="Site", blank=True, null=True
    )  # Field name made lowercase.
    title = models.TextField(
        db_column="Title", blank=True, null=True
    )  # Field name made lowercase.
    events = models.BigIntegerField(
        db_column="Events", blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        """Set VwDarkwebAssetalerts model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_assetalerts"


class VwDarkwebExecalerts(models.Model):
    """Define VwDarkwebExecalerts model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    site = models.TextField(
        db_column="Site", blank=True, null=True
    )  # Field name made lowercase.
    title = models.TextField(
        db_column="Title", blank=True, null=True
    )  # Field name made lowercase.
    events = models.BigIntegerField(
        db_column="Events", blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        """Set VwDarkwebExecalerts model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_execalerts"


class VwDarkwebThreatactors(models.Model):
    """Define VwDarkwebThreatactors model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    creator = models.TextField(
        db_column="Creator", blank=True, null=True
    )  # Field name made lowercase.
    grade = models.DecimalField(
        db_column="Grade", max_digits=1000, decimal_places=1000, blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        """Set VwDarkwebThreatactors model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_threatactors"


class VwDarkwebPotentialthreats(models.Model):
    """Define VwDarkwebPotentialthreats model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    site = models.TextField(
        db_column="Site", blank=True, null=True
    )  # Field name made lowercase.
    threats = models.TextField(
        db_column="Threats", blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        """Set VwDarkwebPotentialthreats model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_potentialthreats"


class VwDarkwebSites(models.Model):
    """Define VwDarkwebSites model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    site = models.TextField(
        db_column="Site", blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        """Set VwDarkwebSites model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_sites"


class VwDarkwebInviteonlymarkets(models.Model):
    """Define VwDarkwebInviteonlymarkets model."""

    organizations_uid = models.UUIDField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    site = models.TextField(
        db_column="Site", blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        """Set VwDarkwebInviteonlymarkets model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_inviteonlymarkets"


class VwDarkwebTopcves(models.Model):
    """Define VwDarkwebTopcves model."""

    top_cves_uid = models.UUIDField(primary_key=True)
    cve_id = models.TextField(blank=True, null=True)
    dynamic_rating = models.TextField(blank=True, null=True)
    nvd_base_score = models.TextField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    data_source_uid = models.UUIDField(blank=True, null=True)

    class Meta:
        """Set VwDarkwebTopcves model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_darkweb_topcves"


class VwCidrs(models.Model):
    """Define VwCidrs model."""

    cidr_uid = models.UUIDField(primary_key=True)
    network = models.TextField(blank=True, null=True)  # This field type is a guess.
    organizations_uid = models.UUIDField(blank=True, null=True)
    data_source_uid = models.UUIDField(blank=True, null=True)
    insert_alert = models.TextField(blank=True, null=True)

    class Meta:
        """Set VwCidrs model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_cidrs"


class VwBreachcomp(models.Model):
    """Define VwBreachcomp model."""

    credential_exposures_uid = models.UUIDField(primary_key=True)
    email = models.TextField(blank=True, null=True)
    breach_name = models.TextField(blank=True, null=True)
    organizations_uid = models.UUIDField(blank=True, null=True)
    root_domain = models.TextField(blank=True, null=True)
    sub_domain = models.TextField(blank=True, null=True)
    hash_type = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    login_id = models.TextField(blank=True, null=True)
    password = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    data_source_uid = models.UUIDField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    breach_date = models.DateField(blank=True, null=True)
    added_date = models.DateTimeField(blank=True, null=True)
    modified_date = models.DateTimeField(blank=True, null=True)
    data_classes = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    password_included = models.BooleanField(blank=True, null=True)
    is_verified = models.BooleanField(blank=True, null=True)
    is_fabricated = models.BooleanField(blank=True, null=True)
    is_sensitive = models.BooleanField(blank=True, null=True)
    is_retired = models.BooleanField(blank=True, null=True)
    is_spam_list = models.BooleanField(blank=True, null=True)

    class Meta:
        """Set VwBreachcomp model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_breachcomp"


class VwOrgsTotalDomains(models.Model):
    """Define VwOrgsTotalDomains model."""

    organizations_uid = models.UUIDField(primary_key=True)
    cyhy_db_name = models.TextField(blank=True, null=True)
    num_root_domain = models.BigIntegerField(blank=True, null=True)
    num_sub_domain = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwOrgsTotalDomains model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_orgs_total_domains"


class VwOrgsContactInfo(models.Model):
    """Define VwOrgsContactInfo model."""

    organizations_uid = models.UUIDField(primary_key=True)
    cyhy_db_name = models.TextField(blank=True, null=True)
    agency_name = models.TextField(blank=True, null=True)
    contact_type = models.TextField(blank=True, null=True)
    contact_name = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    date_pulled = models.DateField(blank=True, null=True)

    class Meta:
        """Set VwOrgsContactInfo model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_orgs_contact_info"


class VwOrgsTotalIps(models.Model):
    """Define VwOrgsTotalIps model."""

    organizations_uid = models.UUIDField(primary_key=True)
    cyhy_db_name = models.TextField(blank=True, null=True)
    num_ips = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwOrgsTotalIps model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_orgs_total_ips"


class MatVwOrgsAllIps(models.Model):
    """Define MatVwOrgsAllIps model."""

    organizations_uid = models.UUIDField(primary_key=True)
    cyhy_db_name = models.TextField(blank=True, null=True)
    ip_addresses = ArrayField(
        models.GenericIPAddressField(blank=True, null=True), blank=True, null=True
    )

    class Meta:
        """Set MatVwOrgsAllIps model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "mat_vw_orgs_all_ips"


class VwOrgsAttacksurface(models.Model):
    """Define VwOrgsAttacksurface model."""

    organizations_uid = models.UUIDField(primary_key=True)
    cyhy_db_name = models.TextField(blank=True, null=True)
    num_ports = models.BigIntegerField(blank=True, null=True)
    num_root_domain = models.BigIntegerField(blank=True, null=True)
    num_sub_domain = models.BigIntegerField(blank=True, null=True)
    num_ips = models.BigIntegerField(blank=True, null=True)
    num_cidrs = models.BigIntegerField(blank=True, null=True)
    num_ports_protocols = models.BigIntegerField(blank=True, null=True)
    num_software = models.BigIntegerField(blank=True, null=True)
    num_foreign_ips = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwOrgsAttacksurface model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_orgs_attacksurface"


class VwOrgsTotalPorts(models.Model):
    """Define VwOrgsTotalPorts model."""

    organizations_uid = models.UUIDField(primary_key=True)
    cyhy_db_name = models.TextField(blank=True, null=True)
    num_ports = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwOrgsTotalPorts model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_orgs_total_ports"


class VwIpsSubRootOrgInfo(models.Model):
    """VwIpsSubRootOrgInfo model class."""

    ip_hash = models.CharField(blank=True, null=True, max_length=255)
    ip = models.CharField(blank=True, null=True, max_length=255)
    origin_cidr = models.UUIDField(blank=True, null=True)
    organizations_uid = models.UUIDField(blank=True, null=True)
    i_current = models.BooleanField(blank=True, null=True)
    sd_current = models.BooleanField(blank=True, null=True)

    class Meta:
        """VwIpsSubRootOrgInfo model meta class."""

        managed = False
        db_table = "vw_ips_sub_root_org_info"


class VwIpsCidrOrgInfo(models.Model):
    """VwIpsCidrOrgInfo model class."""

    ip_hash = models.CharField(blank=True, null=True, max_length=255)
    ip = models.CharField(blank=True, null=True, max_length=255)
    origin_cidr = models.UUIDField(blank=True, null=True)
    network = models.CharField(blank=True, null=True, max_length=255)
    organizations_uid = models.UUIDField(blank=True, null=True)

    class Meta:
        """VwIpsCidrOrgInfo model meta class."""

        managed = False
        db_table = "vw_ips_cidr_org_info"


class VwPEScoreCheckNewCVE(models.Model):
    """VwPEScoreCheckNewCVE model class."""

    cve_name = models.CharField(blank=True, null=True, max_length=255)

    class Meta:
        """VwPEScoreCheckNewCVE model meta class."""

        managed = False
        db_table = "vw_pescore_check_new_cve"


# ---------- D-Score View Models ----------
# D-Score VS Cert View
class VwDscoreVSCert(models.Model):
    """Define VwDscoreVSCert model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    num_ident_cert = models.BigIntegerField(blank=True, null=True)
    num_monitor_cert = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwDscoreVSCert model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_dscore_vs_cert"


# D-Score VS Mail View
class VwDscoreVSMail(models.Model):
    """Define VwDscoreVSMail model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    num_valid_dmarc = models.BigIntegerField(blank=True, null=True)
    num_valid_spf = models.BigIntegerField(blank=True, null=True)
    num_valid_dmarc_or_spf = models.BigIntegerField(blank=True, null=True)
    total_mail_domains = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwDscoreVSMail model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_dscore_vs_mail"


# D-Score PE IP View
class VwDscorePEIp(models.Model):
    """Define VwDscorePEIp model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    num_ident_ip = models.BigIntegerField(blank=True, null=True)
    num_monitor_ip = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwDscorePEIp model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_dscore_pe_ip"


# D-Score PE Domain View
class VwDscorePEDomain(models.Model):
    """Define VwDscorePEDomain model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    num_ident_domain = models.BigIntegerField(blank=True, null=True)
    num_monitor_domain = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwDscorePEDomain model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_dscore_pe_domain"


# D-Score WAS Webapp View
class VwDscoreWASWebapp(models.Model):
    """Define VwDscoreWASWebapp model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    num_ident_webapp = models.BigIntegerField(blank=True, null=True)
    num_monitor_webapp = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwDscoreWASWebapp model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_dscore_was_webapp"


# ---------- I-Score View Models ----------
# I-Score VS Vuln View
class VwIscoreVSVuln(models.Model):
    """Define VwIscoreVSVuln model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    cve_name = models.CharField(blank=True, null=True, max_length=255)
    cvss_score = models.FloatField(blank=True, null=True)

    class Meta:
        """Set VwIscoreVSVuln model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_vs_vuln"


# I-Score VS Vuln Previous View
class VwIscoreVSVulnPrev(models.Model):
    """Define VwIscoreVSVulnPrev model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    cve_name = models.CharField(blank=True, null=True, max_length=255)
    cvss_score = models.FloatField(blank=True, null=True)
    time_closed = models.DateField(blank=True, null=True)

    class Meta:
        """Set VwIscoreVSVulnPrev model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_vs_vuln_prev"


# I-Score PE Vuln View
class VwIscorePEVuln(models.Model):
    """Define VwIscorePEVuln model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    cve_name = models.CharField(blank=True, null=True, max_length=255)
    cvss_score = models.FloatField(blank=True, null=True)

    class Meta:
        """Set VwIscorePEVuln model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_pe_vuln"


# I-Score PE Cred View
class VwIscorePECred(models.Model):
    """Define VwIscorePECred model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    password_creds = models.BigIntegerField(blank=True, null=True)
    total_creds = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwIscorePECred model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_pe_cred"


# I-Score PE Breach View
class VwIscorePEBreach(models.Model):
    """Define VwIscorePEBreach model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    breach_count = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwIscorePEBreach model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_pe_breach"


# I-Score PE Darkweb View
class VwIscorePEDarkweb(models.Model):
    """Define VwIscorePEDarkweb model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    alert_type = models.CharField(blank=True, null=True, max_length=255)
    date = models.DateField(blank=True, null=True)
    Count = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwIscorePEDarkweb model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_pe_darkweb"


# I-Score PE Protocol View
class VwIscorePEProtocol(models.Model):
    """Define VwIscorePEProtocol model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    port = models.CharField(blank=True, null=True, max_length=255)
    ip = models.CharField(blank=True, null=True, max_length=255)
    protocol = models.CharField(blank=True, null=True, max_length=255)
    protocol_type = models.CharField(blank=True, null=True, max_length=255)
    date = models.DateField(blank=True, null=True)

    class Meta:
        """Set VwIscorePEProtocol model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_pe_protocol"


# I-Score WAS Vuln View
class VwIscoreWASVuln(models.Model):
    """Define VwIscoreWASVuln model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    cve_name = models.CharField(blank=True, null=True, max_length=255)
    cvss_score = models.FloatField(blank=True, null=True)
    owasp_category = models.CharField(blank=True, null=True, max_length=255)

    class Meta:
        """Set VwIscoreWASVuln model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_was_vuln"


# I-Score WAS Vuln Previous View
class VwIscoreWASVulnPrev(models.Model):
    """Define VwIscoreWASVulnPrev model."""

    organizations_uid = models.UUIDField(primary_key=True)
    parent_org_uid = models.UUIDField(blank=True, null=True)
    was_total_vulns_prev = models.BigIntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        """Set VwIscoreWASVulnPrev model metadata."""

        managed = False  # Created from a view. Don't remove.
        db_table = "vw_iscore_was_vuln_prev"


# cyhy_kevs table model (needed for kev_list endpoint)
class CyhyKevs(models.Model):
    """Define CyhyKevs model."""

    cyhy_kevs_uid = models.UUIDField(primary_key=True)
    kev = models.CharField(blank=True, null=True, max_length=255)
    first_seen = models.DateField(blank=True, null=True)
    last_seen = models.DateField(blank=True, null=True)

    class Meta:
        """Set CyhyKevs model metadata."""

        managed = False
        db_table = "cyhy_kevs"


# ---------- Misc. Score Related Models ----------
# vw_iscore_orgs_ip_counts view model (used for XS/S/M/L/XL orgs endpoints)
class VwIscoreOrgsIpCounts(models.Model):
    """Define VwIscoreOrgsIpCounts model."""

    organizations_uid = models.UUIDField(primary_key=True)
    cyhy_db_name = models.CharField(blank=True, null=True, max_length=255)
    ip_count = models.BigIntegerField(blank=True, null=True)

    class Meta:
        """Set VwIscoreOrgsIpCounts model metadata."""

        managed = False
        db_table = "vw_iscore_orgs_ip_counts"


class XpanseBusinessUnits(models.Model):
    """Define XpanseBusinessUnits model."""

    xpanse_business_unit_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    entity_name = models.TextField(unique=True, blank=True, null=True)
    cyhy_db_name = models.ForeignKey(
        "Organizations",
        on_delete=models.CASCADE,
        db_column="cyhy_db_name",
        to_field="cyhy_db_name",
    )
    state = models.TextField(blank=True, null=True)
    county = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    sector = models.TextField(blank=True, null=True)
    entity_type = models.TextField(blank=True, null=True)
    region = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)

    class Meta:
        """Set XpanseBusinessUnits metadata."""

        managed = False
        db_table = "xpanse_business_units"


class XpanseAssets(models.Model):
    """Define XpanseAssets model."""

    xpanse_asset_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    asm_id = models.TextField(unique=True, blank=False, null=False)
    asset_name = models.TextField(blank=True, null=True)
    asset_type = models.TextField(blank=True, null=True)
    last_observed = models.DateTimeField(blank=True, null=True)
    first_observed = models.DateTimeField(blank=True, null=True)
    externally_detected_providers = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    created = models.DateTimeField(blank=True, null=True)
    ips = ArrayField(models.TextField(blank=True, null=False), blank=True, null=True)
    active_external_services_types = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    domain = models.TextField(blank=True, null=True)
    certificate_issuer = models.TextField(blank=True, null=True)
    certificate_algorithm = models.TextField(blank=True, null=True)
    certificate_classifications = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    resolves = models.BooleanField(blank=True, null=True)
    # details
    top_level_asset_mapper_domain = models.TextField(blank=True, null=True)
    domain_asset_type = models.JSONField(blank=True, null=True)
    is_paid_level_domain = models.BooleanField(blank=True, null=True)
    domain_details = models.JSONField(blank=True, null=True)
    dns_zone = models.TextField(blank=True, null=True)
    latest_sampled_ip = models.IntegerField(blank=True, null=True)

    recent_ips = models.JSONField(blank=True, null=True)
    external_services = models.JSONField(blank=True, null=True)
    externally_inferred_vulnerability_score = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    externally_inferred_cves = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    explainers = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    tags = ArrayField(models.TextField(blank=True, null=False), blank=True, null=True)

    class Meta:
        """Set XpanseAssets metdata."""

        managed = True
        db_table = "xpanse_assets"


class XpanseCves(models.Model):
    """Define XpanseCves model."""

    xpanse_cve_uid = models.UUIDField(unique=True, primary_key=True, default=uuid.uuid1)
    cve_id = models.TextField(unique=True, blank=True, null=True)
    cvss_score_v2 = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    cve_severity_v2 = models.TextField(blank=True, null=True)
    cvss_score_v3 = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    cve_severity_v3 = models.TextField(blank=True, null=True)

    class Meta:
        """Set XpanseCves metadata."""

        managed = True
        db_table = "xpanse_cves"


class XpanseServices(models.Model):
    """Define XpanseServices model."""

    xpanse_service_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    service_id = models.TextField(unique=True, blank=True, null=True)
    service_name = models.TextField(blank=True, null=True)
    service_type = models.TextField(blank=True, null=True)
    ip_address = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    domain = ArrayField(models.TextField(blank=True, null=False), blank=True, null=True)
    externally_detected_providers = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    is_active = models.TextField(blank=True, null=True)
    first_observed = models.DateTimeField(blank=True, null=True)
    last_observed = models.DateTimeField(blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    protocol = models.TextField(blank=True, null=True)
    active_classifications = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    inactive_classifications = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    discovery_type = models.TextField(blank=True, null=True)
    externally_inferred_vulnerability_score = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    externally_inferred_cves = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    service_key = models.TextField(blank=True, null=True)
    service_key_type = models.TextField(blank=True, null=True)

    cves = models.ManyToManyField(XpanseCves, through="XpanseCveService")

    class Meta:
        """Set XpanseServices metadata."""

        managed = True
        db_table = "xpanse_services"


class XpanseCveService(models.Model):
    """Define XpanseCves-Service linking table model."""

    xpanse_inferred_cve = models.ForeignKey(XpanseCves, on_delete=models.CASCADE)
    xpanse_service = models.ForeignKey(XpanseServices, on_delete=models.CASCADE)
    inferred_cve_match_type = models.TextField(blank=True, null=True)
    product = models.TextField(blank=True, null=True)
    confidence = models.TextField(blank=True, null=True)
    vendor = models.TextField(blank=True, null=True)
    version_number = models.TextField(blank=True, null=True)
    activity_status = models.TextField(blank=True, null=True)
    first_observed = models.DateTimeField(blank=True, null=True)
    last_observed = models.DateTimeField(blank=True, null=True)

    class Meta:
        """Set XpanseCveService metadata."""

        managed = True
        db_table = "xpanse_cve_services"
        unique_together = (("xpanse_inferred_cve", "xpanse_service"),)


class XpanseAlerts(models.Model):
    """Define XpanseAlerts model."""

    xpanse_alert_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    time_pulled_from_xpanse = models.DateTimeField(blank=True, null=True)
    alert_id = models.TextField(unique=True, blank=False, null=False)
    detection_timestamp = models.DateTimeField(blank=True, null=True)
    alert_name = models.TextField(blank=True, null=True)
    # endpoint_id ???,
    description = models.TextField(blank=True, null=True)
    host_name = models.TextField(blank=True, null=True)
    alert_action = models.TextField(blank=True, null=True)
    # user_name ??? null,
    # mac_addresses ??? null,
    # source ??? null,
    action_pretty = models.TextField(blank=True, null=True)
    # category ??? null,
    # project ??? null,
    # cloud_provider ??? null,
    # resource_sub_type ??? null,
    # resource_type ??? null,
    action_country = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    # event_type ??? null,
    # is_whitelisted ??? null,
    # image_name ??? null,
    # action_local_ip ??? null,
    # action_local_port ??? null,
    # action_external_hostname ??? null,
    # action_remote_ip ??? null,
    action_remote_port = ArrayField(
        models.IntegerField(blank=True, null=False), blank=True, null=True
    )
    # "matching_service_rule_id ??? null,
    starred = models.BooleanField(blank=True, null=True)
    external_id = models.TextField(blank=True, null=True)
    related_external_id = models.TextField(blank=True, null=True)
    alert_occurrence = models.IntegerField(blank=True, null=True)
    severity = models.TextField(blank=True, null=True)
    matching_status = models.TextField(blank=True, null=True)
    # end_match_attempt_ts ??? null,
    local_insert_ts = models.DateTimeField(blank=True, null=True)
    last_modified_ts = models.DateTimeField(blank=True, null=True)
    case_id = models.IntegerField(blank=True, null=True)
    # deduplicate_tokens ??? null,
    # filter_rule_id ??? null,
    # event_id ??? null,
    event_timestamp = ArrayField(
        models.DateTimeField(blank=True, null=False), blank=True, null=True
    )
    # action_local_ip_v6 ??? null,
    # action_remote_ip_v6 ??? null,
    alert_type = models.TextField(blank=True, null=True)
    resolution_status = models.TextField(blank=True, null=True)
    resolution_comment = models.TextField(blank=True, null=True)
    # dynamic_fields ??? null,
    tags = ArrayField(models.TextField(blank=True, null=False), blank=True, null=True)
    # malicious_urls ??? null,
    last_observed = models.DateTimeField(blank=True, null=True)
    country_codes = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    cloud_providers = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    ipv4_addresses = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    # ipv6_addresses ??? null,
    domain_names = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    service_ids = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    website_ids = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    asset_ids = ArrayField(
        models.TextField(blank=True, null=False), blank=True, null=True
    )
    certificate = models.JSONField(blank=True, null=True)
    # {
    #            issuerName": "IOS-Self-Signed-Certificate-782645061",
    #            subjectName": "IOS-Self-Signed-Certificate-782645061",
    #            validNotBefore": 1398850008000,
    #            validNotAfter": 1577836800000,
    #            serialNumber": "1"
    # },
    port_protocol = models.TextField(blank=True, null=True)
    # business_unit_hierarchies
    attack_surface_rule_name = models.TextField(blank=True, null=True)
    remediation_guidance = models.TextField(blank=True, null=True)
    asset_identifiers = models.JSONField(blank=True, null=True)

    business_units = models.ManyToManyField(XpanseBusinessUnits, related_name="alerts")
    services = models.ManyToManyField(XpanseServices, related_name="alerts")
    assets = models.ManyToManyField(XpanseAssets, related_name="alerts")

    class Meta:
        """Set XpanseAlerts model metadata."""

        managed = True
        db_table = "xpanse_alerts"


class Cves(models.Model):
    """Define Cves model."""

    cve_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    cve_name = models.TextField(unique=True, blank=True, null=True)
    published_date = models.DateTimeField(blank=True, null=True)
    last_modified_date = models.DateTimeField(blank=True, null=True)
    vuln_status = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    cvss_v2_source = models.TextField(blank=True, null=True)
    cvss_v2_type = models.TextField(blank=True, null=True)
    cvss_v2_version = models.TextField(blank=True, null=True)
    cvss_v2_vector_string = models.TextField(blank=True, null=True)
    cvss_v2_base_score = models.FloatField(blank=True, null=True)
    cvss_v2_base_severity = models.TextField(blank=True, null=True)
    cvss_v2_exploitability_score = models.FloatField(blank=True, null=True)
    cvss_v2_impact_score = models.FloatField(blank=True, null=True)
    cvss_v3_source = models.TextField(blank=True, null=True)
    cvss_v3_type = models.TextField(blank=True, null=True)
    cvss_v3_version = models.TextField(blank=True, null=True)
    cvss_v3_vector_string = models.TextField(blank=True, null=True)
    cvss_v3_base_score = models.FloatField(blank=True, null=True)
    cvss_v3_base_severity = models.TextField(blank=True, null=True)
    cvss_v3_exploitability_score = models.FloatField(blank=True, null=True)
    cvss_v3_impact_score = models.FloatField(blank=True, null=True)
    cvss_v4_source = models.TextField(blank=True, null=True)
    cvss_v4_type = models.TextField(blank=True, null=True)
    cvss_v4_version = models.TextField(blank=True, null=True)
    cvss_v4_vector_string = models.TextField(blank=True, null=True)
    cvss_v4_base_score = models.FloatField(blank=True, null=True)
    cvss_v4_base_severity = models.TextField(blank=True, null=True)
    cvss_v4_exploitability_score = models.FloatField(blank=True, null=True)
    cvss_v4_impact_score = models.FloatField(blank=True, null=True)
    weaknesses = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    reference_urls = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )
    cpe_list = ArrayField(
        models.TextField(blank=True, null=True), blank=True, null=True
    )

    class Meta:
        """Set Cves model metadata."""

        managed = False
        db_table = "cves"


class CpeVender(models.Model):
    """Define CpeVender model."""

    cpe_vender_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    vender_name = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        """Set CpeVender model metadata."""

        managed = False
        db_table = "cpe_vender"


class CpeProduct(models.Model):
    """Define CpeProduct model."""

    cpe_product_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    cpe_product_name = models.TextField(blank=True, null=True)
    version_number = models.TextField(blank=True, null=True)
    cpe_vender_uid = models.ForeignKey(
        "CpeVender", on_delete=models.CASCADE, db_column="cpe_vender_uid", default=None
    )

    # Create linking table for many to many relationship
    cves = models.ManyToManyField(Cves, related_name="products")

    class Meta:
        """Set CpeProduct model metadata."""

        managed = True
        db_table = "cpe_product"
        unique_together = (("cpe_product_name", "version_number"),)


"""
-- WARNING: It may differ from actual native database DDL
CREATE TABLE information_schema.was_findings (
    finding_uid uuid NOT NULL,
    finding_type varchar(10485760) NULL,
    webapp_id int4 NULL,
    was_org_id text NULL,
    owasp_category varchar(10485760) NULL,
    severity varchar(10485760) NULL,
    times_detected int4 NULL,
    base_score float8 NULL,
    temporal_score float8 NULL,
    fstatus varchar(10485760) NULL,
    last_detected date NULL,
    first_detected date NULL,
    is_remediated bool NULL,
    potential bool NULL,
    webapp_url text NULL,
    webapp_name text NULL,
    "name" text NULL,
    cvss_v3_attack_vector text NULL,
    cwe_list _int4 NULL,
    wasc_list jsonb NULL
);
"""


class WasFindings(models.Model):
    """Define WasFindings model."""

    finding_uid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    finding_type = models.TextField(blank=True, null=True)
    webapp_id = models.IntegerField(blank=True, null=True)
    was_org_id = models.TextField(blank=True, null=True)
    owasp_category = models.TextField(blank=True, null=True)
    severity = models.TextField(blank=True, null=True)
    times_detected = models.IntegerField(blank=True, null=True)
    base_score = models.FloatField(blank=True, null=True)
    temporal_score = models.FloatField(blank=True, null=True)
    fstatus = models.TextField(blank=True, null=True)
    last_detected = models.DateField(blank=True, null=True)
    first_detected = models.DateField(blank=True, null=True)
    is_remediated = models.BooleanField(blank=True, null=True)
    potential = models.BooleanField(blank=True, null=True)
    webapp_url = models.TextField(blank=True, null=True)
    webapp_name = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    cvss_v3_attack_vector = models.TextField(blank=True, null=True)
    cwe_list = ArrayField(
        models.IntegerField(blank=True, null=True), blank=True, null=True
    )
    wasc_list = models.JSONField(blank=True, null=True)
    last_tested = models.DateField(blank=True, null=True)
    fixed_date = models.DateField(blank=True, null=True)
    is_ignored = models.BooleanField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    qid = models.IntegerField(blank=True, null=True)
    response = models.TextField(blank=True, null=True)

    class Meta:
        """Set WasFindings model metadata."""

        managed = False
        db_table = "was_findings"


class WasReport(models.Model):
    """Define WasReport model."""

    id = models.AutoField(primary_key=True)
    org_name = models.TextField(blank=True, null=True)
    date_pulled = models.DateTimeField(blank=True, null=True)
    last_scan_date = models.DateTimeField(blank=True, null=True)
    security_risk = models.TextField(blank=True, null=True)
    total_info = models.IntegerField(blank=True, null=True)
    num_apps = models.IntegerField(blank=True, null=True)
    risk_color = models.TextField(blank=True, null=True)
    sensitive_count = models.IntegerField(blank=True, null=True)
    sensitive_color = models.TextField(blank=True, null=True)
    max_days_open_urgent = models.IntegerField(blank=True, null=True)
    max_days_open_critical = models.IntegerField(blank=True, null=True)
    urgent_color = models.TextField(blank=True, null=True)
    critical_color = models.TextField(blank=True, null=True)
    org_was_acronym = models.TextField(blank=True, null=True)
    name_len = models.TextField(blank=True, null=True)
    vuln_csv_dict = models.JSONField(blank=True, null=True, default=dict)
    ssn_cc_dict = models.JSONField(blank=True, null=True, default=dict)
    app_overview_csv_dict = models.JSONField(blank=True, null=True, default=dict)
    details_csv = models.JSONField(blank=True, null=True, default=list)
    info_csv = models.JSONField(blank=True, null=True, default=list)
    links_crawled = models.JSONField(blank=True, null=True, default=list)
    links_rejected = models.JSONField(blank=True, null=True, default=list)
    emails_found = models.JSONField(blank=True, null=True, default=list)
    owasp_count_dict = models.JSONField(blank=True, null=True, default=dict)
    group_count_dict = models.JSONField(blank=True, null=True, default=dict)
    fixed = models.IntegerField(blank=True, null=True)
    total = models.IntegerField(blank=True, null=True)
    vulns_monthly_dict = models.JSONField(blank=True, null=True, default=dict)
    path_disc = models.IntegerField(blank=True, null=True)
    info_disc = models.IntegerField(blank=True, null=True)
    cross_site = models.IntegerField(blank=True, null=True)
    burp = models.IntegerField(blank=True, null=True)
    sql_inj = models.IntegerField(blank=True, null=True)
    bugcrowd = models.IntegerField(blank=True, null=True)
    reopened = models.IntegerField(blank=True, null=True)
    reopened_color = models.TextField(blank=True, null=True)
    new_vulns = models.IntegerField(blank=True, null=True)
    new_vulns_color = models.TextField(blank=True, null=True)
    tot_vulns = models.IntegerField(blank=True, null=True)
    tot_vulns_color = models.TextField(blank=True, null=True)
    lev1 = models.IntegerField(blank=True, null=True)
    lev2 = models.IntegerField(blank=True, null=True)
    lev3 = models.IntegerField(blank=True, null=True)
    lev4 = models.IntegerField(blank=True, null=True)
    lev5 = models.IntegerField(blank=True, null=True)
    severities = ArrayField(models.IntegerField(), blank=True, null=True, default=list)
    ages = ArrayField(models.IntegerField(), blank=True, null=True, default=list)
    pdf_obj = models.BinaryField(blank=True, null=True)

    class Meta:
        """Set WasReport model metadata."""

        managed = False
        db_table = "was_report"
        unique_together = (("last_scan_date", "org_was_acronym"),)

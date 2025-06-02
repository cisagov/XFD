"""Tasks for saving the sixgill scan data into mini data lake."""

# Standard Python Libraries
from datetime import datetime
import logging

# Third-Party Libraries
from django.utils import timezone
from xfd_mini_dl.models import (
    CredentialBreaches,
    CredentialExposures,
    DataSource,
    Mentions,
    Organization,
    SixgillAlerts,
    SubDomains,
    TopCves,
)

LOGGER = logging.getLogger(__name__)


def insert_sixgill_alerts(df, org: Organization, source_obj: DataSource):
    """Insert Sixgill alerts into the database using get_or_create to avoid duplicates."""
    for record in df.to_dict("records"):
        SixgillAlerts.objects.get_or_create(
            sixgill_id=record.get("sixgill_id"),
            defaults={
                "alert_name": record.get("alert_name"),
                "content": record.get("content")[:2000],
                "date": record.get("date"),
                "read": record.get("read"),
                "severity": record.get("severity"),
                "site": record.get("site"),
                "threat_level": record.get("threat_level"),
                "threats": record.get("threats"),
                "title": record.get("title"),
                "user_id": record.get("user_id"),
                "category": record.get("category"),
                "lang": record.get("lang"),
                "organization": org,
                "data_source": source_obj,
                "content_snip": record.get("content_snip"),
                "asset_mentioned": record.get("asset_mentioned"),
                "asset_type": record.get("asset_type"),
            },
        )


def insert_sixgill_mentions(df, org: Organization, source_obj: DataSource):
    """Insert mention records from Cybersixgill into the database."""
    for record in df.to_dict("records"):
        Mentions.objects.get_or_create(
            sixgill_mention_id=record.get("sixgill_mention_id"),
            defaults={
                "category": record.get("category"),
                "collection_date": record.get("collection_date"),
                "content": record.get("content"),
                "creator": record.get("creator"),
                "date": record.get("date"),
                "post_id": record.get("post_id"),
                "lang": record.get("lang"),
                "rep_grade": record.get("rep_grade"),
                "site": record.get("site"),
                "site_grade": record.get("site_grade"),
                "title": record.get("title"),
                "type": record.get("type"),
                "url": record.get("url"),
                "comments_count": record.get("comments_count"),
                "sub_category": record.get("sub_category", "NaN"),
                "tags": record.get("tags"),
                "organization_uid": org,
                "data_source": source_obj,
                "title_translated": record.get("title_translated"),
                "content_translated": record.get("content_translated"),
                "detected_lang": record.get("detected_lang"),
            },
        )


def insert_sixgill_breaches(df, source_obj: DataSource):
    """Insert credential breach summaries into the database."""
    for record in df.to_dict("records"):
        CredentialBreaches.objects.get_or_create(
            breach_name=record.get("breach_name"),
            defaults={
                "exposed_cred_count": record.get("exposed_cred_count"),
                "breach_date": record.get("breach_date"),
                "added_date": record.get("added_date"),
                "modified_date": record.get("modified_date"),
                "password_included": record.get("password_included"),
                "data_source": source_obj,
            },
        )


def insert_sixgill_credentials(df, breach_lookup, org, root, source_obj):
    """Insert individual exposed credentials and subdomains into the database."""
    root_obj, _ = SubDomains.objects.get_or_create(
        organization=org,
        sub_domain=root,
        defaults={
            "is_root_domain": True,
            "data_source": source_obj,
            "subdomain_source": "Sixgill",
            "first_seen": datetime.now(),
            "last_seen": datetime.now(),
            "from_root_domain": root,
            "identified": True,
            "current": True,
        },
    )

    for record in df.to_dict("records"):
        # Get or create the subdomain object for the exposed credential
        sub, _ = SubDomains.objects.get_or_create(
            organization=org,
            sub_domain=record.get("sub_domain"),
            defaults={
                "root_domain": root_obj,
                "is_root_domain": False,
                "data_source": source_obj,
                "subdomain_source": "Sixgill",
                "first_seen": datetime.now(),
                "last_seen": datetime.now(),
                "from_root_domain": root,
                "identified": True,
                "current": True,
            },
        )
        # Insert credential exposure with link to breach and subdomain
        CredentialExposures.objects.get_or_create(
            email=record.get("email"),
            breach_name=record.get("breach_name"),
            organization=org,
            defaults={
                "root_domain": record.get("root_domain"),
                "sub_domain_string": record.get("sub_domain"),
                "sub_domain": sub,
                "credential_breach": breach_lookup.get(record.get("breach_name")),
                "modified_date": record.get("modified_date"),
                "created_at": timezone.now(),
                "data_source": source_obj,
                "password": record.get("password"),
                "hash_type": record.get("hash_type"),
                "intelx_system_id": record.get("intelx_system_id", ""),
            },
        )


def insert_sixgill_topCVEs(df, source_obj: DataSource):
    """Insert top CVE data into the database, avoiding duplicates by CVE ID and date."""
    for record in df.to_dict("records"):
        TopCves.objects.get_or_create(
            cve_id=record.get("cve_id"),
            date=record.get("date"),
            defaults={
                "summary": record.get("summary"),
                "dynamic_rating": record.get("dynamic_rating"),
                "nvd_base_score": record.get("nvd_base_score"),
                "data_source": source_obj,
            },
        )

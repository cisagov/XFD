"""Api methods for syncing Pshtt data."""
# Standard Python Libraries
import hashlib
import json
import logging
import os

# Third-Party Libraries
from django.utils import timezone
from fastapi import HTTPException, Request
from xfd_api.utils.scan_utils.alerting import IngestionError, SyncError
from xfd_mini_dl.models import DataSource, Organization, PshttResults, SubDomains

from ..auth import is_global_view_admin

SALT = os.getenv("CHECKSUM_SALT", "default_salt")
IS_LOCAL = os.getenv("IS_LOCAL") == "1"
DB = "mini_data_lake_secondary" if IS_LOCAL else "mini_data_lake"
LOGGER = logging.getLogger(__name__)


async def pshtt_sync_post(sync_body, request: Request, current_user):
    """Ingest and validate Psthtt data."""
    try:
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")
        headers = request.headers
        request_checksum = headers.get("x-checksum")
        calculated_checksum = hashlib.sha256(
            (SALT + json.dumps(sync_body.data)).encode()
        ).hexdigest()
        if not request_checksum or not sync_body.data:
            raise HTTPException(status_code=500, detail="No checksum error")
        if request_checksum != calculated_checksum:
            raise HTTPException(status_code=500, detail="Checksum doesn't match error.")
        try:
            process_data(sync_body.data)
        except IngestionError as e:
            raise HTTPException(status_code=500, detail=f"IngestionError: {str(e)}")

    except Exception as e:
        raise SyncError("PshttSync Endpoint", str(e), "Error syncing Pshtt data")
    return {"status": "success"}


def process_data(data):
    """Persist Pshtt results to the databxase."""
    # Loop over list
    # For each item, collect sub_domain and organization
    for pshtt_record in data:
        sub_domain = pshtt_record.get("sub_domain")
        organization = pshtt_record.get("organization")
        dns_record = sub_domain.get("dns_record", None)
        root_domain = sub_domain.get("root_domain", None)
        sub_domain_data_source = (
            sub_domain.get("data_source", None) if sub_domain else None
        )
        data_source = pshtt_record.get("data_source", None)
        # Fetched records
        sub_domain_ds_record, pshtt_result_ds_record = get_or_create_data_sources(
            sub_domain_data_source, data_source
        )
        root_domain_record = None
        org_record = None
        sub_domain_record = None
        # To-Do - Handle DNS records
        # dns_record_record = None
        try:
            org_record = Organization.objects.using(DB).get(
                acronym=organization.get("acronym")
            )
        except Organization.DoesNotExist:
            LOGGER("Organization does not exist for record")

        if root_domain:
            try:
                root_domain_record = SubDomains.objects.using(DB).get(
                    sub_domain=root_domain.get("sub_domain"), organization=org_record
                )
            except SubDomains.DoesNotExist:
                pass
        try:
            sub_domain_record, _ = SubDomains.objects.using(DB).get_or_create(
                sub_domain=sub_domain.get("sub_domain"),
                organization=org_record,
                defaults={
                    "data_source": sub_domain_ds_record,
                    "root_domain": root_domain_record,
                    "is_root_domain": sub_domain.get("is_root_domain"),
                    "dns_record": dns_record,
                    "status": sub_domain.get("status", None),
                    "first_seen": sub_domain.get("first_seen", None)
                    if sub_domain.get("first_seen")
                    else None,
                    "last_seen": sub_domain.get("last_seen", None)
                    if sub_domain.get("last_seen")
                    else None,
                    "created_at": sub_domain.get("created_at", None)
                    if sub_domain.get("created_at")
                    else timezone.now(),
                    "updated_at": sub_domain.get("updated_at", None)
                    if sub_domain.get("updated_at")
                    else timezone.now(),
                    "current": sub_domain.get("current_scan", None)
                    if sub_domain.get("current_scan")
                    else None,
                    "identified": sub_domain.get("identified", False),
                    "ip_address": sub_domain.get("ip_address", None)
                    if sub_domain.get("ip_address")
                    else None,
                    "synced_at": sub_domain.get("synced_at", None)
                    if sub_domain.get("synced_at")
                    else timezone.now(),
                    "from_root_domain": sub_domain.get("from_root_domain", False),
                    "enumerate_subs": sub_domain.get("enumerate_subdomains", False),
                    "subdomain_source": sub_domain.get("subdomain_source", None),
                    "reverse_name": sub_domain.get("reverse_name", ""),
                    "screenshot": sub_domain.get("screenshot", None)
                    if sub_domain.get("screenshot")
                    else None,
                    "country": sub_domain.get("country", None)
                    if sub_domain.get("country")
                    else None,
                    "asn": sub_domain.get("asn", None)
                    if sub_domain.get("asn")
                    else None,
                    "cloud_hosted": sub_domain.get("cloud_hosted", False),
                    "ssl": sub_domain.get("ssl", None)
                    if sub_domain.get("ssl")
                    else None,
                    "censys_certificates_results": sub_domain.get(
                        "censys_certificates_results", None
                    )
                    if sub_domain.get("censys_certificates_results")
                    else "{}",
                    "trustymail_results": sub_domain.get("trustymail_results", None)
                    if sub_domain.get("trustymail_results")
                    else "{}",
                },
            )
        except SubDomains.DoesNotExist:
            LOGGER.error("SubDomain does not exist for record", exc_info=True)
        try:
            create_or_update_pshtt_result(
                pshtt_record, pshtt_result_ds_record, org_record, sub_domain_record
            )
        except Exception as e:
            LOGGER.error("Error occurred while processing Pshtt record: %s", e)
            raise IngestionError


def create_or_update_pshtt_result(pshtt_dict, data_source, organization, sub_domain):
    """Create or update a Pshtt result record."""
    try:
        pshtt_result_record, created = PshttResults.objects.using(DB).update_or_create(
            sub_domain=sub_domain,
            organization=organization,
            defaults={
                "data_source": data_source,
                "date_scanned": timezone.now(),
                "base_domain": pshtt_dict.get("Base Domain"),
                "base_domain_hsts_preloaded": pshtt_dict.get(
                    "Base Domain HSTS Preloaded"
                ),
                "canonical_url": pshtt_dict.get("Canonical URL"),
                "defaults_to_https": pshtt_dict.get("Defaults to HTTPS"),
                "domain": pshtt_dict.get("Domain"),
                "domain_enforces_https": pshtt_dict.get("Domain Enforces HTTPS"),
                "domain_supports_https": pshtt_dict.get("Domain Supports HTTPS"),
                "domain_uses_strong_hsts": pshtt_dict.get("Domain Uses Strong HSTS"),
                "downgrades_https": pshtt_dict.get("Downgrades HTTPS"),
                "hsts": pshtt_dict.get("HSTS"),
                "hsts_entire_domain": pshtt_dict.get("HSTS Entire Domain"),
                "hsts_header": pshtt_dict.get("HSTS Header"),
                "hsts_max_age": pshtt_dict.get("HSTS Max Age"),
                "hsts_preload_pending": pshtt_dict.get("HSTS Preload Pending"),
                "hsts_preload_ready": pshtt_dict.get("HSTS Preload Ready"),
                "hsts_preloaded": pshtt_dict.get("HSTS Preloaded"),
                "https_bad_chain": pshtt_dict.get("HTTPS Bad Chain"),
                "https_bad_hostname": pshtt_dict.get("HTTPS Bad Hostname"),
                "https_cert_chain_length": pshtt_dict.get("HTTPS Cert Chain Length"),
                "https_client_auth_required": pshtt_dict.get(
                    "HTTPS Client Auth Required"
                ),
                "https_custom_truststore_trusted": pshtt_dict.get(
                    "HTTPS Custom Truststore Trusted"
                ),
                "https_expired_cert": pshtt_dict.get("HTTPS Expired Cert"),
                "https_full_connection": pshtt_dict.get("HTTPS Full Connection"),
                "https_live": pshtt_dict.get("Live"),
                "https_probably_missing_intermediate_cert": pshtt_dict.get(
                    "HTTPS Probably Missing Intermediate Cert"
                ),
                "https_publicly_trusted": pshtt_dict.get("HTTPS Publicly Trusted"),
                "https_self_signed_cert": pshtt_dict.get("HTTPS Self Signed Cert"),
                "ip": pshtt_dict.get("IP"),
                "live": pshtt_dict.get("Live"),
                "redirect": pshtt_dict.get("Redirect"),
                "redirect_to": pshtt_dict.get("Redirect To"),
                "strictly_forces_https": pshtt_dict.get("Strictly Forces HTTPS"),
                "server_header": pshtt_dict.get("Server Header"),
                "server_version": pshtt_dict.get("Server Version"),
                "notes": pshtt_dict.get("Notes", ""),
                # endpoint => Https
                "ep_http_headers": pshtt_dict.get("endpoints", {})
                .get("http", {})
                .get("headers"),
                "ep_http_server_header": pshtt_dict.get("endpoints", {})
                .get("http", {})
                .get("server_header"),
                "ep_http_server_version": pshtt_dict.get("endpoints", {})
                .get("http", {})
                .get("server_version"),
                "ep_https_headers": pshtt_dict.get("endpoints", {})
                .get("https", {})
                .get("headers"),
                "ep_https_hsts_header": pshtt_dict.get("endpoints", {})
                .get("https", {})
                .get("hsts_header"),
                "ep_https_server_header": pshtt_dict.get("endpoints", {})
                .get("https", {})
                .get("server_header"),
                "ep_https_server_version": pshtt_dict.get("endpoints", {})
                .get("https", {})
                .get("server_version"),
                "ep_httpswww_headers": pshtt_dict.get("endpoints", {})
                .get("httpswww", {})
                .get("headers"),
                "ep_httpswww_hsts_header": pshtt_dict.get("endpoints", {})
                .get("httpswww", {})
                .get("hsts_header"),
                "ep_httpswww_server_header": pshtt_dict.get("endpoints", {})
                .get("httpswww", {})
                .get("server_header"),
                "ep_httpswww_server_version": pshtt_dict.get("endpoints", {})
                .get("httpswww", {})
                .get("server_version"),
                "ep_httpwww_headers": pshtt_dict.get("endpoints", {})
                .get("httpwww", {})
                .get("headers"),
                "ep_httpwww_server_header": pshtt_dict.get("endpoints", {})
                .get("httpwww", {})
                .get("server_header"),
                "ep_httpwww_server_version": pshtt_dict.get("endpoints", {})
                .get("httpwww", {})
                .get("server_version"),
            },
        )
    except Exception as e:
        LOGGER.error("Error creating or updating Pshtt result: %s", e)
        raise e


def get_or_create_data_sources(sub_domain_ds, pshtt_result_ds):
    """Get or create data sources for sub_domain and pshtt_result."""
    sub_domain_ds_record = None
    pshtt_result_ds_record = None
    try:
        sub_domain_ds_record, _ = DataSource.objects.using(DB).get_or_create(
            name=sub_domain_ds.get("name"),
            defaults={
                "description": sub_domain_ds.get("description", ""),
                "last_run": sub_domain_ds.get("last_run", None)
                if sub_domain_ds.get("last_run")
                else timezone.now(),
            },
        )
    except Exception as e:
        LOGGER.error("Error getting or creating sub_domain data source: %s", e)
    try:
        pshtt_result_ds_record, _ = DataSource.objects.using(DB).get_or_create(
            name=pshtt_result_ds.get("name"),
            defaults={
                "description": pshtt_result_ds.get("description", ""),
                "last_run": pshtt_result_ds.get("last_run", None)
                if pshtt_result_ds.get("last_run")
                else timezone.now(),
            },
        )
    except Exception as e:
        LOGGER.error("Error getting or creating pshtt result data source: %s", e)
    return sub_domain_ds_record, pshtt_result_ds_record

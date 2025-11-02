"""Xpanse Sync API Methods."""
# Standard Python Libraries
import json
import logging
import os

DB_NAME = (
    "mini_data_lake_secondary" if os.getenv("IS_LOCAL") == "1" else "mini_data_lake"
)

# Third-Party Libraries
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from fastapi import HTTPException, Request
from xfd_api.auth import is_global_view_admin
from xfd_mini_dl.models import (
    DataSource,
    Organization,
    SubDomains,
    XpanseAlerts,
    XpanseBusinessUnits,
    XpanseCveServiceMdl,
    XpanseCvesMdl,
    XpanseServicesMdl,
)

from ..utils.csv_utils import create_checksum

LOGGER = logging.getLogger(__name__)


def create_xpanse_bu(bu_dict, data_source):
    """Create Xpanse Business Unit and related records."""
    bu, created = None, False
    alerts = bu_dict.get("alerts", [])
    org_record = None
    try:
        org_record = Organization.objects.using(DB_NAME).get(
            acronym=bu_dict["cyhy_db_name"]
        )
    except Exception as e:
        LOGGER.info(
            "Error fetching Organization: %s for business unit %s",
            bu_dict["cyhy_db_name"],
            e,
        )
    try:
        bu, created = XpanseBusinessUnits.objects.using(DB_NAME).update_or_create(
            xpanse_business_unit_uid=bu_dict["xpanse_business_unit_uid"],
            defaults={
                "entity_name": bu_dict["entity_name"],
                "cyhy_db_name": org_record,
                "state": bu_dict["state"],
                "county": bu_dict["county"],
                "city": bu_dict["city"],
                "sector": bu_dict["sector"],
                "entity_type": bu_dict["entity_type"],
                "region": bu_dict["region"],
                "rating": bu_dict["rating"],
            },
        )
        LOGGER.info("Business Unit %s created: %s", bu_dict["entity_name"], created)
        for alert in alerts:
            create_xpanse_alert(alert, bu, data_source, org_record)
    except Exception as e:
        LOGGER.info("Error creating/updating business unit: %s", e)
    return bu, created


def create_sub_domain(sub_domain_dict, data_source, org_record):
    """Create Sub Domain."""
    try:
        sub_domain, created = SubDomains.objects.using(DB_NAME).update_or_create(
            sub_domain=sub_domain_dict["sub_domain"],
            organization=org_record,
            defaults={
                "sub_domain": sub_domain_dict["sub_domain"],
                "root_domain": sub_domain_dict["root_domain"],
                "is_root_domain": sub_domain_dict["is_root_domain"],
                "data_source": data_source,
                "dns_record": sub_domain_dict["dns_record"],
                "status": sub_domain_dict["status"],
                "current": sub_domain_dict["current"],
                "identified": sub_domain_dict["identified"],
                "ip_address": sub_domain_dict["ip_address"],
                "synced_at": timezone.now(),
                "from_root_domain": sub_domain_dict["from_root_domain"],
                "enumerate_subs": sub_domain_dict["enumerate_subs"],
                "subdomain_source": sub_domain_dict["subdomain_source"],
                "ip_only": sub_domain_dict["ip_only"],
                "reverse_name": sub_domain_dict["reverse_name"],
                "screenshot": sub_domain_dict["screenshot"],
                "country": sub_domain_dict["country"],
                "asn": sub_domain_dict["asn"],
                "cloud_hosted": sub_domain_dict["cloud_hosted"],
                "ssl": sub_domain_dict["ssl"],
                "censys_certificates_results": sub_domain_dict[
                    "censys_certificates_results"
                ],
                "trustymail_results": sub_domain_dict["trustymail_results"],
                "organization": org_record,
            },
        )
        LOGGER.info("Sub Domain %s created: %s", sub_domain_dict["sub_domain"], created)
        return sub_domain
    except Exception as e:
        LOGGER.info("Error creating/updating sub_domain: %s", e)
        return None


def create_xpanse_service(service_dict, data_source, org_record):
    """Create Xpanse Service and related records."""
    sub_domains = service_dict.get("sub_domains", [])
    cves = service_dict.get("cves", [])
    xpanse_service = None
    try:
        xpanse_service, created = XpanseServicesMdl.objects.using(
            DB_NAME
        ).update_or_create(
            xpanse_service_uid=service_dict["xpanse_service_uid"],
            defaults={
                "service_id": service_dict["service_id"],
                "service_name": service_dict["service_name"],
                "service_type": service_dict["service_type"],
                "ip_address": service_dict["ip_address"],
                "domain": service_dict["domain"],
                "externally_detected_providers": service_dict[
                    "externally_detected_providers"
                ],
                "is_active": service_dict["is_active"],
                "first_observed": service_dict["first_observed"],
                "last_observed": service_dict["last_observed"],
                "port": service_dict["port"],
                "protocol": service_dict["protocol"],
                "active_classifications": service_dict["active_classifications"],
                "inactive_classifications": service_dict["inactive_classifications"],
                "discovery_type": service_dict["discovery_type"],
                "externally_inferred_vulnerability_score": service_dict[
                    "externally_inferred_vulnerability_score"
                ],
                "externally_inferred_cves": service_dict["externally_inferred_cves"],
                "service_key": service_dict["service_key"],
                "service_key_type": service_dict["service_key_type"],
            },
        )
        LOGGER.info("Service %s created: %s", service_dict["service_id"], created)
    except Exception as e:
        LOGGER.warning("Error creating/updating service: %s", e)
    for sub_domain in sub_domains:
        try:
            create_sub_domain(sub_domain, data_source, org_record)
            LOGGER.info("Sub Domain %s created: %s", sub_domain["sub_domain"], created)
        except Exception as e:
            LOGGER.warning("Error creating or linking sub domain to service: %s", e)
    for cve in cves:
        try:
            cve_record, created = XpanseCvesMdl.objects.using(DB_NAME).update_or_create(
                cve_id=cve["cve_id"],
                defaults={
                    "cvss_score_v2": cve["cvss_score_v2"],
                    "cvss_score_v3": cve["cvss_score_v3"],
                    "cve_severity_v2": cve["cve_severity_v2"],
                    "cve_severity_v3": cve["cve_severity_v3"],
                },
            )
            if created:
                LOGGER.info("CVE %s created:", cve["cve_id"])
            else:
                LOGGER.info("CVE %s updated", cve["cve_id"])
            try:
                # Create the CVE Service link
                cve_service_link_record, created = XpanseCveServiceMdl.objects.using(
                    DB_NAME
                ).update_or_create(
                    xpanse_inferred_cve=cve_record,
                    xpanse_service=xpanse_service,
                    defaults={
                        "product": cve["product"],
                        "confidence": cve["confidence"],
                        "vendor": cve["vendor"],
                        "version_number": cve["version_number"],
                        "activity_status": cve["activity_status"],
                        "first_observed": cve["first_observed"],
                        "last_observed": cve["last_observed"],
                    },
                )
                if created:
                    LOGGER.info("CVE Service link %s created", cve_service_link_record)
                else:
                    LOGGER.info("CVE Service link %s updated", cve_service_link_record)
            except Exception as e:
                LOGGER.warning("Error creating CVE Service link: %s", e)

            LOGGER.info(
                "Linked CVE %s to Service %s", cve["cve"], service_dict["service_id"]
            )
        except Exception as e:
            LOGGER.warning("Error linking CVE to service: %s", e)
    return xpanse_service


def create_xpanse_alert(alert_dict, bu_record, data_source, org_record):
    """Create Xpanse Alert and related records."""
    linkes_services = []
    alert_services = alert_dict.get("services", [])
    for service in alert_services:
        service_record = create_xpanse_service(service, data_source, org_record)
        if service_record:
            linkes_services.append(service_record)
    try:
        LOGGER.info("Creating/updating alert: %s", alert_dict["alert_id"])
        xpanse_alert, created = XpanseAlerts.objects.using(DB_NAME).update_or_create(
            xpanse_alert_uid=alert_dict["xpanse_alert_uid"],
            defaults={
                "time_pulled_from_xpanse": parse_datetime(
                    alert_dict["time_pulled_from_xpanse"]
                ),
                "alert_id": alert_dict["alert_id"],
                "detection_timestamp": parse_datetime(
                    alert_dict["detection_timestamp"]
                ),
                "alert_name": alert_dict["alert_name"],
                "description": alert_dict["description"],
                "host_name": alert_dict["host_name"],
                "alert_action": alert_dict["alert_action"],
                "action_pretty": alert_dict["action_pretty"],
                "action_country": alert_dict["action_country"],
                "action_remote_port": alert_dict["action_remote_port"],
                "starred": alert_dict["starred"],
                "external_id": alert_dict["external_id"],
                "related_external_id": alert_dict["related_external_id"],
                "alert_occurrence": alert_dict["alert_occurrence"],
                "severity": alert_dict["severity"],
                "matching_status": alert_dict["matching_status"],
                "local_insert_ts": parse_datetime(alert_dict["local_insert_ts"]),
                "last_modified_ts": parse_datetime(alert_dict["last_modified_ts"]),
                "case_id": alert_dict["case_id"],
                "event_timestamp": [
                    parse_datetime(ts) for ts in alert_dict["event_timestamp"]
                ],
                "alert_type": alert_dict["alert_type"],
                "resolution_status": alert_dict["resolution_status"],
                "resolution_comment": alert_dict["resolution_comment"],
                "tags": alert_dict["tags"],
                "last_observed": parse_datetime(alert_dict["last_observed"]),
                "country_codes": alert_dict["country_codes"],
                "cloud_providers": alert_dict["cloud_providers"],
                "ipv4_addresses": alert_dict["ipv4_addresses"],
                "domain_names": alert_dict["domain_names"],
                "service_ids": alert_dict["service_ids"],
                "website_ids": alert_dict["website_ids"],
                "asset_ids": alert_dict["asset_ids"],
                "certificate": alert_dict["certificate"],
                "port_protocol": alert_dict["port_protocol"],
                "attack_surface_rule_name": alert_dict["attack_surface_rule_name"],
                "remediation_guidance": alert_dict["remediation_guidance"],
                "asset_identifiers": alert_dict["asset_identifiers"],
            },
        )
        LOGGER.info("Alert %s created: %s", alert_dict["alert_id"], created)
        try:
            xpanse_alert.business_units.add(bu_record)
            LOGGER.info(
                "Linked Business Unit %s to Alert %s",
                bu_record.entity_name,
                alert_dict["alert_id"],
            )
        except Exception as e:
            LOGGER.warning("Error linking business unit to alert: %s", e)
        for service in linkes_services:
            try:
                xpanse_alert.services.add(service)
                LOGGER.info(
                    "Linked Service %s to Alert %s",
                    service.service_id,
                    alert_dict["alert_id"],
                )
            except Exception as e:
                LOGGER.warning("Error linking service to alert: %s", e)
    except Exception as e:
        LOGGER.warning("Error creating/updating alert: %s", e)


async def xpanse_sync_post(sync_body, request: Request, current_user):
    """Ingest and persist Xpanse data to the data lake."""
    if not is_global_view_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")
    headers = request.headers
    request_checksum = headers.get("x-checksum", None)
    validation_checksum = create_checksum(sync_body.data)
    # Validate Data via X-Checksum header
    if request_checksum is None:
        LOGGER.info("Checksum header not provided")
        raise HTTPException(status_code=500, detail="Checksum header not provided")
    if not sync_body.data:
        LOGGER.info("No data provided in request body")
        raise HTTPException(status_code=500, detail="No data provided in request body")
    if request_checksum != validation_checksum:
        LOGGER.info("Checksum validation failed")
        raise HTTPException(
            status_code=500,
            detail="Checksum validation failed",
        )
    # Checksum validation passed, proceed with data ingestion
    xpanse_data_source, created = DataSource.objects.using(DB_NAME).get_or_create(
        name="Xpanse",
        defaults={
            "description": "Xpanse data source",
            "name": "Xpanse",
            "last_run": timezone.now(),
        },
    )
    if created:
        LOGGER.info("Xpanse DataSource did not exist and was created.")
    bus_created = []
    bus_updated = []

    # Data is Valid, process data
    business_units = json.loads(sync_body.data)
    LOGGER.info("Recieved Xpanse data: %d Business Units", len(business_units))
    for business_unit in business_units:
        bu, created = create_xpanse_bu(business_unit, xpanse_data_source)
        if created:
            bus_created.append(bu)
        else:
            bus_updated.append(bu)

    return {"status": "success"}

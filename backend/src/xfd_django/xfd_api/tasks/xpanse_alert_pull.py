"""XpanseAlertPull scan."""
# Standard Python Libraries
import datetime
import json
import logging
import os
import re
import time
from uuid import uuid4

# Third-Party Libraries
import django
import requests

# End Standalone Django Setup
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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
django.setup()

LOGGER = logging.getLogger(__name__)

api_key = os.getenv("XPANSE_API_KEY")
auth_id = os.getenv("XPANSE_AUTH_ID")
xpanse_url = "https://api-cisa-xpanse.crtx.gv.paloaltonetworks.com/public_api/"


def get_or_create_data_source(name):
    """Get or create a data source object."""
    try:
        data_source_obj = DataSource.objects.get(name=name)
        return data_source_obj
    except DataSource.DoesNotExist:
        data_source_obj = DataSource.objects.create(
            data_source_uid=uuid4(),
            name=name,
            description="Xpanse Data Source",
            last_run=datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc),
        )
        return data_source_obj


XPSANSE_DATA_SOURCE = get_or_create_data_source("Xpanse")


def parse_possible_datetime(val):
    """Parse a value into a datetime object."""
    if isinstance(val, str):
        try:
            # Replace space with 'T' in ISO-like strings
            val = val.replace(" ", "T")
            return datetime.datetime.fromisoformat(val)
        except ValueError:
            return None
    elif isinstance(val, (int, float)):
        try:
            # Assume it's a Unix timestamp in milliseconds
            return datetime.datetime.fromtimestamp(
                val / 1000.0, tz=datetime.timezone.utc
            )
        except (OSError, OverflowError):
            return None
    elif isinstance(val, datetime.datetime):
        return val
    return None


def to_datetime_list(millis_list):
    """Convert a list of milliseconds to a list of datetime objects."""
    if not millis_list or not isinstance(millis_list, list):
        return []
    return [
        datetime.datetime.fromtimestamp(millis / 1000.0, tz=datetime.timezone.utc)
        for millis in millis_list
        if isinstance(millis, (int, float))
    ]


def reverse_domain_name(domain):
    """Reverse a domain name."""
    return ".".join(reversed(domain.split(".")))


def pull_acronym_from_org_string(org_str: str):
    """Extract the acronym from an organization string."""
    match = re.search(r"\[(.*?)\]$", org_str)
    acronym = match.group(1) if match else None
    return acronym


def create_cves(cves):
    """Create CVEs for an alert."""
    cve_records = []
    for cve in cves:
        cve_dict = cve[0]
        cve_product_dict = cve[1]
        xpanse_cve = None
        try:
            xpanse_cve = XpanseCvesMdl.objects.get(cve_id=cve_dict["cve_id"])
        except XpanseCvesMdl.DoesNotExist:
            xpanse_cve, _ = XpanseCvesMdl.objects.update_or_create(
                cve_id=cve_dict["cve_id"],
                defaults={
                    "xpanse_cve_uid": uuid4(),
                    "cvss_score_v2": cve_dict["cvss_score_v2"],
                    "cve_severity_v2": cve_dict["cve_severity_v2"],
                    "cvss_score_v3": cve_dict["cvss_score_v3"],
                    "cve_severity_v3": cve_dict["cve_severity_v3"],
                },
            )
        full_cve_data = {
            "cve_source": cve_dict,
            "cve_product": cve_product_dict,
            "created_cve": xpanse_cve,
        }
        cve_records.append(full_cve_data)
    LOGGER.info("Created Xpanse CVEs: %d", len(cve_records))
    return cve_records


def create_service(service_dict, cves, org_record, alert_record):
    """Create a service for an alert."""
    xpanse_service = None
    try:
        xpanse_service = XpanseServicesMdl.objects.get(
            service_id=service_dict["service_id"]
        )
    except XpanseServicesMdl.DoesNotExist:
        xpanse_service, _ = XpanseServicesMdl.objects.update_or_create(
            service_id=service_dict["service_id"],
            defaults={
                "service_name": service_dict["service_name"],
                "service_type": service_dict["service_type"],
                "ip_address": service_dict["ip_address"],
                "domain": service_dict["domain"],
                "externally_detected_providers": service_dict[
                    "externally_detected_providers"
                ],
                "is_active": service_dict["is_active"],
                "first_observed": datetime.datetime.fromtimestamp(
                    service_dict["first_observed"] / 1000
                ),
                "last_observed": datetime.datetime.fromtimestamp(
                    service_dict["last_observed"] / 1000
                ),
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
    except Exception as e:
        LOGGER.error("Error saving service: %s", e)
    if xpanse_service is not None and len(cves) > 0:
        for cve in cves:
            try:
                xpanse_cve = cve["created_cve"]
                XpanseCveServiceMdl.objects.get(
                    xpanse_service=xpanse_service, xpanse_inferred_cve=xpanse_cve
                )
            except XpanseCveServiceMdl.DoesNotExist:
                XpanseCveServiceMdl.objects.update_or_create(
                    xpanse_service=xpanse_service,
                    xpanse_inferred_cve=xpanse_cve,
                    defaults={
                        "inferred_cve_match_type": cve["cve_product"][
                            "inferred_cve_match_type"
                        ],
                        "product": cve["cve_product"]["product"],
                        "confidence": cve["cve_product"]["confidence"],
                        "vendor": cve["cve_product"]["vendor"],
                        "version_number": cve["cve_product"]["version_number"],
                        "activity_status": cve["cve_product"]["activity_status"],
                        "first_observed": datetime.datetime.fromtimestamp(
                            cve["cve_product"]["first_observed"] / 1000
                        ),
                        "last_observed": datetime.datetime.fromtimestamp(
                            cve["cve_product"]["last_observed"] / 1000
                        ),
                    },
                )
    if xpanse_service is not None and len(service_dict["domain"]) > 0:
        created_domains = []
        for domain in service_dict["domain"]:
            sub_domain = create_sub_domain_for_service(domain, org_record)
            created_domains.append(sub_domain)
        # if created_domains:
        #     for domain in created_domains:
        #         xpanse_service.sub_domains.add(domain)
    LOGGER.info("Created Xpanse Service %s", xpanse_service.service_id)
    return xpanse_service


def create_sub_domain_for_service(sub_domain, ord_record):
    """Create a sub domain for a service."""
    # If we're creating it, we want enumerate subs to be false
    # If we're updating, do not update the enumerate subs
    domain_obj, created = SubDomains.objects.get_or_create(
        sub_domain=sub_domain,
        defaults={
            "data_source": XPSANSE_DATA_SOURCE,
            "organization": ord_record,
            "ip_only": False,
            "enumerate_subs": False,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "updated_at": datetime.datetime.now(datetime.timezone.utc),
            "reverse_name": reverse_domain_name(sub_domain),
            "censys_certificates_results": [],
            "trustymail_results": [],
        },
    )
    if not created:
        domain_obj.updated_at = datetime.datetime.now(datetime.timezone.utc)
        domain_obj.save()

    LOGGER.info("Created Sub Domain %s", sub_domain)
    return domain_obj


def insert_xpanse_alert(alert, org_record, business_unit):
    """Insert Xpanse alert into the database."""
    xpanse_alert = None
    try:
        xpanse_alert, _ = XpanseAlerts.objects.update_or_create(
            alert_id=alert["alert_id"],
            defaults={
                "xpanse_alert_uid": uuid4(),
                "time_pulled_from_xpanse": parse_possible_datetime(
                    alert["time_pulled_from_xpanse"]
                ),
                "detection_timestamp": parse_possible_datetime(
                    alert["detection_timestamp"]
                ),
                "alert_name": alert["alert_name"],
                "description": alert["description"],
                "host_name": alert["host_name"],
                "alert_action": alert["alert_action"],
                "action_pretty": alert["action_pretty"],
                "action_country": alert["action_country"],
                "action_remote_port": alert["action_remote_port"],
                "starred": alert["starred"],
                "external_id": alert["external_id"],
                "related_external_id": alert["related_external_id"],
                "alert_occurrence": alert["alert_occurrence"],
                "severity": alert["severity"],
                "matching_status": alert["matching_status"],
                "local_insert_ts": parse_possible_datetime(alert["local_insert_ts"]),
                "last_modified_ts": parse_possible_datetime(alert["last_modified_ts"]),
                "case_id": alert["case_id"],
                "event_timestamp": to_datetime_list(alert["event_timestamp"]),
                "alert_type": alert["alert_type"],
                "resolution_status": alert["resolution_status"],
                "resolution_comment": alert["resolution_comment"],
                "tags": alert["tags"],
                "last_observed": parse_possible_datetime(alert["last_observed"]),
                "country_codes": alert["country_codes"],
                "cloud_providers": alert["cloud_providers"],
                "ipv4_addresses": alert["ipv4_addresses"],
                "domain_names": alert["domain_names"],
                "service_ids": alert["service_ids"],
                "asset_ids": alert["asset_ids"],
                "certificate": alert["certificate"],
                "port_protocol": alert["port_protocol"],
                "attack_surface_rule_name": alert["attack_surface_rule_name"],
                "remediation_guidance": alert["remediation_guidance"],
                "asset_identifiers": alert["asset_identifiers"],
            },
        )
        xpanse_alert.business_units.add(business_unit)
        LOGGER.info("Created Xpanse Alert %s", xpanse_alert.alert_id)
    except Exception as e:
        LOGGER.error("Error saving alert: %s", e)
        return None

    linked_services = []
    linked_cves = []
    # linked_assets = []
    if alert["services"] is not None:
        # This is working, commenting out to work faster
        LOGGER.info("Creating Services for Xpanse Alert %s", xpanse_alert.alert_id)
        for service in alert["services"]:
            service_cves = service["cves"]
            if service_cves:
                linked_cves = create_cves(service_cves)
            xpanse_service = create_service(
                service, linked_cves, org_record, xpanse_alert
            )
            if xpanse_service is not None:
                linked_services.append(xpanse_service)
        LOGGER.info("Attempting to link alert to service")
        xpanse_alert.services.set(linked_services)
        LOGGER.info(
            "Created %d Services for Xpanse Alert %s",
            len(linked_services),
            xpanse_alert.alert_id,
        )
    return xpanse_alert


def pull_alerts_data(linked_org_list, business_units_list=[]):
    """Pull alerts data from the Xpanse API."""
    url = xpanse_url + "v2/alerts/get_alerts_multi_events"
    if len(business_units_list) == 0:
        business_units_list = list(map(lambda d: d.entity_name, linked_org_list))

    linking_dict = {}
    for org in linked_org_list:
        linking_dict[org.cyhy_db_name.acronym] = org

    for org in business_units_list:
        org_acronym = pull_acronym_from_org_string(org)
        mdl_org_record = Organization.objects.get(acronym=org_acronym)
        business_unit = linking_dict.get(org_acronym, None)
        request_data = {"use_page_token": True, "search_from": 0, "search_to": 5000}
        filters = []
        filters.append(
            {"field": "business_units_list", "operator": "in", "value": [org]}
        )
        if len(filters) > 0:
            request_data["filters"] = filters

        payload = json.dumps({"request_data": request_data})
        headers = {
            "x-xdr-auth-id": auth_id,
            "Authorization": api_key,
            "Content-Type": "application/json",
        }
        try:
            response = requests.request(
                "POST", url, headers=headers, data=payload, timeout=60
            )
            resp_dict = response.json()
            page_token = resp_dict["reply"]["next_page_token"]
            formatted_alerts = format_alerts(resp_dict["reply"]["alerts"])

            if isinstance(formatted_alerts, list):
                LOGGER.info("Found %d alerts", len(formatted_alerts))
                for alert in formatted_alerts:
                    insert_xpanse_alert(alert, mdl_org_record, business_unit)

            while page_token is not None:
                request_data = {"next_page_token": page_token}

                payload = json.dumps({"request_data": request_data})

                response = requests.request(
                    "POST", url, headers=headers, data=payload, timeout=60
                )
                resp_dict = response.json()

                page_token = resp_dict["reply"]["next_page_token"]

                formatted_alerts = format_alerts(resp_dict["reply"]["alerts"])
                for alert in formatted_alerts:
                    insert_xpanse_alert(alert, mdl_org_record, business_unit)

            LOGGER.info("Done Xpanse alert pull on %s", org)
        except Exception as e:
            LOGGER.error("Error querying assets for %s: %s.", org, e)


def format_alerts(alerts):
    """Format Xpanse alerts to match db tables."""
    alert_services_dict, service_ids = extract_service_ids(alerts)
    services = fetch_services_with_cves(service_ids)

    alert_list = []
    for alert in alerts:
        business_units_list = extract_business_units(alert)
        current_services = match_services(alert.get("service_ids", []), services)

        alert_dict = build_alert_dict(alert, business_units_list, current_services)
        alert_list.append(alert_dict)

    return alert_list


def extract_service_ids(alerts):
    """Extract service IDs."""
    alert_services_dict = {}
    service_ids = []
    for alert in alerts:
        try:
            service_ids += alert.get("service_ids", [])
            alert_services_dict[alert["alert_id"]] = alert.get("service_ids", [])
        except (KeyError, TypeError):
            continue
    return alert_services_dict, service_ids


def fetch_services_with_cves(service_ids):
    """Fetch services with CVEs from the Xpanse API."""
    services = []
    if not service_ids:
        return services

    max_n = 5000
    service_id_chunks = [
        service_ids[i : i + max_n] for i in range(0, len(service_ids), max_n)
    ]

    for chunk in service_id_chunks:
        service_response = retry_pull_service_data(chunk)
        if service_response is None:
            continue

        for service_obj in service_response:
            cves = extract_cves(service_obj)
            services.append(build_service(service_obj, cves))
    return services


def retry_pull_service_data(service_chunk, max_retries=3, retry_delay=5):
    """Fetch service data pull with retry."""
    for retry_count in range(max_retries):
        try:
            service_response = pull_service_data(service_chunk)
            if service_response is not None:
                return service_response
        except Exception as e:
            LOGGER.error("Error querying services: %s", e)
            if retry_count < max_retries - 1:
                LOGGER.info("Retrying...")
                time.sleep(retry_delay)
    return None


def extract_cves(service_obj):
    """Extrac CVE data from service records."""
    cves = []
    inferred_cves = service_obj["details"].get("inferredCvesObserved", None)
    if inferred_cves:
        for cve in inferred_cves:
            cves.append(
                (
                    {
                        "cve_id": cve["inferredCve"]["cveId"],
                        "cvss_score_v2": cve["inferredCve"].get("cvssScoreV2", None),
                        "cve_severity_v2": cve["inferredCve"].get(
                            "cveSeverityV2", None
                        ),
                        "cvss_score_v3": cve["inferredCve"].get("cvssScoreV3", None),
                        "cve_severity_v3": cve["inferredCve"].get(
                            "cveSeverityV3", None
                        ),
                    },
                    {
                        "inferred_cve_match_type": cve["inferredCve"][
                            "inferredCveMatchMetadata"
                        ].get("inferredCveMatchType", None),
                        "product": cve["inferredCve"]["inferredCveMatchMetadata"].get(
                            "product", None
                        ),
                        "confidence": cve["inferredCve"][
                            "inferredCveMatchMetadata"
                        ].get("confidence", None),
                        "vendor": cve["inferredCve"]["inferredCveMatchMetadata"].get(
                            "vendor", None
                        ),
                        "version_number": cve["inferredCve"][
                            "inferredCveMatchMetadata"
                        ].get("version", None),
                        "activity_status": cve.get("activityStatus", None),
                        "first_observed": cve.get("firstObserved", None),
                        "last_observed": cve.get("lastObserved", None),
                    },
                )
            )
    return cves


def build_service(service_obj, cves):
    """Build service object for processing."""
    return {
        "service_id": service_obj.get("service_id", None),
        "service_name": service_obj.get("service_name", None),
        "service_type": service_obj.get("service_type", None),
        "ip_address": service_obj.get("ip_address", None),
        "domain": service_obj.get("domain", None),
        "externally_detected_providers": service_obj.get(
            "externally_detected_providers", None
        ),
        "is_active": service_obj.get("is_active", None),
        "first_observed": service_obj.get("first_observed", None),
        "last_observed": service_obj.get("last_observed", None),
        "port": service_obj.get("port", None),
        "protocol": service_obj.get("protocol", None),
        "active_classifications": service_obj.get("active_classifications", None),
        "inactive_classifications": service_obj.get("inactive_classifications", None),
        "discovery_type": service_obj.get("discovery_type", None),
        "externally_inferred_vulnerability_score": service_obj.get(
            "externally_inferred_vulnerability_score", None
        ),
        "externally_inferred_cves": service_obj.get("externally_inferred_cves", None),
        "service_key": service_obj["details"].get("serviceKey", None),
        "service_key_type": service_obj["details"].get("serviceKeyType", None),
        "cves": cves,
    }


def extract_business_units(alert):
    """Extract and link Xpanse business units."""
    tags = alert.get("tags", None)
    if not tags:
        return []

    business_units = []
    try:
        for tag in tags:
            if tag.startswith("BU:"):
                business_units.append(tag[3:].strip())
    except Exception:
        return []
    return business_units


def match_services(service_ids, services):
    """Match services to service ID."""
    try:
        matched = []
        for service_id in service_ids:
            try:
                match = next(
                    (d for d in services if d.get("service_id") == service_id), None
                )
                if match:
                    matched.append(match)
            except (TypeError, AttributeError) as e:
                LOGGER.warning("Failed to process service ID '%s': %s", service_id, e)
        return matched
    except ValueError:
        return []


def build_alert_dict(alert, business_units_list, current_services):
    """Shape alert dictionary given bu's and services."""
    external_id = alert.get("external_id", None)
    related_external_id = "-".join(external_id.split("-")[:-1]) if external_id else None
    alert_occurrence = int(external_id.split("-")[-1]) / 2 if external_id else None

    return {
        "time_pulled_from_xpanse": datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        ),
        "alert_id": alert.get("alert_id", None),
        "detection_timestamp": alert.get("detection_timestamp", None),
        "alert_name": alert.get("name", None),
        "description": alert.get("description", None),
        "host_name": alert.get("host_name", None),
        "alert_action": alert.get("action", None),
        "action_pretty": alert.get("action_pretty", None),
        "action_country": alert.get("action_country", None),
        "action_remote_port": alert.get("action_remote_port", None),
        "starred": alert.get("starred", None),
        "external_id": external_id,
        "related_external_id": related_external_id,
        "alert_occurrence": alert_occurrence,
        "severity": alert.get("severity", None),
        "matching_status": alert.get("matching_status", None),
        "local_insert_ts": alert.get("local_insert_ts", None),
        "last_modified_ts": alert.get("last_modified_ts")
        or alert.get("local_insert_ts", None),
        "case_id": alert.get("case_id", None),
        "event_timestamp": alert.get("event_timestamp", None),
        "alert_type": alert.get("alert_type", None),
        "resolution_status": alert.get("resolution_status", None),
        "resolution_comment": alert.get("resolution_comment", None),
        "tags": alert.get("tags", None),
        "last_observed": alert.get("last_observed", None),
        "country_codes": alert.get("country_codes", None),
        "cloud_providers": alert.get("cloud_providers", None),
        "ipv4_addresses": alert.get("ipv4_addresses", None),
        "domain_names": alert.get("domain_names", None),
        "service_ids": alert.get("service_ids", None),
        "asset_ids": alert.get("asset_ids", None),
        "certificate": alert.get("certificate", None),
        "port_protocol": alert.get("port_protocol", None),
        "attack_surface_rule_name": alert.get("attack_surface_rule_name", None),
        "remediation_guidance": alert.get("remediation_guidance", None),
        "asset_identifiers": alert.get("asset_identifiers", None),
        "business_units": business_units_list,
        "services": current_services,
        "assets": [],
    }


def pull_service_data(service_id_list):
    """Pull service info from the Xpanse API using a service_id."""
    LOGGER.info("Pulling service data")
    url = xpanse_url + "v1/assets/get_external_service"
    request_data = {"service_id_list": service_id_list}

    payload = json.dumps({"request_data": request_data})

    headers = {
        "x-xdr-auth-id": auth_id,
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload, timeout=60)

    resp_dict = response.json()

    return resp_dict.get("reply", {}).get("details", None)


def pull_asset_data(xpanse_asset_id_list=[]):
    """Pull asset data from the Xpanse API."""
    LOGGER.info("Pulling asset data")
    assets = []

    url = xpanse_url + "v1/assets/get_asset_internet_exposure"
    request_data = {"asm_id_list": xpanse_asset_id_list}

    payload = json.dumps({"request_data": request_data})

    headers = {
        "x-xdr-auth-id": auth_id,
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload, timeout=60)

    resp_dict = response.json()

    for asset in resp_dict["reply"]["details"]:
        asset_dict = format_asset(asset)
        assets.append(asset_dict)

    return assets


def format_asset(asset):
    """Format Xpanse asset to match db tables."""
    asset_dict = {
        "asm_id": asset.get("asm_ids", None),
        "asset_name": asset.get("name", None),
        "asset_type": asset.get("type", None),
        "last_observed": asset.get("last_observed", None),
        "first_observed": asset.get("first_observed", None),
        "externally_detected_providers": asset.get(
            "externally_detected_providers", None
        ),
        "created": asset.get("created", None),
        "ips": asset.get("ips", None),
        "active_external_services_types": asset.get(
            "active_external_services_types", None
        ),
        "domain": asset.get("domain", None),
        "certificate_issuer": asset.get("certificate_issuer", None),
        "certificate_algorithm": asset.get("certificate_algorithm", None),
        "certificate_classifications": asset.get("certificate_classifications", None),
        "resolves": asset.get("resolves", None),
        "top_level_asset_mapper_domain": asset["details"].get(
            "topLevelAssetMapperDomain", None
        ),
        "domain_asset_type": asset["details"].get("domainAssetType", None),
        "is_paid_level_domain": asset["details"].get("isPaidLevelDomain", None),
        "domain_details": asset["details"].get("domainDetails", None),
        "dns_zone": asset.get("dnsZone", None),
        "latest_sampled_ip": asset.get("latestSampledIp", None),
        "recent_ips": asset.get("recentIps", None),
        "external_services": asset.get("external_services", None),
        "externally_inferred_vulnerability_score": asset.get(
            "externally_inferred_vulnerability_score", None
        ),
        "externally_inferred_cves": asset.get("externally_inferred_cves", None),
        "explainers": asset.get("explainers", None),
        "tags": asset.get("tags", None),
    }

    return asset_dict


def get_linked_business_units(acronym):
    """Get linked business units from the database."""
    try:
        org_records = Organization.objects.filter(acronym=acronym)
        return XpanseBusinessUnits.objects.filter(cyhy_db_name__in=org_records)
    except Exception as e:
        LOGGER.error("Error querying linked business units: %s", e)
        return None


def main(event):
    """Run Xpanse scans."""
    organizationId = event.get("organizationId", None)
    org_record = Organization.objects.get(id=organizationId)
    bu_record = XpanseBusinessUnits.objects.get(cyhy_db_name=org_record)
    orgs_list = [bu_record.entity_name]
    org_acronym = org_record.acronym
    linked_business_units = get_linked_business_units(org_acronym)
    pull_alerts_data(linked_business_units, orgs_list)
    return 1


def handler(event):
    """Xpanse Alert Pull scan handler."""
    try:
        is_dmz = os.getenv("IS_DMZ")
        is_local = os.getenv("IS_LOCAL")
        if str(is_dmz).lower() not in {"true", "1"} and not is_local:
            LOGGER.warning("Scan can only be run in the DMZ or locally. Exiting now.")
            return {
                "statusCode": 200,
                "body": "Xpanse Alerts sync cannot run outside the DMZ.",
            }
        main(event)
        return {
            "statusCode": 200,
            "body": "Xpanse Alerts sync completed successfully.",
        }
    except Exception as e:
        LOGGER.error("Error starting XpanseAlertPull %s", e)
        return {"statusCode": 500, "body": str(e)}


# if __name__ == "__main__":
#     try:
#         main("all")
#     except Exception as e:
#         LOGGER.error("Error", e)

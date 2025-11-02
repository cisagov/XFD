"""Updated Shodan Sync scan hitting new FastAPI endpoint."""
# Standard Python Libraries
import datetime
import hashlib
import json
import logging
import os
from urllib.parse import urljoin

# Third-Party Libraries
import django
from django.utils import timezone
import requests
from xfd_api.helpers.date_time_helpers import calculate_days_back
from xfd_mini_dl.models import DataSource, Ip, Organization, ShodanAssets, ShodanVulns

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Constants
LOGGER = logging.getLogger(__name__)
SALT = os.getenv("CHECKSUM_SALT", "default_salt")
HEADERS = {
    "X-API-KEY": os.getenv("DMZ_API_KEY"),
    "Content-Type": "application/json",
}
# Assume DMZ_SYNC_ENDPOINT is something like 'https://api.staging-cd.crossfeed.cyber.dhs.gov/sync'
base_url = os.getenv("DMZ_SYNC_ENDPOINT", "").rstrip("/")

# Replace the final segment `/sync` with `/dmz_sync/shodan_sync`
if base_url.endswith("/sync"):
    api_url = base_url.rsplit("/", 1)[0] + "/dmz_sync/shodan_sync"
else:
    api_url = urljoin(base_url + "/", "dmz_sync/shodan_sync")
API_URL = api_url


def handler(command_options):
    """Retrieve and save Shodan assets/vulns from commercial via sync."""
    try:
        organization_name = command_options.get("organizationName")
        organization_id = command_options.get("organizationId")
        if not organization_name or not organization_id:
            return {"statusCode": 400, "body": "Organization name or id not provided."}

        orgs_to_sync = Organization.objects.filter(id=organization_id)
        if not orgs_to_sync.exists():
            return {"statusCode": 500, "body": "Organization not found."}
        organization = orgs_to_sync.first()

        LOGGER.info("Running Shodan Sync on organization: %s", organization_name)

        shodan_datasource, _ = DataSource.objects.get_or_create(
            name="Shodan",
            defaults={
                "description": "Shodan is the world's first search engine for Internet-connected devices.",
                "last_run": timezone.now().date(),
            },
        )

        since_date = calculate_days_back(15)

        page = 1
        per_page = 200
        done = False

        while not done:
            payload = {
                "acronym": organization.acronym,
                "page": page,
                "page_size": per_page,
                "since_date": since_date,
            }

            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            response.raise_for_status()
            # Validate checksum by passing the response object
            is_valid = validate_response_checksum(response)

            if is_valid:
                LOGGER.info("Checksum is valid!")
            else:
                LOGGER.error("Checksum validation failed!")
                return {"statusCode": 500, "body": "Checksum validation failed!"}

            body = response.json()

            if body.get("status") != "ok":
                raise Exception("Shodan sync returned non-ok status: {}".format(body))

            result = body.get("payload", {})
            total_pages = result.get("total_pages", 1)
            current_page = result.get("current_page", 1)
            assets = result.get("data", {}).get("shodan_assets", [])
            vulns = result.get("data", {}).get("shodan_vulns", [])

            LOGGER.info(
                "Syncing page %s of %s: %s assets, %s vulns",
                current_page,
                total_pages,
                len(assets),
                len(vulns),
            )
            save_findings_to_db(assets, vulns, organization, shodan_datasource)

            if current_page >= total_pages:
                done = True
            else:
                page += 1

        return {"statusCode": 200, "body": "Shodan sync completed successfully."}

    except Exception as e:
        LOGGER.error(e)
        return {"statusCode": 500, "body": str(e)}


def save_findings_to_db(shodan_asset_array, shodan_vuln_array, org, data_source):
    """Save Shodan assets and vulns data to the mini datalake using Django ORM."""
    for asset in shodan_asset_array:
        create_default = {
            "ip": asset.get("ip_string"),
            "organization": org,
            "has_shodan_results": True,
            "current": True,
            "last_seen_timestamp": datetime.datetime.now(datetime.timezone.utc),
        }
        ip_hash = hashlib.sha256(create_default.get("ip").encode("utf-8")).hexdigest()
        create_default["ip_hash"] = ip_hash
        ip_object, created = Ip.objects.get_or_create(
            ip=create_default.get("ip"),
            organization=create_default.get("organization"),
            defaults=create_default,
        )
        try:
            ShodanAssets.objects.update_or_create(
                timestamp=asset.get("timestamp"),
                ip=ip_object,
                port=asset.get("port"),
                protocol=asset.get("protocol"),
                organization=org,
                defaults={
                    "ip_string": asset.get("ip_string"),
                    "organization_name": asset.get("organization_name"),
                    "product": asset.get("product"),
                    "server": asset.get("server"),
                    "tags": asset.get("tags"),
                    "domains": asset.get("domains"),
                    "hostnames": asset.get("hostnames"),
                    "isp": asset.get("isp"),
                    "asn": asset.get("asn"),
                    "country_code": asset.get("country_code"),
                    "location": asset.get("location"),
                    "data_source": data_source,
                },
            )
        except Exception as e:
            LOGGER.error("Error saving Shodan Asset: %s", e)

    for vuln in shodan_vuln_array:
        create_default = {
            "ip": vuln.get("ip_string"),
            "organization": org,
            "has_shodan_results": True,
            "current": True,
            "last_seen_timestamp": datetime.datetime.now(datetime.timezone.utc),
        }
        ip_hash = hashlib.sha256(create_default.get("ip").encode("utf-8")).hexdigest()
        create_default["ip_hash"] = ip_hash
        ip_object, created = Ip.objects.get_or_create(
            ip=create_default.get("ip"),
            organization=create_default.get("organization"),
            defaults=create_default,
        )
        try:
            ShodanVulns.objects.update_or_create(
                timestamp=vuln.get("timestamp"),
                ip=ip_object,
                port=vuln.get("port"),
                protocol=vuln.get("protocol"),
                organization=org,
                defaults={
                    "ip_string": vuln.get("ip_string"),
                    "organization_name": vuln.get("organization_name"),
                    "cve": vuln.get("cve"),
                    "severity": vuln.get("severity"),
                    "cvss": vuln.get("cvss"),
                    "summary": vuln.get("summary"),
                    "product": vuln.get("product"),
                    "attack_vector": vuln.get("attack_vector"),
                    "av_description": vuln.get("av_description"),
                    "attack_complexity": vuln.get("attack_complexity"),
                    "ac_description": vuln.get("ac_description"),
                    "confidentiality_impact": vuln.get("confidentiality_impact"),
                    "ci_description": vuln.get("ci_description"),
                    "integrity_impact": vuln.get("integrity_impact"),
                    "ii_description": vuln.get("ii_description"),
                    "availability_impact": vuln.get("availability_impact"),
                    "ai_description": vuln.get("ai_description"),
                    "tags": vuln.get("tags"),
                    "domains": vuln.get("domains"),
                    "hostnames": vuln.get("hostnames"),
                    "isp": vuln.get("isp"),
                    "asn": vuln.get("asn"),
                    "type": vuln.get("type"),
                    "name": vuln.get("name"),
                    "potential_vulns": vuln.get("potential_vulns"),
                    "mitigation": vuln.get("mitigation"),
                    "server": vuln.get("server"),
                    "is_verified": vuln.get("is_verified"),
                    "banner": vuln.get("banner"),
                    "version": vuln.get("version"),
                    "cpe": vuln.get("cpe"),
                    "data_source": data_source,
                },
            )
        except Exception as e:
            LOGGER.error("Error saving Shodan Vuln: %s", e)


def validate_response_checksum(response):
    """Validate the checksum from an API response."""
    try:
        # Extract response JSON
        response_data = response.json()

        # Extract checksum from response headers
        received_checksum = response.headers.get("X-Salted-Checksum")
        if not received_checksum:
            LOGGER.warning("No checksum found in headers!")
            return False

        # Recompute the checksum
        response_serialized = json.dumps(response_data, default=str, sort_keys=True)
        calculated_checksum = hashlib.sha256(
            (SALT + response_serialized).encode()
        ).hexdigest()

        return received_checksum == calculated_checksum

    except Exception as e:
        LOGGER.error("Error validating checksum: %s", e)
        return False

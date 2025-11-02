"""VulnSync scan."""
# Standard Python Libraries
import logging
import os
import time

# Third-Party Libraries
import django
import dns.resolver
import requests
from xfd_api.models import Domain, Organization, Service, Vulnerability

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

LOGGER = logging.getLogger(__name__)


def handler(event, context):
    """Retrieve and save vulnerabilities and services from PE."""
    try:
        main()
        return {
            "status_code": 200,
            "body": "PE Vulnerabilities sync completed successfully.",
        }
    except Exception as e:
        return {"status_code": 500, "body": str(e)}


def main():
    """Fetch and save PE vulnerabilities and services."""
    LOGGER.info(
        "Scanning PE database for vulnerabilities & services for all organizations."
    )

    # Retrieve all organizations
    all_orgs = Organization.objects.all()

    # For each organization, fetch vulnerability data
    for org in all_orgs:
        LOGGER.info("Processing organization: %s, %s", org.acronym, org.name)

        # Fetch PE vulnerability task data
        data = fetch_pe_vuln_task(org.acronym)
        if not data or not data.get("tasks_dict"):
            LOGGER.warning(
                "Failed to start PE API task for org: %s, %s", org.acronym, org.name
            )
            continue

        all_vulns = []
        for scan_name, task_id in data["tasks_dict"].items():
            response = fetch_pe_vuln_data(scan_name, task_id)
            while response and response.get("status") == "Pending":
                time.sleep(1)
                response = fetch_pe_vuln_data(scan_name, task_id)

            if response and response.get("status") == "Failure":
                LOGGER.error(
                    "Failed fetching data for task %s for org %s, %s",
                    task_id,
                    org.acronym,
                    org.name,
                )
                continue

            all_vulns.extend(response.get("result", []))
            time.sleep(1)

        # Save vulnerabilities and associated data
        for vuln in all_vulns:
            process_vulnerability(vuln, org)


def fetch_pe_vuln_task(org_acronym):
    """Fetch PE vulnerability task data."""
    LOGGER.info("Fetching PE vulnerability task for organization: %s", org_acronym)
    headers = {
        "X-API-KEY": os.getenv("CF_API_KEY"),
        "access_token": os.getenv("PE_API_KEY"),
        "Content-Type": "",
    }
    data = {"org_acronym": org_acronym}

    try:
        response = requests.post(
            "https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/crossfeed_vulns",
            headers=headers,
            json=data,
            timeout=20,  # Timeout in seconds
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error("Error fetching PE task: %s", e)
        return None


def fetch_pe_vuln_data(scan_name, task_id):
    """Fetch PE vulnerability data for a task."""
    url = "https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/crossfeed_vulns/task/?task_id={}&scan_name={}".format(
        task_id, scan_name
    )
    headers = {
        "X-API-KEY": os.getenv("CF_API_KEY"),
        "access_token": os.getenv("PE_API_KEY"),
        "Content-Type": "",
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error("Error fetching PE vulnerability data: %s", e)
        return None


def process_vulnerability(vuln, org):
    """Process and save a single vulnerability along with associated domains and services."""
    try:
        domain = save_domain(vuln, org)
        service = save_service(vuln, domain)
        save_vulnerability(vuln, domain, service)
    except Exception as e:
        LOGGER.error("Error processing vulnerability: %s", e)


def save_domain(vuln, org):
    """Save domain associated with a vulnerability."""
    try:
        service_asset_type = vuln.get("service_asset_type")
        service_asset = vuln.get("service_asset")
        ip_only = False
        service_domain, service_ip = None, None

        if service_asset_type == "ip":
            service_ip = service_asset
            try:
                service_domain = dns.resolver.resolve(service_ip, "PTR")[0].to_text()
            except Exception as e:
                LOGGER.error(e)
                service_domain = service_ip
                ip_only = True
        else:
            service_domain = service_asset
            try:
                service_ip = dns.resolver.resolve(service_domain, "A")[0].to_text()
            except Exception as e:
                LOGGER.error(e)
                service_ip = None

        domain, _ = Domain.objects.update_or_create(
            name=service_domain,
            organization=org,
            defaults={
                "ip": service_ip,
                "fromRootDomain": None
                if ip_only
                else ".".join(service_domain.split(".")[-2:]),
                "subdomainSource": "P&E - {}".format(vuln["source"]),
                "ipOnly": ip_only,
            },
        )
        return domain
    except Exception as e:
        LOGGER.exception("Failed to save domain: %s", e)
        raise


def save_service(vuln, domain):
    """Save service associated with a vulnerability."""
    try:
        if vuln.get("port") is None:
            return None

        service, _ = Service.objects.update_or_create(
            domain=domain,
            port=vuln["port"],
            defaults={
                "lastSeen": vuln["last_seen"],
                "banner": vuln.get("banner"),
                "serviceSource": vuln.get("source"),
                "shodanResults": {
                    "product": vuln.get("product"),
                    "version": vuln.get("version"),
                    "cpe": vuln.get("cpe"),
                }
                if vuln.get("source") == "shodan"
                else {},
            },
        )
        return service
    except Exception as e:
        LOGGER.exception("Failed to save service: %s", e)
        raise


def save_vulnerability(vuln, domain, service):
    """Save vulnerability to the database."""
    try:
        Vulnerability.objects.update_or_create(
            domain=domain,
            title=vuln["title"],
            defaults={
                "lastSeen": vuln["last_seen"],
                "cve": vuln["cve"],
                "cwe": vuln["cwe"],
                "description": vuln["description"],
                "cvss": vuln["cvss"],
                "severity": vuln["severity"],
                "state": vuln["state"],
                "structuredData": vuln.get("structuredData"),
                "source": vuln["source"],
                "needsPopulation": vuln["needsPopulation"],
                "service": service,
            },
        )
    except Exception as e:
        LOGGER.exception("Failed to save vulnerability: %s", e)
        raise

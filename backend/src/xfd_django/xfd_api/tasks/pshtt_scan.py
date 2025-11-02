"""Task for running Pshtt scans on subdomains and storing results in the database."""
# Standard Python Libraries
import logging

# Third-Party Libraries
from django.utils import timezone
from pshtt import pshtt
from xfd_mini_dl.models import DataSource, Organization, PshttResults, SubDomains

LOGGER = logging.getLogger(__name__)


def handler(event):
    """Handle the Pshtt scan task."""
    try:
        main(event)
    except Exception as e:
        LOGGER.error("Error in pshtt task: %s", e)


def chunk_list(lst, n):
    """Yield successive chunks from lst, each with up to n elements."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def main(event):
    """Perform Pshtt scans on subdomains and store results in the database."""
    org_id = event.get("organizationId")
    org_record = None
    try:
        org_record = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        LOGGER.error("Organization with ID %s does not exist. Exiting task.", org_id)
        return
    data_source, _ = DataSource.objects.get_or_create(
        name="Pshtt",
        defaults={
            "description": "Pshtt scan results for domains",
            "last_run": timezone.now().date(),
        },
    )
    data_source.last_run = timezone.now().date()
    data_source.save()
    if not data_source:
        LOGGER.error("DataSource Pshtt could not be created or updated. Exiting task.")
        return

    sub_domains = SubDomains.objects.filter(organization_id=org_id)
    if len(sub_domains) == 0:
        LOGGER.info(
            "No subdomains found for organization %s. Exiting task.", org_record.name
        )
        return
    LOGGER.info(
        "Found %d subdomains for organization %s", len(sub_domains), org_record.name
    )
    options = {
        "timeout": 30,
        "ca_file": None,
        "pt_int_ca_file": None,
        "user_agent": "pshtt (Python)",
        "cache-third-parties": False,
        "sslyze": True,  # Make sure your patched sslyze setup is tested
    }

    # Chunk the subdomains into groups of 10 to avoid overwhelming Pshtt external service
    chunked_sub_domains = list(chunk_list(sub_domains, 10))
    for chunk in chunked_sub_domains:
        # Convert each subdomain to a list of strings
        subdomain_list = [subdomain.sub_domain for subdomain in chunk]
        subdomain_map = {subdomain.sub_domain: subdomain for subdomain in chunk}
        LOGGER.info("Processing chunk of subdomains: %s", subdomain_list)
        try:
            pshtt_results = pshtt.inspect_domains(subdomain_list, options)
        except Exception as e:
            LOGGER.error("Error during pshtt inspection: %s", e)
            continue
        for result in pshtt_results:
            sub_domain = subdomain_map.get(result["Domain"], None)
            pshtt_result_record, created = PshttResults.objects.update_or_create(
                sub_domain=sub_domain,
                organization=org_record,
                defaults={
                    "data_source": data_source,
                    "date_scanned": timezone.now(),
                    "base_domain": result.get("Base Domain"),
                    "base_domain_hsts_preloaded": result.get(
                        "Base Domain HSTS Preloaded"
                    ),
                    "canonical_url": result.get("Canonical URL"),
                    "defaults_to_https": result.get("Defaults to HTTPS"),
                    "domain": result.get("Domain"),
                    "domain_enforces_https": result.get("Domain Enforces HTTPS"),
                    "domain_supports_https": result.get("Domain Supports HTTPS"),
                    "domain_uses_strong_hsts": result.get("Domain Uses Strong HSTS"),
                    "downgrades_https": result.get("Downgrades HTTPS"),
                    "hsts": result.get("HSTS"),
                    "hsts_entire_domain": result.get("HSTS Entire Domain"),
                    "hsts_header": result.get("HSTS Header"),
                    "hsts_max_age": result.get("HSTS Max Age"),
                    "hsts_preload_pending": result.get("HSTS Preload Pending"),
                    "hsts_preload_ready": result.get("HSTS Preload Ready"),
                    "hsts_preloaded": result.get("HSTS Preloaded"),
                    "https_bad_chain": result.get("HTTPS Bad Chain"),
                    "https_bad_hostname": result.get("HTTPS Bad Hostname"),
                    "https_cert_chain_length": result.get("HTTPS Cert Chain Length"),
                    "https_client_auth_required": result.get(
                        "HTTPS Client Auth Required"
                    ),
                    "https_custom_truststore_trusted": result.get(
                        "HTTPS Custom Truststore Trusted"
                    ),
                    "https_expired_cert": result.get("HTTPS Expired Cert"),
                    "https_full_connection": result.get("HTTPS Full Connection"),
                    "https_live": result.get("Live"),
                    "https_probably_missing_intermediate_cert": result.get(
                        "HTTPS Probably Missing Intermediate Cert"
                    ),
                    "https_publicly_trusted": result.get("HTTPS Publicly Trusted"),
                    "https_self_signed_cert": result.get("HTTPS Self Signed Cert"),
                    "ip": result.get("IP"),
                    "live": result.get("Live"),
                    "redirect": result.get("Redirect"),
                    "redirect_to": result.get("Redirect To"),
                    "strictly_forces_https": result.get("Strictly Forces HTTPS"),
                    "server_header": result.get("Server Header"),
                    "server_version": result.get("Server Version"),
                    "notes": result.get("Notes", ""),
                    # endpoint => Https
                    "ep_http_headers": result.get("endpoints", {})
                    .get("http", {})
                    .get("headers"),
                    "ep_http_server_header": result.get("endpoints", {})
                    .get("http", {})
                    .get("server_header"),
                    "ep_http_server_version": result.get("endpoints", {})
                    .get("http", {})
                    .get("server_version"),
                    "ep_https_headers": result.get("endpoints", {})
                    .get("https", {})
                    .get("headers"),
                    "ep_https_hsts_header": result.get("endpoints", {})
                    .get("https", {})
                    .get("hsts_header"),
                    "ep_https_server_header": result.get("endpoints", {})
                    .get("https", {})
                    .get("server_header"),
                    "ep_https_server_version": result.get("endpoints", {})
                    .get("https", {})
                    .get("server_version"),
                    "ep_httpswww_headers": result.get("endpoints", {})
                    .get("httpswww", {})
                    .get("headers"),
                    "ep_httpswww_hsts_header": result.get("endpoints", {})
                    .get("httpswww", {})
                    .get("hsts_header"),
                    "ep_httpswww_server_header": result.get("endpoints", {})
                    .get("httpswww", {})
                    .get("server_header"),
                    "ep_httpswww_server_version": result.get("endpoints", {})
                    .get("httpswww", {})
                    .get("server_version"),
                    "ep_httpwww_headers": result.get("endpoints", {})
                    .get("httpwww", {})
                    .get("headers"),
                    "ep_httpwww_server_header": result.get("endpoints", {})
                    .get("httpwww", {})
                    .get("server_header"),
                    "ep_httpwww_server_version": result.get("endpoints", {})
                    .get("httpwww", {})
                    .get("server_version"),
                },
            )
            if created:
                LOGGER.info(
                    "Created new PshttResults record for subdomain: %s",
                    pshtt_result_record,
                )
            else:
                LOGGER.info(
                    "Updated PshttResults record for subdomain: %s", pshtt_result_record
                )

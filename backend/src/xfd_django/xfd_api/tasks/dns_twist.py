"""Use DNS twist to fuzz domain names and cross check with a blacklist."""
# Standard Python Libraries
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import json
import logging
import os
import pathlib
import traceback
from typing import Optional
from uuid import uuid4

# Third-Party Libraries
import dnstwist
import dshield
import requests
from xfd_mini_dl.models import DataSource, DomainPermutations, Organization, SubDomains

date = datetime.datetime.now().strftime("%Y-%m-%d")
LOGGER = logging.getLogger(__name__)
BACKEND_DOMAIN = os.getenv("BACKEND_DOMAIN", "http://backend:3000/blocklist/check")
DMZ_API_KEY = os.getenv("DMZ_API_KEY", "local")


# pylint: disable=too-many-statements
def make_domain_dict(
    org, data_source, dom, malicious, attacks, reports, dshield_count, dshield_attacks
):
    """Create a dictionary for a domain permutation record."""
    return {
        "organization": org,
        "data_source": data_source,
        "domain_permutation": dom["domain"],
        "ipv4": dom["dns_a"][0],
        "ipv6": dom["dns_aaaa"][0],
        "mail_server": dom["dns_mx"][0],
        "name_server": dom["dns_ns"][0],
        "fuzzer": dom["fuzzer"],
        "date_active": date,
        "ssdeep_score": dom["ssdeep_score"],
        "malicious": malicious,
        "blocklist_attack_count": attacks,
        "blocklist_report_count": reports,
        "dshield_record_count": dshield_count,
        "dshield_attack_count": dshield_attacks,
    }


def _is_invalid_dom(dom):
    if "original" in dom.get("fuzzer", ""):
        return True
    if "dns_a" not in dom:
        return True
    if str(dom["dns_a"][0]) == "!ServFail":
        return True
    return False


def _check_blocklist(ip, blocklist_results):
    if not blocklist_results or not ip or ip not in blocklist_results:
        return False, 0, 0

    result = blocklist_results[ip]
    attacks = result.get("attacks", 0)
    reports = result.get("reports", 0)

    malicious = attacks > 0 or reports > 0
    return malicious, attacks, reports


def _check_ipv6(dom, blocklist_results, attacks, reports):
    dom.setdefault("dns_aaaa", [""])

    ipv6 = str(dom["dns_aaaa"][0])
    if not ipv6 or ipv6 == "!ServFail":
        dom["dns_aaaa"] = [""]
        return False, attacks, reports

    malicious, v6_attacks, v6_reports = _check_blocklist(ipv6, blocklist_results)

    return (
        malicious,
        max(attacks, v6_attacks),
        max(reports, v6_reports),
    )


def _query_dshield(ip):
    try:
        result = dshield.ip(ip, return_format=dshield.JSON)
        parsed = json.loads(result)
        ip_info = parsed.get("ip", {})

        attacks = int(ip_info.get("attacks") or 0)
        feeds = len(ip_info.get("threatfeeds", []))

        return attacks, feeds
    except Exception as exc:
        LOGGER.info("Error querying DShield API: %s", exc)
        return 0, 0


def _cleanup_dom(dom):
    dom.setdefault("ssdeep_score", "")
    dom.setdefault("dns_mx", [""])
    dom.setdefault("dns_ns", [""])


def checkDshield(dom, data_source, org, perm_list, blocklist_results=None):
    """Check DShield for the given domain and return a domain dict."""
    malicious = False
    attacks = reports = 0
    dshield_attacks = dshield_count = 0

    if _is_invalid_dom(dom):
        return None, perm_list

    ipv4 = str(dom["dns_a"][0])
    v4_malicious, attacks, reports = _check_blocklist(ipv4, blocklist_results)
    malicious |= v4_malicious

    v6_malicious, attacks, reports = _check_ipv6(
        dom, blocklist_results, attacks, reports
    )
    malicious |= v6_malicious

    if ipv4:
        dshield_attacks, dshield_count = _query_dshield(ipv4)
        if dshield_attacks > 0 or dshield_count > 0:
            malicious = True

    _cleanup_dom(dom)

    permutation = dom["domain"]
    if permutation in perm_list:
        return None, perm_list

    perm_list.append(permutation)

    domain_dict = make_domain_dict(
        org,
        data_source,
        dom,
        malicious,
        attacks,
        reports,
        dshield_count,
        dshield_attacks,
    )

    return domain_dict, perm_list


def execute_dnstwist(root_domain, test=0, threads=2):
    """Run dnstwist on each root domain.

    Args:
        root_domain: The domain to run dnstwist on
        test: If 1, return early without secondary .gov processing
        threads: Number of internal threads for dnstwist (default 2 to allow for
                 concurrent execution at the caller level without overloading)
    """
    pathtoDict = str(pathlib.Path(__file__).parent.resolve()) + "/data/common_tlds.dict"
    dnstwist_result = dnstwist.run(
        registered=True,
        tld=pathtoDict,
        format="json",
        threads=threads,
        domain=root_domain,
    )
    LOGGER.info(
        "DNSTwist found %d permutations for %s", len(dnstwist_result), root_domain
    )
    LOGGER.info("DNSTwist data: %s", dnstwist_result)
    if test == 1:
        return dnstwist_result
    finalorglist = dnstwist_result + []
    if root_domain.split(".")[-1] == "gov":
        for dom in dnstwist_result:
            if is_not_excluded_fuzzer(dom["fuzzer"]):
                LOGGER.info("Running again on %s", dom["domain"])
                secondlist = dnstwist.run(
                    registered=True,
                    tld=pathtoDict,
                    format="json",
                    threads=threads,
                    domain=dom["domain"],
                )
                finalorglist += secondlist
    return finalorglist


def is_not_excluded_fuzzer(fuzzer):
    """Check if the fuzzer is not excluded."""
    excluded = {
        "tld-swap",
        "original",
        "replacement",
        "repetition",
        "omission",
        "insertion",
        "transposition",
    }
    return fuzzer not in excluded


def get_data_source(data_source_name: str) -> Optional[str]:
    """Get or create a data source record."""
    try:
        data_source_record = DataSource.objects.filter(name=data_source_name).first()
        if data_source_record:
            return data_source_record
        data_source_record = DataSource.objects.create(
            name=data_source_name,
            data_source_uid=uuid4(),
            description="Data source for DNSTwist",
            last_run=datetime.datetime.now(datetime.timezone.utc),
        )
        LOGGER.info("Created data source: %s", data_source_name)
        return data_source_record
    except Exception as e:
        LOGGER.error("Error retrieving/creating data source: %s", str(e))
        return None


def check_domains_in_blocklist(domains: list) -> dict:
    """
    Check multiple domains against the blocklist API in bulk.

    Args:
        domains: List of domain objects from dnstwist results

    Returns:
        Dictionary mapping IP addresses to their blocklist results
        Format: {
            "ip_address": {
                "attacks": int,
                "reports": int
            }
        }
    """
    # Collect all unique IPs from the domains (both IPv4 and IPv6)
    ip_addresses = set()

    for dom in domains:
        # Collect IPv4 addresses
        if "dns_a" in dom and dom["dns_a"]:
            ip = str(dom["dns_a"][0])
            if ip != "!ServFail" and ip.strip():
                ip_addresses.add(ip)

        # Collect IPv6 addresses
        if "dns_aaaa" in dom and dom["dns_aaaa"]:
            ip = str(dom["dns_aaaa"][0])
            if ip != "!ServFail" and ip.strip():
                ip_addresses.add(ip)

    # Convert set to list for JSON serialization
    ip_list = list(ip_addresses)

    if not ip_list:
        LOGGER.info("No IP addresses to check in blocklist")
        return {}

    # Make bulk API call
    try:
        response = requests.post(
            "http://backend:3000/blocklist/check",
            json={"ip_addresses": ip_list},
            timeout=60,
            headers={"Authorization": DMZ_API_KEY},
        )
        response.raise_for_status()
        results = response.json()
        LOGGER.info("Bulk blocklist API response for %d IPs", len(results))
        return results
    except Exception as e:
        LOGGER.error("Error querying bulk blocklist API: %s", str(e))
        return {}


def get_org_root_domains(org_id):
    """Return the root domains for the given organization."""
    sub_domains = SubDomains.objects.filter(
        organization_id=org_id, is_root_domain=True, enumerate_subs=True
    )
    LOGGER.info("Found %s root domains for org %s", len(sub_domains), org_id)
    return sub_domains


def reverse_domain(domain: str) -> str:
    """Reverse the domain."""
    return ".".join(domain.split(".")[::-1])


def get_orgs() -> list:
    """Return all organizations."""
    try:
        orgs = Organization.objects.all()
        return orgs
    except Exception:
        return []


def bulk_upsert_domain_permutations(domain_dicts):
    """Bulk insert/update domain permutations into the database."""
    if not domain_dicts:
        return

    # Build model instances from dicts
    instances = [
        DomainPermutations(
            organization=d["organization"],
            domain_permutation=d["domain_permutation"],
            ipv4=d["ipv4"],
            ipv6=d["ipv6"],
            mail_server=d["mail_server"],
            name_server=d["name_server"],
            fuzzer=d["fuzzer"],
            date_observed=datetime.datetime.now(datetime.timezone.utc),
            date_active=d["date_active"],
            ssdeep_score=d["ssdeep_score"],
            malicious=d["malicious"],
            blocklist_attack_count=d["blocklist_attack_count"],
            blocklist_report_count=d["blocklist_report_count"],
            data_source=d["data_source"],
            dshield_record_count=d["dshield_record_count"],
            dshield_attack_count=d["dshield_attack_count"],
        )
        for d in domain_dicts
    ]

    DomainPermutations.objects.bulk_create(
        instances,
        update_conflicts=True,
        unique_fields=["organization", "domain_permutation"],
        update_fields=[
            "ipv4",
            "ipv6",
            "mail_server",
            "name_server",
            "fuzzer",
            "date_observed",
            "date_active",
            "ssdeep_score",
            "malicious",
            "blocklist_attack_count",
            "blocklist_report_count",
            "data_source",
            "dshield_record_count",
            "dshield_attack_count",
        ],
    )
    LOGGER.info("Bulk upserted %d domain permutations", len(instances))


def process_org(org, orgs_list, data_source, failures):
    """Process the domains for the given organization."""
    org_id = org.id
    org_name = org.name
    pe_org_id = org.name
    if pe_org_id in orgs_list or orgs_list == "all" or orgs_list == "DEMO":
        LOGGER.info("Running DNSTwist on %s", org_name)
        try:
            # Get root domains
            root_dict = get_org_root_domains(org_id)
            domain_list = []
            perm_list = []
            all_domains = []

            # First pass: collect all domains from all root domains using thread pool
            def run_dnstwist_for_root(root):
                """Run dnstwist for a single root domain."""
                root_domain = root.sub_domain
                LOGGER.info("\tRunning on root domain: %s", root_domain)
                return execute_dnstwist(root_domain)

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {
                    executor.submit(run_dnstwist_for_root, root): root
                    for root in root_dict
                }
                for future in as_completed(futures):
                    try:
                        finalorglist = future.result()
                        all_domains.extend(finalorglist)
                    except Exception as e:
                        root = futures[future]
                        LOGGER.error(
                            "Error running dnstwist for %s: %s", root.sub_domain, str(e)
                        )

            # Perform bulk blocklist check for all domains
            LOGGER.info(
                "Performing bulk blocklist check for %d domains", len(all_domains)
            )
            blocklist_results = check_domains_in_blocklist(all_domains)

            # Second pass: process each domain with pre-fetched blocklist results
            # Use thread pool for concurrent DShield checks
            seen_permutations = set(perm_list)

            def process_domain(dom):
                """Process a single domain through DShield check."""
                # Check for duplicates using domain permutation
                permutation = dom.get("domain")
                if permutation and permutation in seen_permutations:
                    return None
                LOGGER.info("Checking D Shield: %s", dom)
                # Pass empty perm_list since we handle deduplication here
                domain_dict, _ = checkDshield(
                    dom, data_source, org, [], blocklist_results
                )
                return domain_dict

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {
                    executor.submit(process_domain, dom): dom for dom in all_domains
                }
                for future in as_completed(futures):
                    try:
                        domain_dict = future.result()
                        if domain_dict is not None:
                            # Track seen permutations to avoid duplicates
                            seen_permutations.add(domain_dict["domain_permutation"])
                            domain_list.append(domain_dict)
                    except Exception as e:
                        LOGGER.error("Error processing domain: %s", str(e))

            try:
                bulk_upsert_domain_permutations(domain_list)
            except Exception:
                # TODO: Create custom exceptions.
                # Issue 265: https://github.com/cisagov/pe-reports/issues/265
                LOGGER.info("Failure inserting data into database.")
                failures.append(org_name)
                LOGGER.info(traceback.format_exc())
        except Exception:
            # TODO: Create custom exceptions.
            # Issue 265: https://github.com/cisagov/pe-reports/issues/265
            LOGGER.info("Failed selecting DNSTwist data.")
            failures.append(org_name)
            LOGGER.info(traceback.format_exc())


def select_orgs(orgs_list):
    """Select organizations to run DNSTwist on."""
    orgs_final = []
    orgs = get_orgs()
    if orgs_list == "all":
        for org in orgs:
            if org.pe_report_on:
                orgs_final.append(org)
            else:
                continue
    elif orgs_list == "DEMO":
        for org in orgs:
            if org.pe_demo:
                orgs_final.append(org)
            else:
                continue
    else:
        for org in orgs:
            if org.name in orgs_list:
                orgs_final.append(org)
            else:
                continue
    return orgs_final


def main(event):
    """Run DNStwist on certain domains and upload findings to database."""
    organizationId = event.get("organizationId")
    org_record = Organization.objects.get(id=organizationId)
    LOGGER.info("Running DNSTwist on %s", org_record.name)
    data_source = get_data_source("DNSTwist")
    failures = []
    orgs_list = [org_record.name]
    process_org(org_record, orgs_list, data_source, failures)
    if failures:
        LOGGER.error("These orgs failed:")
        LOGGER.error(failures)


def handler(event):
    """Dns Twist sync handler."""
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
        LOGGER.error("Error in handler: %s", e)
        return {"statusCode": 500, "body": str(e)}

"""Use DNS twist to fuzz domain names and cross check with a blacklist."""
# Standard Python Libraries
import contextlib
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


# Update this function to use the new homebrew blocklist checking system
def checkBlocklist(dom, data_source, org, perm_list):
    """Cross reference the dnstwist results with DShield Blocklist."""
    malicious = False
    attacks = 0
    reports = 0
    dshield_attacks = 0
    dshield_count = 0
    if "original" in dom["fuzzer"]:
        return None, perm_list
    elif "dns_a" not in dom:
        return None, perm_list
    else:
        if str(dom["dns_a"][0]) == "!ServFail":
            return None, perm_list

        # Check IP in Blocklist API
        check_domain_in_blocklist(
            dom, malicious, attacks, reports, dshield_attacks, dshield_count
        )

    # Check IPv6
    if "dns_aaaa" not in dom:
        dom["dns_aaaa"] = [""]
    elif str(dom["dns_aaaa"][0]) == "!ServFail":
        dom["dns_aaaa"] = [""]
    else:
        # Check IP in Blocklist API
        # To-Do: Update this function to use the new homebrew blocklist checking system
        dom["use_check_ipv6"] = True
        check_domain_in_blocklist(
            dom,
            malicious,
            attacks,
            reports,
            dshield_attacks,
            dshield_count,
        )

    # Clean-up other fields
    if "ssdeep_score" not in dom:
        dom["ssdeep_score"] = ""
    if "dns_mx" not in dom:
        dom["dns_mx"] = [""]
    if "dns_ns" not in dom:
        dom["dns_ns"] = [""]

    # Ignore duplicates
    permutation = dom["domain"]
    if permutation in perm_list:
        return None, perm_list
    else:
        perm_list.append(permutation)

    domain_dict = {
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
    return domain_dict, perm_list


def execute_dnstwist(root_domain, test=0):
    """Run dnstwist on each root domain."""
    pathtoDict = str(pathlib.Path(__file__).parent.resolve()) + "/data/common_tlds.dict"
    dnstwist_result = dnstwist.run(
        registered=True,
        tld=pathtoDict,
        format="json",
        threads=8,
        domain=root_domain,
    )
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
                    threads=8,
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


def check_domain_in_blocklist(
    dom, malicious, attacks, reports, dshield_attacks, dshield_count
):
    """Cross reference the dnstwist results with internal and DShield blocklists."""
    dns_key = "dns_aaaa" if dom.get("use_check_ipv6") else "dns_a"

    try:
        ip_address = str(dom[dns_key][0])
    except (KeyError, IndexError):
        return malicious, attacks, reports, dshield_attacks, dshield_count

    # Query internal blocklist API
    try:
        response = requests.get(
            f"{BACKEND_DOMAIN}?ip_address={ip_address}",
            timeout=60,
            headers={"Authorization": DMZ_API_KEY},
        )
        response.raise_for_status()
        data = response.json()
        LOGGER.info("Blocklist API response: %s", data)
        if isinstance(data, dict) and (
            data.get("attacks", 0) > 0 or data.get("reports", 0) > 0
        ):
            malicious = True
            attacks = int(data.get("attacks", 0))
            reports = int(data.get("reports", 0))

    except Exception as e:
        # Optionally log the error
        LOGGER.info("Error querying internal blocklist API: %s", str(e))
        attacks = 0
        reports = 0

    # Query DShield API
    try:
        dshield_result = dshield.ip(ip_address, return_format=dshield.JSON)
        parsed = json.loads(dshield_result)
        ip_info = parsed.get("ip", {})

        dshield_attacks = int(ip_info.get("attacks") or 0)
        dshield_count = len(ip_info.get("threatfeeds", []))

        if dshield_attacks > 0 or dshield_count > 0:
            malicious = True

    except Exception as e:
        LOGGER.info("Error querying DShield API: %s", str(e))
        dshield_attacks = 0
        dshield_count = 0

    return malicious, attacks, reports, dshield_attacks, dshield_count


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


def execute_dnstwist_data(domain_dict):
    """Insert the domain permutation into the database."""
    try:
        DomainPermutations.objects.update_or_create(
            suspected_domain_uid=uuid4(),
            organization=domain_dict["organization"],
            domain_permutation=domain_dict["domain_permutation"],
            ipv4=domain_dict["ipv4"],
            ipv6=domain_dict["ipv6"],
            mail_server=domain_dict["mail_server"],
            name_server=domain_dict["name_server"],
            fuzzer=domain_dict["fuzzer"],
            date_observed=datetime.datetime.now(datetime.timezone.utc),
            date_active=domain_dict["date_active"],
            ssdeep_score=domain_dict["ssdeep_score"],
            malicious=domain_dict["malicious"],
            blocklist_attack_count=domain_dict["blocklist_attack_count"],
            blocklist_report_count=domain_dict["blocklist_report_count"],
            data_source=domain_dict["data_source"],
            dshield_record_count=domain_dict["dshield_record_count"],
            dshield_attack_count=domain_dict["dshield_attack_count"],
        )
    except Exception as e:
        LOGGER.error("Error adding domain permutation to data lake: %s", str(e))


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

            for root in root_dict:
                root_domain = root.sub_domain
                LOGGER.info("\tRunning on root domain: %s", root_domain)
                with open("dnstwist_output.txt", "w") as f, contextlib.redirect_stdout(
                    f
                ):
                    finalorglist = execute_dnstwist(root_domain)
                # Get subdomain uid
                # Check Blocklist
                for dom in finalorglist:
                    LOGGER.info("Checking Blocklist: %s", dom)
                    domain_dict, perm_list = checkBlocklist(
                        dom, data_source, org, perm_list
                    )
                    if domain_dict is not None:
                        domain_list.append(domain_dict)
            try:
                for domain in domain_list:
                    execute_dnstwist_data(domain)
                    LOGGER.info(
                        "Inserted %s into database", domain["domain_permutation"]
                    )
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

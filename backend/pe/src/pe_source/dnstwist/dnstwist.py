"""Use DNS twist to fuzz domain names and cross check with a blacklist."""

# Standard Python Libraries
import contextlib
import datetime
from datetime import timedelta
import json
import logging
import pathlib
import traceback
import uuid

# Third-Party Libraries
import dnstwist
import dshield
from pe_source.data.db_query_source import (
    addSubdomain,
    connect,
    get_data_source_uid,
    get_orgs,
    getSubdomain,
    org_root_domains,
)
import psycopg2.extras as extras
import requests

# Save findings as the last day of the report period
date = (datetime.datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
LOGGER = logging.getLogger(__name__)

_COMMON_TLDS_DICT = pathlib.Path(__file__).resolve().parent / "common_tlds.dict"


def checkBlocklist(dom, sub_domain_uid, source_uid, pe_org_uid, perm_list):
    """Cross reference the dnstwist results with DShield Blocklist."""
    malicious = False
    attacks = 0
    reports = 0

    # Check IPv4
    if "original" in dom["fuzzer"]:
        return None, perm_list
    elif "dns_a" not in dom:
        return None, perm_list
    else:
        if str(dom["dns_a"][0]) == "!ServFail":
            return None, perm_list
        # Check IP in Blocklist API
        response = requests.get(
            "http://api.blocklist.de/api.php?ip=" + str(dom["dns_a"][0]), timeout=60
        ).content

        if str(response) != "b'attacks: 0<br />reports: 0<br />'":
            try:
                malicious = True
                attacks = int(str(response).split("attacks: ")[1].split("<")[0])
                reports = int(str(response).split("reports: ")[1].split("<")[0])
            except Exception:
                malicious = False
                dshield_attacks = 0
                dshield_count = 0
        # Check IP in DSheild API
        try:
            results = dshield.ip(str(dom["dns_a"][0]), return_format=dshield.JSON)
            results = json.loads(results)
            threats = results["ip"]["threatfeeds"]
            attacks = results["ip"]["attacks"]
            attacks = int(0 if attacks is None else attacks)
            malicious = True
            dshield_attacks = attacks
            dshield_count = len(threats)
        except Exception:
            dshield_attacks = 0
            dshield_count = 0

    # Check IPv6
    if "dns_aaaa" not in dom:
        dom["dns_aaaa"] = [""]
    elif str(dom["dns_aaaa"][0]) == "!ServFail":
        dom["dns_aaaa"] = [""]
    else:
        # Check IP in Blocklist API
        response = requests.get(
            "http://api.blocklist.de/api.php?ip=" + str(dom["dns_aaaa"][0]), timeout=60
        ).content
        if str(response) != "b'attacks: 0<br />reports: 0<br />'":
            try:
                malicious = True
                attacks = int(str(response).split("attacks: ")[1].split("<")[0])
                reports = int(str(response).split("reports: ")[1].split("<")[0])
            except Exception:
                malicious = False
                dshield_attacks = 0
                dshield_count = 0
        # Check IP in DSheild API
        try:
            results = dshield.ip(str(dom["dns_aaaa"][0]), return_format=dshield.JSON)
            results = json.loads(results)
            threats = results["ip"]["threatfeeds"]
            attacks = results["ip"]["attacks"]
            attacks = int(0 if attacks is None else attacks)
            malicious = True
            dshield_attacks = attacks
            dshield_count = len(threats)
        except Exception:
            dshield_attacks = 0
            dshield_count = 0

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
        "suspected_domain_uid": str(uuid.uuid4()),
        "organizations_uid": pe_org_uid,
        "data_source_uid": source_uid,
        "sub_domain_uid": sub_domain_uid,
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
    """Run dnstwist on a specified root domain."""
    LOGGER.info(
        "Starting dnstwist fuzzer for %s (DNS resolution may take several minutes)",
        root_domain,
    )
    pathtoDict = str(_COMMON_TLDS_DICT)
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
            if (
                ("tld-swap" not in dom["fuzzer"])
                and ("original" not in dom["fuzzer"])
                and ("replacement" not in dom["fuzzer"])
                and ("repetition" not in dom["fuzzer"])
                and ("omission" not in dom["fuzzer"])
                and ("insertion" not in dom["fuzzer"])
                and ("transposition" not in dom["fuzzer"])
            ):
                LOGGER.info("\tRunning again on %s", dom["domain"])
                secondlist = dnstwist.run(
                    registered=True,
                    tld=pathtoDict,
                    format="json",
                    threads=8,
                    domain=dom["domain"],
                )
                finalorglist += secondlist
    return finalorglist


def _requested_org_names(orgs_list):
    """Normalize --orgs values to a set of exact cyhy_db_name matches."""
    if isinstance(orgs_list, str):
        return {part.strip() for part in orgs_list.split(",") if part.strip()}
    return set(orgs_list)


def run_dnstwist(orgs_list):
    """Run DNStwist on certain domains and upload findings to database."""
    # Retrieve full org info from PE database
    pe_orgs = get_orgs()
    pe_orgs_final = []
    if orgs_list == "all":
        for pe_org in pe_orgs:
            if pe_org["report_on"]:
                pe_orgs_final.append(pe_org)
            else:
                continue
    elif orgs_list == "DEMO":
        for pe_org in pe_orgs:
            if pe_org["demo"]:
                pe_orgs_final.append(pe_org)
            else:
                continue
    else:
        requested = _requested_org_names(orgs_list)
        for pe_org in pe_orgs:
            if pe_org["cyhy_db_name"] in requested:
                pe_orgs_final.append(pe_org)
            else:
                continue

    # alphabetize org list for consistent order
    pe_orgs_final = sorted(pe_orgs_final, key=lambda d: d["cyhy_db_name"])

    # Get data source uid
    PE_conn = connect()
    source_uid = get_data_source_uid("DNSTwist")

    # Run DNSTwist on each organization
    failures = []
    for org_idx, org in enumerate(pe_orgs_final):
        pe_org_uid = org["organizations_uid"]
        org_name = org["name"]
        pe_org_id = org["cyhy_db_name"]
        LOGGER.info(
            f"Running DNSTwist on {pe_org_id} ({org_idx + 1} of {len(pe_orgs_final)})"
        )
        # Retrieve DNSTwist data from crossfeed
        try:
            # Get root domains for this org
            # root_dict = org_root_domains(PE_conn, pe_org_uid) # TSQL ver.
            root_dict = org_root_domains(pe_org_uid)  # API ver.
            # Dedupe list of root domains
            list_of_roots = [d["root_domain"] for d in root_dict]
            list_of_roots = [s.strip() for s in list_of_roots]
            list_of_roots = list(set(list_of_roots))
            LOGGER.info(f"Found {len(list_of_roots)} roots for {pe_org_id}")
            # Iterate over each root domain
            domain_list = []
            perm_list = []
            for root_idx, root in enumerate(list_of_roots):
                # Run DNSTwist on each root
                root_domain = root
                if root_domain == "Null_Root":
                    continue
                LOGGER.info("Running DNSTwist on root domain: %s", root)
                with open("dnstwist_output.txt", "w") as f, contextlib.redirect_stdout(
                    f
                ):
                    finalorglist = execute_dnstwist(root_domain)
                LOGGER.info(f"Finished running DNSTwist on root domain: {root}")

                # Root domain row in sub_domains; getSubdomain returns -1 if missing
                sub_domain = root_domain
                sub_domain_uid = getSubdomain(sub_domain)
                if sub_domain_uid == -1:
                    addSubdomain(sub_domain, pe_org_uid, True)
                    sub_domain_uid = getSubdomain(sub_domain)
                if sub_domain_uid == -1:
                    raise RuntimeError(
                        "Could not resolve sub_domain_uid for root domain "
                        f"{sub_domain!r}"
                    )

                # Check root domain using Blocklist/DShield
                LOGGER.info(
                    "Running blocklist/dshield check on DNSTwist results "
                    "from root domain: %s",
                    root,
                )
                for dom_idx, dom in enumerate(finalorglist):
                    domain_name = dom.get("domain")
                    LOGGER.info(
                        "%s - blocklist/dshield check on %s (%s/%s), root: %s (%s/%s)",
                        pe_org_id,
                        domain_name,
                        dom_idx + 1,
                        len(finalorglist),
                        root,
                        root_idx + 1,
                        len(list_of_roots),
                    )
                    domain_dict, perm_list = checkBlocklist(
                        dom, sub_domain_uid, source_uid, pe_org_uid, perm_list
                    )
                    if domain_dict is not None:
                        domain_list.append(domain_dict)
                LOGGER.info(
                    "Finished blocklist/dshield check on DNSTwist results "
                    "from root domain: %s",
                    root,
                )
        except Exception:
            LOGGER.error(f"Failed retrieving DNSTwist data for {pe_org_id}")
            failures.append(org_name)
            LOGGER.error(traceback.format_exc())

        # Insert DNSTwist data into PE database
        LOGGER.info(f"Inserting DNSTwist data for {pe_org_id}")
        try:
            cursor = PE_conn.cursor()
            try:
                columns = domain_list[0].keys()
            except Exception:
                LOGGER.critical("No data in the domain list.")
                failures.append(org_name)
                continue
            table = "domain_permutations"
            sql = """INSERT INTO {}({}) VALUES %s
            ON CONFLICT (domain_permutation,organizations_uid)
            DO UPDATE SET malicious = EXCLUDED.malicious,
                blocklist_attack_count = EXCLUDED.blocklist_attack_count,
                blocklist_report_count = EXCLUDED.blocklist_report_count,
                dshield_record_count = EXCLUDED.dshield_record_count,
                dshield_attack_count = EXCLUDED.dshield_attack_count,
                data_source_uid = EXCLUDED.data_source_uid,
                date_active = EXCLUDED.date_active;"""

            values = [[value for value in dict.values()] for dict in domain_list]
            extras.execute_values(
                cursor,
                sql.format(
                    table,
                    ",".join(columns),
                ),
                values,
            )
            PE_conn.commit()
            LOGGER.info("DNSTwist data inserted successfully...")
        except Exception:
            LOGGER.error(f"Failed inserting DNSTwist data for {pe_org_id}")
            failures.append(org_name)
            LOGGER.error(traceback.format_exc())

    # Output summary stats
    LOGGER.info(
        "%s/%s orgs successfully underwent the DNSTwist scan",
        len(pe_orgs_final) - len(failures),
        len(pe_orgs_final),
    )
    LOGGER.info(
        "%s/%s orgs had a significant failure during the DNSTwist scan",
        len(failures),
        len(pe_orgs_final),
    )

    # Clean up and log failures
    PE_conn.close()
    if failures != []:
        LOGGER.error("These orgs failed: ", failures)


if __name__ == "__main__":
    run_dnstwist("all")

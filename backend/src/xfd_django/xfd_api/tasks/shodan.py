"""Shodan scan."""
# Standard Python Libraries
import datetime
import logging
import os
import time
from typing import Any, Dict, List

# Third-Party Libraries
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import requests
import shodan
from xfd_api.tasks.helpers.get_ips import get_ips_by_cidr
from xfd_mini_dl.models import DataSource, Ip, Organization, ShodanAssets, ShodanVulns


class FatalScanError(Exception):
    """Non-recoverable scan error (e.g. invalid API key)."""


SHODAN_IP_CHUNK_SIZE = int(
    os.getenv("SHODAN_IP_CHUNK_SIZE", "50")
)  # TODO: CRASM-3708 Validate this number used to be set to 10 but the comment said it was doing 100
SHODAN_QUERY_DAYS_BACK = int(
    os.getenv("SHODAN_QUERY_DAYS_BACK", "15")
)  # TODO: CRASM-3708 tune based on pull cadence
# Constants controlling pagination and rate limiting
LOGGER = logging.getLogger(__name__)


def handler(command_options):
    """Run the Shodan scan."""
    failed = []
    organization_name = command_options.get("organizationName")
    organization_id = command_options.get("organizationId")
    if not organization_name:
        return {"status_code": 400, "body": "Organization name not provided."}

    orgs_to_sync = Organization.objects.filter(id=organization_id)
    if not orgs_to_sync.exists():
        return {"status_code": 500, "body": "Organization not found."}
    organization = orgs_to_sync.first()
    org_uid = organization.id
    org_name = organization.name

    LOGGER.info("Running Shodan on organization: %s", organization_name)

    # Get dates for Shodan query (30 days)
    start, end = get_dates()

    # Retrieve IPs for this org
    try:
        ips = get_ips_by_cidr(org_uid)
    except Exception as e:
        LOGGER.error("Failed fetching IPs for %s.", org_name)
        LOGGER.error("%s - %s", e, org_name)
        failed.append("{} fetching IPs".format(org_name))
        return {
            "status_code": 500,
            "body": "Error - {}".format(e),
        }
    # If no IPs, skip this org
    if len(ips) == 0:
        LOGGER.warning("No IPs for %s.", org_name)
        return {
            "status_code": 500,
            "body": "No Ips for {}".format(org_name),
        }

    # Get initialized API object
    api_key = command_options.get("SHODAN_API_KEY")
    LOGGER.debug("Running on api key: %s", api_key)

    api = shodan.Shodan(api_key)

    # Otherwise run shodan search on the IPs
    failed = search_shodan(ips, api, start, end, organization, failed)

    # Log all failures for this thread
    if len(failed) > 0:
        return {
            "status_code": 500,
            "body": failed,
        }

    return {"status_code": 200, "body": "Success running Shodan."}


def search_shodan(
    ips, api, start, end, organization: Organization, failed
):  # pylint: disable=R0913, R0915
    """Search IPs in the Shodan API."""
    # Build dictionaries for naming conventions and definitions
    risky_ports, name_dict, risk_dict, av_dict, ac_dict, ci_dict = get_shodan_dicts()

    # Break up IPs into chunks of 100
    tot_ips = len(ips)
    ip_chunks = [
        ips[i : i + SHODAN_IP_CHUNK_SIZE]
        for i in range(0, tot_ips, SHODAN_IP_CHUNK_SIZE)
    ]
    tot = len(ip_chunks)
    LOGGER.info("Split %s IPs into %s chunks - %s", tot_ips, tot, organization.name)

    # Loop through chunks and query Shodan
    # Fetch or create the Censys data source record.
    source_uid, _ = DataSource.objects.get_or_create(
        name="Shodan",
        defaults={
            "description": "Shodan is the world's first search engine for Internet-connected devices.",
            "last_run": timezone.now().date(),
        },
    )
    for i, ip_chunk in enumerate(ip_chunks):  # pylint: disable=R1702
        count = i + 1
        try_count = 1
        while try_count < 7:
            try:
                # Initialize lists to store Shodan results
                data = []
                risk_data = []
                vuln_data: List[Dict[str, Any]] = []
                # Attempt batch lookup first
                try:
                    results = api.host(ip_chunk)
                except shodan.APIError as e:
                    if "No information available" in str(e):
                        LOGGER.info(
                            "One or more IPs had no Shodan data. Falling back to per-IP calls. - %s",
                            organization.name,
                        )
                        results = []
                        for ip in ip_chunk:
                            try:
                                results.append(api.host(ip))
                            except shodan.APIError:
                                LOGGER.info(
                                    "No Shodan data for IP %s - %s",
                                    ip,
                                    organization.name,
                                )
                                continue
                    else:
                        # Real API failure (rate limit, auth, etc.)
                        raise
                for r in results:
                    # Catch situation where response is a single string
                    if isinstance(r, str):
                        continue
                    for d in r["data"]:
                        # Convert Shodan date string to UTC datetime
                        shodan_utc = datetime.datetime.strptime(
                            d["timestamp"], "%Y-%m-%dT%H:%M:%S.%f"
                        ).replace(tzinfo=datetime.timezone.utc)
                        # Only include results in the timeframe
                        if start < shodan_utc < end:
                            prod = d.get("product", None)
                            serv = d.get("http", {}).get("server")
                            asn = d.get("ASN", None)
                            vulns = d.get("vulns", None)
                            location = d.get("location", None)
                            if vulns is not None:
                                unverified: List[str] = []
                                for cve in list(vulns.keys()):
                                    # Check if CVEs are verified
                                    unverified, vuln_data = is_verified(
                                        vulns,
                                        cve,
                                        av_dict,
                                        ac_dict,
                                        ci_dict,
                                        vuln_data,
                                        organization.id,
                                        r,
                                        d,
                                        asn,
                                        unverified,
                                    )
                                if len(unverified) > 0:
                                    ftype = "Pontentially Vulnerable Product"
                                    name = prod
                                    risk = unverified
                                    mitigation = "Verify asset is up to date, supported by the vendor, and configured securely"
                                    risk_data.append(
                                        {
                                            "asn": asn,
                                            "domains": r["domains"],
                                            "hostnames": r["hostnames"],
                                            "ip": r["ip_str"],
                                            "isn": r["isp"],
                                            "mitigation": mitigation,
                                            "name": name,
                                            "organization": r["org"],
                                            "organizations_uid": organization.id,
                                            "port": d["port"],
                                            "potential_vulns": risk,
                                            "product": prod,
                                            "protocol": d["_shodan"]["module"],
                                            "server": serv,
                                            "tags": r["tags"],
                                            "timestamp": parse_utc_timestamp(
                                                d["timestamp"]
                                            ),
                                            "type": ftype,
                                            "is_verified": False,
                                            "cpe": d.get("cpe", None),
                                            "banner": d.get("data", None),
                                            "version": d.get("version", None),
                                            "data_source_uid": source_uid,
                                        }
                                    )
                            elif d["_shodan"]["module"] in risky_ports:
                                ftype = "Insecure Protocol"
                                name = name_dict[d["_shodan"]["module"]]
                                risk = [risk_dict[d["_shodan"]["module"]]]
                                mitigation = "Confirm open port has a required business use for internet exposure and ensure necessary safeguards are in place through TCP wrapping, TLS encryption, or authentication requirements"
                                risk_data.append(
                                    {
                                        "ac_description": None,
                                        "ai_description": None,
                                        "asn": asn,
                                        "attack_complexity": None,
                                        "attack_vector": None,
                                        "av_description": None,
                                        "availability_impact": None,
                                        "ci_description": None,
                                        "confidentiality_impact": None,
                                        "cve": None,
                                        "cvss": None,
                                        "domains": r["domains"],
                                        "hostnames": r["hostnames"],
                                        "ii_Description": None,
                                        "integrity_impact": None,
                                        "ip": r["ip_str"],
                                        "isn": r["isp"],
                                        "mitigation": mitigation,
                                        "name": name,
                                        "organization": r["org"],
                                        "organizations_uid": organization.id,
                                        "port": d["port"],
                                        "potential_vulns": risk,
                                        "product": prod,
                                        "protocol": d["_shodan"]["module"],
                                        "server": serv,
                                        "severity": None,
                                        "summary": None,
                                        "tags": r["tags"],
                                        "timestamp": parse_utc_timestamp(
                                            d["timestamp"]
                                        ),
                                        "type": ftype,
                                        "is_verified": False,
                                        "cpe": d.get("cpe", None),
                                        "banner": d.get("data", None),
                                        "version": d.get("version", None),
                                        "data_source_uid": source_uid,
                                    }
                                )

                            data.append(
                                {
                                    "asn": asn,
                                    "domains": r["domains"],
                                    "hostnames": r["hostnames"],
                                    "ip": r["ip_str"],
                                    "isn": r["isp"],
                                    "organization": r["org"],
                                    "organizations_uid": organization.id,
                                    "port": d["port"],
                                    "product": prod,
                                    "protocol": d["_shodan"]["module"],
                                    "server": serv,
                                    "tags": r["tags"],
                                    "timestamp": d["timestamp"],
                                    "country_code": location["country_code"],
                                    "location": str(location),
                                    "data_source_uid": source_uid,
                                }
                            )
                all_vulns = vuln_data + risk_data

                # Insert shodan assets/vulns for this ip chunk
                insert_shodan_assets(data, organization)
                insert_shodan_vulns(all_vulns, organization)
                time.sleep(1)
                break
            except shodan.APIError as e:
                msg = str(e).lower()

                # FATAL: invalid / revoked key → STOP CONTAINER
                if any(
                    s in msg
                    for s in ("invalid api key", "unauthorized", "access denied")
                ):
                    LOGGER.critical(
                        "Invalid Shodan API key detected. Stopping worker. Error: %s",
                        e,
                    )
                    raise FatalScanError("Invalid Shodan API key")

                # RATE LIMIT → RETRY WITH BACKOFF
                if "rate limit" in msg:
                    sleep = min(60, try_count * 10)
                    LOGGER.warning(
                        "Rate limited by Shodan (try %s). Sleeping %ss",
                        try_count,
                        sleep,
                    )
                    time.sleep(sleep)
                    try_count += 1
                    continue

                # OTHER TRANSIENT ERRORS → RETRY
                LOGGER.warning(
                    "Transient Shodan API error (try %s/%s): %s",
                    try_count,
                    5,
                    e,
                )

                if try_count >= 5:
                    LOGGER.error(
                        "Transient Shodan failure after %s retries. Skipping chunk %s for %s.",
                        try_count,
                        count,
                        organization.name,
                    )
                    break  # skip THIS chunk only

                try_count += 1
                time.sleep(5)

        LOGGER.info("chunk %s/%s complete - %s", count, tot, organization.name)

    return failed


def get_dates():
    """Get dates for the query."""
    now = timezone.now()
    start = now - datetime.timedelta(days=SHODAN_QUERY_DAYS_BACK)
    end = now + datetime.timedelta(days=1)
    return start, end


def parse_utc_timestamp(ts):
    """Convert strings to datetime."""
    if isinstance(ts, str):
        return parse_datetime(ts).replace(tzinfo=datetime.timezone.utc)
    return ts  # already a datetime


def time_to_utc(in_time):
    """Convert time to UTC."""
    # If time does not have timezone info, assume it is local
    if in_time.tzinfo is None:
        local_tz = datetime.datetime.now().astimezone().tzinfo
        in_time = in_time.replace(tzinfo=local_tz)
    utc_time = in_time.astimezone(datetime.timezone.utc)
    return utc_time


def search_circl(cve):
    """Fetch CVE info from Circl."""
    re = requests.get("https://cve.circl.lu/api/cve/{}".format(cve), timeout=10)
    return re


def is_verified(
    vulns, cve, av_dict, ac_dict, ci_dict, vuln_data, org_uid, r, d, asn, unverified
):  # pylint: disable=R0913
    """Check if a CVE is verified."""
    v = vulns[cve]
    if v["verified"]:
        re = search_circl(cve)
        r_json = re.json()
        if r_json is not None:
            summary = r_json.get("summary")
            product = r_json.get("vulnerable_product")
            attack_vector = r_json.get("access", {}).get("vector")
            av = av_dict.get(attack_vector)
            attack_complexity = r_json.get("access", {}).get("complexity")
            ac = ac_dict.get(attack_complexity)
            conf_imp = r_json.get("impact", {}).get("confidentiality")
            ci = ci_dict.get(conf_imp)
            int_imp = r_json.get("impact", {}).get("integrity")
            ii = ci_dict.get(int_imp)
            avail_imp = r_json.get("impact", {}).get("availability")
            ai = ci_dict.get(avail_imp)
            cvss = r_json.get("cvss")
            if cvss == 10:
                severity = "Critical"
            elif cvss >= 7:
                severity = "High"
            elif cvss >= 4:
                severity = "Medium"
            elif cvss > 0:
                severity = "Low"
            else:
                severity = None
        vuln_data.append(
            {
                "ac_description": ac or "",
                "ai_description": ai or "",
                "asn": asn,
                "attack_complexity": attack_complexity or "",
                "attack_vector": attack_vector or "",
                "av_description": av or "",
                "availability_impact": avail_imp or "",
                "ci_description": ci or "",
                "confidentiality_impact": conf_imp or "",
                "cve": cve,
                "cvss": cvss or None,
                "domains": r["domains"],
                "hostnames": r["hostnames"],
                "ii_Description": ii or "",
                "integrity_impact": int_imp or "",
                "ip": r["ip_str"],
                "isn": r["isp"],
                "mitigation": None,
                "name": None,
                "organization": r["org"],
                "organizations_uid": org_uid,
                "port": d["port"],
                "potential_vulns": None,
                "product": product or "",
                "protocol": d["_shodan"]["module"],
                "server": None,
                "severity": severity or "",
                "summary": summary or "",
                "tags": r["tags"],
                "timestamp": d["timestamp"],
                "type": None,
                "is_verified": True,
            }
        )
    else:
        unverified.append(cve)

    return unverified, vuln_data


def get_shodan_dicts():
    """Build Shodan dictionaries that hold definitions and naming conventions."""
    risky_ports = [
        "ftp",
        "telnet",
        "http",
        "smtp",
        "pop3",
        "imap",
        "netbios",
        "snmp",
        "ldap",
        "smb",
        "sip",
        "rdp",
        "vnc",
        "kerberos",
    ]
    name_dict = {
        "ftp": "File Transfer Protocol",
        "telnet": "Telnet",
        "http": "Hypertext Transfer Protocol",
        "smtp": "Simple Mail Transfer Protocol",
        "pop3": "Post Office Protocol 3",
        "imap": "Internet Message Access Protocol",
        "netbios": "Network Basic Input/Output System",
        "snmp": "Simple Network Management Protocol",
        "ldap": "Lightweight Directory Access Protocol",
        "smb": "Server Message Block",
        "sip": "Session Initiation Protocol",
        "rdp": "Remote Desktop Protocol",
        "kerberos": "Kerberos",
    }
    risk_dict = {
        "ftp": "FTP",
        "telnet": "Telnet",
        "http": "HTTP",
        "smtp": "SMTP",
        "pop3": "POP3",
        "imap": "IMAP",
        "netbios": "NetBIOS",
        "snmp": "SNMP",
        "ldap": "LDAP",
        "smb": "SMB",
        "sip": "SIP",
        "rdp": "RDP",
        "vnc": "VNC",
        "kerberos": "Kerberos",
    }
    # Create dictionaries for CVSSv2 vector definitions using https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator
    av_dict = {
        "NETWORK": "A vulnerability exploitable with network access means the vulnerable software is bound to the network stack and the attacker does not require local network access or local access. Such a vulnerability is often termed “remotely exploitable”. An example of a network attack is an RPC buffer overflow.",
        "ADJACENT_NETWORK": "A vulnerability exploitable with adjacent network access requires the attacker to have access to either the broadcast or collision domain of the vulnerable software. Examples of local networks include local IP subnet, Bluetooth, IEEE 802.11, and local Ethernet segment.",
        "LOCAL": "A vulnerability exploitable with only local access requires the attacker to have either physical access to the vulnerable system or a local (shell) account. Examples of locally exploitable vulnerabilities are peripheral attacks such as Firewire/USB DMA attacks, and local privilege escalations (e.g., sudo).",
    }
    ac_dict = {
        "LOW": "Specialized access conditions or extenuating circumstances do not exist. The following are examples: The affected product typically requires access to a wide range of systems and users, possibly anonymous and untrusted (e.g., Internet-facing web or mail server). The affected configuration is default or ubiquitous. The attack can be performed manually and requires little skill or additional information gathering. The 'race condition' is a lazy one (i.e., it is technically a race but easily winnable).",
        "MEDIUM": "The access conditions are somewhat specialized; the following are examples: The attacking party is limited to a group of systems or users at some level of authorization, possibly untrusted. Some information must be gathered before a successful attack can be launched. The affected configuration is non-default, and is not commonly configured (e.g., a vulnerability present when a server performs user account authentication via a specific scheme, but not present for another authentication scheme). The attack requires a small amount of social engineering that might occasionally fool cautious users (e.g., phishing attacks that modify a web browser’s status bar to show a false link, having to be on someone’s “buddy” list before sending an IM exploit).",
        "HIGH": "Specialized access conditions exist. For example, in most configurations, the attacking party must already have elevated privileges or spoof additional systems in addition to the attacking system (e.g., DNS hijacking). The attack depends on social engineering methods that would be easily detected by knowledgeable people. For example, the victim must perform several suspicious or atypical actions. The vulnerable configuration is seen very rarely in practice. If a race condition exists, the window is very narrow.",
    }
    ci_dict = {
        "NONE": "There is no impact to the confidentiality of the system",
        "PARTIAL": "There is considerable informational disclosure. Access to some system files is possible, but the attacker does not have control over what is obtained, or the scope of the loss is constrained. An example is a vulnerability that divulges only certain tables in a database.",
        "COMPLETE": "There is total information disclosure, resulting in all system files being revealed. The attacker is able to read all of the system's data (memory, files, etc.).",
    }
    return risky_ports, name_dict, risk_dict, av_dict, ac_dict, ci_dict


def insert_shodan_assets(data, organization):
    """Insert Shodan data into the shodan_assets table using bulk operations."""
    if not data:
        return "0 records created in the shodan_assets table"

    # --- Preload IPs (already a win you added) ---
    ips = {
        ip.ip: ip
        for ip in Ip.objects.filter(
            organization=organization,
            ip__in={row["ip"] for row in data},
        )
    }

    # --- Preload existing assets for idempotency ---
    existing_assets = {
        (
            asset.ip_id,
            int(asset.port),
            asset.protocol.lower(),
        ): asset
        for asset in ShodanAssets.objects.filter(
            organization=organization,
            ip__in=ips.values(),
        )
    }

    to_create = []
    to_update = []
    create_cnt = 0

    with transaction.atomic():
        for row in data:
            row_dict = row if isinstance(row, dict) else row.__dict__

            ip_instance = ips.get(row_dict["ip"])
            if not ip_instance:
                continue

            key = (
                ip_instance.id,
                int(row_dict["port"]),
                row_dict["protocol"].lower(),
            )

            mdl_asset_fields = {
                "asn": row_dict.get("asn"),
                "domains": row_dict.get("domains", []),
                "hostnames": row_dict.get("hostnames", []),
                "isp": row_dict.get("isn"),
                "organization_name": row_dict.get("organization"),
                "product": row_dict.get("product"),
                "server": row_dict.get("server"),
                "tags": row_dict.get("tags", []),
                "country_code": row_dict.get("country_code"),
                "location": row_dict.get("location"),
                "data_source": row_dict.get("data_source_uid"),
                "timestamp": parse_utc_timestamp(row_dict["timestamp"]),
                "ip_string": row_dict["ip"],
            }

            if key in existing_assets:
                # --- Update existing object ---
                asset = existing_assets[key]
                for field, value in mdl_asset_fields.items():
                    setattr(asset, field, value)
                to_update.append(asset)
            else:
                # --- Create new object ---
                to_create.append(
                    ShodanAssets(
                        organization=organization,
                        ip=ip_instance,
                        port=row_dict["port"],
                        protocol=row_dict["protocol"],
                        **mdl_asset_fields,
                    )
                )
                create_cnt += 1

        # --- Bulk DB writes ---
        if to_create:
            ShodanAssets.objects.bulk_create(
                to_create,
                batch_size=500,
            )

        if to_update:
            ShodanAssets.objects.bulk_update(
                to_update,
                fields=list(mdl_asset_fields.keys()),
                batch_size=500,
            )

    return f"{create_cnt} records created in the shodan_assets table"


def insert_shodan_vulns(data, organization):
    """Insert Shodan vulnerability data into the credential_exposures table."""
    if not data:
        return "0 records created in the credential_exposures table"

    create_cnt = 0

    # --- Preload IPs ---
    ips = {
        ip.ip: ip
        for ip in Ip.objects.filter(
            organization=organization,
            ip__in={row["ip"] for row in data},
        )
    }

    # --- Preload existing vulns for idempotency ---
    existing_vulns = {
        (
            vuln.ip_id,
            int(vuln.port),
            vuln.protocol.lower(),
        ): vuln
        for vuln in ShodanVulns.objects.filter(
            organization=organization,
            ip__in=ips.values(),
        )
    }

    to_create = []
    to_update = []

    with transaction.atomic():
        for row in data:
            row_dict = row if isinstance(row, dict) else row.__dict__

            ip_instance = ips.get(row_dict["ip"])
            if not ip_instance:
                continue

            key = (
                ip_instance.id,
                int(row_dict["port"]),
                row_dict["protocol"].lower(),
            )

            mdl_vuln_data = {
                "organization_name": row_dict.get("organization"),
                "cve": row_dict.get("cve"),
                "severity": row_dict.get("severity"),
                "cvss": row_dict.get("cvss"),
                "summary": row_dict.get("summary"),
                "product": row_dict.get("product"),
                "attack_vector": row_dict.get("attack_vector"),
                "av_description": row_dict.get("av_description"),
                "attack_complexity": row_dict.get("attack_complexity"),
                "ac_description": row_dict.get("ac_description"),
                "confidentiality_impact": row_dict.get("confidentiality_impact"),
                "ci_description": row_dict.get("ci_description"),
                "integrity_impact": row_dict.get("integrity_impact"),
                "ii_description": row_dict.get("ii_description"),
                "availability_impact": row_dict.get("availability_impact"),
                "ai_description": row_dict.get("ai_description"),
                "tags": row_dict.get("tags"),
                "domains": row_dict.get("domains"),
                "hostnames": row_dict.get("hostnames"),
                "isp": row_dict.get("isn"),
                "asn": row_dict.get("asn"),
                "data_source": row_dict.get("data_source_uid"),
                "type": row_dict.get("type"),
                "name": row_dict.get("name"),
                "potential_vulns": row_dict.get("potential_vulns"),
                "mitigation": row_dict.get("mitigation"),
                "server": row_dict.get("server"),
                "is_verified": row_dict.get("is_verified"),
                "banner": row_dict.get("banner"),
                "version": row_dict.get("version"),
                "cpe": row_dict.get("cpe"),
                "timestamp": parse_utc_timestamp(row_dict["timestamp"]),
                "ip_string": row_dict["ip"],
            }

            if key in existing_vulns:
                # --- Update existing vuln ---
                vuln = existing_vulns[key]
                for field, value in mdl_vuln_data.items():
                    setattr(vuln, field, value)
                to_update.append(vuln)
            else:
                # --- Create new vuln ---
                to_create.append(
                    ShodanVulns(
                        organization=organization,
                        ip=ip_instance,
                        port=row_dict["port"],
                        protocol=row_dict["protocol"],
                        **mdl_vuln_data,
                    )
                )
                create_cnt += 1

        # --- Bulk DB writes ---
        if to_create:
            ShodanVulns.objects.bulk_create(
                to_create,
                batch_size=500,
            )

        if to_update:
            ShodanVulns.objects.bulk_update(
                to_update,
                fields=list(mdl_vuln_data.keys()),
                batch_size=500,
            )

    return f"{create_cnt} records created in the credential_exposures table"

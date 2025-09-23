"""VS Vuln Scan Helper."""

# Standard Python Libraries
from collections import Counter
from ipaddress import ip_network
import logging
import os
from typing import Dict

# Third-Party Libraries
from django.db import models
from django.db.models import Count, ExpressionWrapper, F, FloatField, Max, Min, Q, Sum
from django.db.models.functions import Power
from django.utils import timezone
from xfd_api.tasks.utils.datetime_utils import safe_fromisoformat
from xfd_api.tasks.utils.mdl_insert_utils import (
    save_cve_to_datalake,
    save_ip_to_datalake,
)
from xfd_api.tasks.utils.query_redshift import fetch_from_redshift
from xfd_api.utils.hash import hash_ip
from xfd_api.utils.scan_utils.alerting import IngestionError
from xfd_mini_dl.models import (
    Cidr,
    Organization,
    Ticket,
    Vulnerability,
    VulnScan,
    VulnScanSummary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="vuln_scanning_sync.log",
)
LOGGER = logging.getLogger(__name__)
SCAN_NAME = "VulnScanningSync"
IS_LOCAL = os.getenv("IS_LOCAL")


def fetch_vuln_scans_from_redshift(ps_start_dt, ps_end_dt, org_id_dict):
    """Fetch vuln_scans from redshift."""
    LOGGER.info("Started processing vulnerability scans...")
    # Query with frozen window
    vuln_scans = fetch_from_redshift(
        f"""
        SELECT *
        FROM vmtableau.vuln_scans
        WHERE time >= '{ps_start_dt.strftime('%Y-%m-%d %H:%M:%S')}'
        AND time < '{ps_end_dt.strftime('%Y-%m-%d %H:%M:%S')}'
        """  # nosec B608
    )
    LOGGER.info("Fetched %d vulnerability scans from Redshift", len(vuln_scans))
    if vuln_scans:
        process_vulnerability_scans(vuln_scans, org_id_dict)
        LOGGER.info("Finished processing vulnerability scans")


def process_vulnerability_scans(vuln_scans, org_id_dict):
    """Process and save vulnerability scans."""
    for vuln in vuln_scans:
        try:
            owner_id = org_id_dict.get(vuln.get("owner"))
            ip_id = (
                save_ip_to_datalake(
                    {
                        "ip": vuln["ip"],
                        "ip_hash": hash_ip(vuln["ip"]),
                        "organization": owner_id,
                    }
                )
                if vuln.get("ip")
                else None
            )
            cve = (
                save_cve_to_datalake({"name": vuln["cve"]}) if vuln.get("cve") else None
            )
            vuln_scan_dict = build_vuln_scan_dict(vuln, owner_id, ip_id, cve)
            try:
                save_vuln_scan(vuln_scan_dict)
            except Exception as e:
                LOGGER.exception("Error saving vulnerability scan: %s", e)
                # Raise to catch in the outer block
                raise e
        except Exception as e:
            LOGGER.exception("Error processing Vulnerability Scan: %s", e)
            raise IngestionError(
                SCAN_NAME, str(e), "Failed processing vulnerability scans"
            ) from e


def build_vuln_scan_dict(vuln, owner_id, ip_id, cve):
    """Construct a vulnerability scan dictionary."""
    return {
        "id": vuln.get("_id"),
        "cert_id": vuln.get("cert", None),
        "cpe": vuln.get("cpe", None),
        "cve_string": vuln.get("cve", None),
        "cve": cve,
        "cvss_base_score": vuln.get("cvss_base_score", None),
        "cvss_temporal_score": vuln.get("cvss_temporal_score", None),
        "cvss_temporal_vector": vuln.get("cvss_temporal_vector", None),
        "cvss_vector": vuln.get("cvss_vector", None),
        "description": vuln.get("description", None),
        "exploit_available": vuln.get("exploit_available", None),
        "exploitability_ease": vuln.get("exploit_ease", None),
        "ip_string": vuln.get("ip", None),
        "ip": ip_id if ip_id else None,
        "latest": vuln.get("latest", None),
        "owner": vuln.get("owner", None),
        "osvdb_id": vuln.get("osvdb", None),
        "organization_id": owner_id,
        "patch_publication_timestamp": safe_fromisoformat(
            vuln.get("patch_publication_date", None)
        ),
        "cisa_known_exploited": safe_fromisoformat(
            vuln.get("cisa-known-exploited", None)
        ),
        "port": vuln.get("port", None),
        "port_protocol": vuln.get("protocol", None),
        "risk_factor": vuln.get("risk_factor", None),
        "script_version": vuln.get("script_version", None),
        "see_also": vuln.get("see_also", None),
        "service": vuln.get("service", None),
        "severity": vuln.get("severity"),
        "solution": vuln.get("solution", None),
        "source": vuln.get("source", None),
        "synopsis": vuln.get("synopsis", None),
        "vuln_detection_timestamp": safe_fromisoformat(vuln.get("time")),
        "vuln_publication_timestamp": safe_fromisoformat(
            vuln.get("vuln_publication_timestamp")
        ),
        "xref": vuln.get("xref", None),
        "cwe": vuln.get("cwe", None),
        "bid": vuln.get("bid", None),
        "exploited_by_malware": bool(vuln.get("exploited_by_malware", None)),
        "thorough_tests": bool(vuln.get("thorough_tests", None)),
        "cvss_score_rationale": vuln.get("cvss_score_rationale", None),
        "cvss_score_source": vuln.get("cvss_score_source", None),
        "cvss3_base_score": vuln.get("cvss3_base_score", None),
        "cvss3_vector": vuln.get("cvss3_vector", None),
        "cvss3_temporal_vector": vuln.get("cvss3_temporal_vector", None),
        "cvss3_temporal_score": vuln.get("cvss3_temporal_score", None),
        "asset_inventory": bool(vuln.get("asset_inventory", None)),
        "plugin_id": vuln.get("plugin_id", None),
        "plugin_modification_date": safe_fromisoformat(
            vuln.get("plugin_modification_date", None)
        ),
        "plugin_publication_date": safe_fromisoformat(
            vuln.get("plugin_publication_date", None)
        ),
        "plugin_name": vuln.get("plugin_name", None),
        "plugin_type": vuln.get("plugin_type", None),
        "plugin_family": vuln.get("plugin_family", None),
        "f_name": vuln.get("fname", None),
        "cisco_bug_id": vuln.get("cisco-bug-id", None),
        "cisco_sa": vuln.get("cisco-sa", None),
        "plugin_output": vuln.get("plugin_output", None),
        "other_findings": {},
    }


def truncate_charfields(model_cls, data_dict):
    """Trim or stringify charfields in the given data dict to their model-defined max_length."""
    for field in model_cls._meta.fields:
        if isinstance(field, models.CharField):
            val = data_dict.get(field.name)
            if val is None:
                continue
            if not isinstance(val, str):
                val = str(val)
            if field.max_length and len(val) > field.max_length:
                LOGGER.warning(
                    "Truncating field %s: %d → %d",
                    field.name,
                    len(val),
                    field.max_length,
                )
                val = val[: field.max_length]
            data_dict[field.name] = val


def save_vuln_scan(vuln_scan: Dict) -> str:
    """Save a Vulnerability Scan record to the data lake.

    Args:
        vuln_scan (dict): A dictionary containing vulnerability scan data.

    Returns:
        str: The ID of the inserted/updated record.
    """
    id = vuln_scan.get("id")
    del vuln_scan["id"]
    truncate_charfields(VulnScan, vuln_scan)
    if isinstance(id, str):
        id = id.replace("ObjectId('", "").replace("')", "")

    vuln_scan_obj, created = VulnScan.objects.update_or_create(
        id=id, defaults=vuln_scan
    )

    return str(vuln_scan_obj.id)


def create_vuln_scan_summary(summary_date=None):
    """Fill vuln_scan_summary table for todays date."""
    if summary_date is None:
        summary_date = timezone.now().date()

    for org in Organization.objects.all():
        # Base queryset for this org
        all_org_tickets = Ticket.objects.filter(organization=org)
        open_tickets = all_org_tickets.filter(is_open=True)
        included = open_tickets.filter(
            false_positive__in=[False, None], vuln_source="nessus"
        )

        if not included.exists():
            VulnScanSummary.objects.update_or_create(
                summary_date=summary_date,
                organization=org,
                defaults={
                    "enrolled_in_vs_timestamp": org.enrolled_in_vs_timestamp,
                    "start_date": None,
                    "end_date": None,
                    "assets_owned_count": get_asset_owned_count(org),
                    "false_positive_count": 0,
                    "vulnerable_host_count": 0,
                    "unique_service_count": 0,
                    "risky_services_count": 0,
                    "unsupported_software_count": 0,
                    "unique_os_count": 0,
                    "low_severity_count": 0,
                    "medium_severity_count": 0,
                    "high_severity_count": 0,
                    "critical_severity_count": 0,
                    "unique_low_severity_count": 0,
                    "unique_medium_severity_count": 0,
                    "unique_high_severity_count": 0,
                    "unique_critical_severity_count": 0,
                    "low_kev_count": 0,
                    "medium_kev_count": 0,
                    "high_kev_count": 0,
                    "critical_kev_count": 0,
                    "critical_max_age": None,
                    "high_max_age": None,
                    "medium_max_age": None,
                    "low_max_age": None,
                    "kev_max_age": None,
                    "critical_kev_max_age": None,
                    "high_kev_max_age": None,
                    "medium_kev_max_age": None,
                    "low_kev_max_age": None,
                    "one_to_five_vulns_count": 0,
                    "six_to_nine_vulns_count": 0,
                    "ten_plus_vulns_count": 0,
                    "top_5_occurring_cves": [],
                    "top_5_occurring_kevs": [],
                    "included_tickets": {},
                    "top_5_risky_hosts": {},
                },
            )
            continue  # Skip orgs with no valid tickets

        start_date = included.aggregate(Min("updated_timestamp"))[
            "updated_timestamp__min"
        ]
        end_date = included.aggregate(Max("updated_timestamp"))[
            "updated_timestamp__max"
        ]

        # Severity logic using cvss_severity
        severity_map = {1: "low", 2: "medium", 3: "high", 4: "critical"}
        severity_counts = {
            f"{name}_severity_count": included.filter(cvss_severity=level).count()
            for level, name in severity_map.items()
        }
        # TODO confirm if the distinct field should be id and not ip_string
        unique_sev_counts = {
            f"unique_{name}_severity_count": included.filter(cvss_severity=level)
            .values("vuln_source_id")
            .distinct()
            .count()
            for level, name in severity_map.items()
        }

        # KEV by severity
        kev_counts = {
            f"{name}_kev_count": included.filter(
                is_kev=True, cvss_severity=level
            ).count()
            for level, name in severity_map.items()
        }

        def max_ticket_life(qs):
            """Calculate max ticket life for the passed query."""
            return max(
                (
                    (u - o).days
                    for o, u in qs.values_list("opened_timestamp", "updated_timestamp")
                    if o and u
                ),
                default=None,
            )

        critical_max = max_ticket_life(included.filter(cvss_severity=4))
        high_max = max_ticket_life(included.filter(cvss_severity=3))
        medium_max = max_ticket_life(included.filter(cvss_severity=2))
        low_max = max_ticket_life(included.filter(cvss_severity=1))
        kev_max = max_ticket_life(included.filter(is_kev=True))
        critical_kev_max = max_ticket_life(
            included.filter(is_kev=True, cvss_severity=4)
        )
        high_kev_max = max_ticket_life(included.filter(is_kev=True, cvss_severity=3))
        medium_kev_max = max_ticket_life(included.filter(is_kev=True, cvss_severity=2))
        low_kev_max = max_ticket_life(included.filter(is_kev=True, cvss_severity=1))

        # Host vuln distribution
        ip_counts = Counter(included.values_list("ip_string", flat=True))
        one_to_five = sum(1 for c in ip_counts.values() if 1 <= c <= 5)
        six_to_nine = sum(1 for c in ip_counts.values() if 6 <= c <= 9)
        ten_plus = sum(1 for c in ip_counts.values() if c >= 10)

        # Filtered and grouped by CVE string
        top_cves_qs = (
            included.filter(~Q(cve_string__isnull=True), ~Q(cve_string=""))
            .values("cve_string")
            .annotate(
                count=Count("ip_string"),
                cvss_base_score=Max(
                    "cvss_base_score"
                ),  # or Avg if you want to average across tickets
                severity=Max(
                    "cvss_severity"
                ),  # assuming severity is consistent across same CVE
                vuln_name=Max("vuln_name"),
            )
            .order_by("-count")[:5]
        )

        top_5_occurring_cves = [
            {
                "cve_string": cve["cve_string"],
                "vuln_name": cve["vuln_name"],
                "cvss_base_score": float(cve["cvss_base_score"])
                if cve["cvss_base_score"] is not None
                else None,
                "severity_string": severity_map.get(int(cve["severity"]), "unknown")
                if cve["severity"] is not None
                else "unknown",
                "count": cve["count"],
            }
            for cve in top_cves_qs
        ]

        # Same logic but filtered for KEVs
        top_kevs_qs = (
            included.filter(is_kev=True)
            .filter(~Q(cve_string__isnull=True), ~Q(cve_string=""))
            .values("cve_string")
            .annotate(
                count=Count("ip_string"),
                cvss_base_score=Max("cvss_base_score"),
                severity=Max("cvss_severity"),
                vuln_name=Max("vuln_name"),
            )
            .order_by("-count")[:5]
        )

        top_5_occurring_kevs = [
            {
                "cve_string": kev["cve_string"],
                "vuln_name": kev["vuln_name"],
                "cvss_base_score": float(kev["cvss_base_score"])
                if kev["cvss_base_score"] is not None
                else None,
                "severity_string": severity_map.get(int(kev["severity"]), "unknown")
                if kev["severity"] is not None
                else "unknown",
                "count": kev["count"],
            }
            for kev in top_kevs_qs
        ]
        # Top 5 risky hosts by severity breakdown
        tickets = Ticket.objects.filter(
            organization=org,
            is_open=True,
            cvss_base_score__isnull=False,
            ip_string__isnull=False,
            vuln_source="nessus",
            false_positive__in=[False, None],
        )

        # Base RRS score expression: (cvss_base_score^7) / 1,000,000
        weighted_expr = ExpressionWrapper(
            Power(F("cvss_base_score"), 7) / 1000000, output_field=FloatField()
        )

        risky_host_qs = (
            tickets.values("ip_string")
            .annotate(
                total=Count("id"),
                low=Count("id", filter=Q(cvss_severity=1)),
                medium=Count("id", filter=Q(cvss_severity=2)),
                high=Count("id", filter=Q(cvss_severity=3)),
                critical=Count("id", filter=Q(cvss_severity=4)),
                weighted=Sum(weighted_expr),
                sample_ticket_id=Min("id"),
            )
            .order_by("-weighted")[:5]
        )

        ticket_ids = [str(item["sample_ticket_id"]) for item in risky_host_qs]

        # Build a mapping from ticket_id → domain_id
        vuln_domain_map = {
            str(v.id): str(v.domain_id)
            for v in Vulnerability.objects.filter(id__in=ticket_ids).only(
                "id", "domain_id"
            )
        }
        # Convert to dictionary for JSONField
        top_5_hosts = {
            item["ip_string"]: {
                "total": item["total"],
                "low": item["low"],
                "medium": item["medium"],
                "high": item["high"],
                "critical": item["critical"],
                "rrs": round(item["weighted"], 2)
                if item["weighted"] is not None
                else 0,
                "domain_id": vuln_domain_map.get(str(item["sample_ticket_id"])),
            }
            for item in risky_host_qs
        }

        VulnScanSummary.objects.update_or_create(
            summary_date=summary_date,
            organization=org,
            defaults={
                "enrolled_in_vs_timestamp": org.enrolled_in_vs_timestamp,
                "start_date": start_date,
                "end_date": end_date,
                "assets_owned_count": get_asset_owned_count(org),
                "false_positive_count": all_org_tickets.filter(
                    false_positive=True,
                    is_open=True,
                    vuln_source="nessus",
                ).count(),
                "vulnerable_host_count": included.values("ip_string")
                .distinct()
                .count(),
                "unique_service_count": open_tickets.filter(vuln_source="nmap")
                .values("vuln_port")
                .distinct()
                .count(),
                "risky_services_count": get_risky_services_count(org),
                "unsupported_software_count": included.filter(
                    vuln_name__icontains="unsupported"
                )
                .values("ip_string")
                .distinct()
                .count(),
                "unique_os_count": open_tickets.exclude(operating_system__isnull=True)
                .values("operating_system")
                .distinct()
                .count(),
                **severity_counts,
                **unique_sev_counts,
                **kev_counts,
                "critical_max_age": critical_max,
                "high_max_age": high_max,
                "medium_max_age": medium_max,
                "low_max_age": low_max,
                "kev_max_age": kev_max,
                "critical_kev_max_age": critical_kev_max,
                "high_kev_max_age": high_kev_max,
                "medium_kev_max_age": medium_kev_max,
                "low_kev_max_age": low_kev_max,
                "one_to_five_vulns_count": one_to_five,
                "six_to_nine_vulns_count": six_to_nine,
                "ten_plus_vulns_count": ten_plus,
                "top_5_occurring_cves": top_5_occurring_cves,
                "top_5_occurring_kevs": top_5_occurring_kevs,
                "included_tickets": {
                    str(ticket.id): {
                        "severity": severity_map.get(ticket.cvss_severity, "unknown"),
                        "is_kev": ticket.is_kev,
                    }
                    for ticket in included.only("id", "cvss_severity", "is_kev")
                },
                "top_5_risky_hosts": top_5_hosts,
            },
        )


def get_asset_owned_count(org):
    """Return count of IPs in the reported CIDRs for passed org."""
    # Get only CIDRs currently associated with the org via CidrOrgs.current=True
    cidrs = Cidr.objects.filter(
        cidrorgs__organization=org, cidrorgs__current=True, network__isnull=False
    ).distinct()

    if not cidrs.exists():
        LOGGER.warning("No CIDRs found for organization ID: %s (%s)", org.id, org.name)

    total_ips = 0
    for cidr in cidrs:
        try:
            network = ip_network(str(cidr.network), strict=False)
            total_ips += network.num_addresses
        except (ValueError, TypeError) as e:
            LOGGER.warning(
                "Invalid CIDR '%s' for organization ID: %s (%s) — %s",
                getattr(cidr, "network", None),
                org.id,
                org.name,
                str(e),
            )
        except Exception as e:
            LOGGER.warning(
                "Unexpected error while processing CIDR for org ID: %s (%s) — %s",
                org.id,
                org.name,
                str(e),
            )

    return total_ips


def get_risky_services_count(org):
    """Return count of risky services for passed org."""
    return (
        Ticket.objects.filter(
            organization=org,
            is_risky=True,
            is_open=True,
            vuln_port__isnull=False,
        )
        .values("ip_string", "vuln_port")
        .distinct()
        .count()
    )

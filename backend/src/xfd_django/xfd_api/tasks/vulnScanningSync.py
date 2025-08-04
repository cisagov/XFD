"""Task for synchronizing vulnerability scanning data.

This module handles fetching, processing, and saving vulnerability scans,
port scans, hosts, and tickets from Redshift into the Django models.
"""

# Standard Python Libraries
from collections import Counter

# Uncomment the above to run the script standalone
import datetime
from ipaddress import IPv4Network, IPv6Network, ip_network
import json
import logging
import os
import traceback

# Third-Party Libraries
from dateutil import parser  # type: ignore
from django.db.models import Count, ExpressionWrapper, F, FloatField, Max, Min, Q, Sum
from django.db.models.functions import Power
from django.utils import timezone
import psycopg2
import requests
from xfd_api.helpers.regionStateMap import REGION_STATE_MAP
from xfd_api.tasks.refresh_material_views import handler as refresh_materialized_views
from xfd_api.utils.chunk import chunk_list_by_bytes
from xfd_api.utils.csv_utils import create_checksum
from xfd_api.utils.hash import hash_ip
from xfd_api.utils.scan_utils.alerting import (
    IngestionError,
    QueryError,
    ScanExecutionError,
    SyncError,
)
from xfd_api.utils.scan_utils.vuln_scanning_sync_utils import (  # fill_cidr_live_ips,
    enforce_latest_flag_port_scan,
    fetch_orgs_and_relations,
    fill_cidr_live_ips_bulk_update,
    get_latest_os_type,
    load_test_data,
    save_cve_to_datalake,
    save_ip_to_datalake,
    save_organization_to_mdl,
    save_port_scan_to_datalake,
    save_ticket_to_datalake,
    save_vuln_scan,
)
from xfd_mini_dl.models import (
    Cidr,
    HostSummary,
    NMIServiceGroup,
    Organization,
    PortScan,
    PortScanServiceSummary,
    PortScanSummary,
    RiskyServiceGroup,
    Sector,
    Ticket,
    Vulnerability,
    VulnScanSummary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="vuln_scanning_sync.log",
)
LOGGER = logging.getLogger(__name__)
IS_LOCAL = os.getenv("IS_LOCAL")
SCAN_NAME = "VulnScanningSync"

VS_PULL_DATE_RANGE = os.getenv("VS_PULL_DATE_RANGE", "2")


def handler(event):
    """Handle execution of the vulnerability scanning sync task.

    This function serves as the entry point for triggering the synchronization
    process. It calls the `main` function and returns the appropriate response
    based on the execution outcome.

    Args:
        event (dict): The event data that triggers the function.

    Returns:
        dict: Response containing the status code and message.
    """
    print("VS_PULL_DATE_RANGE: ", VS_PULL_DATE_RANGE)
    try:
        main()
        return {"status_code": 200, "body": "VS Sync completed successfully"}
    except Exception as e:
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e
        # LOGGER.info("Error occurred: %s", e)
        # return {"status_code": 500, "body": str(e)}


def query_redshift(query, params=None):
    """Execute a query on Redshift and return results as a list of dictionaries."""
    conn = psycopg2.connect(
        dbname=os.environ.get("REDSHIFT_DATABASE"),
        user=os.environ.get("REDSHIFT_USER"),
        password=os.environ.get("REDSHIFT_PASSWORD"),
        host=os.environ.get("REDSHIFT_HOST"),
        port=5439,
    )

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)  # <-- this avoids the IndexError
        results = cursor.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        raise QueryError(SCAN_NAME, str(e)) from e
    finally:
        cursor.close()
        conn.close()


def fetch_in_chunks(base_query: str, chunk_size: int = 5000):
    """Yield chunks of rows from Redshift using LIMIT/OFFSET pagination."""
    offset = 0
    while True:
        query = f"{base_query} LIMIT {chunk_size} OFFSET {offset}"
        chunk = fetch_from_redshift(query)
        if not chunk:
            break
        yield chunk
        offset += chunk_size


def main():  # pylint: disable=R0915
    """Execute the vulnerability scanning synchronization task."""
    LOGGER.info("Started VulnScanningSync scan...")

    # Load request data
    request_list = fetch_from_redshift("SELECT * FROM vmtableau.requests;")
    LOGGER.info("Fetched %d requests from Redshift", len(request_list))
    org_id_dict = process_orgs(request_list)
    LOGGER.info("Completed saving organizations to the LZ MDL.")

    # Process Vulnerability Scans
    LOGGER.info("Started processing vulnerability scans...")
    vuln_scans = fetch_from_redshift(
        f"SELECT * FROM vmtableau.vuln_scans WHERE time >= GETDATE() - INTERVAL '{VS_PULL_DATE_RANGE} days';"  # nosec B608
    )
    LOGGER.info("Fetched %d vulnerability scans from Redshift", len(vuln_scans))
    if vuln_scans:
        process_vulnerability_scans(vuln_scans, org_id_dict)
        LOGGER.info("Finished processing vulnerability scans")

    # Process Host Scans
    LOGGER.info("Started processing host scans...")
    create_daily_host_summary(org_id_dict)

    # Port Scans (Chunked)
    LOGGER.info("Started processing port scans...")
    base_query = (
        "SELECT * FROM vmtableau.port_scans "
        f"WHERE time >= GETDATE() - INTERVAL '{VS_PULL_DATE_RANGE} days'"  # nosec B608
    )

    total_processed = 0
    chunk_number = 1
    for chunk in fetch_in_chunks(base_query):
        LOGGER.info(
            "Processing port scan chunk #%d with %d rows", chunk_number, len(chunk)
        )
        process_port_scans(chunk, org_id_dict)
        total_processed += len(chunk)
        chunk_number += 1

    if total_processed == 0:
        LOGGER.warning(
            f"No port scans found in Redshift for the last {VS_PULL_DATE_RANGE} days."
        )
    else:
        LOGGER.info(
            "Processed %d total port scans across %d chunks",
            total_processed,
            chunk_number - 1,
        )
        # Set latest flag
        LOGGER.info("Setting port scans latest flag")
        enforce_latest_flag_port_scan()

    # Fill CIDR live IPs
    fill_cidr_live_ips_bulk_update()

    # Send organizations to the DMZ MDL
    send_organizations_to_dmz()

    # Process Tickets (Chunked)
    LOGGER.info("Started processing tickets...")
    base_query = (
        "SELECT * FROM vmtableau.tickets "
        f"WHERE last_change >= GETDATE() - INTERVAL '{VS_PULL_DATE_RANGE} days'"  # nosec B608
    )

    total_processed = 0
    chunk_number = 1
    for chunk in fetch_in_chunks(base_query):
        LOGGER.info(
            "Processing ticket chunk #%d with %d rows", chunk_number, len(chunk)
        )
        process_tickets(chunk, org_id_dict)
        total_processed += len(chunk)
        chunk_number += 1

    if total_processed == 0:
        LOGGER.warning(
            f"No tickets found in Redshift for the last {VS_PULL_DATE_RANGE} days."
        )
    else:
        LOGGER.info(
            "Processed %d total tickets across %d chunks",
            total_processed,
            chunk_number - 1,
        )
        LOGGER.info("Finished processing tickets")

    # 🔁 REFRESH MATERIALIZED VIEWS BEFORE CREATING SUMMARIES
    LOGGER.info("Refreshing materialized views before creating summaries...")
    # Create or refresh materialized views
    result = refresh_materialized_views({})
    LOGGER.info(result)
    LOGGER.info("Finished refreshing materialized views")

    # ✅ Create summaries with individual error handling
    LOGGER.info("Creating port scan summary...")
    try:
        create_port_scan_summary()
        LOGGER.info("Finished port scan summary")
    except Exception as e:
        LOGGER.error("Failed to create port scan summary: %s", e, exc_info=True)

    LOGGER.info("Creating port scan service summaries...")
    try:
        create_port_scan_service_summaries()
        LOGGER.info("Finished port scan service summaries")
    except Exception as e:
        LOGGER.error(
            "Failed to create port scan service summaries: %s", e, exc_info=True
        )

    LOGGER.info("Creating vulnerability scan summary...")
    try:
        create_vuln_scan_summary()
        LOGGER.info("Finished vulnerability scan summary")
    except Exception as e:
        LOGGER.error(
            "Failed to create vulnerability scan summary: %s", e, exc_info=True
        )


def detect_data_set(query):
    """Detect the data set from the query."""
    if "requests" in query:
        return "requests"
    if "vuln_scans" in query:
        return "vuln_scan"
    if "hosts" in query:
        return "hosts"
    if "tickets" in query:
        return "tickets"
    if "port_scans" in query:
        return "port_scans"
    return None


def fetch_from_redshift(query):
    """Fetch data from Redshift and log execution time."""
    if IS_LOCAL:
        data_set = detect_data_set(query)
        return load_test_data(data_set)
    try:
        start_time = datetime.datetime.now()
        result = query_redshift(query)
        end_time = datetime.datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        LOGGER.info(f"[Redshift] [{duration_seconds}s] [{len(result)} records] {query}")
        return result
    except Exception as e:
        LOGGER.info("Error fetching data from Redshift: %s", e)
        LOGGER.info("Erroneous query: %s", query)
        return []


def save_json_to_file(data, filename="test.json"):
    """Save JSON data to a file."""
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving JSON to file: {e}")


def send_organizations_to_dmz():
    """Fetch organizations and sync with the external API."""
    try:
        shaped_orgs = fetch_orgs_and_relations()
        if not shaped_orgs:
            return

        # 100_000 = 100 KB
        chunks = chunk_list_by_bytes(shaped_orgs, 100_000)
        for idx, chunk_info in enumerate(chunks):
            chunk = chunk_info["chunk"]
            bounds = chunk_info["bounds"]
            LOGGER.info(
                "Sending chunk %d - %d to sync API", bounds["start"], bounds["end"]
            )
            send_csv_to_sync(json.dumps(chunk), bounds)

    except Exception as e:
        LOGGER.error(
            "Error sending organizations to DMZ sync endpoint:\n%s",
            traceback.format_exc(),
        )
        print(e)
        raise SyncError(SCAN_NAME, str(e), "Error sending organizations to dmz") from e


def send_csv_to_sync(csv_data, bounds):
    """Send CSV data to /sync API."""
    body = {"data": csv_data}
    try:
        checksum = create_checksum(csv_data)
    except Exception as e:
        LOGGER.error("Error creating checksum: %s", e)
        return

    headers = {
        "x-checksum": checksum,
        "x-cursor": f"{bounds['start']}-{bounds['end']}",
        "Content-Type": "application/json",
        "Authorization": os.getenv("DMZ_API_KEY", ""),
    }
    try:
        response = requests.post(
            os.getenv("DMZ_SYNC_ENDPOINT") + "/sync",
            json=body,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        LOGGER.info("Successfully sent chunk to sync API")
    except requests.exceptions.HTTPError as http_err:
        try:
            error_data = response.json()
            error_detail = error_data.get("detail", error_data)
            print(http_err)
        except ValueError:
            error_detail = response.text
        LOGGER.error(
            "HTTPError sending chunk to sync API:\nStatus Code: %s\nDetail: %s\nHeaders: %s",
            response.status_code,
            error_detail,
            response.headers,
        )
    except Exception as e:
        LOGGER.error("Unexpected error sending chunk: %s", str(e))
        raise SyncError(
            SCAN_NAME,
            str(e),
        ) from e


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
                        "organization": {"id": owner_id},
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
                LOGGER.error("Error saving vulnerability scan: %s", e)
                print(traceback.format_exc())
                # Raise to catch in the outer block
                raise e
        except Exception as e:
            LOGGER.error("Error processing Vulnerability Scan: %s", e)
            print(traceback.format_exc())
            raise IngestionError(
                SCAN_NAME, str(e), "Failed processing vulnerability scans"
            ) from e


def safe_fromisoformat(date_input) -> datetime.datetime | None:
    """Safely convert input to timezone-aware datetime, or return None if invalid."""
    if isinstance(date_input, datetime.datetime):
        return (
            timezone.make_aware(date_input)
            if timezone.is_naive(date_input)
            else date_input
        )
    if isinstance(date_input, str):
        try:
            parsed = parser.parse(date_input)
            return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
        except Exception as e:
            LOGGER.warning(
                "Failed to parse datetime from string: %s | Error: %s", date_input, e
            )
            return None
    return None


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
        "description": vuln.get("description", None)[:255],
        "exploit_available": vuln.get("exploit_available", None),
        "exploitability_ease": vuln.get("exploit_ease", None),
        "ip_string": vuln.get("ip", None),
        "ip": ip_id if ip_id else None,
        "latest": vuln.get("latest", None),
        "owner": vuln.get("owner", None),
        "osvdb_id": vuln.get("osvdb", None),
        "organization": Organization.objects.get(id=owner_id),
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


def create_daily_host_summary(org_id_dict, summary_date=None):
    """Create host summary records directly from Redshift data."""
    if summary_date is None:
        summary_date = timezone.now().date()

    LOGGER.info("Starting host summary creation directly from Redshift...")

    redshift_query = """
        SELECT
            owner,
            MIN(last_change) AS start_date,
            MAX(last_change) AS end_date,
            SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) AS host_done_count,
            SUM(CASE WHEN status = 'WAITING' THEN 1 ELSE 0 END) AS host_waiting_count,
            SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) AS host_running_count,
            SUM(CASE WHEN status = 'READY' THEN 1 ELSE 0 END) AS host_ready_count,
            SUM(CASE WHEN POSITION('\"up\":true' IN json_serialize(state)) > 0 THEN 1 ELSE 0 END) AS up_host_count,
            SUM(CASE WHEN POSITION('\"up\":false' IN json_serialize(state)) > 0 THEN 1 ELSE 0 END) AS down_host_count,
            COUNT(DISTINCT ip) AS scanned_asset_count
        FROM vmtableau.hosts
        WHERE last_change >= GETDATE() - INTERVAL '100 days'
        GROUP BY owner;
    """

    summary_rows = fetch_from_redshift(redshift_query)

    if not summary_rows:
        LOGGER.warning("No host data found in Redshift to summarize.")
        return

    LOGGER.info("Fetched %d host summary records from Redshift", len(summary_rows))

    for row in summary_rows:
        try:
            owner = row["owner"]
            owner_id = org_id_dict.get(owner)

            if not owner_id:
                LOGGER.warning(
                    "No matching org_id found for owner %s; skipping.", owner
                )
                continue

            organization = Organization.objects.get(id=owner_id)

            HostSummary.objects.update_or_create(
                organization=organization,
                summary_date=summary_date,
                defaults={
                    "start_date": row["start_date"],
                    "end_date": row["end_date"],
                    "host_done_count": row["host_done_count"],
                    "host_waiting_count": row["host_waiting_count"],
                    "host_running_count": row["host_running_count"],
                    "host_ready_count": row["host_ready_count"],
                    "up_host_count": row["up_host_count"],
                    "down_host_count": row["down_host_count"],
                    "scanned_asset_count": row["scanned_asset_count"],
                },
            )
        except Organization.DoesNotExist:
            LOGGER.warning(
                "Organization ID %s not found in local DB; skipping.", owner_id
            )
        except Exception as e:
            LOGGER.error(
                "Error creating host summary for owner %s (mapped to %s): %s",
                owner,
                owner_id,
                e,
            )
            raise QueryError(
                SCAN_NAME, str(e), "Error creating daily host summary"
            ) from e

    LOGGER.info("Completed host summary creation from Redshift.")


def create_port_scan_summary(summary_date=None):
    """Create port summary record for each organization."""
    try:
        if summary_date is None:
            summary_date = timezone.now().date()

        for org in Organization.objects.all():
            scans = PortScan.objects.filter(
                organization=org,
                latest=True,  # only latest scans
                time_scanned__isnull=False,
                state="open",
            )

            if not scans.exists():
                continue

            aggregated = scans.aggregate(
                start_date=Min("time_scanned"),
                end_date=Max("time_scanned"),
                open_port_count=Count("id"),
                risky_port_count=Count(
                    "id", filter=Q(risky_service_group__isnull=False)
                ),
                nmi_service_count=Count(
                    "id", filter=Q(nmi_service_group__isnull=False)
                ),
                unique_ip_count=Count("ip_string", distinct=True),
                unique_service_count=Count("service_name", distinct=True),
            )

            risky_group_data = (
                scans.filter(risky_service_group__isnull=False)
                .values("risky_service_group")
                .annotate(count=Count("id"))
            )

            # Convert to dict: {group: count}
            risky_service_group_counts = {
                item["risky_service_group"]: item["count"] for item in risky_group_data
            }

            PortScanSummary.objects.update_or_create(
                organization=org,
                summary_date=summary_date,
                defaults={
                    "start_date": aggregated["start_date"],
                    "end_date": aggregated["end_date"],
                    "open_port_count": aggregated["open_port_count"],
                    "risky_port_count": aggregated["risky_port_count"],
                    "nmi_service_count": aggregated["nmi_service_count"],
                    "unique_ip_count": aggregated["unique_ip_count"],
                    "unique_service_count": aggregated["unique_service_count"],
                    "risky_service_group_counts": risky_service_group_counts,
                },
            )

    except Exception as e:
        print("Error creating port scan summary: {}".format(e))
        raise QueryError(SCAN_NAME, str(e), "Error creating port scan summary") from e


def create_port_scan_service_summaries(summary_date=None):
    """Fill the port scan service summary table."""
    try:
        if summary_date is None:
            summary_date = timezone.now().date()

        for org in Organization.objects.all():
            scans = PortScan.objects.filter(
                organization=org,
                latest=True,
                time_scanned__isnull=False,
                service_name__isnull=False,
            )

            if not scans.exists():
                continue

            # Group by service_name
            service_names = scans.values_list("service_name", flat=True).distinct()

            for service in service_names:
                service_scans = scans.filter(service_name=service)

                agg = service_scans.aggregate(
                    start_date=Min("time_scanned"),
                    end_date=Max("time_scanned"),
                    unique_ip_count=Count("ip_string", distinct=True),
                    unique_service_count=Count("service_name", distinct=True),
                )

                # Collect risky ports
                risky_ports_qs = service_scans.filter(risky_service_group__isnull=False)
                risky_ports = list(
                    risky_ports_qs.values_list("port", flat=True).distinct()
                )

                PortScanServiceSummary.objects.update_or_create(
                    organization=org,
                    summary_date=summary_date,
                    service_name=service,
                    defaults={
                        "start_date": agg["start_date"],
                        "end_date": agg["end_date"],
                        "unique_ip_count": agg["unique_ip_count"],
                        "unique_service_count": agg["unique_service_count"],
                        "risky_ports": risky_ports,
                    },
                )
    except Exception as e:
        print("Error creating port scan service summary: {}".format(e))
        raise QueryError(
            SCAN_NAME, str(e), "Error creating port scan service summary"
        ) from e


def process_tickets(tickets, org_id_dict):
    """Process and save ticket data."""
    # To-Do
    # Add fields to the Django model: is_kev, first_discovered, risky_service_group
    # Fields that don't exist in the data? OS
    for ticket in tickets:
        try:
            details = json.loads(ticket.get("details", "{}"))
            owner_id = org_id_dict.get(ticket["owner"])
            ip = (
                save_ip_to_datalake(
                    {
                        "ip": ticket["ip"],
                        "ip_hash": hash_ip(ticket["ip"]),
                        "organization": {"id": owner_id},
                    }
                )
                if ticket.get("ip")
                else None
            )
            cve = (
                save_cve_to_datalake({"name": details.get("cve")})
                if details.get("cve")
                else None
            )
            lon, lat = json.loads(ticket.get("loc", "[]"))
            time_closed_str = ticket.get("time_closed")
            time_opened_str = ticket.get("time_opened")
            is_risky = "Potentially Risky Service Detected:" in details.get("name", "")
            ticket_dict = {
                "id": ticket["_id"].replace("ObjectId('", "").replace("')", ""),
                "cve_string": details.get("cve"),
                "cve": cve,
                "cvss_base_score": details.get("cvss_base_score"),
                "cvss_version": details.get("cvss_version"),
                "vuln_name": details.get("name"),
                "cvss_score_source": details.get("score_source"),
                "cvss_severity": details.get("severity"),
                "vpr_score": details.get("vpr_score"),
                "false_positive": ticket.get("false_positive"),
                "ip_string": ticket.get("ip"),
                "ip": ip,
                "updated_timestamp": safe_fromisoformat(ticket.get("last_change")),
                "location_longitude": lon,
                "location_latitude": lat,
                "organization": Organization.objects.get(id=owner_id),
                "vuln_port": ticket.get("port"),
                "port_protocol": ticket.get("protocol"),
                "snapshots_bool": bool(ticket.get("snapshots", None)),
                "vuln_source": ticket.get("source"),
                "vuln_source_id": ticket.get("source_id"),
                "closed_timestamp": safe_fromisoformat(time_closed_str)
                if time_closed_str
                else None,
                "opened_timestamp": safe_fromisoformat(time_opened_str)
                if time_opened_str
                else None,
                "is_open": ticket.get("open"),
                "is_kev": details.get("kev"),
                "is_kev_ransomware": details.get("kev_ransomware"),
                "is_risky": is_risky,
                "service_name": details.get("service"),
                "operating_system": get_latest_os_type(ticket.get("ip"))
                if ticket.get("ip")
                else None,
            }
            events = json.loads(ticket.get("events", "[]"))
            save_ticket_to_datalake(ticket_dict, events, details)
        except Exception as e:
            print(
                f"Error processing ticket data: {e} - {owner_id} - {ticket.get('owner')}"
            )
            raise IngestionError(SCAN_NAME, str(e), "Failed processing tickets") from e


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
                default=0,
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


def process_port_scans(port_scans, org_id_dict):
    """Process and save port scan data."""
    for port_scan in port_scans:
        try:
            owner_id = org_id_dict.get(port_scan.get("owner"))
            if not owner_id:
                print(
                    f"{port_scan.get('Owner')} is not a recognized organization, skipping host"
                )
                continue

            ip = (
                save_ip_to_datalake(
                    {
                        "ip": port_scan.get("ip"),
                        "ip_hash": hash_ip(port_scan.get("ip")),
                        "organization": {"id": owner_id},
                    }
                )
                if port_scan.get("ip")
                else None
            )
            service_obj = json.loads(port_scan.get("service", "{}"))
            port_scan_dict = {
                "id": port_scan["_id"].replace("ObjectId('", "").replace("')", ""),
                "ip_string": port_scan.get("ip"),
                "ip": ip,
                "latest": port_scan.get("latest"),
                "port": port_scan.get("port"),
                "protocol": port_scan.get("protocol"),
                "reason": port_scan.get("reason"),
                "service": port_scan.get("service"),
                "service_name": service_obj.get("name", None),
                "service_confidence": service_obj.get("conf", None),
                "service_method": service_obj.get("method", None),
                "service_cpe": service_obj.get("cpe", [None])[0],
                "service_hostname": service_obj.get("hostname", None),
                "service_extra_info": service_obj.get("extrainfo", None),
                "service_os_type": service_obj.get("ostype", None),
                "service_product": service_obj.get("product", None),
                "service_version": service_obj.get("version", None),
                "service_tunnel": service_obj.get("tunnel", None),
                "service_device_type": service_obj.get("devicetype", None),
                "source": port_scan.get("source"),
                "state": port_scan.get("state"),
                "time_scanned": safe_fromisoformat(port_scan.get("time")),
                "organization": Organization.objects.get(id=owner_id),
                "risky_service_group": RiskyServiceGroup.objects.filter(
                    service_name=service_obj.get("name", None)
                )
                .values_list("group", flat=True)
                .first()
                if service_obj.get("name", None)
                else None,
                "nmi_service_group": NMIServiceGroup.objects.filter(
                    service_name=service_obj.get("name", None)
                )
                .values_list("group", flat=True)
                .first()
                if service_obj.get("name", None)
                else None,
            }
            save_port_scan_to_datalake(port_scan_dict)
        except Exception as e:
            print(f"Error processing port scan data: {e}")
            raise IngestionError(
                SCAN_NAME, str(e), "Failed processing port scans"
            ) from e


def process_orgs(request_list):
    """Process organization data, save to MDL and return org ID dict for linking."""
    LOGGER.info("Processing organizations...")
    org_id_dict = {}
    sector_child_dict = {}
    parent_child_dict = {}

    # Process the request data
    try:
        if request_list and isinstance(request_list, list):
            process_request(
                request_list, sector_child_dict, parent_child_dict, org_id_dict
            )

            # Link parent-child organizations
            link_parent_child_organizations(parent_child_dict, org_id_dict)

            # Assign organizations to sectors
            assign_organizations_to_sectors(sector_child_dict, org_id_dict)

        return org_id_dict
    except Exception as e:
        raise IngestionError(
            SCAN_NAME, str(e), "Failed processing organizations"
        ) from e


def link_parent_child_organizations(
    parent_child_dict, org_id_dict, db_name="mini_data_lake"
):
    """Link child organizations to their respective parent organizations."""
    for parent_acronym, child_acronyms in parent_child_dict.items():
        parent_id = org_id_dict.get(parent_acronym)
        if not parent_id:
            continue

        try:
            parent_org = Organization.objects.using(db_name).get(id=parent_id)
        except Organization.DoesNotExist:
            continue

        # Collect child organization IDs
        children_ids = [
            org_id_dict.get(acronym)
            for acronym in child_acronyms
            if acronym in org_id_dict
        ]

        # Update parent field for child organizations
        if children_ids:
            Organization.objects.using(db_name).filter(id__in=children_ids).update(
                parent=parent_org.id
            )


def assign_organizations_to_sectors(
    sector_child_dict, org_id_dict, db_name="mini_data_lake"
):
    """Assign organizations to sectors based on sector-child relationships."""
    try:
        for sector_id, child_acronyms in sector_child_dict.items():
            try:
                sector = Sector.objects.using(db_name).get(id=sector_id)
            except Sector.DoesNotExist:
                continue

            organization_ids = [
                org_id_dict.get(acronym)
                for acronym in child_acronyms
                if acronym in org_id_dict
            ]

            if organization_ids:
                sector.organizations.add(
                    *Organization.objects.using(db_name).filter(id__in=organization_ids)
                )
    except Exception as e:
        print("Error assigning organization to sectors:")
        print(e)
        raise e


def process_request(request_list, sector_child_dict, parent_child_dict, org_id_dict):
    """Process requests and build dictionaries for linking later."""
    non_sector_list = {
        "CRITICAL_INFRASTRUCTURE",
        "FEDERAL",
        "ROOT",
        "SLTT",
        "CATEGORIES",
        "INTERNATIONAL",
        "THIRD_PARTY",
    }

    for request in request_list:
        request = parse_request_data(request)

        # Skip non-sector records
        if "type" not in request["agency"]:
            if request["_id"] in non_sector_list:
                continue

            process_sector(request, sector_child_dict)
            continue

        # Process parent-child relationships
        if request.get("children"):
            parent_child_dict[request["_id"]] = request["children"]

        # Process networks
        network_list = process_networks(request.get("networks", []))

        # Process location
        location_dict = process_location(request.get("agency", {}).get("location"))

        # Process organization
        process_organization(request, network_list, location_dict, org_id_dict)


def parse_request_data(request):
    """Parse JSON fields in the request if they are strings."""
    json_fields = ["agency", "networks", "report_types", "scan_types", "children"]
    for field in json_fields:
        val = request.get(field)
        if isinstance(val, str):
            try:
                request[field] = json.loads(val)
            except Exception:
                request[field] = {}
        elif not isinstance(val, (dict, list)):  # corrupt or malformed
            request[field] = {} if field == "agency" else []
    return request


def process_sector(request, sector_child_dict):
    """Process sector data and update sector_child_dict."""
    if request.get("children"):
        sector_data = {
            "name": request["agency"]["name"],
            "acronym": request["_id"],
            "retired": bool(request["retired"]),
        }
        try:
            sector_obj, created = Sector.objects.update_or_create(
                acronym=sector_data["acronym"],
                defaults={
                    "name": sector_data["name"],
                    "retired": sector_data["retired"],
                },
            )
            sector_child_dict[sector_obj.id] = request["children"]
        except Exception as e:
            print("Error occurred creating sector", e)


def process_networks(networks):
    """Process network CIDR entries and return a list of network objects."""
    network_list = []
    for cidr in networks:
        try:
            address = (
                IPv6Network(cidr, strict=False)
                if ":" in cidr
                else IPv4Network(cidr, strict=False)
            )
            network_list.append(
                {"network": cidr, "start_ip": address[0], "end_ip": address[-1]}
            )
        except Exception as e:
            print("Invalid CIDR Format", e)
    return network_list


def process_location(org_location):
    """Create a dictionary representation of an organization's location."""
    if not org_location:
        return None

    return {
        "name": org_location.get("name"),
        "country_abrv": org_location.get("country", ""),
        "country": org_location.get("country_name"),
        "county": org_location.get("county"),
        "county_fips": org_location.get("county_fips"),
        "gnis_id": org_location.get("gnis_id"),
        "state_abrv": org_location.get("state"),
        "stateFips": org_location.get("state_fips"),
        "state": org_location.get("state_name"),
    }


def parse_int(value):
    """Safely parse integers, return None for blanks."""
    try:
        if value == "" or value is None:
            return None
        return int(value)
    except (ValueError, TypeError):
        return None


def process_organization(request, network_list, location_dict, org_id_dict):
    """Save organization data and update org_id_dict."""
    org_data = {
        "name": request.get("agency", {}).get("name"),
        "acronym": request.get("_id"),
        "retired": bool(request.get("retired", False)),
        "type": request.get("agency", {}).get("type"),
        "state": request.get("agency", {}).get("location", {}).get("state"),
        "state_name": request.get("agency", {}).get("location", {}).get("state_name"),
        "county": request.get("agency", {}).get("location", {}).get("county"),
        "county_fips": parse_int(
            request.get("agency", {}).get("location", {}).get("county_fips")
        ),
        "state_fips": parse_int(
            request.get("agency", {}).get("location", {}).get("state_fips")
        ),
        "country": request.get("agency", {}).get("location", {}).get("country"),
        "country_name": request.get("agency", {})
        .get("location", {})
        .get("country_name"),
        "region_id": REGION_STATE_MAP.get(
            request.get("agency", {}).get("location", {}).get("state_name"), None
        ),
        "stakeholder": bool(request.get("stakeholder", False)),
        "enrolled_in_vs_timestamp": request.get("enrolled") or timezone.now(),
        "period_start_vs_timestamp": request.get("period_start"),
        "report_types": json.dumps(request.get("report_types", [])),
        "scan_types": json.dumps(request.get("scan_types", [])),
        "is_passive": False,
    }
    try:
        org_record = save_organization_to_mdl(org_data, network_list, location_dict)
        org_id_dict[request["_id"]] = org_record.id
    except Exception as e:
        LOGGER.info("Error saving organization: %s - %s", e, request["_id"])
        raise IngestionError(
            SCAN_NAME, str(e), "Failed processing organizations"
        ) from e


if __name__ == "__main__":
    main()

"""VS Host Scan Helper."""

# Standard Python Libraries
import logging
import os

# Third-Party Libraries
from django.utils import timezone
from xfd_api.tasks.utils.query_redshift import fetch_from_redshift
from xfd_api.utils.scan_utils.alerting import QueryError
from xfd_mini_dl.models import HostSummary, Organization

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="vuln_scanning_sync.log",
)
LOGGER = logging.getLogger(__name__)
SCAN_NAME = "VulnScanningSync"
IS_LOCAL = os.getenv("IS_LOCAL")


def create_daily_host_summary(org_id_dict, summary_date=None):
    """Create host summary records directly from Redshift data."""
    LOGGER.info("Started processing host scans...")
    if summary_date is None:
        summary_date = timezone.now().date()

    LOGGER.info("Starting host summary creation directly from Redshift...")

    redshift_query = """
    SELECT
        owner,
        -- existing metrics
        MIN(last_change) AS start_date,
        MAX(last_change) AS end_date,
        SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END)    AS host_done_count,
        SUM(CASE WHEN status = 'WAITING' THEN 1 ELSE 0 END) AS host_waiting_count,
        SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) AS host_running_count,
        SUM(CASE WHEN status = 'READY' THEN 1 ELSE 0 END)   AS host_ready_count,
        SUM(CASE WHEN POSITION('\"up\":true'  IN json_serialize(state)) > 0 THEN 1 ELSE 0 END) AS up_host_count,
        SUM(CASE WHEN POSITION('\"up\":false' IN json_serialize(state)) > 0 THEN 1 ELSE 0 END) AS down_host_count,
        COUNT(DISTINCT ip) AS scanned_asset_count,

        -- PORTSCAN timestamps
        MIN(
            CASE
                WHEN POSITION('\"PORTSCAN\":\"' IN ls) > 0 THEN
                    CASE
                        WHEN CAST(SPLIT_PART(SPLIT_PART(ls, '\"PORTSCAN\":\"', 2), '\"', 1) AS TIMESTAMPTZ) >= GETDATE() - INTERVAL '120 days' THEN
                        CAST(SPLIT_PART(SPLIT_PART(ls, '\"PORTSCAN\":\"', 2), '\"', 1) AS TIMESTAMPTZ)
                    END
            END
        ) AS port_scan_min_timestamp,
        MAX(
            CASE
                WHEN POSITION('\"PORTSCAN\":\"' IN ls) > 0 THEN
                    CASE
                        WHEN CAST(SPLIT_PART(SPLIT_PART(ls, '\"PORTSCAN\":\"', 2), '\"', 1) AS TIMESTAMPTZ) >= GETDATE() - INTERVAL '120 days' THEN
                        CAST(SPLIT_PART(SPLIT_PART(ls, '\"PORTSCAN\":\"', 2), '\"', 1) AS TIMESTAMPTZ)
                    END
            END
        ) AS port_scan_max_timestamp,

        -- VULNSCAN timestamps
        MIN(
            CASE
                WHEN POSITION('\"VULNSCAN\":\"' IN ls) > 0 THEN
                    CASE
                        WHEN CAST(SPLIT_PART(SPLIT_PART(ls, '\"VULNSCAN\":\"', 2), '\"', 1) AS TIMESTAMPTZ) >= GETDATE() - INTERVAL '120 days' THEN
                        CAST(SPLIT_PART(SPLIT_PART(ls, '\"VULNSCAN\":\"', 2), '\"', 1) AS TIMESTAMPTZ)
                    END
            END
        ) AS vuln_scan_min_timestamp,
        MAX(
            CASE
                WHEN POSITION('\"VULNSCAN\":\"' IN ls) > 0 THEN
                    CASE
                        WHEN CAST(SPLIT_PART(SPLIT_PART(ls, '\"VULNSCAN\":\"', 2), '\"', 1) AS TIMESTAMPTZ) >= GETDATE() - INTERVAL '120 days' THEN
                        CAST(SPLIT_PART(SPLIT_PART(ls, '\"VULNSCAN\":\"', 2), '\"', 1) AS TIMESTAMPTZ)
                    END
            END
        ) AS vuln_scan_max_timestamp,

        -- NETSCAN1 timestamps
        MIN(CASE WHEN POSITION('\"NETSCAN1\":\"' IN ls) > 0
                THEN CAST(SPLIT_PART(SPLIT_PART(ls, '\"NETSCAN1\":\"', 2), '\"', 1) AS TIMESTAMPTZ) END) AS net_scan1_min_timestamp,
        MAX(CASE WHEN POSITION('\"NETSCAN1\":\"' IN ls) > 0
                THEN CAST(SPLIT_PART(SPLIT_PART(ls, '\"NETSCAN1\":\"', 2), '\"', 1) AS TIMESTAMPTZ) END) AS net_scan1_max_timestamp,

        -- NETSCAN2 timestamps
        MIN(CASE WHEN POSITION('\"NETSCAN2\":\"' IN ls) > 0
                THEN CAST(SPLIT_PART(SPLIT_PART(ls, '\"NETSCAN2\":\"', 2), '\"', 1) AS TIMESTAMPTZ) END) AS net_scan2_min_timestamp,
        MAX(CASE WHEN POSITION('\"NETSCAN2\":\"' IN ls) > 0
                THEN CAST(SPLIT_PART(SPLIT_PART(ls, '\"NETSCAN2\":\"', 2), '\"', 1) AS TIMESTAMPTZ) END) AS net_scan2_max_timestamp

    FROM (
        SELECT
            owner,
            last_change,
            status,
            state,
            ip,
            json_serialize(latest_scan) AS ls
        FROM vmtableau.hosts
        WHERE last_change >= GETDATE() - INTERVAL '100 days'
    ) t
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
                    "port_scan_min_timestamp": row["port_scan_min_timestamp"],
                    "port_scan_max_timestamp": row["port_scan_max_timestamp"],
                    "vuln_scan_min_timestamp": row["vuln_scan_min_timestamp"],
                    "vuln_scan_max_timestamp": row["vuln_scan_max_timestamp"],
                    "net_scan1_min_timestamp": row["net_scan1_min_timestamp"],
                    "net_scan1_max_timestamp": row["net_scan1_max_timestamp"],
                    "net_scan2_min_timestamp": row["net_scan2_min_timestamp"],
                    "net_scan2_max_timestamp": row["net_scan2_max_timestamp"],
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

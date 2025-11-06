"""MDL Insert Helpers."""

# Standard Python Libraries
import logging
import time

# Third-Party Libraries
from django.db import connections, transaction

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)


def fill_cidr_live_ips_bulk_update():
    """Fill live_ips field in the cidr table based on recent port scans."""
    start_time = time.time()

    with transaction.atomic(using="mini_data_lake"):
        with connections["mini_data_lake"].cursor() as cursor:
            cursor.execute(
                """
                WITH new_ips AS (
                    SELECT
                        cidr.id AS cidr_id,
                        array_agg(DISTINCT ip.ip) AS new_ip_list
                    FROM cidr
                    JOIN cidr_orgs ON cidr_orgs.cidr_id = cidr.id
                    JOIN port_scan ON port_scan.state = 'open'
                        AND port_scan.time_scanned >= NOW() - INTERVAL '90 days'
                    JOIN ip ON port_scan.ip_id = ip.id
                    WHERE cidr_orgs.current = TRUE
                      AND cidr.network IS NOT NULL
                      AND ip.ip << cidr.network
                    GROUP BY cidr.id
                ),
                merged_ips AS (
                    SELECT
                        cidr.id,
                        ARRAY(
                            SELECT DISTINCT ip_address::inet
                            FROM jsonb_array_elements_text(
                                COALESCE(cidr.live_ips, '[]'::jsonb) || to_jsonb(new_ips.new_ip_list)
                            ) AS ip_address
                        ) AS updated_ips
                    FROM cidr
                    JOIN new_ips ON cidr.id = new_ips.cidr_id
                )
                UPDATE cidr
                SET live_ips = to_jsonb(merged_ips.updated_ips)
                FROM merged_ips
                WHERE cidr.id = merged_ips.id;
                """  # nosec B608
            )

    duration = time.time() - start_time
    LOGGER.info("fill_cidr_live_ips_bulk_update completed in %.2f seconds", duration)

"""Functions to manage asset relationships."""
# Third-Party Libraries
from django.db import connections
from xfd_mini_dl.models import CidrOrgs  # replace 'your_app' with your app name


def bulk_assign_ips_to_cidrs(batch_size: int = 1000):
    """
    Assign IPs to their smallest current CIDR per organization in batches.

    - First unlinks IPs from non-current CIDRs
    - Then processes IPs without from_cidr in batches
    - Updates origin_cidr_id, from_cidr, and retired flags
    """
    # Step 1: Unlink IPs from non-current CIDRs
    with connections["mini_data_lake"].cursor() as cursor:
        unlink_query = """
            UPDATE ip
            SET origin_cidr_id = NULL,
                from_cidr = NULL,
                retired = NULL
            FROM cidr_orgs co
            WHERE ip.origin_cidr_id = co.cidr_id
            AND ip.organization_id = co.organization_id
            AND co.current = FALSE;
        """  # nosec B608
        cursor.execute(unlink_query)

    # Step 2: Process IPs org by org
    org_ids = (
        CidrOrgs.objects.filter(current=True)
        .values_list("organization_id", flat=True)
        .distinct()
    )

    for org_id in org_ids:
        last_ip_id = None

        while True:
            with connections["mini_data_lake"].cursor() as cursor:
                query = f"""
                    WITH org_cidrs AS (
                        SELECT c.id AS cidr_id, c.network::cidr AS network
                        FROM cidr c
                        JOIN cidr_orgs co ON co.cidr_id = c.id
                        WHERE co.current = TRUE AND co.organization_id = %s
                        ORDER BY masklen(c.network::cidr) ASC
                    ),
                    ip_batch AS (
                        SELECT id AS ip_id, ip
                        FROM ip
                        WHERE organization_id = %s
                        AND (from_cidr IS NULL OR from_cidr = FALSE)
                        {"AND id > %s" if last_ip_id else ""}
                        ORDER BY id ASC
                        LIMIT %s
                    ),
                    ip_to_update AS (
                        SELECT ip_batch.ip_id,
                               (SELECT cidr_id
                                FROM org_cidrs
                                WHERE ip_batch.ip::inet << org_cidrs.network
                                LIMIT 1) AS cidr_id
                        FROM ip_batch
                    )
                    UPDATE ip
                    SET origin_cidr_id = ip_to_update.cidr_id,
                        from_cidr = CASE WHEN ip_to_update.cidr_id IS NOT NULL THEN TRUE ELSE FALSE END,
                        retired = CASE WHEN ip_to_update.cidr_id IS NULL THEN TRUE ELSE FALSE END
                    FROM ip_to_update
                    WHERE ip.id = ip_to_update.ip_id
                    RETURNING ip.id;
                """  # nosec B608

                params = [str(org_id), str(org_id)]
                if last_ip_id:
                    params.append(str(last_ip_id))
                params.append(str(batch_size))

                cursor.execute(query, params)
                updated_rows = cursor.fetchall()

                if not updated_rows:
                    break  # No more IPs to process in this org

                last_ip_id = updated_rows[-1][
                    0
                ]  # last processed IP ID for keyset pagination

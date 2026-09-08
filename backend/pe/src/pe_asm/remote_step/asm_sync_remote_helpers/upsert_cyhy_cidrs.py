"""Upsert CyHy database CIDR data (cyhy_db_assets) into the cidrs table."""

# Standard Python Libraries
import datetime
import logging

# Third-Party Libraries
from pe_asm.remote_step.asm_sync_remote_query import connect, query_cyhy_assets

# Setup logging
LOGGER = logging.getLogger(__name__)


def upsert_cyhy_cidrs(orgs_df):
    """Upsert cidr data from cyhy_db_assets into the cidrs table."""
    # Connect to database
    conn = connect()
    first_seen = datetime.datetime.today().date()
    last_seen = datetime.datetime.today().date()
    # Iterate over each organization
    for org_index, org_row in orgs_df.iterrows():
        # Retrieve cyhy assets for this org
        org_id = org_row["organizations_uid"]
        networks = query_cyhy_assets(org_row["cyhy_db_name"])
        # Iterate over each CyHy CIDR
        for network_index, network in networks.iterrows():
            # Upsert CIDR into the cidrs table
            cur = conn.cursor()
            try:
                cur.callproc(
                    "insert_cidr",
                    (network["network"], org_id, "cyhy_db", first_seen, last_seen),
                )
            except Exception as e:
                LOGGER.error(e)
                continue
            conn.commit()
            cur.close()
    # Close database connection
    conn.close()

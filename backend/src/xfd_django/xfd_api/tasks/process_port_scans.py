"""Worker that processes port scans from Redshift in parallel."""
# Standard Python Libraries
import logging
import os

# Third-Party Libraries
from vulnScanningSync import (
    bulk_insert_ips_and_link_to_port_scans,
    fetch_in_chunks_keyset,
)
from xfd_mini_dl.models import NMIServiceGroup, RiskyServiceGroup

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def handler(command):
    """Run worker to gather port scan data from redshift."""
    chunk_start_id = command.get("chunk_start_id")
    chunk_end_id = command.get(
        "chunk_end_id"
    )  # optional if you want to limit chunk size

    org_id_dict = {}  # Or load from shared cache if needed

    risky_service_groups = {
        rsg.service_name: rsg.group for rsg in RiskyServiceGroup.objects.all()
    }
    nmi_service_groups = {
        nsg.service_name: nsg.group for nsg in NMIServiceGroup.objects.all()
    }

    base_query = (
        "SELECT * FROM vmtableau.port_scans "
        f"WHERE time >= GETDATE() - INTERVAL '{os.getenv('VS_PULL_DATE_RANGE', '90')} days'"  # nosec B608
    )

    if chunk_start_id:
        base_query += f" AND _id >= '{chunk_start_id}'"
    if chunk_end_id:
        base_query += f" AND _id <= '{chunk_end_id}'"

    for chunk in fetch_in_chunks_keyset(base_query):
        bulk_insert_ips_and_link_to_port_scans(
            chunk, org_id_dict, risky_service_groups, nmi_service_groups
        )


if __name__ == "__main__":
    handler({})

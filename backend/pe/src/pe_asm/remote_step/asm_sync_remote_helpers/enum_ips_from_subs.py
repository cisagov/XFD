"""Link sub-domains and IPs from sub-domain lookups."""

# Standard Python Libraries
import datetime
import hashlib
import logging
import socket

# Third-Party Libraries
from pe_asm.remote_step.asm_sync_remote_query import connect, query_subs_by_org

# Setup logging
LOGGER = logging.getLogger(__name__)
DATE = datetime.datetime.today().date()


def get_ip_for_domain(domain):
    """Find the ip for a provided domain."""
    try:
        ip = socket.gethostbyname(domain)
    except Exception:
        ip = None
    return ip


def link_ip_from_domain(sub, root_uid, org_uid, data_source, conn):
    """Link IP from domain."""
    ip = get_ip_for_domain(sub)
    if not ip:
        return 0
    hash_object = hashlib.sha256(str(ip).encode("utf-8"))
    ip_hash = hash_object.hexdigest()
    cur = conn.cursor()
    cur.callproc(
        "link_ips_and_subs",
        (DATE, ip_hash, ip, org_uid, sub, data_source, root_uid, None),
    )
    cur.fetchone()
    # print(row)
    conn.commit()
    cur.close()
    return 1


def enum_ips_from_subs(orgs_df):
    """For each org, find all ips associated with its sub_domains and link them in the ips_subs table."""
    num_orgs = len(orgs_df.index)
    # Iterate over each organization
    org_count = 1
    for org_index, org_row in orgs_df.iterrows():
        # Connect to database
        conn = connect()
        LOGGER.info(
            "Running on %s, %d/%d",
            org_row["cyhy_db_name"],
            org_count,
            num_orgs,
        )
        org_uid = org_row["organizations_uid"]
        # Query sub-domains
        subs_df = query_subs_by_org(str(org_uid))
        LOGGER.info("Number of Sub-domains: %d", len(subs_df.index))
        # For each subdomain get associated IP
        for sub_index, sub_row in subs_df.iterrows():
            sub_domain = sub_row["sub_domain"]
            root_uid = sub_row["root_domain_uid"]
            if sub_domain == "Null_Sub":
                continue
            link_ip_from_domain(sub_domain, root_uid, org_uid, "unknown", conn)

        org_count += 1
        # Close database connection
        conn.close()

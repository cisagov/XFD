#!/usr/bin/python3
"""CyHy database and sync queries."""

# Standard Python Libraries
from datetime import datetime
from decimal import Decimal
import json
import logging
import sys

# Third-Party Libraries
import pandas as pd
from pe_reports.data.config import config, staging_config
import psycopg2
from psycopg2 import OperationalError
import psycopg2.extras as extras
import requests

# Setup logging
LOGGER = logging.getLogger(__name__)

CONN_PARAMS_DIC = config()
API_DIC = staging_config(section="pe_api")
pe_api_key = API_DIC.get("pe_api_key")
pe_api_url = API_DIC.get("pe_api_url")


def show_psycopg2_exception(err):
    """Handle errors for PostgreSQL issues."""
    err_type, err_obj, traceback = sys.exc_info()
    LOGGER.error(
        "Database connection error: %s on line number: %s", err, traceback.tb_lineno
    )


def connect():
    """Connect to PostgreSQL database."""
    try:
        return psycopg2.connect(**CONN_PARAMS_DIC)
    except OperationalError as err:
        show_psycopg2_exception(err)
        return None


def get_orgs():
    """
    Query API to retrieve data for all organizations in P&E database both report_on or demo.

    Return:
        All demo or report_on org data as list of tuples
    """
    # Endpoint info
    endpoint_url = pe_api_url + "organizations_demo_or_report_on"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    try:
        result = requests.get(endpoint_url, headers=headers, timeout=60).json()
        # Process data and return
        for row in result:
            if row.get("date_first_reported") is not None:
                row["date_first_reported"] = datetime.strptime(
                    row.get("date_first_reported"), "%Y-%m-%d"
                )
            if row.get("cyhy_period_start") is not None:
                row["cyhy_period_start"] = datetime.strptime(
                    row.get("cyhy_period_start"), "%Y-%m-%d"
                )
            if row.get("county_fips") is not None:
                row["county_fips"] = Decimal(row.get("county_fips"))
            if row.get("state_fips") is not None:
                row["state_fips"] = Decimal(row.get("state_fips"))
        return result
    except requests.exceptions.HTTPError as errh:
        LOGGER.error(errh)
    except requests.exceptions.ConnectionError as errc:
        LOGGER.error(errc)
    except requests.exceptions.Timeout as errt:
        LOGGER.error(errt)
    except requests.exceptions.RequestException as err:
        LOGGER.error(err)
    except json.decoder.JSONDecodeError as err:
        LOGGER.error(err)


def query_cyhy_assets(org_cyhy_name):
    """
    Query API to retrieve all cyhy assets for an organization.

    Args:
        org_cyhy_name: CyHy database name of the specified organization (not uid)

    Return:
        All the cyhy assets belonging to the specified org as a dataframe
    """
    # Endpoint info
    endpoint_url = pe_api_url + "cyhy_assets_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"org_cyhy_name": org_cyhy_name})
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=60
        ).json()
        # Process data and return
        result_df = pd.DataFrame.from_dict(result)
        result_df.rename(
            columns={
                "field_id": "_id",
            },
            inplace=True,
        )
        result_df["first_seen"] = pd.to_datetime(result_df["first_seen"]).dt.date
        result_df["last_seen"] = pd.to_datetime(result_df["last_seen"]).dt.date
        # Return truly empty dataframe if no results
        if result_df[result_df.columns].isnull().apply(lambda x: all(x), axis=1)[0]:
            result_df.drop(result_df.index, inplace=True)
        return result_df
    except requests.exceptions.HTTPError as errh:
        LOGGER.info(errh)
    except requests.exceptions.ConnectionError as errc:
        LOGGER.info(errc)
    except requests.exceptions.Timeout as errt:
        LOGGER.info(errt)
    except requests.exceptions.RequestException as err:
        LOGGER.info(err)
    except json.decoder.JSONDecodeError as err:
        LOGGER.info(err)


def update_cidrs_status(org_uids):
    """Update the statuses of all CIDRs for specified organizations."""
    if not org_uids:
        LOGGER.info("No organization UIDs supplied for CIDR status update")
        return
    # Connect to database
    connection = connect()
    if connection is None:
        raise ConnectionError("Unable to connect to the PE database")
    # Assembled org UIDs
    organization_uids = [str(org_uid) for org_uid in org_uids]
    try:
        with connection.cursor() as cursor:
            LOGGER.info("Marking CIDRs as current if seen within the last 15 days")
            cursor.execute(
                """
                UPDATE cidrs
                SET current = TRUE
                WHERE last_seen > CURRENT_DATE - INTERVAL '15 days'
                  AND organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )
            LOGGER.info(
                "Marking CIDRs as not current if not seen within the last 15 days"
            )
            cursor.execute(
                """
                UPDATE cidrs
                SET current = FALSE
                WHERE last_seen < CURRENT_DATE - INTERVAL '15 days'
                  AND organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )

        connection.commit()
    except Exception:
        connection.rollback()
        LOGGER.exception("Failed to update CIDR statuses")
        raise
    finally:
        connection.close()


def query_roots(org_uids):
    """Query root domains for the specified organizations."""
    if not org_uids:
        return pd.DataFrame(columns=["root_domain_uid", "root_domain"])

    conn = connect()
    if conn is None:
        raise ConnectionError("Unable to connect to the PE database")

    LOGGER.info("Retrieving root domains for organizations")
    organization_uids = [str(org_uid) for org_uid in org_uids]

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.root_domain_uid,
                    r.root_domain
                FROM root_domains AS r
                JOIN organizations AS o
                    ON r.organizations_uid = o.organizations_uid
                WHERE o.organizations_uid = ANY(%s::uuid[])
                    AND r.enumerate_subs = TRUE
                """,
                (organization_uids,),
            )
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

        return pd.DataFrame(rows, columns=columns)
    except Exception:
        LOGGER.exception("Failed to retrieve root domains")
        raise
    finally:
        conn.close()


def insert_sub_domains(df):
    """Save subdomains dataframe to the P&E DB."""
    conn = connect()
    try:
        # Execute insert query
        df = df.drop_duplicates()
        df.insert(len(df.columns), "current", True)
        tpls = [tuple(x) for x in df.to_numpy()]
        cols = ",".join(list(df.columns))
        table = "sub_domains"
        sql = """
            INSERT INTO {}({}) VALUES %s
            ON CONFLICT (sub_domain, root_domain_uid)
            DO UPDATE SET
                last_seen = EXCLUDED.last_seen,
                identified = EXCLUDED.identified,
                current = EXCLUDED.current;
            """
        cursor = conn.cursor()
        extras.execute_values(cursor, sql.format(table, cols), tpls)
        conn.commit()
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as err:
        # Show error and close connection if failed
        LOGGER.error("There was a problem with your database query %s", err)
    conn.close()


def get_data_source_uid(source_name):
    """Get data source uid."""
    params = config()
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    sql = """SELECT * FROM data_source WHERE name = '{}'"""
    cur.execute(sql.format(source_name))
    source_uid = cur.fetchone()[0]
    cur.close()
    cur = conn.cursor()
    # Update last_run in data_source table
    date = datetime.today().strftime("%Y-%m-%d")
    sql = """UPDATE data_source SET last_run = '{}'
            WHERE name = '{}';"""
    cur.execute(sql.format(date, source_name))
    cur.close()
    conn.close()
    return source_uid


def query_cidrs_by_org(org_uid):
    """Get current CIDRs for an organization."""
    conn = connect()
    if conn is None:
        raise ConnectionError("Unable to connect to the PE database")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ct.network,
                    ct.cidr_uid
                FROM cidrs AS ct
                JOIN organizations AS o
                    ON o.organizations_uid = ct.organizations_uid
                WHERE o.organizations_uid = %(org_uid)s
                    AND ct.current
                """,
                {"org_uid": org_uid},
            )

            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
        return pd.DataFrame(rows, columns=columns)
    except Exception:
        LOGGER.exception(
            "Failed to retrieve CIDRs for organization %s",
            org_uid,
        )
        raise
    finally:
        conn.close()


def upsert_ips(df):
    """Upsert the ips into the ips table in the database and link them to the associated cidr."""
    conn = connect()
    try:
        df = pd.DataFrame([df])
        # Execute insert query
        tpls = [tuple(x) for x in df.to_numpy()]
        cols = ",".join(list(df.columns))
        table = "ips"
        sql = """
        INSERT INTO {}({}) VALUES %s
        ON CONFLICT (ip)
        DO UPDATE SET
            origin_cidr = UUID(EXCLUDED.origin_cidr),
            last_seen = EXCLUDED.last_seen,
            last_reverse_lookup = EXCLUDED.last_reverse_lookup,
            organizations_uid = EXCLUDED.organizations_uid;
        """
        cursor = conn.cursor()
        extras.execute_values(cursor, sql.format(table, cols), tpls, page_size=100000)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        # Show error and close connection if failed
        LOGGER.error("There was a problem with your database query %s", err)
        cursor.close()
    conn.close()


def query_subs_by_org(org_uid):
    """Query all current subdomains for an organization."""
    conn = connect()
    if conn is None:
        raise ConnectionError("Unable to connect to the PE database")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT sd.*
                FROM sub_domains AS sd
                JOIN root_domains AS rd
                    ON rd.root_domain_uid = sd.root_domain_uid
                WHERE rd.organizations_uid = %(org_uid)s
                    AND sd.current
                """,
                {"org_uid": org_uid},
            )

            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
        return pd.DataFrame(rows, columns=columns)
    except Exception:
        LOGGER.exception(
            "Failed to retrieve subdomains for organization %s",
            org_uid,
        )
        raise
    finally:
        conn.close()


def update_ips_status(org_uids):
    """Update IP statuses for the specified organizations."""
    if not org_uids:
        LOGGER.info("No organization UIDs supplied for IP status update")
        return

    conn = connect()
    if conn is None:
        raise ConnectionError("Unable to connect to the PE database")

    organization_uids = [str(org_uid) for org_uid in org_uids]

    try:
        with conn.cursor() as cursor:
            LOGGER.info("Marking IPs as current if seen within the last 15 days")
            cursor.execute(
                """
                UPDATE ips
                SET current = TRUE
                WHERE
                    last_seen > CURRENT_DATE - INTERVAL '15 days'
                    AND organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )

            LOGGER.info(
                "Marking IPs as not current if not seen within the last 15 days"
            )
            cursor.execute(
                """
                UPDATE ips
                SET current = FALSE
                WHERE (
                    last_seen < CURRENT_DATE - INTERVAL '15 days'
                    OR last_seen IS NULL
                )
                AND organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        LOGGER.exception("Failed to update IP statuses")
        raise
    finally:
        conn.close()


def update_subs_status(org_uids):
    """Update subdomain statuses for the specified organizations."""
    if not org_uids:
        LOGGER.info("No organization UIDs supplied for subdomain status update")
        return

    conn = connect()
    if conn is None:
        raise ConnectionError("Unable to connect to the PE database")

    organization_uids = [str(org_uid) for org_uid in org_uids]

    try:
        with conn.cursor() as cursor:
            LOGGER.info("Marking subdomains as current if seen within the last 15 days")
            cursor.execute(
                """
                UPDATE sub_domains AS sd
                SET current = TRUE
                FROM root_domains AS rd
                WHERE sd.root_domain_uid = rd.root_domain_uid
                    AND sd.last_seen > CURRENT_DATE - INTERVAL '15 days'
                    AND rd.organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )

            LOGGER.info(
                "Marking subdomains as not current if not seen within "
                "the last 15 days"
            )
            cursor.execute(
                """
                UPDATE sub_domains AS sd
                SET current = FALSE
                FROM root_domains AS rd
                WHERE sd.root_domain_uid = rd.root_domain_uid
                    AND (
                        sd.last_seen <
                            CURRENT_DATE - INTERVAL '15 days'
                        OR sd.last_seen IS NULL
                    )
                    AND rd.organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        LOGGER.exception("Failed to update subdomain statuses")
        raise
    finally:
        conn.close()


def update_ips_subs_status(org_uids):
    """Update IP-to-subdomain statuses for specified organizations."""
    if not org_uids:
        LOGGER.info("No organization UIDs supplied for IP-subdomain status update")
        return

    conn = connect()
    if conn is None:
        raise ConnectionError("Unable to connect to the PE database")

    organization_uids = [str(org_uid) for org_uid in org_uids]

    try:
        with conn.cursor() as cursor:
            LOGGER.info(
                "Marking IP-subdomain links as current if seen within "
                "the last 15 days"
            )
            cursor.execute(
                """
                UPDATE ips_subs AS ip_sub
                SET current = TRUE
                FROM ips AS ip
                WHERE ip_sub.ip_hash = ip.ip_hash
                    AND ip_sub.last_seen > CURRENT_DATE - INTERVAL '15 days'
                    AND ip.organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )

            LOGGER.info(
                "Marking IP-subdomain links as not current if not seen "
                "within the last 15 days"
            )
            cursor.execute(
                """
                UPDATE ips_subs AS ip_sub
                SET current = FALSE
                FROM ips AS ip
                WHERE ip_sub.ip_hash = ip.ip_hash
                    AND (
                        ip_sub.last_seen <
                            CURRENT_DATE - INTERVAL '15 days'
                        OR ip_sub.last_seen IS NULL
                    )
                    AND ip.organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        LOGGER.exception("Failed to update IP-subdomain statuses")
        raise
    finally:
        conn.close()


def update_subs_identified(org_ids):
    """Mark subdomains as identified for specified organizations."""
    if not org_ids:
        LOGGER.info("No organization UIDs supplied for subdomain identification")
        return

    conn = connect()
    if conn is None:
        raise ConnectionError("Unable to connect to the PE database")

    organization_uids = [str(org_id) for org_id in org_ids]

    try:
        with conn.cursor() as cursor:
            LOGGER.info("Marking identified subdomains")
            cursor.execute(
                """
                UPDATE sub_domains AS sd
                SET identified = TRUE
                FROM root_domains AS rd
                WHERE sd.root_domain_uid = rd.root_domain_uid
                    AND rd.enumerate_subs = FALSE
                    AND rd.organizations_uid = ANY(%s::uuid[])
                """,
                (organization_uids,),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        LOGGER.exception("Failed to mark subdomains as identified")
        raise
    finally:
        conn.close()


def query_floating_ips(org_id):
    """Query floating IPs found from current subdomains."""
    conn = connect()
    if conn is None:
        raise ConnectionError("Unable to connect to the PE database")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT i.ip
                FROM ips AS i
                JOIN ips_subs AS ip_s
                    ON ip_s.ip_hash = i.ip_hash
                JOIN sub_domains AS sd
                    ON sd.sub_domain_uid = ip_s.sub_domain_uid
                JOIN root_domains AS rd
                    ON rd.root_domain_uid = sd.root_domain_uid
                WHERE rd.organizations_uid = %(org_id)s
                    AND i.origin_cidr IS NULL
                    AND sd.current
                    AND i.current
                """,
                {"org_id": org_id},
            )

            return {row[0] for row in cursor.fetchall()}
    except Exception:
        LOGGER.exception(
            "Failed to retrieve floating IPs for organization %s",
            org_id,
        )
        raise
    finally:
        conn.close()


def update_shodan_ips(conn, df):
    """Update if an IP is a shodan IP."""
    tpls = [tuple(x) for x in df.to_numpy()]
    cols = ",".join(list(df.columns))
    table = "ips"
    sql = """
        INSERT INTO {}({})
        VALUES %s
        ON CONFLICT (ip)
            DO UPDATE SET shodan_results = EXCLUDED.shodan_results,
            origin_cidr = EXCLUDED.origin_cidr,
            current = EXCLUDED.current"""
    cursor = conn.cursor()
    try:
        extras.execute_values(cursor, sql.format(table, cols), tpls)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        show_psycopg2_exception(err)
        cursor.close()

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


def insert_sectors(conn, db_pass, sectors_list):
    """Insert sectors into PE DB."""
    # Build upsert SQL query
    sector_input_values = ""
    for sector in sectors_list:
        clean_p = sector["password"]
        if clean_p is not None:
            clean_p = clean_p.replace("'", "''")
        if clean_p is None:
            clean_p = ""
        sector_input_values += (
            "('%s', '%s', '%s', '%s', '%s', %s, '%s', '%s', PGP_SYM_ENCRYPT('%s', '%s')), \n"
            % (
                sector["id"],
                sector["acronym"],
                sector["name"],
                sector["email"],
                sector["contact_name"],
                sector["retired"],
                datetime.today().date(),
                datetime.today().date(),
                clean_p,
                db_pass,
            )
        )
    # remove final comma
    sector_input_values = sector_input_values[:-3]
    sql = """
    INSERT INTO sectors(id, acronym, name, email, contact_name, retired, first_seen, last_seen, password) VALUES
    %s
    ON CONFLICT (id)
    DO UPDATE SET
        acronym = EXCLUDED.acronym,
        name = EXCLUDED.name,
        email = EXCLUDED.email,
        contact_name = EXCLUDED.contact_name,
        retired = EXCLUDED.retired,
        last_seen = EXCLUDED.last_seen,
        password = EXCLUDED.password
    """
    sql = sql % sector_input_values
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        LOGGER.info(
            "Sector data inserted successfully using insert_sectors(): upserted %d row(s)",
            len(sectors_list),
        )
    except Exception as e:
        LOGGER.error(e)
    finally:
        if cursor is not None:
            cursor.close()


def query_pe_sectors(conn):
    """Query sectors from the P&E database."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT sector_uid, id, acronym, run_scorecards
                FROM sectors
                """
            )
            columns = [description[0] for description in cursor.description]
            sectors_df = pd.DataFrame(cursor.fetchall(), columns=columns)

        LOGGER.info("PE sectors retrieved successfully using query_pe_sectors()")
        return sectors_df
    except Exception:
        LOGGER.exception("Failed to retrieve PE sectors")
        raise


def insert_assets(conn, assets_df):
    """Insert CyHy assets into the P&E DB."""
    # Build upsert SQL query
    on_conflict = """ ON CONFLICT (org_id, network)
    DO UPDATE SET
    contact = EXCLUDED.contact,
    org_name = EXCLUDED.org_name,
    type = EXCLUDED.type,
    last_seen = EXCLUDED.last_seen; """
    tpls = [tuple(x) for x in assets_df.to_numpy()]
    cols = ",".join(list(assets_df.columns))
    sql = "INSERT INTO cyhy_db_assets({}) VALUES %s"
    sql = sql + on_conflict
    cursor = conn.cursor()
    # Execute completed query
    try:
        extras.execute_values(cursor, sql.format(cols), tpls)
        conn.commit()
        LOGGER.info(
            "Asset data inserted successfully using insert_assets(): upserted %d row(s)",
            len(assets_df),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        LOGGER.error("Error: Failed inserting asset data into PE DB")
        show_psycopg2_exception(err)
        cursor.close()


def insert_contacts(conn, contacts_df):
    """Insert CyHy contacts into the P&E databse."""
    # Build upsert SQL query
    on_conflict = """ ON CONFLICT (org_id, contact_type, email, name)
    DO UPDATE SET
    org_name = EXCLUDED.org_name,
    phone = EXCLUDED.phone,
    date_pulled = EXCLUDED.date_pulled;
    """
    tpls = [tuple(x) for x in contacts_df.to_numpy()]
    cols = ",".join(list(contacts_df.columns))
    sql = "INSERT INTO cyhy_contacts({}) VALUES %s"
    sql = sql + on_conflict
    cursor = conn.cursor()
    # Execute completed query
    try:
        extras.execute_values(cursor, sql.format(cols), tpls)
        conn.commit()
        LOGGER.info(
            "Contact data inserted successfully using insert_contacts(): upserted %d row(s)",
            len(contacts_df),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        LOGGER.error("Error: Failed inserting contact data into PE DB")
        show_psycopg2_exception(err)
        cursor.close()
    # Delete any old/outdated PE Report contacts
    # that aren't currently in the VS database
    curr_date = datetime.today().strftime("%Y-%m-%d")
    delete_query = """
        DELETE FROM cyhy_contacts
        WHERE
            date_pulled != '%s'
            AND
            org_id IN (
                SELECT
                    cyhy_db_name
                FROM
                    organizations
                WHERE
                    report_on = True
            )
    """
    delete_query = delete_query % curr_date
    cursor = None
    try:
        cursor = conn.cursor()
        LOGGER.info("insert_contacts: deleting contacts not currently in VS DB")
        cursor.execute(delete_query)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        LOGGER.exception(
            "insert_contacts: failed deleting contacts not currently in VS DB"
        )
        show_psycopg2_exception(err)
        raise
    finally:
        if cursor is not None:
            cursor.close()


def insert_cyhy_agencies(conn, db_pass, cyhy_agency_df):
    """Insert CyHy agencies into the P&E database."""
    # Build upsert SQL query
    agency_input_values = ""
    for idx, agency in cyhy_agency_df.iterrows():
        # handle single quotes in fields
        agency = agency.replace("'", "''", regex=True)
        clean_pass = agency["password"]
        if clean_pass is not None:
            clean_pass = clean_pass.replace("'", "''")

        agency_input_values += (
            "('%s', '%s', '%s', %s, %s, %s, %s, %s, %s, '%s', %s, '%s', '%s', %s, '%s', %s, '%s', '%s', '%s', PGP_SYM_ENCRYPT('%s', '%s')), "
            % (
                agency["name"],
                agency["cyhy_db_name"],
                agency["agency_type"],
                agency["retired"],
                agency["receives_cyhy_report"],
                agency["receives_bod_report"],
                agency["receives_cybex_report"],
                agency["is_parent"],
                agency["fceb"],
                agency["cyhy_period_start"],
                agency["scorecard"],
                agency["location_name"],
                agency["county"],
                agency["county_fips"] or "NULL",
                agency["state_abbreviation"],
                agency["state_fips"] or "NULL",
                agency["state_name"],
                agency["country"],
                agency["country_name"],
                clean_pass,
                db_pass,
            )
        )
    # remove final comma
    agency_input_values = agency_input_values[:-2]
    sql = """
    INSERT INTO organizations(name, cyhy_db_name, agency_type, retired,
    receives_cyhy_report, receives_bod_report, receives_cybex_report,
    is_parent, fceb, cyhy_period_start, scorecard, location_name, county,
    county_fips, state_abbreviation, state_fips, state_name, country, country_name, password) VALUES %s
    ON CONFLICT (cyhy_db_name)
    DO UPDATE SET
        name = EXCLUDED.name,
        password = EXCLUDED.password,
        agency_type = EXCLUDED.agency_type,
        retired = EXCLUDED.retired,
        receives_cyhy_report = EXCLUDED.receives_cyhy_report,
        receives_bod_report= EXCLUDED.receives_bod_report,
        receives_cybex_report = EXCLUDED.receives_cybex_report,
        is_parent = EXCLUDED.is_parent,
        fceb = EXCLUDED.fceb,
        cyhy_period_start = EXCLUDED.cyhy_period_start,
        scorecard = EXCLUDED.scorecard,
        location_name = EXCLUDED.location_name,
        county = EXCLUDED.county,
        county_fips = EXCLUDED.county_fips,
        state_abbreviation = EXCLUDED.state_abbreviation,
        state_fips = EXCLUDED.state_fips,
        state_name = EXCLUDED.state_name,
        country = EXCLUDED.country,
        country_name = EXCLUDED.country_name
    """
    sql = sql % agency_input_values
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        LOGGER.info(
            "Organization data inserted successfully using insert_cyhy_agencies(): upserted %d row(s)",
            len(cyhy_agency_df),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        LOGGER.exception(
            "insert_cyhy_agencies: upsert failed for %d row(s)", len(cyhy_agency_df)
        )
        show_psycopg2_exception(err)
        raise
    finally:
        if cursor is not None:
            cursor.close()


def query_pe_orgs(conn):
    """Query organizations from the P&E database."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT organizations_uid, cyhy_db_name, name, agency_type, report_on, fceb, scorecard
                FROM organizations
                """
            )
            columns = [description[0] for description in cursor.description]
            organizations_df = pd.DataFrame(cursor.fetchall(), columns=columns)

        LOGGER.info("PE organizations retrieved successfully using query_pe_orgs()")
        return organizations_df
    except Exception:
        LOGGER.exception("Failed to retrieve PE organizations")
        raise


def insert_sector_org_relationship(conn, sector_org_list):
    """Insert sector org relationship into many to many table."""
    # MAYBE TODO delete relationships first to make sure we are up to date
    # Build upsert SQL query
    sector_org_input_values = ""
    for sector_org in sector_org_list:
        sector_org_input_values += "\n('{}', '{}', '{}', '{}'), ".format(
            sector_org[0],
            sector_org[1],
            sector_org[2],
            sector_org[3],
        )
    # remove final comma
    sector_org_input_values = sector_org_input_values[:-2]
    sql = """
    INSERT INTO sectors_orgs(sector_uid, organizations_uid, first_seen, last_seen)
    VALUES %s
    ON CONFLICT (sector_uid, organizations_uid)
    DO UPDATE SET
    last_seen = EXCLUDED.last_seen
    """
    sql = sql % sector_org_input_values
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        LOGGER.info(
            "Sectors_orgs data inserted successfully using insert_sector_org_relationship(): upserted %d row(s)",
            len(sector_org_list),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        LOGGER.exception(
            "insert_sector_org_relationship: upsert failed for %d row(s)",
            len(sector_org_list),
        )
        show_psycopg2_exception(err)
        raise
    finally:
        if cursor is not None:
            cursor.close()


def add_sector_hierachy(conn, child_uid, parent_uid):
    """Update parent_sector_uid field."""
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE sectors
        SET parent_sector_uid = %s
        WHERE sector_uid = %s
        """,
        (parent_uid, child_uid),
    )
    conn.commit()
    cursor.close()


def update_child_parent_orgs(conn, parent_uid, child_name):
    """Update child parent relationships between organizations."""
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE organizations
        SET parent_org_uid = %s
        WHERE cyhy_db_name = %s
        """,
        (parent_uid, child_name),
    )
    conn.commit()
    cursor.close()


def update_scan_status(conn, child_name):
    """Update child parent relationships between organizations."""
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE organizations
        SET run_scans = True
        WHERE cyhy_db_name = %s
        """,
        (child_name,),
    )
    conn.commit()
    cursor.close()


def update_fceb_child_status(conn, child_name):
    """Update child parent relationships between organizations."""
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE organizations
        SET fceb_child = True
        WHERE cyhy_db_name = %s
        """,
        (child_name,),
    )
    conn.commit()
    cursor.close()


def insert_dotgov_domains(conn, dotgov_df):
    """Insert dot gov domains."""
    # Build upsert SQL query
    table = "dotgov_domains"
    conflict = """
        ON CONFLICT (domain_name)
        DO UPDATE SET  domain_type = EXCLUDED.domain_type, agency = EXCLUDED.agency, organization = EXCLUDED.organization, city = EXCLUDED.city, state = EXCLUDED.state, security_contact_email = EXCLUDED.security_contact_email;
    """
    tpls = [tuple(x) for x in dotgov_df.to_numpy()]
    cols = ",".join(list(dotgov_df.columns))
    sql = "INSERT INTO {}({}) VALUES %s"
    sql = sql + conflict
    cursor = conn.cursor()
    # Execute query
    try:
        extras.execute_values(cursor, sql.format(table, cols), tpls)
        conn.commit()
        LOGGER.info(
            "Dotgov data inserted successfully using insert_dotgov_domains(): upserted %d row(s)",
            len(dotgov_df),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        LOGGER.error("Error: Failed inserting Dotgov data into PE DB")
        show_psycopg2_exception(err)
        cursor.close()


def identify_org_asset_changes(conn):
    """Identify Org Asset changes."""
    cursor = conn.cursor()
    LOGGER.info(
        "Marking CIDRs that have been seen in the CyHy DB within the last 3 days"
    )
    cursor.execute(
        """
        UPDATE cyhy_db_assets
        SET currently_in_cyhy = True
        WHERE last_seen > (CURRENT_DATE - INTERVAL '3 days')
        """
    )
    conn.commit()
    LOGGER.info("Current CIDRs marked successfully using identify_org_asset_changes()")

    LOGGER.info(
        "Marking CIDRs that have not been seen in the CyHy DB within the last 3 days"
    )
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE cyhy_db_assets
        SET currently_in_cyhy = False
        WHERE last_seen < (CURRENT_DATE - INTERVAL '3 days')
        """
    )
    conn.commit()
    LOGGER.info(
        "Non-Current CIDRs marked successfully using identify_org_asset_changes()"
    )

"""All SQL database queries needed for the ASM Sync local process."""

# Standard Python Libraries
import datetime
import logging
import sys

# Third-Party Libraries
import pandas as pd
import psycopg2
import psycopg2.extras as extras

# Setup Logging
main_log = logging.getLogger(__name__)


def show_psycopg2_exception(err):
    """Handle errors for PostgreSQL issues."""
    err_type, err_obj, traceback = sys.exc_info()
    main_log.error(
        "Database connection error: %s on line number: %s", err, traceback.tb_lineno
    )


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
                datetime.datetime.today().date(),
                datetime.datetime.today().date(),
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
        main_log.info(
            "Sector data inserted successfully using insert_sectors(): upserted %d row(s)",
            len(sectors_list),
        )
    except Exception as e:
        main_log.error(e)
    finally:
        if cursor is not None:
            cursor.close()


def query_pe_sectors(conn):
    """Query sectors from PE DB."""
    sql = """
    SELECT sector_uid, id, acronym, run_scorecards
    FROM sectors
    """
    try:
        df = pd.read_sql(sql, conn)
        main_log.info("PE sectors retrieved successfully using query_pe_sectors()")
    except Exception as e:
        main_log.error(e)
    return df


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
        main_log.info(
            "Asset data inserted successfully using insert_assets(): upserted %d row(s)",
            len(assets_df),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        main_log.error("Error: Failed inserting asset data into PE DB")
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
        main_log.info(
            "Contact data inserted successfully using insert_contacts(): upserted %d row(s)",
            len(contacts_df),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        main_log.error("Error: Failed inserting contact data into PE DB")
        show_psycopg2_exception(err)
        cursor.close()
    # Delete any old/outdated PE Report contacts
    # that aren't currently in the VS database
    curr_date = datetime.datetime.today().strftime("%Y-%m-%d")
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
        main_log.info("insert_contacts: deleting contacts not currently in VS DB")
        cursor.execute(delete_query)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.exception(
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
        main_log.info(
            "Organization data inserted successfully using insert_cyhy_agencies(): upserted %d row(s)",
            len(cyhy_agency_df),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.exception(
            "insert_cyhy_agencies: upsert failed for %d row(s)", len(cyhy_agency_df)
        )
        show_psycopg2_exception(err)
        raise
    finally:
        if cursor is not None:
            cursor.close()


def query_pe_orgs(conn):
    """Query P&E organizations."""
    sql = """
    SELECT organizations_uid, cyhy_db_name, name, agency_type, report_on, fceb, scorecard
    FROM organizations
    """
    df = pd.read_sql(sql, conn)
    main_log.info("PE organizations retrieved successfully using query_pe_orgs()")
    return df


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
        main_log.info(
            "Sectors_orgs data inserted successfully using insert_sector_org_relationship(): upserted %d row(s)",
            len(sector_org_list),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.exception(
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
        main_log.info(
            "Dotgov data inserted successfully using insert_dotgov_domains(): upserted %d row(s)",
            len(dotgov_df),
        )
    except (Exception, psycopg2.DatabaseError) as err:
        main_log.error("Error: Failed inserting Dotgov data into PE DB")
        show_psycopg2_exception(err)
        cursor.close()


def identify_org_asset_changes(conn):
    """Identify Org Asset changes."""
    cursor = conn.cursor()
    main_log.info(
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
    main_log.info(
        "Current CIDRs marked successfully using identify_org_asset_changes()"
    )

    main_log.info(
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
    main_log.info(
        "Non-Current CIDRs marked successfully using identify_org_asset_changes()"
    )


def install_pgcrypto(conn):
    """Install the pgcrypto extension if not present in DB."""
    cursor = conn.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    conn.commit()
    cursor.close()


def add_sectors_uniq_constr(conn):
    """Add unique contstraint to sectors in local db."""
    cursor = conn.cursor()
    try:
        sql = "ALTER TABLE sectors ADD CONSTRAINT sectors_id_unique UNIQUE (id);"
        cursor.execute(sql)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.info(
            "sector table constraint was not added: %s",
            err,
        )
    finally:
        if cursor is not None:
            cursor.close()


def add_sectors_orgs_uniq_constr(conn):
    """Add unique contstraint to sectors_orgs in local db."""
    cursor = conn.cursor()
    try:
        sql = "ALTER TABLE sectors_orgs ADD CONSTRAINT sector_id_org_id_unique UNIQUE (sector_uid, organizations_uid)"
        cursor.execute(sql)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.info(
            "sector_orgs table constraint was not added: %s",
            err,
        )
    finally:
        if cursor is not None:
            cursor.close()


def add_tables_uniq_constraint(conn):
    """Add unique constraint to tables in local db."""
    add_sectors_uniq_constr(conn)
    add_sectors_orgs_uniq_constr(conn)


def add_sectors_default_pkey(conn):
    """Add pkey default uuid gen to sectors in local db."""
    cursor = conn.cursor()
    try:
        sql = (
            "ALTER TABLE sectors ALTER COLUMN sector_uid SET DEFAULT gen_random_uuid();"
        )
        cursor.execute(sql)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.info(
            "sectors table default pkey uuid gen was not added: %s",
            err,
        )
    finally:
        if cursor is not None:
            cursor.close()


def add_sectors_orgs_default_pkey(conn):
    """Add pkey default uuid gen to sectors_orgs in local db."""
    cursor = conn.cursor()
    try:
        sql = "ALTER TABLE sectors_orgs ALTER COLUMN sector_org_uid SET DEFAULT gen_random_uuid();"
        cursor.execute(sql)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.info(
            "sectors_orgs table default pkey uuid gen was not added: %s",
            err,
        )
    finally:
        if cursor is not None:
            cursor.close()


def add_cyhy_db_assets_default_pkey(conn):
    """Add pkey default uuid gen to cyhy_db_assets in local db."""
    cursor = conn.cursor()
    try:
        sql = (
            "ALTER TABLE cyhy_db_assets ALTER COLUMN _id SET DEFAULT gen_random_uuid();"
        )
        cursor.execute(sql)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.info(
            "cyhy_db_assets table default pkey uuid gen was not added: %s",
            err,
        )
    finally:
        if cursor is not None:
            cursor.close()


def add_cyhy_contacts_default_pkey(conn):
    """Add pkey default uuid gen to cyhy_contacts in local db."""
    cursor = conn.cursor()
    try:
        sql = (
            "ALTER TABLE cyhy_contacts ALTER COLUMN _id SET DEFAULT gen_random_uuid();"
        )
        cursor.execute(sql)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.info(
            "cyhy_contacts table default pkey uuid gen was not added: %s",
            err,
        )
    finally:
        if cursor is not None:
            cursor.close()


def add_organizations_default_pkey(conn):
    """Add pkey default uuid gen to organizations in local db."""
    cursor = conn.cursor()
    try:
        sql = "ALTER TABLE organizations ALTER COLUMN organizations_uid SET DEFAULT gen_random_uuid();"
        cursor.execute(sql)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.info(
            "organizations table default pkey uuid gen was not added: %s",
            err,
        )
    finally:
        if cursor is not None:
            cursor.close()


def add_dotgov_domains_default_pkey(conn):
    """Add pkey default uuid gen to dotgov_domains in local db."""
    cursor = conn.cursor()
    try:
        sql = "ALTER TABLE dotgov_domains ALTER COLUMN dotgov_uid SET DEFAULT gen_random_uuid();"
        cursor.execute(sql)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as err:
        conn.rollback()
        main_log.info(
            "dotgov_domains table default pkey uuid gen was not added: %s",
            err,
        )
    finally:
        if cursor is not None:
            cursor.close()


def add_tables_default_uid(conn):
    """Add default uuid generation for tables in local db."""
    add_sectors_default_pkey(conn)
    add_sectors_orgs_default_pkey(conn)
    add_cyhy_db_assets_default_pkey(conn)
    add_cyhy_contacts_default_pkey(conn)
    add_organizations_default_pkey(conn)
    add_dotgov_domains_default_pkey(conn)

"""PE database helpers used by dnstwist (API reads + direct psycopg2 writes)."""

# Standard Python Libraries
from datetime import datetime
from decimal import Decimal
import json
import logging
import sys
import uuid

# Third-Party Libraries
import pandas as pd
from pe_reports.data.config import config, staging_config
import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import execute_values
import requests

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


def get_data_source_uid(source):
    """
    Query API to get the uid for the specified data source.

    Args:
        source: The name of the specified data source

    Return:
        Data for the specified data source
    """
    # Endpoint info
    endpoint_url = pe_api_url + "data_source_by_name"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"name": source})
    try:
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=60
        ).json()
        if not result:
            raise ValueError(
                "No PE data source named {!r}; run "
                "'make -C backend/pe syncdb-populate' for local dev".format(source)
            )
        # Process data and return
        tup_result = [tuple(row.values()) for row in result]
        return tup_result[0][0]
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


def getSubdomain(domain):
    """Query API to get the uid for the specified subdomain."""
    endpoint_url = pe_api_url + "subdomain_uid_by_domain"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"domain": domain})
    result = requests.post(endpoint_url, headers=headers, data=data, timeout=60).json()
    tup_result = [tuple(row.values()) for row in result]
    try:
        return tup_result[0][0]
    except Exception:
        return -1


def addSubdomain(domain, pe_org_uid, root):
    """Query API to insert a single sub domain into the sub_domains table."""
    endpoint_url = pe_api_url + "sub_domains_single_insert"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {
            "domain": domain,
            "pe_org_uid": pe_org_uid,
            "root": root,
        }
    )
    result = requests.put(endpoint_url, headers=headers, data=data, timeout=60).json()
    LOGGER.info(result)


def org_root_domains(org_uid):
    """Query API to get the root domains for the specified org uid."""
    endpoint_url = pe_api_url + "rootdomains_by_org_uid"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"org_uid": org_uid})
    result = requests.post(endpoint_url, headers=headers, data=data, timeout=60).json()
    result_df = pd.DataFrame.from_dict(result)
    result_df.rename(
        columns={"root_domain_uid": "root_uid", "organizations_uid": "org_uid"},
        inplace=True,
    )
    return result_df.to_dict("records")


def insert_subdomain(domain, pe_org_uid, root):
    """
    Query API to insert a single sub domain into the sub_domains table.

    Args:
        domain: The sub domain associated with the new record
        pe_org_uid: The organizations_uid associated with the new record
        root: Boolean whether or not specified domain is also a root domain
    """
    # Endpoint info
    endpoint_url = pe_api_url + "sub_domains_single_insert"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {
            "domain": domain,
            "pe_org_uid": pe_org_uid,
            "root": root,
        }
    )
    try:
        # Call endpoint
        result = requests.put(
            endpoint_url, headers=headers, data=data, timeout=60
        ).json()
        # Process data and return
        LOGGER.info(result)
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


def insert_domain_permu(df):
    """
    Query API to insert multiple records into the domain_permutations table.

    Args:
        df: Dataframe containing DNSMonitor domain_permutations data to be inserted
    """
    # Endpoint info
    endpoint_url = pe_api_url + "domain_permu_insert"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    # Adjust data types and convert to list of dictionaries
    df["date_observed"] = pd.to_datetime(df["date_observed"])
    df["date_observed"] = df["date_observed"].dt.strftime("%Y-%m-%d")
    df_dict_list = df.to_dict("records")
    data = json.dumps({"insert_data": df_dict_list})
    try:
        # Call endpoint
        result = requests.put(
            endpoint_url, headers=headers, data=data, timeout=60
        ).json()
        # Process data and return
        LOGGER.info(result)
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


def insert_domain_alert(df):
    """
    Query API to insert multiple records into the domain_alerts table.

    Args:
        df: Dataframe containing DNSMonitor domain_alerts data to be inserted
    """
    # Endpoint info
    endpoint_url = pe_api_url + "domain_alerts_insert"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    # Adjust data types and convert to list of dictionaries
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["previous_value"] = df["previous_value"].fillna("")
    df_dict_list = df.to_dict("records")
    data = json.dumps({"insert_data": df_dict_list})
    try:
        # Call endpoint
        result = requests.put(
            endpoint_url, headers=headers, data=data, timeout=60
        ).json()
        # Process data and return
        LOGGER.info(result)
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


def get_subdomain_uid(domain):
    """
    Query API to get the uid for the specified subdomain.

    Args:
        domain: The name of the specified subdomain

    Return:
        uid for the specified subdomain
    """
    # Endpoint info
    endpoint_url = pe_api_url + "subdomain_uid_by_domain"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"domain": domain})
    try:
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=60
        ).json()
        # Process data and return
        tup_result = [tuple(row.values()) for row in result]
        # Catch deleted subdomain error
        try:
            return tup_result[0][0]
        except Exception:
            return -1
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


def insert_flare_events(event_list):
    """Insert list of flare event dictionaries into the PE DB."""
    if not event_list:
        return

    rows = [
        (
            event.get("flare_events_uid") or str(uuid.uuid1()),
            event.get("organizations_uid"),
            event.get("flare_uid"),
            event.get("event_type"),
            event.get("event_date"),
            event.get("collection_date"),
            event.get("title"),
            event.get("content"),
            event.get("content_hash"),
            event.get("actor"),
            event.get("category"),
            event.get("source"),
            event.get("url"),
            event.get("risk_scores"),
            event.get("related_identifiers"),
            event.get("data_source_uid"),
            event.get("severity"),
            event.get("related_identifiers_txt"),
        )
        for event in event_list
    ]

    query = """
        INSERT INTO flare_events(
            flare_events_uid, organizations_uid, flare_uid, event_type, event_date,
            collection_date, title, content, content_hash, actor, category, source,
            url, risk_scores, related_identifiers, data_source_uid, severity,
            related_identifiers_txt
        ) VALUES %s
        ON CONFLICT (organizations_uid, flare_uid)
        DO UPDATE SET
            event_date = EXCLUDED.event_date,
            collection_date = EXCLUDED.collection_date,
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            related_identifiers = EXCLUDED.related_identifiers,
            related_identifiers_txt = EXCLUDED.related_identifiers_txt
    """

    conn = connect()
    if conn is None:
        LOGGER.error("insert_flare_events: PE database connection failed")
        raise RuntimeError("PE database connection failed")

    cursor = None
    try:
        cursor = conn.cursor()
        LOGGER.info("insert_flare_events: upserting %d row(s)", len(rows))
        execute_values(cursor, query, rows)
        conn.commit()
    except Exception:
        conn.rollback()
        LOGGER.exception("insert_flare_events: upsert failed for %d row(s)", len(rows))
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def get_dnsmonitor_domain_mapping():
    """
    Query API to get the latest DNSMonitor domain to organization mapping.

    Return:
        Dataframe mapping all DNSMonitor domains to their organization
    """
    # Endpoint info
    endpoint_url = pe_api_url + "dnsmonitor_mapping_by_date"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    try:
        result = requests.post(endpoint_url, headers=headers, timeout=60).json()
        # Process data and return
        return pd.DataFrame(result)[["domain", "organization"]]
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
    return pd.DataFrame(columns=["domain", "organization"])


def get_ips(org_uid):
    """
    Query API to get all ips for an org to run through Shodan.

    Return:
        All ips to run through Shodan
    """
    # Endpoint info
    endpoint_url = pe_api_url + "query_shodan_ips/" + org_uid
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    try:
        result = requests.get(endpoint_url, headers=headers, timeout=60).json()
        # Process data and return
        return result if isinstance(result, list) else []
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
    return []


def insert_shodan_assets(asset_data, failed):
    """
    Query API to insert Shodan data into the shodan_assets table.

    Args:
        data: Dataframe of the shodan data to be inserted into shodan_assets.
    """
    # Endpoint info
    endpoint_url = pe_api_url + "shodan_assets_insert"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"asset_data": asset_data})
    try:
        # Call endpoint
        result = requests.put(
            endpoint_url, headers=headers, data=data, timeout=60
        ).json()
        # Process data and return
        LOGGER.info(result.get("message"))
    except requests.exceptions.HTTPError as errh:
        LOGGER.error(errh)
        failed.append("Failed inserting shodan assets: {}".format(errh))
    except requests.exceptions.ConnectionError as errc:
        LOGGER.error(errc)
        failed.append("Failed inserting shodan assets: {}".format(errc))
    except requests.exceptions.Timeout as errt:
        LOGGER.error(errt)
        failed.append("Failed inserting shodan assets: {}".format(errt))
    except requests.exceptions.RequestException as err:
        LOGGER.error(err)
        failed.append("Failed inserting shodan assets: {}".format(err))
    except json.decoder.JSONDecodeError as err:
        LOGGER.error(err)
        failed.append("Failed inserting shodan assets: {}".format(err))
    return failed


def insert_shodan_vulns(vuln_data, failed):
    """
    Query API to insert Shodan data into the shodan_vulns table.

    Args:
        data: Dataframe of the shodan data to be inserted into shodan_vulns.
    """
    # Endpoint info
    endpoint_url = pe_api_url + "shodan_vulns_insert"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"vuln_data": vuln_data})
    try:
        # Call endpoint
        result = requests.put(
            endpoint_url, headers=headers, data=data, timeout=60
        ).json()
        # Process data and return
        LOGGER.info(result)
    except requests.exceptions.HTTPError as errh:
        LOGGER.error(errh)
        failed.append("Failed inserting shodan assets: {}".format(errh))
    except requests.exceptions.ConnectionError as errc:
        LOGGER.error(errc)
        failed.append("Failed inserting shodan assets: {}".format(errc))
    except requests.exceptions.Timeout as errt:
        LOGGER.error(errt)
        failed.append("Failed inserting shodan assets: {}".format(errt))
    except requests.exceptions.RequestException as err:
        LOGGER.error(err)
        failed.append("Failed inserting shodan assets: {}".format(err))
    except json.decoder.JSONDecodeError as err:
        LOGGER.error(err)
        failed.append("Failed inserting shodan assets: {}".format(err))
    return failed


def get_current_ips_by_org(org_abbrv):
    """
    Get all IPs that are marked as current for the specified org.

    Return:
        All current IPs for org as dataframe
    """
    query = """
    SELECT
        o.organizations_uid,
        o.cyhy_db_name,
        i.ip
    FROM
        ips i join
        organizations o
        on i.organizations_uid = o.organizations_uid
    WHERE
        o.cyhy_db_name = %s AND
        i.current=True
    ORDER BY
        cyhy_db_name
    """
    result = None
    # Attempt DB connection
    conn = connect()
    if conn is None:
        LOGGER.error("get_current_ips_by_org: PE database connection failed")
        raise RuntimeError("PE database connection failed")
    # Attempt query
    try:
        LOGGER.info("get_current_ips_by_org: Querying current IPs for customer")
        result = pd.read_sql(query, conn, params=(org_abbrv,))
        conn.commit()
    except Exception:
        conn.rollback()
        LOGGER.exception("get_current_ips_by_org: Data retieval failed")
        raise
    finally:
        conn.close()
    return result


def get_execs_by_org_uid(org_uid):
    """Get executives for the specified organization_uid."""
    # Build query
    sql = """
    SELECT *
    FROM executives
    WHERE organizations_uid = %s
    """
    # Attempt DB connection
    conn = connect()
    if conn is None:
        LOGGER.error("get_execs_by_org_uid: PE database connection failed")
        raise RuntimeError("PE database connection failed")
    # Attempt query
    try:
        LOGGER.info("get_execs_by_org_uid: Querying executives for customer")
        result = pd.read_sql(sql, conn, params=(org_uid,))
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        LOGGER.exception("get_execs_by_org_uid: Data retieval failed")
        raise
    finally:
        conn.close()


def get_cred_breach_uids(breach_name_list):
    """
    Query API to get the uid for the specified crediential breaches.

    Args:
        breach_name_list: The list of names of the credential breaches

    Return:
        uid for the specified credential breaches
    """
    # Endpoint info
    endpoint_url = pe_api_url + "cred_breaches_by_name"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    try:
        result = requests.post(
            endpoint_url,
            headers=headers,
            json={
                "breach_name_list": [{"breach_name": name} for name in breach_name_list]
            },
            timeout=60,
        ).json()

        # Process data and return
        for row in result:
            if row.get("credential_breaches_uid") is not None:
                row["credential_breaches_uid"] = str(row.get("credential_breaches_uid"))
            if row.get("breach_name") is not None:
                row["breach_name"] = str(row.get("breach_name"))
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


# TODO: Convert to API endpoint in CRASM-4061
def insert_flare_breaches(breach_list):
    """Insert list of flare breaches into the PE DB."""
    if not breach_list:
        return

    rows = [
        (
            str(uuid.uuid1()),
            event.get("breach_name"),
            event.get("description"),
            event.get("exposed_cred_count"),
            event.get("breach_date"),
            event.get("added_date"),
            event.get("modified_date"),
            event.get("data_classes"),
            event.get("password_included"),
            event.get("is_verified"),
            event.get("is_fabricated"),
            event.get("is_sensitive"),
            event.get("is_retired"),
            event.get("is_spam_list"),
            event.get("data_source_uid"),
        )
        for event in breach_list
    ]

    query = """
        INSERT INTO credential_breaches(
            credential_breaches_uid, breach_name, description, exposed_cred_count, breach_date, added_date,
            modified_date, data_classes, password_included, is_verified, is_fabricated, is_sensitive,
            is_retired, is_spam_list, data_source_uid)
        VALUES %s
        ON CONFLICT (breach_name)
        DO UPDATE SET
            password_included = EXCLUDED.password_included;
    """

    conn = connect()
    if conn is None:
        LOGGER.error("insert_flare_breaches: PE database connection failed")
        raise RuntimeError("PE database connection failed")

    cursor = None
    try:
        cursor = conn.cursor()
        LOGGER.info("insert_flare_breaches: upserting %d row(s)", len(rows))
        execute_values(cursor, query, rows)
        conn.commit()
    except Exception:
        conn.rollback()
        LOGGER.exception(
            "insert_flare_breaches: upsert failed for %d row(s)", len(rows)
        )
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


# TODO: Convert to API endpoint in CRASM-4061
def insert_flare_credentials(cred_list):
    """Insert list of flare credentials into the PE DB."""
    if not cred_list:
        return

    rows = [
        (
            str(uuid.uuid1()),
            event.get("email"),
            event.get("organizations_uid"),
            event.get("root_domain"),
            event.get("sub_domain"),
            event.get("breach_name"),
            event.get("modified_date"),
            event.get("credential_breaches_uid"),
            event.get("data_source_uid"),
            event.get("name"),
            event.get("login_id"),
            event.get("phone"),
            event.get("password"),
            event.get("hash_type"),
            event.get("intelx_system_id"),
        )
        for event in cred_list
    ]

    query = """
        INSERT INTO credential_exposures(
            credential_exposures_uid, email, organizations_uid, root_domain, sub_domain, breach_name,
            modified_date, credential_breaches_uid, data_source_uid, name, login_id, phone, password, hash_type, intelx_system_id)
        VALUES %s
        ON CONFLICT (email, breach_name)
        DO UPDATE SET
            modified_date = EXCLUDED.modified_date;
    """

    conn = connect()
    if conn is None:
        LOGGER.error("insert_flare_credentials: PE database connection failed")
        raise RuntimeError("PE database connection failed")

    cursor = None
    try:
        cursor = conn.cursor()
        LOGGER.info("insert_flare_credentials: upserting %d row(s)", len(rows))
        execute_values(cursor, query, rows)
        conn.commit()
    except Exception:
        conn.rollback()
        LOGGER.exception(
            "insert_flare_credentials: upsert failed for %d row(s)", len(rows)
        )
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

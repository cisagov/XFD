#!/usr/bin/env python
"""Query the PE PostgreSQL database."""

# Standard Python Libraries
import datetime
import json
import logging
import sys

# Third-Party Libraries
import pandas as pd
import psycopg2
from psycopg2 import OperationalError, sql
from psycopg2.extensions import AsIs
import requests

from .config import PE_API_REQUEST_TIMEOUT, config, staging_config

# Setup logging to central file
LOGGER = logging.getLogger(__name__)

CONN_PARAMS_DIC = config()

# These need to filled with API key/url path in database.ini
API_DIC = staging_config(section="pe_api")
pe_api_url = API_DIC.get("pe_api_url")
pe_api_key = API_DIC.get("pe_api_key")


def _dataframe_from_api_json(result):
    """Convert report API JSON to a DataFrame; empty or null-only rows -> empty frame."""
    if not result:
        return pd.DataFrame()
    if len(result) == 1 and all(value is None for value in result[0].values()):
        return pd.DataFrame()
    return pd.DataFrame.from_dict(result)


def _empty_foreign_ips_df():
    """Empty foreign-IP frame with columns expected by report metrics/ASM."""
    return pd.DataFrame(
        columns=[
            "organizations_uid",
            "organization",
            "ip",
            "port",
            "protocol",
            "timestamp",
            "product",
            "country_code",
            "location",
        ]
    )


def _empty_dataframe(columns):
    """Empty DataFrame preserving column names for downstream selects."""
    return pd.DataFrame(columns=columns)


def show_psycopg2_exception(err):
    """Handle errors for PostgreSQL issues."""
    err_type, err_obj, traceback = sys.exc_info()
    LOGGER.error(
        "Database connection error: %s on line number: %s", err, traceback.tb_lineno
    )


def _rollback_query_error(conn, error):
    """Log a failed query and reset the connection for follow-up reads."""
    LOGGER.error("There was a problem with your database query %s", error)
    if conn is not None:
        conn.rollback()


def connect():
    """Connect to PostgreSQL database."""
    conn = None
    try:
        conn = psycopg2.connect(**CONN_PARAMS_DIC)
    except OperationalError as err:
        LOGGER.error(err)
        show_psycopg2_exception(err)
        conn = None
    return conn


def close(conn):
    """Close connection to PostgreSQL."""
    conn.close()
    return


def query_domMasq_alerts(org_uid, start_date, end_date):
    """
    Query API to retrieve all domain_alerts data for the specified org_uid and date range.

    Args:
        org_uid: The uid of the organization to retrieve data for
        start_date: The start date of the query's date range
        end_date: The end date of the query's date range

    Return:
        All domain_alerts data for the specified org_uid and date range as a dataframe
    """
    if isinstance(start_date, datetime.datetime) or isinstance(
        start_date, datetime.date
    ):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.datetime) or isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "domain_alerts_by_org_date"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {"org_uid": org_uid, "start_date": start_date, "end_date": end_date}
    )
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return result_df
        result_df.rename(
            columns={
                "sub_domain_uid_id": "sub_domain_uid",
                "data_source_uid_id": "data_source_uid",
                "organizations_uid_id": "organizations_uid",
            },
            inplace=True,
        )
        result_df["date"] = pd.to_datetime(result_df["date"]).dt.date
        return result_df
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


# --- Issue 563, 626? ---
def query_domMasq(org_uid, start_date, end_date):
    """
    Query API to retrieve all domain_permutations data for the specified org_uid and date range.

    Args:
        org_uid: The uid of the organization to retrieve data for
        start_date: The start date of the query's date range
        end_date: The end date of the query's date range

    Return:
        All domain_permutations data for the specified org_uid and date range as a dataframe
    """
    if isinstance(start_date, datetime.datetime) or isinstance(
        start_date, datetime.date
    ):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.datetime) or isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "domain_permu_by_org_date"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {"org_uid": org_uid, "start_date": start_date, "end_date": end_date}
    )
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return result_df
        result_df.rename(
            columns={
                "organizations_uid_id": "organizations_uid",
                "data_source_uid_id": "data_source_uid",
                "sub_domain_uid_id": "sub_domain_uid",
            },
            inplace=True,
        )
        result_df["date_observed"] = pd.to_datetime(result_df["date_observed"]).dt.date
        result_df["date_active"] = pd.to_datetime(result_df["date_active"]).dt.date
        return result_df
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


# --- Issue 564 ---
def get_org_assets_count_past(org_uid, date):
    """
    Query API to retrieve all report_summary_stats data for the specified org_uid and date.

    Args:
        org_uid: The organizations_uid of the specified org
        date: The end date of the specified report period

    Return:
        All report_summary_stats data for the specified org_uid and date as a dataframe
    """
    if isinstance(date, datetime.datetime):
        date = date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "past_asset_counts_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"org_uid": org_uid, "date": date})
    try:
        response = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            LOGGER.info(
                "past_asset_counts_by_org returned %s; using database fallback",
                response.status_code,
            )
            return _past_asset_counts_from_db(org_uid, date)
        result = response.json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return result_df
        result_df.rename(
            columns={
                "organizations_uid_id": "organizations_uid",
            },
            inplace=True,
        )
        result_df["start_date"] = pd.to_datetime(result_df["start_date"]).dt.date
        result_df["end_date"] = pd.to_datetime(result_df["end_date"]).dt.date
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
    except (KeyError, IndexError, ValueError) as err:
        LOGGER.info(err)

    return _past_asset_counts_from_db(org_uid, date)


# TODO: Convert to API endpoint in CRASM-4061
def _past_asset_counts_from_db(org_uid, date):
    """Load prior-period ASM stats directly from report_summary_stats."""
    try:
        result_df = get_org_assets_count_past_tsql(org_uid, date)
        if result_df is None:
            return pd.DataFrame()
        return result_df
    except Exception as exc:
        LOGGER.warning("Past asset counts database query failed: %s", exc)
        return pd.DataFrame()


# --- Issue 604 ---
def query_extra_ips(org_uid):
    """
    Query API to retrieve all extra IPs for an organization.

    Args:
        org_uid: uid of the specified organization

    Return:
        All the extra IPs belonging to the specified org as a dataframe
    """
    # Endpoint info
    endpoint_url = pe_api_url + "extra_ips_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"org_uid": org_uid})
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_list = list({d["ip"] for d in result})
        return result_list
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
    except (KeyError, TypeError) as err:
        LOGGER.info(err)
    return []


# --- Issue 616 ---
def query_cidrs_by_org(org_uid):
    """
    Query API to retrieve all CIDRs for an organization.

    Args:
        org_uid: uid of the specified organization

    Return:
        All the CIDRs belonging to the specified org as a dataframe
    """
    # Endpoint info
    endpoint_url = pe_api_url + "cidrs_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"org_uid": org_uid})
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return _empty_dataframe(["network"])
        result_df.rename(
            columns={
                "organizations_uid_id": "organizations_uid",
                "data_source_uid_id": "data_source_uid",
            },
            inplace=True,
        )
        result_df["first_seen"] = pd.to_datetime(result_df["first_seen"]).dt.date
        result_df["last_seen"] = pd.to_datetime(result_df["last_seen"]).dt.date
        return result_df
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
    return _empty_dataframe(["network"])


# --- Issue 619 ---
def query_software(org_uid, start_date, end_date):
    """
    Query API to retrieve all distinct software products for an organization.

    Args:
        org_uid: uid of the specified organization

    Return:
        All the distinct software belonging to the specified org as a dataframe
    """
    if isinstance(start_date, datetime.date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "software_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {
            "org_uid": org_uid,
            "start_date": start_date,
            "end_date": end_date,
        }
    )
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return _empty_dataframe(["product"])
        return result_df
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
    return _empty_dataframe(["product"])


# --- Issue 621 ---
def query_foreign_IPs(org_uid):
    """
    Query API to retrieve all foreign ips for an organization.

    Args:
        org_uid: uid of the specified organization

    Return:
        All the foreign ips belonging to the specified org as a dataframe
    """
    # Endpoint info
    endpoint_url = pe_api_url + "foreign_ips_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"org_uid": org_uid})
    try:
        response = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            LOGGER.info(
                "foreign_ips_by_org returned %s; using database fallback",
                response.status_code,
            )
            return query_foreign_IPs_tsql(org_uid)
        result = response.json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return _empty_foreign_ips_df()
        result_df.rename(
            columns={
                "organizations_uid_id": "organizations_uid",
                "data_source_uid_id": "data_source_uid",
            },
            inplace=True,
        )
        return result_df
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
    except (KeyError, IndexError, ValueError) as err:
        LOGGER.error(err)

    try:
        return query_foreign_IPs_tsql(org_uid)
    except Exception as exc:
        LOGGER.warning("Foreign IPs database query failed: %s", exc)
        return _empty_foreign_ips_df()


# --- Issue 622 ---
def query_roots(org_uid):
    """
    Query API to retrieve all root domains for an organization.

    Args:
        org_uid: uid of the specified organization

    Return:
        All the root domains belonging to the specified org as a dataframe
    """
    # Endpoint info
    endpoint_url = pe_api_url + "root_domains_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"org_uid": org_uid})
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return _empty_dataframe(["root_domain"])
        return result_df
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
    return _empty_dataframe(["root_domain"])


# --- Issue 623 ---
def query_creds_view(org_uid, start_date, end_date):
    """
    Query API to retrieve vw_breachcomp data for an org and date range.

    Args:
        org_uid: uid of the specified organization
        start_date: start date of report period
        end_date: end date of report period

    Return:
        vw_breachcomp data for the specified org  and date range as a dataframe
    """
    if isinstance(start_date, datetime.date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "breachcomp_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {
            "org_uid": org_uid,
            "start_date": start_date,
            "end_date": end_date,
        }
    )
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return result_df
        result_df["breach_date"] = pd.to_datetime(result_df["breach_date"]).dt.date
        # result_df["added_date"] = pd.to_datetime(result_df["added_date"]).dt.date
        # result_df["modified_date"] = pd.to_datetime(result_df["modified_date"]).dt.date
        result_df["added_date"] = pd.to_datetime(result_df["added_date"])
        result_df["modified_date"] = pd.to_datetime(result_df["modified_date"])
        return result_df
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


# --- Issue 624 ---
def query_credsbyday_view(org_uid, start_date, end_date):
    """
    Query API to retrieve vw_breachcomp_credsbydate data for an org and date range.

    Args:
        org_uid: uid of the specified organization
        start_date: start date of report period
        end_date: end date of report period

    Return:
        vw_breachcomp_credsbydate data for the specified org  and date range as a dataframe
    """
    if isinstance(start_date, datetime.date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "credsbydate_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {
            "org_uid": org_uid,
            "start_date": start_date,
            "end_date": end_date,
        }
    )
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return result_df
        result_df["mod_date"] = pd.to_datetime(result_df["mod_date"]).dt.date
        return result_df
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


# --- Issue 625 ---
def query_breachdetails_view(org_uid, start_date, end_date):
    """
    Query API to retrieve vw_breachcomp_breachdetails data for an org and date range.

    Args:
        org_uid: uid of the specified organization
        start_date: start date of report period
        end_date: end date of report period

    Return:
        vw_breachcomp_breachdetails data for the specified org  and date range as a dataframe
    """
    if isinstance(start_date, datetime.date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "breachdetails_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {
            "org_uid": org_uid,
            "start_date": start_date,
            "end_date": end_date,
        }
    )
    try:
        # Call endpoint
        result = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        # Process data and return
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return result_df
        result_df["mod_date"] = pd.to_datetime(result_df["mod_date"]).dt.date
        result_df["breach_date"] = pd.to_datetime(result_df["breach_date"]).dt.date
        result_df.rename(
            columns={"mod_date": "modified_date"},
            inplace=True,
        )
        return result_df
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


# --- Issue 628 ---
# API conversion still needs to be completed


# --- Issue 629 ---
def query_darkweb(org_uid, start_date, end_date, table):
    """
    Query API to retrieve darkweb data for an organization.

    Args:
        org_uid: uid of the specified organization
        start_date: start date of the report period
        end_date: end date of the report period
        table: darkweb related table to query

    Return:
        Darkweb data belonging to the specified org as a dataframe
    """
    if isinstance(start_date, datetime.date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "darkweb_data"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    # Check table name is valid
    if table in [
        "mentions",
        "alerts",
        "vw_darkweb_mentionsbydate",
        "vw_darkweb_inviteonlymarkets",
        "vw_darkweb_socmedia_mostactposts",
        "vw_darkweb_mostactposts",
        "vw_darkweb_execalerts",
        "vw_darkweb_assetalerts",
        "vw_darkweb_threatactors",
        "vw_darkweb_potentialthreats",
        "vw_darkweb_sites",
    ]:
        data = json.dumps(
            {
                "org_uid": org_uid,
                "start_date": start_date,
                "end_date": end_date,
                "table": table,
            }
        )
        try:
            # Call endpoint
            result = requests.post(
                endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
            ).json()
            # Process data and return
            result_df = _dataframe_from_api_json(result)
            if result_df.empty:
                return result_df
            result_df.rename(
                columns={
                    "organizations_uid_id": "organizations_uid",
                    "data_source_uid_id": "data_source_uid",
                    "count": "Count",
                    "creator": "Creator",
                    "grade": "Grade",
                    "events": "Events",
                    "title": "Title",
                    "comments_count": "Comments Count",
                    "site": "Site",
                    "threats": "Threats",
                },
                inplace=True,
            )
            if "date" in result_df.columns:
                result_df["date"] = pd.to_datetime(result_df["date"]).dt.date
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
    else:
        LOGGER.error("query_darkweb() error, invalid table")


# TODO: Convert to API endpoint in CRASM-4061
def query_darkweb_asset_alerts(org_uid, start_date, end_date, table):
    """Retrieve asset alerts for the specified organization and date range."""
    conn = connect()
    sql = """
    SELECT
        q1.site AS "Site",
        q1.title AS "Title",
        count(*) AS "Events"
    FROM (
        SELECT *
        FROM alerts a
        WHERE
            a.organizations_uid = %(org_uid)s AND
            a.date between %(start_date)s AND %(end_date)s AND
            a.alert_name !~~ '%%executive%%'::text AND
            a.site IS NOT NULL AND
            a.site <> 'NaN'::text
        ) q1
    GROUP BY
        q1.site,
        q1.title,
        q1.organizations_uid
    ORDER BY (count(*)) DESC;
    """
    df = pd.read_sql(
        sql,
        conn,
        params={
            "org_uid": org_uid,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    conn.close()
    return df


# --- Issue 630 ---
def query_darkweb_cves(table):
    """
    Query API to retrieve the entire top_cves table.

    Return:
        top_cve table as a dataframe
    """
    _TOP_CVE_COLUMNS = [
        "top_cves_uid",
        "cve_id",
        "dynamic_rating",
        "nvd_base_score",
        "date",
        "summary",
        "data_source_uid",
    ]
    endpoint_url = pe_api_url + "darkweb_cves"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    try:
        result = requests.post(
            endpoint_url, headers=headers, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        result_df = _dataframe_from_api_json(result)
        if result_df.empty:
            return pd.DataFrame(columns=_TOP_CVE_COLUMNS)
        result_df.rename(
            columns={
                "data_source_uid_id": "data_source_uid",
            },
            inplace=True,
        )
        result_df["date"] = pd.to_datetime(result_df["date"]).dt.date
        return result_df
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
    return pd.DataFrame(columns=_TOP_CVE_COLUMNS)


# --- Issue 632 ---
def execute_scorecard(summary_dict):
    """
    Insert a record for an organization into the report_summary_stats table.

    On org_uid/star_date conflict, update the old record with the new data

    Args:
        summary_dict: Dictionary of column names and values to be inserted
    """
    input_dict = summary_dict.copy()
    input_dict["start_date"] = input_dict["start_date"].strftime("%Y-%m-%d")
    input_dict["end_date"] = input_dict["end_date"].strftime("%Y-%m-%d")
    input_dict["insecure_port_count"] = int(input_dict["insecure_port_count"])
    input_dict["verified_vuln_count"] = int(input_dict["verified_vuln_count"])
    if "dns" in input_dict:
        input_dict.pop("dns")
    if "circles_df" in input_dict:
        input_dict.pop("circles_df")
    if "org_name" in input_dict:
        input_dict.pop("org_name")
    # Fill in any empty fields in dictionary
    for key in input_dict.keys():
        if ("count" in key or key == "num_ports") and input_dict.get(key) is None:
            input_dict.update({key: 0})
    # Endpoint info
    endpoint_url = pe_api_url + "rss_insert"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(input_dict)
    try:
        # Call endpoint
        requests.put(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        ).json()
        LOGGER.info("Successfully inserted new record in report_summary_stats table")
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


# --- Issue 633 (paginated) ---
def query_subs(org_uid):
    """
    Query API to retrieve all subdomains for an organization.

    Args:
        org_uid: uid of the specified organization

    Return:
        All the subdomains belonging to the specified org as a dataframe
    """
    _SUB_COLUMNS = [
        "sub_domain_uid",
        "sub_domain",
        "root_domain_uid_id",
        "root_domain_uid__root_domain",
        "data_source_uid_id",
        "dns_record_uid_id",
        "status",
        "first_seen",
        "last_seen",
        "current",
        "identified",
        "origin_root_domain",
        "pe_discovered_asset",
    ]
    endpoint_url = pe_api_url + "sub_domains_by_org"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    total_num_pages = 1
    page_num = 1
    total_data = []
    try:
        while page_num <= total_num_pages:
            data = json.dumps({"org_uid": org_uid, "page": page_num, "per_page": 50000})
            result = requests.post(
                endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
            ).json()
            total_data += result.get("data") or []
            total_num_pages = result.get("total_pages", 1)
            LOGGER.info("Retrieved page: %s of %s", page_num, total_num_pages)
            page_num += 1
        result_df = _dataframe_from_api_json(total_data)
        if result_df.empty:
            return pd.DataFrame(columns=_SUB_COLUMNS)
        result_df.rename(
            columns={
                "root_domain_uid__root_domain": "origin_root_domain",
                "identified": "pe_discovered_asset",
            },
            inplace=True,
        )
        return result_df
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
    return pd.DataFrame(columns=_SUB_COLUMNS)


# TODO: Convert to API endpoint in CRASM-4061
def get_subs_origin_ip(sub_df, org_uid):
    """Given a df of identified subdomains, retrieve their origin IPs."""
    if sub_df.empty:
        return pd.DataFrame(columns=["sub_domain", "origin_ip", "origin_cidr"])
    sub_domains = sub_df["sub_domain"].tolist()
    conn = connect()
    sql = """
    SELECT
        sd.sub_domain,
        ips.ip as origin_ip,
        cidrs.network as origin_cidr
    FROM
        sub_domains sd JOIN
        ips_subs ON
        sd.sub_domain_uid = ips_subs.sub_domain_uid JOIN
        ips ON
        ips_subs.ip_hash = ips.ip_hash JOIN
        cidrs ON
        ips.origin_cidr = cidrs.cidr_uid
    WHERE
        sd.sub_domain = ANY(%(sub_domains)s) AND
        cidrs.organizations_uid = %(org_uid)s
    """
    df = pd.read_sql(sql, conn, params={"sub_domains": sub_domains, "org_uid": org_uid})
    conn.close()
    return df


# --- Issue 634 ---
def query_previous_period(org_uid, prev_end_date):
    """
    Query API for previous period report_summary_stats data for a specific org.

    Args:
        org_uid: The organizations_uid of the specified organization
        prev_end_date: The end_date of the previous report period

    Return:
        Report_summary_stats data from the previous report period for a specific org as a dataframe
    """
    prev_end_date_value = prev_end_date
    prev_end_date = prev_end_date.strftime("%Y-%m-%d")
    # Endpoint info
    endpoint_url = pe_api_url + "rss_prev_period"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps(
        {
            "org_uid": org_uid,
            "prev_end_date": prev_end_date,
        }
    )
    rss_prev_period_result = None
    try:
        response = requests.post(
            endpoint_url, headers=headers, data=data, timeout=PE_API_REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            rss_prev_period_result = response.json()
        else:
            LOGGER.info(
                "rss_prev_period returned %s; using database fallback",
                response.status_code,
            )
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

    if not rss_prev_period_result:
        try:
            return query_previous_period_tsql(org_uid, prev_end_date_value)
        except Exception as exc:
            LOGGER.warning("Previous period database query failed: %s", exc)

    # Once task finishes, return result
    if rss_prev_period_result:
        rss_prev_period_result = rss_prev_period_result[0]
        # Return results if valid
        assets_dict = {
            "last_ip_count": rss_prev_period_result["ip_count"],
            "last_root_domain_count": rss_prev_period_result["root_count"],
            "last_sub_domain_count": rss_prev_period_result["sub_count"],
            "last_cred_password_count": rss_prev_period_result["cred_password_count"],
            "last_sus_vuln_addrs_count": rss_prev_period_result[
                "suspected_vuln_addrs_count"
            ],
            "last_suspected_vuln_count": rss_prev_period_result["suspected_vuln_count"],
            "last_insecure_port_count": rss_prev_period_result["insecure_port_count"],
            "last_actor_activity_count": rss_prev_period_result["threat_actor_count"],
        }
    else:
        # If no results, return all 0 dict
        assets_dict = {
            "last_ip_count": 0,
            "last_root_domain_count": 0,
            "last_sub_domain_count": 0,
            "last_cred_password_count": 0,  # nosec B105
            "last_sus_vuln_addrs_count": 0,
            "last_suspected_vuln_count": 0,
            "last_insecure_port_count": 0,
            "last_actor_activity_count": 0,
        }
    return assets_dict


#  ---------- PE-Score API Queries, Issue 635 ----------
# --- Issue 635 ---
# TODO: Convert to API endpoint in CRASM-4061
def refresh_asset_counts_vw():
    """Refresh materialized views used by report generation."""
    for view_name in (
        "mat_vw_breachcomp",
        "mat_vw_breachcomp_breachdetails",
        "mat_vw_breachcomp_credsbydate",
    ):
        LOGGER.info("Refreshing %s", view_name)
        conn = connect()
        cur = conn.cursor()
        cur.execute(
            sql.SQL("REFRESH MATERIALIZED VIEW {} WITH DATA").format(
                sql.Identifier(view_name)
            )
        )
        conn.commit()


# --- Issue 628 ---
# TODO: Convert to API endpoint in CRASM-4061
def query_shodan(org_uid, start_date, end_date, table):
    """Query Shodan table."""
    conn = connect()
    try:
        df = pd.DataFrame()
        df_list = []
        chunk_size = 1000
        sql = """SELECT * FROM %(table)s
        WHERE organizations_uid = %(org_uid)s
        AND timestamp BETWEEN %(start_date)s AND %(end_date)s"""
        count = 0
        # Batch SQL call to reduce memory (https://pythonspeed.com/articles/pandas-sql-chunking/)
        for chunk_df in pd.read_sql(
            sql,
            conn,
            params={
                "table": AsIs(table),
                "org_uid": org_uid,
                "start_date": start_date,
                "end_date": end_date,
            },
            chunksize=chunk_size,
        ):
            count += 1
            df_list.append(chunk_df)

        if len(df_list) == 0:
            df = pd.read_sql(
                sql,
                conn,
                params={
                    "table": AsIs(table),
                    "org_uid": org_uid,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
        else:
            df = pd.concat(df_list, ignore_index=True)
        return df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
        return pd.DataFrame()
    finally:
        if conn is not None:
            close(conn)


# --- Issue 018 atc-framework ---
# TODO: Convert to API endpoint in CRASM-4061
def get_orgs(conn):
    """Query organizations table for orgs we report on."""
    try:
        cur = conn.cursor()
        sql = """SELECT * FROM organizations
        WHERE report_on is True
        ORDER BY cyhy_db_name"""
        cur.execute(sql)
        pe_orgs = cur.fetchall()
        cur.close()
        return pe_orgs
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)


def get_orgs_pass(conn, password_key):
    """Return (cyhy_db_name, decrypted_password) for every report_on org."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cyhy_db_name, PGP_SYM_DECRYPT(password::bytea, %s) "
                "FROM organizations WHERE report_on",
                (password_key,),
            )
            return cur.fetchall()
    finally:
        close(conn)


# TODO: Convert to API endpoint in CRASM-4061
def get_org_assets_count_past_tsql(org_uid, date):
    """Get asset counts for an organization."""
    conn = connect()
    sql = """select * from report_summary_stats rss
                where organizations_uid = %(org_id)s
                and end_date = %(date)s;"""
    df = pd.read_sql(sql, conn, params={"org_id": org_uid, "date": date})
    conn.close()
    return df


# TODO: Convert to API endpoint in CRASM-4061
def get_org_assets_count(org_uid, start_date, end_date):
    """Retrieve ASM summary stats for the specified org."""
    if isinstance(start_date, datetime.date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    conn = connect()
    org_params = {"org_uid": org_uid}
    date_params = {
        "org_uid": org_uid,
        "start_date": start_date,
        "end_date": end_date,
    }
    gen_info_df = pd.DataFrame()
    roots_df = pd.DataFrame()
    subs_df = pd.DataFrame()
    cidr_ips_df = pd.DataFrame(columns=["ip_count"])
    noncidr_ips_df = pd.DataFrame()
    ports_df = pd.DataFrame()
    cidrs_df = pd.DataFrame()
    portprotos_df = pd.DataFrame()
    software_df = pd.DataFrame()
    forip_df = pd.DataFrame()
    # Retrieve general org info
    sql_gen_info = """
    SELECT * FROM organizations WHERE organizations_uid = %(org_uid)s
    """
    try:
        gen_info_df = pd.read_sql(sql_gen_info, conn, params=org_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)
    # Retrieve root domain info
    sql_roots = """
    SELECT * FROM root_domains WHERE organizations_uid = %(org_uid)s AND enumerate_subs=TRUE
    """
    try:
        roots_df = pd.read_sql(sql_roots, conn, params=org_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)
    # Retrieve sub domain info
    if not roots_df.empty:
        sql_subs = """
        SELECT * FROM sub_domains
        WHERE root_domain_uid = ANY(%(root_uids)s::uuid[]) AND current=TRUE
        """
        try:
            subs_df = pd.read_sql(
                sql_subs,
                conn,
                params={"root_uids": roots_df["root_domain_uid"].tolist()},
            )
        except (Exception, psycopg2.DatabaseError) as error:
            _rollback_query_error(conn, error)

    # Retrieve IP info
    sql_cidr_ips = """
    SELECT
        c.network,
        CASE
            WHEN family(c.network::inet) = 4 THEN
            CASE
                WHEN masklen(c.network::inet) < 31 THEN (2::double precision ^ (32 - (( SELECT masklen(c.network::inet) AS masklen)))::double precision) - 2::double precision
                WHEN masklen(c.network::inet) = 31 THEN 2::double precision
                WHEN masklen(c.network::inet) = 32 THEN 1::double precision
                ELSE NULL::double precision
            END
            WHEN family(c.network::inet) = 6 THEN
            CASE
                WHEN masklen(c.network::inet) < 127 THEN (2::double precision ^ (128 - (( SELECT masklen(c.network::inet) AS masklen)))::double precision) - 2::double precision
                WHEN masklen(c.network::inet) = 127 THEN 2::double precision
                WHEN masklen(c.network::inet) = 128 THEN 1::double precision
                ELSE NULL::double precision
            END
            ELSE NULL::double precision
        END AS ip_count
    FROM cidrs c
    WHERE
        c.current AND
        c.organizations_uid = %(org_uid)s
    """
    try:
        cidr_ips_df = pd.read_sql(sql_cidr_ips, conn, params=org_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)
    sql_noncidr_ips = """
    SELECT DISTINCT
        rd.organizations_uid,
        i.ip
    FROM ips i
        JOIN ips_subs si ON si.ip_hash = i.ip_hash
        JOIN sub_domains sd ON sd.sub_domain_uid = si.sub_domain_uid
        JOIN root_domains rd ON rd.root_domain_uid = sd.root_domain_uid
    WHERE
        sd.current AND
        i.current AND
        i.origin_cidr IS NULL AND
        rd.organizations_uid = %(org_uid)s
    """
    try:
        noncidr_ips_df = pd.read_sql(sql_noncidr_ips, conn, params=org_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)
    total_ips = int(cidr_ips_df["ip_count"].sum()) + len(noncidr_ips_df)
    # Retrieve ports info
    sql_ports = """
    SELECT DISTINCT ip, port::text FROM shodan_assets WHERE organizations_uid = %(org_uid)s AND timestamp BETWEEN %(start_date)s AND %(end_date)s
    UNION
    SELECT DISTINCT ip, port FROM shodan_vulns WHERE organizations_uid = %(org_uid)s AND timestamp BETWEEN %(start_date)s AND %(end_date)s
    """
    try:
        ports_df = pd.read_sql(sql_ports, conn, params=date_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)
    # Retrieve CIDR info
    sql_cidrs = """
    SELECT * FROM cidrs WHERE organizations_uid = %(org_uid)s AND current=True
    """
    try:
        cidrs_df = pd.read_sql(sql_cidrs, conn, params=org_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)
    # Retrieve port/protocol info
    sql_portprotos = """
    SELECT DISTINCT port::text, protocol FROM shodan_assets WHERE organizations_uid = %(org_uid)s AND timestamp BETWEEN %(start_date)s AND %(end_date)s
    """
    try:
        portprotos_df = pd.read_sql(sql_portprotos, conn, params=date_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)
    # Retrieve software info
    sql_software = """
    SELECT DISTINCT product FROM shodan_assets WHERE organizations_uid = %(org_uid)s AND timestamp BETWEEN %(start_date)s AND %(end_date)s AND product IS NOT NULL
    """
    try:
        software_df = pd.read_sql(sql_software, conn, params=date_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)
    # Retrieve foreign IP info
    sql_forip = """
    SELECT * FROM shodan_assets WHERE organizations_uid = %(org_uid)s AND timestamp BETWEEN %(start_date)s AND %(end_date)s AND country_code != 'US' AND country_code IS NOT NULL
    """
    try:
        forip_df = pd.read_sql(sql_forip, conn, params=date_params)
    except (Exception, psycopg2.DatabaseError) as error:
        _rollback_query_error(conn, error)

    conn.close()
    cyhy_db_name = (
        gen_info_df["cyhy_db_name"].iloc[0] if not gen_info_df.empty else "N/A"
    )
    # Format and return results
    result_dict = {
        "org_uid": org_uid,
        "cyhy_db_name": cyhy_db_name,
        "num_root_domain": len(roots_df),
        "num_sub_domain": len(subs_df),
        "num_ips": total_ips,
        "num_ports": len(ports_df),
        "num_cidrs": len(cidrs_df),
        "num_ports_protocols": len(portprotos_df),
        "num_software": len(software_df),
        "num_foreign_ips": len(forip_df),
    }
    return result_dict


# TODO: Convert to API endpoint in CRASM-4061
def query_ports_protocols(org_uid, start_date, end_date):
    """Query distinct ports and protocols by org."""
    if isinstance(start_date, datetime.date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.date):
        end_date = end_date.strftime("%Y-%m-%d")
    conn = connect()
    sql = """select distinct sa.port,sa.protocol
            from shodan_assets sa
            where sa.organizations_uid  = %(org_uid)s and
            timestamp between %(start_date)s and %(end_date)s;
            """
    df = pd.read_sql(
        sql,
        conn,
        params={
            "org_uid": org_uid,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    conn.close()
    return df


# TODO: Convert to API endpoint in CRASM-4061
def query_foreign_IPs_tsql(org_uid):
    """Query distinct software by org."""
    conn = connect()
    sql = """select * from
            shodan_assets sa
            where (sa.country_code != 'US' and sa.country_code notnull)
            and sa.organizations_uid  = %(org_uid)s;
            """
    df = pd.read_sql(sql, conn, params={"org_uid": org_uid})
    conn.close()
    return df


# TODO: Convert to API endpoint in CRASM-4061
def query_previous_period_tsql(org_uid, previous_end_date):
    """Get summary statistics for the previous period."""
    conn = connect()
    cur = conn.cursor()
    sql = """select
                sum.ip_count, sum.root_count, sum.sub_count, cred_password_count,
                sum.suspected_vuln_addrs_count, sum.suspected_vuln_count, sum.insecure_port_count,
                sum.threat_actor_count

            from report_summary_stats sum
            where sum.organizations_uid = %s and sum.end_date = %s"""
    cur.execute(sql, [org_uid, previous_end_date])
    source = cur.fetchone()
    cur.close()
    conn.close()
    if source:
        assets_dict = {
            "last_ip_count": source[0],
            "last_root_domain_count": source[1],
            "last_sub_domain_count": source[2],
            "last_cred_password_count": source[3],
            "last_sus_vuln_addrs_count": source[4],
            "last_suspected_vuln_count": source[5],
            "last_insecure_port_count": source[6],
            "last_actor_activity_count": source[7],
        }
    else:
        assets_dict = {
            "last_ip_count": 0,
            "last_root_domain_count": 0,
            "last_sub_domain_count": 0,
            "last_cred_password_count": 0,  # nosec B105
            "last_sus_vuln_addrs_count": 0,
            "last_suspected_vuln_count": 0,
            "last_insecure_port_count": 0,
            "last_actor_activity_count": 0,
        }

    return assets_dict


# TODO: Convert to API endpoint in CRASM-4061
def get_demo_orgs(conn):
    """Query organizations table for orgs we report on."""
    try:
        cur = conn.cursor()
        sql = """SELECT * FROM organizations
        WHERE demo is True
        ORDER BY cyhy_db_name"""
        cur.execute(sql)
        pe_orgs = cur.fetchall()
        cur.close()
        return pe_orgs
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)


# TODO: Convert to API endpoint in CRASM-4061
def get_specific_orgs(conn, org_list):
    """Query info for the specified organizations."""
    try:
        cur = conn.cursor()
        sql = """
        SELECT * FROM organizations
        WHERE cyhy_db_name = ANY(%(org_list)s)
        ORDER BY cyhy_db_name
        """
        cur.execute(sql, {"org_list": org_list})
        pe_orgs = cur.fetchall()
        cur.close()
        return pe_orgs
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)


# TODO: Convert to API endpoint in CRASM-4061
def query_flare_all_events(org_uid, start_date, end_date):
    """Retrieve all Flare events for the specified organization and time period."""
    sql = """
    SELECT *
    FROM flare_events
    WHERE
        organizations_uid = %(org_uid)s
        AND
        event_date BETWEEN %(start_date)s AND %(end_date)s
    """
    conn = connect()
    df = pd.read_sql(
        sql,
        conn,
        params={
            "org_uid": org_uid,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    conn.close()
    # Return results
    return df


# TODO: Convert to API endpoint in CRASM-4061
def query_flare_event_type_defs():
    """Retrieve definitions for all Flare event types used in the report."""
    sql = """
    SELECT event_type, definition
    FROM flare_event_types
    WHERE used_in_report = True
    ORDER BY event_type ASC
    """
    conn = connect()
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


# TODO: Convert to API endpoint in CRASM-4061
def query_flare_mentions_by_date(start_date, end_date, org_uid, mention_event_types):
    """Get the number of Flare mention events for each day in the specified date range."""
    sql = """
    SELECT
        fe.organizations_uid,
        fe.event_date as date,
        count(*) AS "Count"
    FROM flare_events fe
    WHERE
        fe.event_date BETWEEN %(start_date)s AND %(end_date)s AND
        fe.organizations_uid = %(org_uid)s AND
        fe.event_type = ANY(%(event_types)s)
    GROUP BY fe.organizations_uid, fe.event_date
    ORDER BY fe.event_date ASC
    """
    conn = connect()
    df = pd.read_sql(
        sql,
        conn,
        params={
            "start_date": start_date,
            "end_date": end_date,
            "org_uid": org_uid,
            "event_types": mention_event_types,
        },
    )
    conn.close()
    # Return results
    return df


# TODO: Convert to API endpoint in CRASM-4061
def query_shodan_top_cves():
    """Retrieve the most recent top 10 CVEs from top_cves_shodan."""
    sql = """
    SELECT
        cve_id,
        epss_score,
        nvd_base_score,
        collection_date,
        summary,
        data_source_uid
    FROM
        top_cves_shodan
    ORDER BY
        collection_date DESC NULLS LAST
    LIMIT 10
    """
    conn = connect()
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


# TODO: Convert to API endpoint in CRASM-4061
def query_flare_creds_view(org_uid, start_date, end_date):
    """Query Flare version of the vw_breachcomp view."""
    conn = connect()
    try:
        # Build query
        sql = """SELECT
            credential_exposures_uid,
            organizations_uid,
            added_date,
            modified_date,
            email,
            password,
            hash_type,
            login_url,
            root_domain,
            sub_domain,
            breach_date,
            breach_name,
            description,
            password_included,
            data_source_uid
        FROM vw_flare_breachcomp
        WHERE organizations_uid = %(org_uid)s
        AND modified_date BETWEEN %(start_date)s AND %(end_date)s"""
        # Execute query
        df = pd.read_sql(
            sql,
            conn,
            params={"org_uid": org_uid, "start_date": start_date, "end_date": end_date},
        )
        # Return results
        return df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)


# TODO: Convert to API endpoint in CRASM-4061
def query_flare_credsbyday_view(org_uid, start_date, end_date):
    """Query Flare version of the vw_breachcomp_credsbydate view."""
    conn = connect()
    try:
        # Build query
        sql = """SELECT mod_date, no_password, password_included
        FROM vw_flare_breachcomp_credsbydate
        WHERE organizations_uid = %(org_uid)s
        AND mod_date BETWEEN %(start_date)s AND %(end_date)s"""
        # Execute query
        df = pd.read_sql(
            sql,
            conn,
            params={"org_uid": org_uid, "start_date": start_date, "end_date": end_date},
        )
        # Return results
        return df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)


# TODO: Convert to API endpoint in CRASM-4061
def query_flare_breachdetails_view(org_uid, start_date, end_date):
    """Query Flare version of the vw_breachcomp_breachdetails view."""
    conn = connect()
    try:
        # Build query
        sql = """SELECT breach_name, mod_date modified_date, breach_date, password_included, number_of_creds
        FROM vw_flare_breachcomp_breachdetails
        WHERE organizations_uid = %(org_uid)s
        AND mod_date BETWEEN %(start_date)s AND %(end_date)s"""
        # Execute query
        df = pd.read_sql(
            sql,
            conn,
            params={"org_uid": org_uid, "start_date": start_date, "end_date": end_date},
        )
        # Return results
        return df
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error("There was a problem with your database query %s", error)
    finally:
        if conn is not None:
            close(conn)

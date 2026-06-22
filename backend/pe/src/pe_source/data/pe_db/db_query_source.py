"""PE database helpers used by dnstwist (API reads + direct psycopg2 writes)."""

# Standard Python Libraries
from datetime import datetime
from decimal import Decimal
import json
import logging
import sys

# Third-Party Libraries
import pandas as pd
import psycopg2
from psycopg2 import OperationalError
import requests

# cisagov Libraries
from pe_reports.data.config import config, staging_config

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
    """Query API to retrieve data for all demo or report_on orgs."""
    endpoint_url = pe_api_url + "organizations_demo_or_report_on"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    result = requests.get(endpoint_url, headers=headers, timeout=60).json()
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


def get_data_source_uid(source):
    """Query API to get the uid for the specified data source."""
    endpoint_url = pe_api_url + "data_source_by_name"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"name": source})
    result = requests.post(
        endpoint_url, headers=headers, data=data, timeout=60
    ).json()
    tup_result = [tuple(row.values()) for row in result]
    return tup_result[0][0]


def getSubdomain(domain):
    """Query API to get the uid for the specified subdomain."""
    endpoint_url = pe_api_url + "subdomain_uid_by_domain"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"domain": domain})
    result = requests.post(
        endpoint_url, headers=headers, data=data, timeout=60
    ).json()
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
    result = requests.put(
        endpoint_url, headers=headers, data=data, timeout=60
    ).json()
    LOGGER.info(result)


def org_root_domains(org_uid):
    """Query API to get the root domains for the specified org uid."""
    endpoint_url = pe_api_url + "rootdomains_by_org_uid"
    headers = {
        "Content-Type": "application/json",
        "access_token": pe_api_key,
    }
    data = json.dumps({"org_uid": org_uid})
    result = requests.post(
        endpoint_url, headers=headers, data=data, timeout=60
    ).json()
    result_df = pd.DataFrame.from_dict(result)
    result_df.rename(
        columns={"root_domain_uid": "root_uid", "organizations_uid": "org_uid"},
        inplace=True,
    )
    return result_df.to_dict("records")

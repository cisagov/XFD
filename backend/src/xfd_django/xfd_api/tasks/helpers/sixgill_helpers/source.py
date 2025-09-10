"""Scripts for importing Sixgill data into PE Postgres database."""

# Standard Python Libraries
import logging

# Third-Party Libraries
import pandas as pd

from .api import (
    alerts_count,
    alerts_list,
    credential_auth,
    dve_top_cves,
    intel_post,
    intel_post_next,
    org_assets,
)
from .config import cybersix_token

LOGGER = logging.getLogger(__name__)


def alerts(org_id, sixgill_org_id):
    """Get actionable alerts for an organization."""
    # Get overall number of alerts for this org
    count = alerts_count(sixgill_org_id)
    count_total = count["total"]
    LOGGER.info("Total alerts for %s: %d", org_id, count_total)

    # Begin Retrieving all alerts
    token = cybersix_token()
    fetch_size = 50
    all_alerts = []
    df_all_alerts = pd.DataFrame()
    # Retrieve alert data for each chunk
    for offset in range(0, count_total, fetch_size):
        try:
            LOGGER.info(
                "Working on %s alert chunk at offset %d out of %d",
                org_id,
                offset,
                count_total,
            )
            # Make API call
            [resp, token] = alerts_list(token, sixgill_org_id, fetch_size, offset)
            # Process data
            df_alerts = pd.DataFrame.from_dict(resp)
            # df_alerts.drop(columns=["sub_alerts"], inplace=True) # large unused data field
            all_alerts.append(df_alerts)
            df_all_alerts = pd.concat(all_alerts).reset_index(drop=True)
        except Exception as e:
            LOGGER.error("Issue fetching alert data chunk at offset: %d", offset)
            LOGGER.error(e)
            continue

    # Fetch the full content of each alert
    # for i, r in df_all_alerts.iterrows():
    #     LOGGER.info(r["id"])
    #     content = alerts_content(org_id, r["id"])
    #     df_all_alerts.at[i, "content"]

    return df_all_alerts


def mentions(org_abbrv, date, aliases, soc_media_included=False):
    """Pull dark web mentions data for an organization."""
    # Build query using the org's aliases
    alias_str = ""
    for alias in aliases:
        alias_str += '"' + alias + '",'
    alias_str = alias_str[:-1]
    if soc_media_included:
        query = "date:" + date + " AND " + "(" + str(alias_str) + ")"
    else:
        query = (
            "date:"
            + date
            + " AND "
            + "("
            + str(alias_str)
            + """)
                NOT site:(twitter, Twitter, reddit, Reddit, Parler, parler,
                linkedin, Linkedin, discord, forum_discord, raddle, telegram,
                jabber, ICQ, icq, mastodon)"""
        )
    # Make initial API call and get the total number of mentions
    token = cybersix_token()
    all_mentions = []
    try:
        total_mentions = 0
        LOGGER.info("Retrieving total number of mentions for %s", org_abbrv)
        [resp, token] = intel_post(token, query, frm=0, scroll=True, result_size=100)
        total_mentions = resp["total_intel_items"]
        scroll_id = resp["scroll_id"]
    except Exception as e:
        LOGGER.error("Total mentions count retrieval failed for %s", org_abbrv)
        LOGGER.error(e)
    LOGGER.info("Total mentions for %s: %d", org_abbrv, total_mentions)
    # Catch scenario where org has 0 mentions
    if total_mentions == 0:
        return pd.DataFrame()
    else:
        all_mentions += resp["intel_items"]
    # Fetch all remaining mentions
    token = cybersix_token()
    more_results = True
    idx = 0
    # Keep retrieving until no more results
    while more_results:
        # Progress logging
        if len(all_mentions) % 1000 == 0:
            LOGGER.info(
                "Retrieved %d of %d mentions for %s",
                len(all_mentions),
                total_mentions,
                org_abbrv,
            )
        LOGGER.info(
            "Retrieved %d of %d mentions for %s",
            len(all_mentions),
            total_mentions,
            org_abbrv,
        )
        # Make API call
        [resp, token] = intel_post_next(token, scroll_id)
        intel_items = resp["intel_items"]
        if len(intel_items) != 0:
            # If there are more results, append this chunk
            all_mentions += intel_items
            # Update for variables for next iteration
            scroll_id = resp.get("scroll_id")
            idx += 1
        else:
            # If no more results, stop retrieving
            more_results = False
    # When all mentions retrieved, convert to df and return
    df_all_mentions = pd.DataFrame(all_mentions)
    return df_all_mentions


def alias_organization(org_id):
    """List an organization's aliases."""
    assets = org_assets(org_id)
    df_assets = pd.DataFrame(assets)
    aliases = df_assets["organization_aliases"].loc["explicit":].tolist()[0]
    return aliases


def creds(domain, from_date, to_date):
    """Get credentials."""
    token = cybersix_token()
    skip = 0
    params = {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "max_results": 100,
        "skip": skip,
    }
    # Retrieve cred data
    [resp, token] = credential_auth(token, params)
    total_hits = resp["total_results"]
    resp = resp["leaks"]
    # Continue retrieving cred data if there's more
    while total_hits > len(resp):
        skip += 1
        params["skip"] = skip
        [next_resp, token] = credential_auth(token, params)
        resp = resp + next_resp["leaks"]
    # Format and return data
    resp = pd.DataFrame(resp)
    df = resp.drop_duplicates(
        subset=["email", "breach_name"], keep="first"
    ).reset_index(drop=True)
    return df


def root_domains(org_id):
    """Get root domains."""
    assets = org_assets(org_id)
    df_assets = pd.DataFrame(assets)
    root_domains = df_assets["domain_names"].loc["explicit":].tolist()[0]
    return root_domains


def top_cves(size):
    """Top 10 CVEs mentioned in the dark web."""
    resp = dve_top_cves()
    return pd.DataFrame(resp)

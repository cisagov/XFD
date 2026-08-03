"""Collect and distribute graphical data to readable charts in the presentation."""

# Standard Python Libraries
import datetime
from datetime import timedelta
import json
import logging
import os

# Third-Party Libraries
import pandas as pd
from pe_reports.data.db_query import (
    execute_scorecard,
    get_org_assets_count,
    get_org_assets_count_past,
    query_foreign_IPs,
    query_previous_period,
)

from .charts import Charts

# Import Classes
from .metrics import Credentials, Cyber_Six, Domains_Masqs, Flare, Malware_Vulns

# Setup logging to central
LOGGER = logging.getLogger(__name__)


def credential(
    scorecard_dict,
    chevron_dict,
    trending_start_date,
    start_date,
    end_date,
    org_uid,
    org_code,
    output_directory,
):
    """Build exposed credential page."""
    Credential = Credentials(trending_start_date, start_date, end_date, org_uid)
    # Build exposed credential stacked bar chart
    width = 16.51
    height = 10
    name = "inc_date_df"
    title = "Trending Exposures by Week"
    x_label = "7-Day Intervals"
    y_label = "Credentials Exposed"
    cred_date_chart = Charts(
        Credential.by_days(),
        width,
        height,
        name,
        title,
        x_label,
        y_label,
    )
    cred_date_chart.line_chart()

    creds_dict = {
        "breach": Credential.breaches(),
        "creds": Credential.total(),
        "pw_creds": Credential.password(),
        "breach_table": Credential.breach_details()[:15],
        "breach_appendix": Credential.breach_appendix(),
    }

    scorecard_dict["creds_count"] = creds_dict.get("creds", 0)
    scorecard_dict["breach_count"] = creds_dict.get("breach", 0)
    scorecard_dict["cred_password_count"] = creds_dict.get("pw_creds", 0)

    chevron_dict.update(creds_dict)

    # Create Credential Exposure JSON file
    cred_json = f"{output_directory}/{org_code}/compromised_credentials.json"
    cred_dict = Credential.creds_view.to_dict(orient="records")
    final_dict = {"credentials": cred_dict}
    with open(cred_json, "w") as outfile:
        json.dump(final_dict, outfile, default=str)

    # Create Credential Exposure Excel file
    cred_xlsx = f"{output_directory}/{org_code}/compromised_credentials.xlsx"
    credWriter = pd.ExcelWriter(cred_xlsx, engine="xlsxwriter")
    Credential.creds_view.to_excel(credWriter, sheet_name="Credentials", index=False)
    credWriter.close()

    return scorecard_dict, chevron_dict, cred_json, cred_xlsx


def masquerading(
    scorecard_dict,
    chevron_dict,
    start_date,
    end_date,
    org_uid,
    org_code,
    output_directory,
):
    """Build masquerading page."""
    Domain_Masq = Domains_Masqs(start_date, end_date, org_uid)
    domain_count = Domain_Masq.count()
    dom_alert_count = Domain_Masq.alert_count()
    chevron_dict.update(
        {
            "domain_table": Domain_Masq.summary()[:10],
            "domain_alerts_table": Domain_Masq.alerts()[:10],
            "suspectedDomains": domain_count,
            "domain_alerts": dom_alert_count,
        }
    )
    df_mal = Domain_Masq.df_mal
    if len(df_mal) > 0:
        df_mal["tld"] = "." + df_mal["domain_permutation"].str.split(".").str[-1]
        count_df = df_mal.groupby(["tld"])["tld"].count().reset_index(name="count")
    else:
        count_df = pd.DataFrame(columns=["tld", "count"])
    scorecard_dict["domain_alert_count"] = dom_alert_count
    scorecard_dict["suspected_domain_count"] = domain_count
    scorecard_dict["dns"] = count_df

    # Create Domain Masquerading JSON file
    da_json = f"{output_directory}/{org_code}/domain_alerts.json"
    susp_domains_dict = Domain_Masq.df_mal.to_dict(orient="records")
    dom_alerts_dict = Domain_Masq.alerts_sum().to_dict(orient="records")
    final_dict = {
        "suspected_domains": susp_domains_dict,
        "domain_alerts": dom_alerts_dict,
    }
    with open(da_json, "w") as outfile:
        json.dump(final_dict, outfile, default=str)

    # Create Domain Masquerading Excel file
    da_xlsx = f"{output_directory}/{org_code}/domain_alerts.xlsx"
    domWriter = pd.ExcelWriter(da_xlsx, engine="xlsxwriter")
    Domain_Masq.df_mal.to_excel(domWriter, sheet_name="Suspected Domains", index=False)
    Domain_Masq.alerts_sum().to_excel(
        domWriter, sheet_name="Domain Alerts", index=False
    )
    domWriter.close()

    return scorecard_dict, chevron_dict, da_json, da_xlsx


def mal_vuln(
    scorecard_dict,
    chevron_dict,
    start_date,
    end_date,
    org_uid,
    org_code,
    output_directory,
):
    """Build Malwares and Vulnerabilities page."""
    Malware_Vuln = Malware_Vulns(start_date, end_date, org_uid)
    # Build insecure protocol horizontal bar chart
    width = 16.51
    height = 5.3
    name = "pro_count"
    title = ""
    x_label = "Insecure Protocols"
    y_label = ""
    protocol_chart = Charts(
        Malware_Vuln.protocol_count(),
        width,
        height,
        name,
        title,
        x_label,
        y_label,
    )
    protocol_chart.h_bar()
    # Build unverified vulnerability horizontal bar chart
    width = 16.51
    height = 9
    name = "unverif_vuln_count"
    title = ""
    x_label = "Unverified CVEs"
    y_label = "IP Address"
    unverif_vuln_chart = Charts(
        Malware_Vuln.unverified_cve_count(),
        width,
        height,
        name,
        title,
        x_label,
        y_label,
    )
    unverif_vuln_chart.h_bar()
    # Build tables
    risky_assets = Malware_Vuln.insecure_protocols()
    risky_assets = risky_assets[:10]
    risky_assets.columns = ["Protocol", "IP", "Port"]
    verif_vulns = Malware_Vuln.verif_vulns()[:10]
    verif_vulns.columns = ["CVE", "IP", "Port"]
    risky_ports = Malware_Vuln.risky_ports_count()
    verif_vulns_count = Malware_Vuln.total_verif_vulns()
    unverif_vulns = Malware_Vuln.unverified_vuln_count()
    # Update chevron dictionary
    vulns_dict = {
        "verif_vulns": verif_vulns,
        "risky_assets": risky_assets,
        "riskyPorts": risky_ports,
        "verifVulns": verif_vulns_count,
        "unverifVulns": unverif_vulns,
        "verif_vulns_summary": Malware_Vuln.verif_vulns_summary(),
    }

    scorecard_dict["insecure_port_count"] = risky_ports
    scorecard_dict["verified_vuln_count"] = verif_vulns_count
    scorecard_dict["suspected_vuln_count"] = unverif_vulns
    scorecard_dict["suspected_vuln_addrs_count"] = Malware_Vuln.ip_count()

    all_cves_df = Malware_Vuln.all_cves()
    chevron_dict.update(vulns_dict)

    # Create Suspected vulnerability JSON file
    vuln_json = f"{output_directory}/{org_code}/vuln_alerts.json"
    assets_dict = Malware_Vuln.assets_df.to_dict(orient="records")
    insecure_dict = Malware_Vuln.insecure_df.to_dict(orient="records")
    vulns_dict = Malware_Vuln.vulns_df.to_dict(orient="records")
    final_dict = {
        "assets": assets_dict,
        "insecure": insecure_dict,
        "verified_vulns": vulns_dict,
    }
    with open(vuln_json, "w") as outfile:
        json.dump(final_dict, outfile, default=str)

    # Create Suspected vulnerability Excel file
    vuln_xlsx = f"{output_directory}/{org_code}/vuln_alerts.xlsx"
    vulnWriter = pd.ExcelWriter(vuln_xlsx, engine="xlsxwriter")
    Malware_Vuln.assets_df.to_excel(vulnWriter, sheet_name="Assets", index=False)
    Malware_Vuln.insecure_df.to_excel(vulnWriter, sheet_name="Insecure", index=False)
    Malware_Vuln.vulns_df.to_excel(vulnWriter, sheet_name="Verified Vulns", index=False)
    vulnWriter.close()

    return (scorecard_dict, chevron_dict, vuln_json, all_cves_df, vuln_xlsx)


def dark_web(
    scorecard_dict,
    chevron_dict,
    trending_start_date,
    start_date,
    end_date,
    org_uid,
    all_cves_df,
    soc_med_included,
    org_code,
    output_directory,
):
    """Dark Web data from CyberSixGill."""
    Cyber6 = Cyber_Six(
        trending_start_date,
        start_date,
        end_date,
        org_uid,
        all_cves_df,
        soc_med_included,
    )
    # Build dark web mentions over time line chart
    width = 16.51
    height = 10
    name = "web_only_df_2"
    title = ""
    x_label = "7-Day Intervals"
    y_label = "Mentions Count"
    dark_mentions_chart = Charts(
        Cyber6.dark_web_date(),
        width,
        height,
        name,
        title,
        x_label,
        y_label,
    )
    dark_mentions_chart.line_chart()
    # Assemble list of notable threat actors
    dark_web_actors = Cyber6.dark_web_bad_actors()
    threshold = 7  # Threshold for notable threat actor
    scorecard_dict["threat_actor_count"] = len(
        dark_web_actors[dark_web_actors["Grade"] > threshold]
    )
    # Assemble executive alerts
    exec_alerts = Cyber6.alerts_exec()
    scorecard_dict["dark_web_executive_alerts_count"] = len(exec_alerts)
    # Assemble asset alerts
    asset_alerts = Cyber6.asset_alerts()
    scorecard_dict["dark_web_asset_alerts_count"] = len(asset_alerts)
    # Assemble social media posts
    social_media = Cyber6.social_media_most_act()
    if not soc_med_included:
        social_media = social_media[0:0]
    # Assemble dark web posts
    dark_web_count = Cyber6.dark_web_count()
    # Assemble full dark web dictionary
    dark_web_dict = {
        "darkWeb": dark_web_count,
        "mentions_count": Cyber6.dark_web_mentions_count(),
        "dark_web_sites": Cyber6.dark_web_sites(),
        "alerts_threats": Cyber6.alerts_threats(),
        "dark_web_actors": dark_web_actors,
        "alerts_exec": exec_alerts[:10],
        "asset_alerts": asset_alerts[:10],
        "dark_web_act": Cyber6.dark_web_most_act(),
        "social_med_act": social_media,
        "markets_table": Cyber6.invite_only_markets(),
        "top_cves": Cyber6.top_cve_table(),
    }
    # Add dark web data to scorecard dictionary
    scorecard_dict["dark_web_alerts_count"] = dark_web_count
    scorecard_dict["dark_web_mentions_count"] = len(Cyber6.dark_web_mentions)
    circles_df = Cyber6.create_count_df()
    scorecard_dict["circles_df"] = circles_df
    chevron_dict.update(dark_web_dict)
    # Create dark web JSON file
    mentions_df = Cyber6.dark_web_mentions
    mentions_df["content"] = mentions_df["content"].str[:2000]
    mi_json = f"{output_directory}/{org_code}/mention_incidents.json"
    mentions_dict = mentions_df.to_dict(orient="records")
    alerts_dict = Cyber6.alerts.to_dict(orient="records")
    cve_dict = Cyber6.top_cves.to_dict(orient="records")
    final_dict = {
        "dark_web_mentions": mentions_dict,
        "dark_web_alerts": alerts_dict,
        "top_cves": cve_dict,
    }
    with open(mi_json, "w") as outfile:
        json.dump(final_dict, outfile, default=str)
    # Create dark web XLSX file
    mi_xlsx = f"{output_directory}/{org_code}/mention_incidents.xlsx"
    miWriter = pd.ExcelWriter(mi_xlsx, engine="xlsxwriter")
    mentions_df.to_excel(miWriter, sheet_name="Dark Web Mentions", index=False)
    Cyber6.alerts.to_excel(miWriter, sheet_name="Dark Web Alerts", index=False)
    Cyber6.top_cves.to_excel(miWriter, sheet_name="Top CVEs", index=False)
    miWriter.close()
    # Return all results
    return (scorecard_dict, chevron_dict, mi_json, mi_xlsx)


def dark_web_flare(
    scorecard_dict,
    chevron_dict,
    trending_start_date,
    start_date,
    end_date,
    org_uid,
    all_cves_df,
    soc_med_included,
    org_code,
    output_directory,
):
    """Dark Web data from Flare."""
    # Create Flare dark web metrics object
    FlareObj = Flare(
        trending_start_date,
        start_date,
        end_date,
        org_uid,
        all_cves_df,
        soc_med_included,
    )
    # Build dark web mentions over time line chart
    width = 16.51
    height = 10
    name = "web_only_df_2"
    title = ""
    x_label = "7-Day Intervals"
    y_label = "Mentions Count"
    dark_mentions_chart = Charts(
        FlareObj.dark_web_mentions_by_date(),
        width,
        height,
        name,
        title,
        x_label,
        y_label,
    )
    dark_mentions_chart.line_chart()
    # Get total dark web mentions count
    dark_web_total_mentions = FlareObj.dark_web_mentions_total()
    # Get toal dark web alerts count
    dark_web_total_alerts = FlareObj.dark_web_alerts_total()
    # Get social media posts
    social_media_posts = FlareObj.dark_web_mentions_soc_media()
    # If social media disabled, set to empty dataframe
    if not soc_med_included:
        social_media_posts = social_media_posts[0:0]
    # Get dark web posts
    dark_web_posts = FlareObj.dark_web_mentions_other()
    # Get dark web asset alerts
    dark_web_asset_alerts = FlareObj.dark_web_alerts_assets()
    # Get dark web executive alerts
    dark_web_exec_alerts = FlareObj.dark_web_alerts_exec()
    # Get dark web threat actors
    dark_web_actors = FlareObj.dark_web_threat_actors()
    # Get dark web potential threat alerts
    dark_web_threat_alerts = FlareObj.dark_web_alerts_threats()
    # Get dark web sites
    dark_web_sites = FlareObj.dark_web_sites()
    # Get dark web invite-only market alerts
    dark_web_market_alerts = FlareObj.dark_web_alerts_market()
    # Get top 10 CVEs for all orgs this period
    top_cves = FlareObj.top_cve_table()
    # Get Flare event type definitions
    dark_web_event_types = FlareObj.dark_web_event_types()
    # Assemble full dark web dictionary
    dark_web_dict = {
        "mentions_count": dark_web_total_mentions,
        "darkWeb": dark_web_total_alerts,
        "social_med_act": social_media_posts,
        "dark_web_act": dark_web_posts,
        "asset_alerts": dark_web_asset_alerts[:10],
        "alerts_exec": dark_web_exec_alerts[:10],
        "dark_web_actors": dark_web_actors,
        "alerts_threats": dark_web_threat_alerts,
        "dark_web_sites": dark_web_sites,
        "markets_table": dark_web_market_alerts,
        "top_cves": top_cves,
    }
    # Add dark web data to scorcard dictionary
    scorecard_dict["dark_web_mentions_count"] = dark_web_total_mentions
    scorecard_dict["dark_web_alerts_count"] = dark_web_total_alerts
    scorecard_dict["dark_web_asset_alerts_count"] = len(dark_web_asset_alerts)
    scorecard_dict["dark_web_executive_alerts_count"] = len(dark_web_exec_alerts)
    scorecard_dict["threat_actor_count"] = len(dark_web_actors)
    circles_df = FlareObj.dark_web_counts_df()
    scorecard_dict["circles_df"] = circles_df
    # Add dark web data to chevron dictionary
    chevron_dict.update(dark_web_dict)
    # Prep mentions raw data
    mentions_df = FlareObj.mentions
    mentions_df.drop("flare_events_uid", axis=1, inplace=True)
    mentions_df["content"] = mentions_df["content"].str[:2000]
    mentions_df["related_identifiers"] = mentions_df["related_identifiers"].apply(
        lambda x: [FlareObj.flare_all_asset_dict.get(item, item) for item in x]
    )
    mentions_df["related_identifiers"] = mentions_df["related_identifiers"].apply(
        lambda x: list(set(x))
    )
    mentions_df.drop(columns=["related_identifiers_txt"], inplace=True)
    # Prep alerts raw data
    alerts_df = FlareObj.alerts
    alerts_df.drop("flare_events_uid", axis=1, inplace=True)
    alerts_df["related_identifiers"] = alerts_df["related_identifiers"].apply(
        lambda x: [FlareObj.flare_all_asset_dict.get(item, item) for item in x]
    )
    alerts_df["related_identifiers"] = alerts_df["related_identifiers"].apply(
        lambda x: list(set(x))
    )
    alerts_df.drop(columns=["related_identifiers_txt"], inplace=True)
    alerts_df["content"] = alerts_df["content"].str.slice(0, 32000)
    # Prep top 10 cves raw data
    top_cves_df = FlareObj.top_cves
    top_cves_df.drop(columns=["summary_short"], inplace=True, errors="ignore")
    # Create dark web JSON file
    mentions_dict = mentions_df.to_dict(orient="records")
    alerts_dict = alerts_df.to_dict(orient="records")
    cve_dict = top_cves_df.to_dict(orient="records")
    event_types_dict = dark_web_event_types.to_dict(orient="records")
    final_dict = {
        "dark_web_mentions": mentions_dict,
        "dark_web_alerts": alerts_dict,
        "top_cves": cve_dict,
        "event_types": event_types_dict,
    }
    mi_json = f"{output_directory}/{org_code}/mention_incidents.json"
    with open(mi_json, "w") as outfile:
        json.dump(final_dict, outfile, default=str)
    # Create dark web XLSX file
    mi_xlsx = f"{output_directory}/{org_code}/mention_incidents.xlsx"
    miWriter = pd.ExcelWriter(mi_xlsx, engine="xlsxwriter")
    mentions_df.to_excel(miWriter, sheet_name="Dark Web Mentions", index=False)
    alerts_df.to_excel(miWriter, sheet_name="Dark Web Alerts", index=False)
    top_cves_df.to_excel(miWriter, sheet_name="Top CVEs", index=False)
    dark_web_event_types.to_excel(
        miWriter, sheet_name="Event Type Definitions", index=False
    )
    miWriter.close()
    # Return all results
    return (scorecard_dict, chevron_dict, mi_json, mi_xlsx)


def init(
    datestring,
    org_name,
    org_code,
    org_uid,
    premium,
    score,
    grade,
    output_directory,
    soc_med_included=False,
):
    """Call each page of the report."""
    # Format start_date and end_date for the bi-monthly reporting period.
    end_date = datetime.datetime.strptime(datestring, "%Y-%m-%d").date()
    if end_date.day == 15:
        # If the given end_date is the 15th, then the start_date is the 1st.
        start_date = datetime.datetime(end_date.year, end_date.month, 1)
    else:
        # Otherwise, the start_date will be the 16th of the respective month.
        start_date = datetime.datetime(end_date.year, end_date.month, 16)
    # Calculate trending and previous dates
    days = datetime.timedelta(27)
    trending_start_date = end_date - days
    previous_end_date = start_date - datetime.timedelta(days=1)
    # Get base directory to save images
    base_dir = os.path.abspath(os.path.dirname(__file__))
    start = start_date.strftime("%m/%d/%Y")
    end = end_date.strftime("%m/%d/%Y")
    chevron_dict = {
        "department": org_name,
        "dateRange": start + " - " + end,
        "endDate": end,
        "base_dir": base_dir,
    }
    # Retrieve ASM Summary values for current and previous report periods
    asset_dict = get_org_assets_count(org_uid, start_date, end_date)
    asset_dict_past = get_org_assets_count_past(org_uid, start_date - timedelta(days=1))
    if asset_dict_past.empty:
        # If there's no ASM Summary values for last period
        LOGGER.error("No ASM summary data for the last report period.")
        past_ip_count = 0
        past_cidr_count = 0
        past_port_protocol_count = 0
        past_root_count = 0
        past_sub_count = 0
        past_software_count = 0
        past_for_ip_count = 0
    else:
        # If there are ASM Summary values for last period
        past_ip_count = asset_dict_past["ip_count"][0]
        past_cidr_count = asset_dict_past["cidr_count"][0]
        past_port_protocol_count = asset_dict_past["port_protocol_count"][0]
        past_root_count = asset_dict_past["root_count"][0]
        past_sub_count = asset_dict_past["sub_count"][0]
        past_software_count = asset_dict_past["software_count"][0]
        past_for_ip_count = asset_dict_past["foreign_ips_count"][0]
    # Special date-sensitive query needed for calculating foreign IPs
    foreign_ips = query_foreign_IPs(org_uid)
    foreign_ips["timestamp"] = pd.to_datetime(foreign_ips["timestamp"])
    curr_end = datetime.datetime.strptime(datestring, "%Y-%m-%d")
    curr_start = start_date
    prev_end = previous_end_date
    if prev_end.day == 15:
        prev_start = datetime.datetime(prev_end.year, prev_end.month, 1)
    else:
        prev_start = datetime.datetime(prev_end.year, prev_end.month, 16)
    curr_foreign_ips = foreign_ips.loc[
        (foreign_ips["timestamp"] >= curr_start)
        & (foreign_ips["timestamp"] <= curr_end)
    ].reset_index(drop=True)
    past_foreign_ips = foreign_ips.loc[
        (foreign_ips["timestamp"] >= prev_start)
        & (foreign_ips["timestamp"] <= prev_end)
    ].reset_index(drop=True)
    asset_dict["num_foreign_ips"] = len(curr_foreign_ips)
    past_for_ip_count = len(past_foreign_ips)
    # Create ASM Summary dictionary
    summary_dict = {
        "org_name": org_name,
        "date": end_date.strftime("%B %d, %Y"),
        "ip_address": asset_dict["num_ips"],
        "last_ip_address": past_ip_count,
        "cidrs": asset_dict["num_cidrs"],
        "last_cidrs": past_cidr_count,
        "ports_and_protocols": asset_dict["num_ports_protocols"],
        "last_ports_and_protocols": past_port_protocol_count,
        "root_domains": asset_dict["num_root_domain"],
        "last_root_domains": past_root_count,
        "sub_domains": asset_dict["num_sub_domain"],
        "last_sub_domains": past_sub_count,
        "software": asset_dict["num_software"],
        "last_software": past_software_count,
        "foreign_ips": asset_dict["num_foreign_ips"],
        "last_foreign_ips": past_for_ip_count,
    }
    # Create Scorecard dictionary
    scorecard_dict = {
        "organizations_uid": org_uid,
        "org_name": org_name,
        "start_date": start_date,
        "end_date": end_date,
        "ip_count": asset_dict["num_ips"],
        "cidr_count": asset_dict["num_cidrs"],
        "root_count": asset_dict["num_root_domain"],
        "sub_count": asset_dict["num_sub_domain"],
        "num_ports": asset_dict["num_ports"],
        "port_protocol_count": asset_dict["num_ports_protocols"],
        "software_count": asset_dict["num_software"],
        "foreign_ips_count": asset_dict["num_foreign_ips"],
        "pe_number_score": score,
        "pe_letter_grade": grade,
    }
    # Credential Leak Data
    (scorecard_dict, chevron_dict, cred_json, cred_xlsx) = credential(
        scorecard_dict,
        chevron_dict,
        trending_start_date,
        start_date,
        end_date,
        org_uid,
        org_code,
        output_directory,
    )
    # Domain Masquerading Data
    scorecard_dict, chevron_dict, da_json, da_xlsx = masquerading(
        scorecard_dict,
        chevron_dict,
        start_date,
        end_date,
        org_uid,
        org_code,
        output_directory,
    )
    # Inferred/Verified Vulnerabilities Data
    (scorecard_dict, chevron_dict, vuln_json, all_cves_df, vuln_xlsx) = mal_vuln(
        scorecard_dict,
        chevron_dict,
        start_date,
        end_date,
        org_uid,
        org_code,
        output_directory,
    )
    # Dark Web Data (Flare)
    scorecard_dict, chevron_dict, mi_json, mi_xlsx = dark_web_flare(
        scorecard_dict,
        chevron_dict,
        trending_start_date,
        start_date,
        end_date,
        org_uid,
        all_cves_df,
        soc_med_included,
        org_code,
        output_directory,
    )

    # Save report summary stats for the current period to the PE DB
    execute_scorecard(
        scorecard_dict
    )  # Updating RSS table, may want to disable when developing
    # Retrieve report summary stats for the previous period
    last_period_stats = query_previous_period(org_uid, previous_end_date)
    scorecard_dict.update(last_period_stats)
    # Return all data/metrics/raw files to populate the HTML template
    return (
        chevron_dict,
        scorecard_dict,
        summary_dict,
        cred_json,
        da_json,
        vuln_json,
        mi_json,
        cred_xlsx,
        da_xlsx,
        vuln_xlsx,
        mi_xlsx,
    )

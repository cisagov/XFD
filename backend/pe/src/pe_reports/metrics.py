"""Class methods for report metrics."""

# Standard Python Libraries
import datetime
import logging
import os
import time

# Third-Party Libraries
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

from .data.config import PE_API_REQUEST_TIMEOUT
from .data.db_query import (
    connect,
    get_orgs,
    query_darkweb,
    query_darkweb_asset_alerts,
    query_darkweb_cves,
    query_domMasq,
    query_domMasq_alerts,
    query_flare_all_events,
    query_flare_breachdetails_view,
    query_flare_creds_view,
    query_flare_credsbyday_view,
    query_flare_event_type_defs,
    query_flare_mentions_by_date,
    query_shodan,
    query_shodan_top_cves,
)

_TOP_CVE_COLUMNS = [
    "top_cves_uid",
    "cve_id",
    "dynamic_rating",
    "nvd_base_score",
    "date",
    "summary",
    "data_source_uid",
]


def _latest_top_cves(top_cves):
    """Keep only rows for the latest top_cves snapshot date."""
    if top_cves is None or top_cves.empty:
        return pd.DataFrame(columns=_TOP_CVE_COLUMNS)
    if top_cves["date"].notna().any():
        return top_cves[top_cves["date"] == top_cves["date"].max()]
    return top_cves


# Setup logging
LOGGER = logging.getLogger(__name__)


class Credentials:
    """Credentials class."""

    def __init__(self, trending_start_date, start_date, end_date, org_uid):
        """Initialize credentials class."""
        self.trending_start_date = trending_start_date
        self.start_date = start_date
        self.end_date = end_date
        self.org_uid = org_uid
        self.trending_creds_view = query_flare_creds_view(
            org_uid, trending_start_date, end_date
        )
        self.creds_view = query_flare_creds_view(org_uid, start_date, end_date)
        self.creds_by_day = query_flare_credsbyday_view(
            org_uid, trending_start_date, end_date
        )
        self.breach_details_view = query_flare_breachdetails_view(
            org_uid, start_date, end_date
        )

    def by_days(self):
        """Return number of credentials by day."""
        df = self.creds_by_day
        # df = df[["mod_date", "no_password", "password_included"]].copy()
        idx = pd.date_range(self.trending_start_date, self.end_date)
        df = df.set_index("mod_date").reindex(idx).fillna(0.0).rename_axis("added_date")
        group_limit = self.end_date + datetime.timedelta(1)
        df = df.groupby(
            pd.Grouper(level="added_date", freq="7d", origin=group_limit)
        ).sum()
        df["modified_date"] = df.index
        # Adjust dates field for readability
        df["date_readable"] = ""
        for idx, row in df.iterrows():
            start_date = row["modified_date"]
            start_date_str = start_date.strftime("%m/%d")
            end_date = start_date + datetime.timedelta(days=6)
            end_date_str = end_date.strftime("%m/%d")
            df.at[idx, "date_readable"] = f"{start_date_str} - {end_date_str}"
        df["modified_date"] = df["date_readable"]
        df.drop(columns=["date_readable"], inplace=True)
        # df["modified_date"] = df["modified_date"].dt.strftime("%b %d")
        df = df.set_index("modified_date")
        df = df.rename(
            columns={
                "password_included": "Passwords Included",  # nosec B105
                "no_password": "No Password",  # nosec B105
            }
        )
        if len(df.columns) == 0:
            df["Passwords Included"] = 0
        return df

    def breaches(self):
        """Return total number of breaches."""
        all_breaches = self.creds_view["breach_name"]
        return all_breaches.nunique()

    def breach_appendix(self):
        """Return breach name and description to be added to the appendix."""
        view_df = self.creds_view
        view_df = view_df[["breach_name", "description"]]
        view_df = view_df.drop_duplicates()
        view_df.sort_values("breach_name", inplace=True)
        view_df = view_df[["breach_name", "description"]]
        # Only include the top 15 breaches displayed in table 1
        table_breaches = self.breach_details()[:15]
        table_breaches.rename(columns={"Breach Name": "breach_name"}, inplace=True)
        breach_names = table_breaches["breach_name"]
        appendix_df = pd.merge(breach_names, view_df, on="breach_name", how="left")
        return appendix_df

    def breach_details(self):
        """Return breach details."""
        breach_df = self.breach_details_view
        breach_det_df = breach_df.rename(columns={"modified_date": "update_date"})
        breach_det_df["update_date"] = pd.to_datetime(breach_det_df["update_date"])
        if len(breach_det_df) > 0:
            breach_det_df["update_date"] = breach_det_df["update_date"].dt.strftime(
                "%m/%d/%y"
            )
            breach_det_df["breach_date"] = pd.to_datetime(
                breach_det_df["breach_date"]
            ).dt.strftime("%m/%d/%y")
        breach_det_df = breach_det_df.rename(
            columns={
                "breach_name": "Breach Name",
                "breach_date": "Breach Date",
                "update_date": "Date Reported",
                "password_included": "Password Included",  # nosec B105
                "number_of_creds": "Number of Creds",
            }
        )
        breach_det_df.sort_values(
            by=["Number of Creds", "Date Reported"], ascending=False, inplace=True
        )
        # convert 1/0 values to boolean for displaying
        breach_det_df["Password Included"] = breach_det_df["Password Included"].astype(
            bool
        )
        return breach_det_df

    def password(self):
        """Return total number of credentials with passwords."""
        pw_creds = len(self.creds_view[self.creds_view["password_included"]])
        return pw_creds

    def total(self):
        """Return total number of credentials found in breaches."""
        df_cred = self.creds_view.shape[0]
        return df_cred


class Domains_Masqs:
    """Domains Masquerading class."""

    def __init__(self, start_date, end_date, org_uid):
        """Initialize domains masquerading class."""
        self.start_date = start_date
        self.end_date = end_date
        self.org_uid = org_uid
        df = query_domMasq(org_uid, start_date, end_date)
        if df is None or df.empty:
            self.df_mal = pd.DataFrame()
        else:
            self.df_mal = df[df["malicious"]]
        dom_alerts = query_domMasq_alerts(org_uid, start_date, end_date)
        self.dom_alerts_df = dom_alerts if dom_alerts is not None else pd.DataFrame()

    def count(self):
        """Return total count of malicious domains."""
        df = self.df_mal
        return len(df.index)

    def summary(self):
        """Return domain masquerading summary information."""
        if len(self.df_mal) > 0:
            domain_sum = self.df_mal[
                [
                    "domain_permutation",
                    "ipv4",
                    "ipv6",
                    "mail_server",
                    "name_server",
                ]
            ]
            domain_sum.loc[domain_sum["ipv6"] == "", "ipv6"] = "NA"
            domain_sum = domain_sum.rename(
                columns={
                    "domain_permutation": "Domain",
                    "ipv4": "IPv4",
                    "ipv6": "IPv6",
                    "mail_server": "Mail Server",
                    "name_server": "Name Server",
                }
            )
        else:
            domain_sum = pd.DataFrame(
                columns=[
                    "Domain",
                    "IPv4",
                    "IPv6",
                    "Mail Server",
                    "Name Server",
                ]
            )
            domain_sum.sort_values(by=["Domain"], ascending=True, inplace=True)
        return domain_sum

    def alert_count(self):
        """Return number of alerts."""
        dom_alert_count = len(self.dom_alerts_df)
        return dom_alert_count

    def alerts(self):
        """Return domain alerts."""
        if self.dom_alerts_df is None or self.dom_alerts_df.empty:
            return pd.DataFrame(columns=["Alert", "Date"])
        dom_alerts_df = self.dom_alerts_df[["message", "date"]]
        dom_alerts_df = dom_alerts_df.rename(
            columns={"message": "Alert", "date": "Date"}
        )
        dom_alerts_df.sort_values(by=["Date"], ascending=False, inplace=True)
        return dom_alerts_df

    def alerts_sum(self):
        """Return domain alerts summary."""
        if self.dom_alerts_df is None or self.dom_alerts_df.empty:
            return pd.DataFrame(
                columns=["message", "date", "previous_value", "new_value"]
            )
        dom_alerts_sum = self.dom_alerts_df[
            ["message", "date", "previous_value", "new_value"]
        ]
        return dom_alerts_sum


class Malware_Vulns:
    """Malware and Vulnerabilities Class."""

    def __init__(self, start_date, end_date, org_uid):
        """Initialize Shodan vulns and malware class."""
        self.start_date = start_date
        self.end_date = end_date
        self.org_uid = org_uid
        insecure_df = query_shodan(
            org_uid,
            start_date,
            end_date,
            "vw_shodanvulns_suspected",
        )
        self.insecure_df = insecure_df if insecure_df is not None else pd.DataFrame()

        vulns_df = query_shodan(
            org_uid, start_date, end_date, "vw_shodanvulns_verified"
        )
        if vulns_df is None:
            vulns_df = pd.DataFrame()
        if not vulns_df.empty and "port" in vulns_df.columns:
            vulns_df["port"] = vulns_df["port"].astype(str)
        self.vulns_df = vulns_df

        assets_df = query_shodan(org_uid, start_date, end_date, "shodan_assets")
        self.assets_df = assets_df if assets_df is not None else pd.DataFrame()

    @staticmethod
    def isolate_risky_assets(df):
        """Return risky assets from the insecure_df dataframe."""
        insecure = df[df["type"] == "Insecure Protocol"]
        insecure = insecure[
            (insecure["protocol"] != "http") & (insecure["protocol"] != "smtp")
        ]
        insecure["port"] = insecure["port"].astype(str)
        return insecure[["protocol", "ip", "port"]].drop_duplicates(keep="first")

    def insecure_protocols(self):
        """Get risky assets grouped by protocol."""
        risky_assets = self.isolate_risky_assets(self.insecure_df)
        risky_assets = (
            risky_assets.groupby("protocol")
            .agg(lambda x: "  ".join(set(x)))
            .reset_index()
        )
        if len(risky_assets.index) > 0:
            risky_assets["ip"] = risky_assets["ip"].str[:30]
            risky_assets.loc[risky_assets["ip"].str.len() == 30, "ip"] = (
                risky_assets["ip"] + "  ..."
            )
        return risky_assets

    def protocol_count(self):
        """Return a count for each insecure protocol."""
        risky_assets = self.isolate_risky_assets(self.insecure_df)
        # Horizontal bar: insecure protocol count
        pro_count = risky_assets.groupby("protocol", as_index=False).agg(
            id_count=("protocol", "count")
        )
        return pro_count

    def risky_ports_count(self):
        """Return total count of insecure ports."""
        risky_assets = self.isolate_risky_assets(self.insecure_df)

        pro_count = risky_assets.groupby("protocol", as_index=False).agg(
            id_count=("protocol", "count")
        )
        # Total Open Ports with Insecure protocols
        return pro_count["id_count"].sum()

    def total_verif_vulns(self):
        """Return total count of verified vulns."""
        vulns_df = self.vulns_df
        verif_vulns = (
            vulns_df[["cve", "ip", "port"]]
            .groupby("cve")
            .agg(lambda x: "  ".join(set(x)))
            .reset_index()
        )
        if len(verif_vulns) > 0:
            verif_vulns["count"] = verif_vulns["ip"].str.split("  ").str.len()
            verifVulns = verif_vulns["count"].sum()

        else:
            verifVulns = 0
        return verifVulns

    def ip_count(self):
        """Return the number of total ips with suspected and confirmed vulns."""
        vulns_df = self.vulns_df
        unverif_df = self.insecure_df

        combined_ips = pd.concat([vulns_df["ip"], unverif_df["ip"]], ignore_index=True)

        return len(pd.unique(combined_ips))

    @staticmethod
    def unverified_cve(df):
        """Subset insecure df to only potential vulnerabilities."""
        unverif_df = df[df["type"] != "Insecure Protocol"]
        unverif_df = unverif_df.copy()
        unverif_df["potential_vulns"] = (
            unverif_df["potential_vulns"].sort_values().apply(lambda x: sorted(x))
        )
        unverif_df["potential_vulns"] = unverif_df["potential_vulns"].astype("str")
        unverif_df = (
            unverif_df[["potential_vulns", "ip"]]
            .drop_duplicates(keep="first")
            .reset_index(drop=True)
        )
        unverif_df["potential_vulns_list"] = unverif_df["potential_vulns"].str.split(
            ","
        )
        unverif_df["count"] = unverif_df["potential_vulns_list"].str.len()
        return unverif_df

    def unverified_cve_count(self):
        """Return top 15 unverified CVEs and their counts."""
        unverif_df = self.unverified_cve(self.insecure_df)
        unverif_df = unverif_df[["ip", "count"]]
        unverif_df = unverif_df.sort_values(by=["count"], ascending=False)
        unverif_df = unverif_df[:15].reset_index(drop=True)
        return unverif_df

    def all_cves(self):
        """Get all verified and unverified CVEs."""
        unverif_df = self.unverified_cve(self.insecure_df)
        vulns_df = self.vulns_df
        verified_cves = vulns_df["cve"].tolist()
        all_cves = []
        for unverif_index, unverif_row in unverif_df.iterrows():
            for cve in unverif_row["potential_vulns_list"]:
                cve = cve.strip("[]' ")
                all_cves.append(cve)
        all_cves += verified_cves
        all_cves = list(set(all_cves))
        return all_cves

    def unverified_vuln_count(self):
        """Return the count of IP addresses with unverified vulnerabilities."""
        insecure_df = self.insecure_df
        unverif_df = insecure_df[insecure_df["type"] != "Insecure Protocol"]
        unverif_df = unverif_df.copy()
        unverif_df["potential_vulns"] = (
            unverif_df["potential_vulns"].sort_values().apply(lambda x: sorted(x))
        )
        unverif_df["potential_vulns"] = unverif_df["potential_vulns"].astype("str")
        unverif_df = (
            unverif_df[["potential_vulns", "ip"]]
            .drop_duplicates(keep="first")
            .reset_index(drop=True)
        )
        return len(unverif_df.index)

    def verif_vulns(self):
        """Return a dataframe with each CVE, the associated IPs and the affected ports."""
        vulns_df = self.vulns_df
        verif_vulns = (
            vulns_df[["cve", "ip", "port"]]
            .groupby("cve")
            .agg(lambda x: "  ".join(set(x)))
            .reset_index()
        )
        return verif_vulns

    def verif_vulns_summary(self):
        """Return summary dataframe for verified vulns."""
        vulns_df = self.vulns_df
        verif_vulns_summary = (
            vulns_df[["cve", "ip", "port", "summary"]]
            .groupby("cve")
            .agg(lambda x: "  ".join(set(x)))
            .reset_index()
        )
        verif_vulns_summary = verif_vulns_summary.rename(
            columns={
                "cve": "CVE",
                "ip": "IP",
                "port": "Port",
                "summary": "Summary",
            }
        )
        return verif_vulns_summary


class Cyber_Six:
    """Dark web and Cyber Six data class."""

    def __init__(
        self,
        trending_start_date,
        start_date,
        end_date,
        org_uid,
        all_cves_df,
        soc_med_included,
    ):
        """Initialize Cybersixgill vulns and malware class."""
        self.trending_start_date = trending_start_date
        self.start_date = start_date
        self.end_date = end_date
        self.org_uid = org_uid
        self.all_cves_df = all_cves_df
        self.soc_med_included = soc_med_included
        self.soc_med_platforms = [
            "twitter",
            "Twitter",
            "reddit",
            "Reddit",
            "Parler",
            "parler",
            "linkedin",
            "Linkedin",
            "discord",
            "forum_discord",
            "raddle",
            "telegram",
            "jabber",
            "ICQ",
            "icq",
            "mastodon",
        ]
        dark_web_mentions = query_darkweb(
            org_uid,
            start_date,
            end_date,
            "mentions",
        )
        dark_web_mentions = dark_web_mentions.drop(
            columns=["organizations_uid", "mentions_uid"],
            errors="ignore",
        )
        if not soc_med_included:
            dark_web_mentions = dark_web_mentions[
                ~dark_web_mentions["site"].isin(self.soc_med_platforms)
            ]
        self.dark_web_mentions = dark_web_mentions
        alerts = query_darkweb(
            org_uid,
            start_date,
            end_date,
            "alerts",
        )
        alerts = alerts.drop(
            columns=["organizations_uid", "alerts_uid"],
            errors="ignore",
        )
        if not soc_med_included:
            alerts = alerts[~alerts["site"].isin(self.soc_med_platforms)]
        self.alerts = alerts
        top_cves = _latest_top_cves(query_darkweb_cves("top_cves"))
        self.top_cves = top_cves

    def dark_web_count(self):
        """Get total number of dark web alerts."""
        return len(self.alerts.index)

    def dark_web_mentions_count(self):
        """Get total number of dark web mentions."""
        return len(self.dark_web_mentions)

    def dark_web_date(self):
        """Get dark web mentions by date."""
        trending_dark_web_mentions = query_darkweb(
            self.org_uid,
            self.trending_start_date,
            self.end_date,
            "vw_darkweb_mentionsbydate",
        )
        dark_web_date = trending_dark_web_mentions.drop(
            columns=["organizations_uid"],
            errors="ignore",
        )
        idx = pd.date_range(self.trending_start_date, self.end_date)
        dark_web_date = (
            dark_web_date.set_index("date").reindex(idx).fillna(0.0).rename_axis("date")
        )
        group_limit = self.end_date + datetime.timedelta(1)
        dark_web_date = dark_web_date.groupby(
            pd.Grouper(level="date", freq="7d", origin=group_limit)
        ).sum()
        dark_web_date["date"] = dark_web_date.index
        # Adjust dates field for readability
        dark_web_date["date_readable"] = ""
        for idx, row in dark_web_date.iterrows():
            start_date = row["date"]
            start_date_str = start_date.strftime("%m/%d")
            end_date = start_date + datetime.timedelta(days=6)
            end_date_str = end_date.strftime("%m/%d")
            dark_web_date.at[
                idx, "date_readable"
            ] = f"{start_date_str} - {end_date_str}"
        dark_web_date = dark_web_date[["Count", "date_readable"]]
        dark_web_date.rename(columns={"date_readable": "date"}, inplace=True)
        dark_web_date = dark_web_date.set_index("date")
        dark_web_date = dark_web_date[["Count"]]
        return dark_web_date

    def create_count_df(self):
        """Retrieve dataframe of counts by mention type."""
        name = []
        value = []
        markets = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_inviteonlymarkets",
        )
        if len(markets) > 0:
            name.append("INVITE ONLY MARKET")
            value.append(len(markets))

        if self.soc_med_included:
            soc_med = query_darkweb(
                self.org_uid,
                self.start_date,
                self.end_date,
                "vw_darkweb_socmedia_mostactposts",
            )
            if len(soc_med) > 0:
                name.append("SOCIAL MEDIA")
                value.append(len(soc_med))

        dark_web_forum = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_mostactposts",
        )
        if len(dark_web_forum) > 0:
            name.append("DARK WEB FORUM")
            value.append(len(dark_web_forum))

        alerts_exec = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_execalerts",
        )
        if len(alerts_exec) > 0:
            name.append("EXECUTIVES")
            value.append(len(alerts_exec))
        if name:
            circle_df = pd.DataFrame({"Name": name, "Value": value})
            return circle_df
        else:
            return 0

    def social_media_most_act(self):
        """Get most active social media posts."""
        soc_med_most_act = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_socmedia_mostactposts",
        )
        soc_med_most_act = soc_med_most_act.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        soc_med_most_act.sort_values(
            by=["Comments Count", "Title"], ascending=[False, True], inplace=True
        )
        soc_med_most_act = soc_med_most_act[:10]
        # Translate title field to english
        # soc_med_most_act = translate(soc_med_most_act, ["Title"])
        soc_med_most_act["Title"] = soc_med_most_act["Title"].str[:200]
        soc_med_most_act = soc_med_most_act.replace(r"^\s*$", "Untitled", regex=True)
        return soc_med_most_act

    def dark_web_most_act(self):
        """Get most active dark web posts."""
        dark_web_most_act = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_mostactposts",
        )
        dark_web_most_act = dark_web_most_act.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        # Translate title field to english
        dark_web_most_act.sort_values(
            by=["Comments Count", "Title"], ascending=[False, True], inplace=True
        )
        dark_web_most_act = dark_web_most_act[:10]
        # dark_web_most_act = translate(dark_web_most_act, ["Title"])
        dark_web_most_act["Title"] = dark_web_most_act["Title"].str[:200]
        dark_web_most_act = dark_web_most_act.replace(r"^\s*$", "Untitled", regex=True)
        return dark_web_most_act

    def asset_alerts(self):
        """Get top executive mentions."""
        asset_alerts = query_darkweb_asset_alerts(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_assetalerts",
        )
        if not self.soc_med_included:
            asset_alerts = asset_alerts[
                ~asset_alerts["Site"].isin(self.soc_med_platforms)
            ]
        asset_alerts.sort_values(
            by=["Events", "Title"], ascending=[False, True], inplace=True
        )
        asset_alerts["Title"] = asset_alerts["Title"].str[:200]
        return asset_alerts

    def alerts_exec(self):
        """Get top executive alerts."""
        alerts_exec = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_execalerts",
        )
        alerts_exec = alerts_exec.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        if not self.soc_med_included:
            alerts_exec = alerts_exec[~alerts_exec["Site"].isin(self.soc_med_platforms)]
        alerts_exec.sort_values(
            by=["Events", "Title"], ascending=[False, True], inplace=True
        )
        alerts_exec["Title"] = alerts_exec["Title"].str[:200]
        return alerts_exec

    def dark_web_bad_actors(self):
        """Get dark web bad actors."""
        dark_web_bad_actors = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_threatactors",
        )
        dark_web_bad_actors = dark_web_bad_actors.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        dark_web_bad_actors = dark_web_bad_actors.groupby(
            "Creator", as_index=False
        ).max()
        dark_web_bad_actors = dark_web_bad_actors.sort_values(
            by=["Grade"], ascending=False
        )
        dark_web_bad_actors = dark_web_bad_actors[:10]
        # dark_web_bad_actors = translate(dark_web_bad_actors, ["Creator"])
        return dark_web_bad_actors

    def alerts_threats(self):
        """Get threat alerts."""
        alerts_threats = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_potentialthreats",
        )
        alerts_threats = alerts_threats.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        if not self.soc_med_included:
            alerts_threats = alerts_threats[
                ~alerts_threats["Site"].isin(self.soc_med_platforms)
            ]
        alerts_threats = (
            alerts_threats.groupby(["Site", "Threats"])["Threats"]
            .count()
            .nlargest(10)
            .reset_index(name="Events")
        )
        alerts_threats["Threats"] = alerts_threats["Threats"].str[:200]
        return alerts_threats

    def dark_web_sites(self):
        """Get mentions by dark web sites (top 10)."""
        dark_web_sites = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_sites",
        )
        dark_web_sites = dark_web_sites.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        if not self.soc_med_included:
            dark_web_sites = dark_web_sites[
                ~dark_web_sites["Site"].isin(self.soc_med_platforms)
            ]
        dark_web_sites = (
            dark_web_sites.groupby(["Site"])["Site"]
            .count()
            .nlargest(10)
            .reset_index(name="count")
        )
        return dark_web_sites

    def invite_only_markets(self):
        """Get alerts in invite-only markets."""
        markets = query_darkweb(
            self.org_uid,
            self.start_date,
            self.end_date,
            "vw_darkweb_inviteonlymarkets",
        )
        markets = markets.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        markets = (
            markets.groupby(["Site"])["Site"]
            .count()
            .nlargest(10)
            .reset_index(name="Alerts")
        )
        return markets

    def top_cve_table(self):
        """Get top CVEs."""
        if self.top_cves.empty:
            return pd.DataFrame(
                columns=["CVE", "Description", "DVE Rating", "Identified By"]
            )
        top_cves = self.top_cves
        top_cves["summary_short"] = top_cves["summary"].str[:500]
        top_cve_table = top_cves[["cve_id", "summary_short", "dynamic_rating"]]
        top_cve_table = top_cve_table.rename(
            columns={
                "cve_id": "CVE",
                "summary_short": "Description",
                "dynamic_rating": "DVE Rating",
            }
        )
        top_cve_table["Identified By"] = "Cybersixgill"
        # Convert to float for proper sorting
        top_cve_table["DVE Rating"] = top_cve_table["DVE Rating"].astype(float)
        top_cve_table.sort_values(by=["DVE Rating"], ascending=False, inplace=True)
        top_cve_table["DVE Rating"] = top_cve_table["DVE Rating"].astype(str)
        # Get all CVEs found in shodan
        shodan_cves = self.all_cves_df
        for cve_index, cve_row in top_cve_table.iterrows():
            if cve_row["CVE"] in shodan_cves:
                LOGGER.debug("CVE match in Shodan: %s", cve_row["CVE"])
                top_cve_table.at[cve_index, "Identified By"] += ",   Shodan"
        return top_cve_table


class Core_Cyber_Six:
    """Collect relevant CyberSix data for a given Core report."""

    def __init__(
        self,
        all_cves_df,
    ):
        """Initialize Core CyberSix class."""
        self.all_cves_df = all_cves_df
        top_cves = _latest_top_cves(query_darkweb_cves("top_cves"))
        self.top_cves = top_cves

    def top_cve_table(self):
        """Get top CVEs."""
        if self.top_cves.empty:
            return pd.DataFrame(
                columns=["CVE", "Description", "DVE Rating", "Identified By"]
            )
        top_cves = self.top_cves
        top_cves["summary_short"] = top_cves["summary"].str[:500]
        top_cve_table = top_cves[["cve_id", "summary_short", "dynamic_rating"]]
        top_cve_table = top_cve_table.rename(
            columns={
                "cve_id": "CVE",
                "summary_short": "Description",
                "dynamic_rating": "DVE Rating",
            }
        )
        top_cve_table["Identified By"] = "Cybersixgill"
        # Convert to float for proper sorting
        top_cve_table["DVE Rating"] = top_cve_table["DVE Rating"].astype(float)
        top_cve_table.sort_values(by=["DVE Rating"], ascending=False, inplace=True)
        top_cve_table["DVE Rating"] = top_cve_table["DVE Rating"].astype(str)
        # Get all CVEs found in shodan
        shodan_cves = self.all_cves_df
        for cve_index, cve_row in top_cve_table.iterrows():
            if cve_row["CVE"] in shodan_cves:
                top_cve_table.at[cve_index, "Identified By"] += ",   Shodan"
        return top_cve_table


class Flare:
    """Flare dark web data class."""

    def __init__(
        self,
        trending_start_date,
        start_date,
        end_date,
        org_uid,
        all_cves_df,
        soc_med_included,
    ):
        """Initialize Flare dark web class."""
        # Initialize variables
        self.trending_start_date = trending_start_date
        self.start_date = start_date
        self.end_date = end_date
        self.org_uid = org_uid
        self.all_cves_df = all_cves_df
        self.soc_med_included = soc_med_included
        self.soc_med_platforms = [
            "twitter",
            "Twitter",
            "reddit",
            "Reddit",
            "Parler",
            "parler",
            "linkedin",
            "Linkedin",
            "discord",
            "forum_discord",
            "raddle",
            "telegram",
            "jabber",
            "ICQ",
            "icq",
            "mastodon",
        ]
        # Get cyhy_db_name for this org
        conn = connect()
        all_org_details = get_orgs(conn)
        org_details = [item for item in all_org_details if item[0] == self.org_uid]
        self.org_abbrv = org_details[0][2]
        # Retrieve all Flare events for this org and time period
        all_events = query_flare_all_events(org_uid, start_date, end_date)
        # Filter out social media platforms if specified
        if not soc_med_included:
            all_events = all_events[~all_events["source"].isin(self.soc_med_platforms)]
        all_events = all_events.reset_index(drop=True)
        self.all_events = all_events
        # Get Flare identifier (asset) info for this org
        [
            self.flare_alias_dict,
            self.flare_domain_dict,
            self.flare_ip_dict,
            self.flare_exec_dict,
            self.flare_extra_ident_dict,
        ] = self.get_flare_identifier_dicts(self.org_abbrv)
        self.flare_all_asset_dict = (
            self.flare_alias_dict
            | self.flare_domain_dict
            | self.flare_ip_dict
            | self.flare_exec_dict
            | self.flare_extra_ident_dict
        )
        # Aggregate all Flare "mention" events (both social media and dark web)
        self.mention_event_types = [
            "chat_message",
            "social_media",
            "social_media_account",
            "blog_content",
            "blog_post",
            "forum_post",
            "forum_profile",
            "forum_topic",
        ]
        mentions = self.all_events.loc[
            self.all_events["event_type"].isin(self.mention_event_types)
        ]
        mentions = mentions.reset_index(drop=True)
        self.mentions = mentions
        # Aggregate all Flare "executive alert" events (any events involving executive identifiers)
        self.flare_exec_ids = list(self.flare_exec_dict.keys())
        exec_events = self.all_events[
            self.all_events["related_identifiers"].apply(
                lambda x: any(item in x for item in self.flare_exec_ids)
            )
        ]
        exec_events = exec_events.reset_index(drop=True)
        self.exec_events = exec_events
        # Aggregate all Flare "asset alert" events (any events involving domain/ip identifiers)
        domain_ids = list(self.flare_domain_dict.keys())
        ip_ids = list(self.flare_ip_dict.keys())
        self.flare_asset_ids = domain_ids + ip_ids
        asset_events = self.all_events[
            self.all_events["related_identifiers"].apply(
                lambda x: any(item in x for item in self.flare_asset_ids)
            )
        ]
        asset_events = asset_events.reset_index(drop=True)
        self.asset_events = asset_events
        # Aggregate all Flare "alert" events
        # alert type events + executive alert events + asset alert events
        self.alert_event_types = [
            "bot",
            "bucket",
            "bucket_object",
            "domain",
            "service",
            "stealer_log",
            "listing",
        ]
        alerts = self.all_events.loc[
            self.all_events["event_type"].isin(self.alert_event_types)
        ]
        alerts = pd.concat([alerts, self.exec_events, self.asset_events], axis=0)
        dedupe_cols = [
            item
            for item in alerts.columns.tolist()
            if item not in ["related_identifiers", "related_identifiers_txt"]
        ]
        alerts.drop_duplicates(subset=dedupe_cols, inplace=True)
        alerts = alerts.reset_index(drop=True)
        self.alerts = alerts
        # Assemble top 10 CVEs for this report period (Shodan EPSS)
        self.top_cves = query_shodan_top_cves()
        # Retrieve Flare event type definitions
        self.event_type_defs = query_flare_event_type_defs()

    def get_flare_token(self, api_auth, tenant_id):
        """Get Flare API authentication token."""
        url = "https://api.flare.io/tokens/generate"
        headers = {
            "Content-Type": "application/json",
        }
        data = f'{{"tenant_id": {tenant_id}}}'
        resp = requests.post(
            url,
            data=data,
            headers=headers,
            auth=api_auth,
            timeout=PE_API_REQUEST_TIMEOUT,
        )
        # Retry clause in case API falters
        retry_count, max_retries, time_delay = 1, 5, 3
        while resp.status_code != 200 and retry_count <= max_retries:
            LOGGER.warning(
                f"\tRetrying Flare token API endpoint (code {resp.status_code}), attempt {retry_count} of {max_retries}"
            )
            time.sleep(time_delay)
            resp = requests.post(
                url,
                data=data,
                headers=headers,
                auth=api_auth,
                timeout=PE_API_REQUEST_TIMEOUT,
            )
            retry_count += 1
        # Return results
        if retry_count == max_retries + 1:
            LOGGER.error("Error: Failed to retrieve Flare token")
            return None
        else:
            resp = resp.json()
            return resp.get("token")

    def get_ident_group_info(self, flare_token, org_name):
        """Retrieve identifier group info for the specified organization."""
        url = "https://api.flare.io/firework/v2/assets/groups/"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {flare_token}",
        }
        resp = requests.get(url, headers=headers, timeout=PE_API_REQUEST_TIMEOUT)
        # Retry clause in case API falters
        retry_count, max_retries, time_delay = 1, 5, 3
        while resp.status_code != 200 and retry_count <= max_retries:
            LOGGER.warning(
                f"\tRetrying Flare identifier group info API endpoint (code {resp.status_code}), attempt {retry_count} of {max_retries}"
            )
            time.sleep(time_delay)
            resp = requests.get(url, headers=headers, timeout=PE_API_REQUEST_TIMEOUT)
            retry_count += 1
        # Return results
        if retry_count == max_retries + 1:
            LOGGER.error("Error: Failed to retrieve Flare identifier group info")
            return None
        else:
            # PE&T parent group id
            resp = resp.json()
            group_id = 191286
            orgs_list = resp.get("assets_groups")
            org_id = [
                o
                for o in orgs_list
                if o["name"] == org_name and o["parent_group_id"] == group_id
            ][0].get("id")
            return {
                "name": org_name,
                "id": org_id,
            }

    def get_ident_by_group_id(self, flare_token, ident_group_id):
        """Retrieve all identifiers for the specified group ID."""
        url = "https://api.flare.io/firework/v3/identifiers/"
        params = {
            "parent_group_id": ident_group_id,
        }
        headers = {"Authorization": f"Bearer {flare_token}"}
        resp = requests.get(
            url, headers=headers, params=params, timeout=PE_API_REQUEST_TIMEOUT
        )
        # Retry clause in case API falters
        retry_count, max_retries, time_delay = 1, 5, 3
        while resp.status_code != 200 and retry_count <= max_retries:
            LOGGER.warning(
                f"\tRetrying org Flare identifiers API endpoint (code {resp.status_code}), attempt {retry_count} of {max_retries}"
            )
            time.sleep(time_delay)
            resp = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=PE_API_REQUEST_TIMEOUT,
            )
            retry_count += 1
        # Return results
        if retry_count == max_retries + 1:
            LOGGER.error("Error: Failed to retrieve org Flare identifiers")
            return None
        else:
            resp = resp.json()
            # Format identifier info
            ident_list = []
            for ident in resp.get("items"):
                ident_id = ident.get("id")
                ident_value = ident.get("name")
                ident_type = ident.get("type")
                ident_dict = {"id": ident_id, "value": ident_value, "type": ident_type}
                ident_list.append(ident_dict)
            if len(ident_list) == 0:
                return [
                    {
                        "id": None,
                        "value": None,
                        "type": None,
                    }
                ]
            else:
                return ident_list

    def _identifiers_from_stored_events(self):
        """Build identifier id→label map from flare_events rows already in the DB."""
        event_idents_dict = {}
        if self.all_events is None or self.all_events.empty:
            return event_idents_dict
        for _, row in self.all_events.iterrows():
            ids = row.get("related_identifiers") or []
            txts = row.get("related_identifiers_txt") or []
            if not isinstance(ids, (list, tuple)):
                continue
            if not isinstance(txts, (list, tuple)):
                txts = []
            for idx, ident_id in enumerate(ids):
                label = txts[idx] if idx < len(txts) else ident_id
                event_idents_dict[str(ident_id)] = str(label)
        return event_idents_dict

    def get_flare_identifier_dicts(self, org_abbrv):
        """Format Flare identifiers into dictionaries for the specified org."""
        flare_key = os.environ.get("FLARE_API_KEY", "").strip()
        flare_tenant_id = os.environ.get("FLARE_TENANT_ID", "").strip()
        flare_aliases = {}
        flare_domains = {}
        flare_ips = {}
        flare_execs = {}

        if flare_key and flare_tenant_id:
            flare_api_auth = HTTPBasicAuth("", flare_key)
            flare_token = self.get_flare_token(flare_api_auth, flare_tenant_id)
            if flare_token:
                flare_org_info = self.get_ident_group_info(flare_token, org_abbrv)
                if flare_org_info and flare_org_info.get("id") is not None:
                    flare_org_identifiers = self.get_ident_by_group_id(
                        flare_token, flare_org_info.get("id")
                    )
                    if flare_org_identifiers:
                        for ident in flare_org_identifiers:
                            if ident.get("type") == "keyword":
                                flare_aliases[str(ident.get("id"))] = str(
                                    ident.get("value")
                                )
                            elif ident.get("type") == "domain":
                                flare_domains[str(ident.get("id"))] = str(
                                    ident.get("value")
                                )
                            elif ident.get("type") == "ip":
                                flare_ips[str(ident.get("id"))] = str(
                                    ident.get("value")
                                )
                            elif ident.get("type") == "identity":
                                flare_execs[str(ident.get("id"))] = str(
                                    ident.get("value")
                                )
            else:
                LOGGER.warning(
                    "Flare API token unavailable for %s; "
                    "using identifier text from stored flare_events",
                    org_abbrv,
                )
        else:
            LOGGER.warning(
                "FLARE_API_KEY or FLARE_TENANT_ID not set; "
                "using identifier text from stored flare_events for %s",
                org_abbrv,
            )

        # Identifiers referenced in events but not returned by the API (or when API is skipped)
        flare_extra_idents = {}
        event_idents_df = self.all_events[
            ["related_identifiers", "related_identifiers_txt"]
        ]
        if len(event_idents_df) > 0:
            event_idents_df["related_identifiers_dict"] = event_idents_df.apply(
                lambda row: dict(
                    zip(row["related_identifiers"], row["related_identifiers_txt"])
                ),
                axis=1,
            )
            event_idents_dict = {}
            for _, row in event_idents_df.iterrows():
                event_idents_dict.update(row["related_identifiers_dict"])
            group_idents_dict = flare_aliases | flare_domains | flare_ips | flare_execs
            extra_ident_keys = list(event_idents_dict.keys() - group_idents_dict.keys())
            flare_extra_idents = {
                key: event_idents_dict[key]
                for key in extra_ident_keys
                if key in event_idents_dict
            }

        return [
            flare_aliases,
            flare_domains,
            flare_ips,
            flare_execs,
            flare_extra_idents,
        ]

    def dark_web_mentions_total(self):
        """Get the total number of dark web mentions."""
        return len(self.mentions)

    def dark_web_alerts_total(self):
        """Get the total number of dark web alerts."""
        return len(self.alerts)

    def dark_web_mentions_by_date(self):
        """Get the dark web mention counts for each of the past 4 weeks."""
        # Caclculate daily totals for Flare mentions
        all_date_list = pd.date_range(
            start=self.trending_start_date, end=self.end_date, freq="d"
        ).to_list()
        all_date_list = [dt_obj.date() for dt_obj in all_date_list]
        all_date_df = pd.DataFrame(
            {
                "organizations_uid": self.org_uid,
                "date": all_date_list,
                "Count": 0,
            }
        )
        mention_daily_counts = query_flare_mentions_by_date(
            self.trending_start_date,
            self.end_date,
            self.org_uid,
            self.mention_event_types,
        )
        all_date_df = all_date_df[
            ~all_date_df["date"].isin(mention_daily_counts["date"].to_list())
        ]
        mention_daily_counts = (
            pd.concat([mention_daily_counts, all_date_df], axis=0)
            .sort_values(by="date", ascending=False)
            .reset_index(drop=True)
        )
        mention_daily_counts = mention_daily_counts.drop(
            columns=["organizations_uid"],
            errors="ignore",
        )
        # Calculate weekly totals for Flare mentions
        idx = pd.date_range(self.trending_start_date, self.end_date)
        mention_daily_counts = (
            mention_daily_counts.set_index("date")
            .reindex(idx)
            .fillna(0.0)
            .rename_axis("date")
        )
        group_limit = self.end_date + datetime.timedelta(1)
        mention_weekly_counts = mention_daily_counts.groupby(
            pd.Grouper(level="date", freq="7d", origin=group_limit)
        ).sum()
        mention_weekly_counts["date"] = mention_weekly_counts.index
        # Adjust dates field for readability
        mention_weekly_counts["date_readable"] = ""
        for idx, row in mention_weekly_counts.iterrows():
            start_date = row["date"]
            start_date_str = start_date.strftime("%m/%d")
            end_date = start_date + datetime.timedelta(days=6)
            end_date_str = end_date.strftime("%m/%d")
            mention_weekly_counts.at[
                idx, "date_readable"
            ] = f"{start_date_str} - {end_date_str}"
        mention_weekly_counts = mention_weekly_counts[["Count", "date_readable"]]
        mention_weekly_counts.rename(columns={"date_readable": "date"}, inplace=True)
        mention_weekly_counts = mention_weekly_counts.set_index("date")
        mention_weekly_counts = mention_weekly_counts[["Count"]]
        return mention_weekly_counts

    def dark_web_mentions_soc_media(self):
        """Get social media mentions."""
        soc_media_event_types = [
            "chat_message",
            "social_media",
            "social_media_account",
        ]
        mentions_soc_media = self.mentions.loc[
            self.mentions["event_type"].isin(soc_media_event_types)
        ]
        mentions_soc_media = mentions_soc_media[["title", "actor", "risk_scores"]]
        mentions_soc_media["risk_scores"] = mentions_soc_media[
            "risk_scores"
        ].str.replace("{'score': ", "")
        mentions_soc_media["risk_scores"] = mentions_soc_media[
            "risk_scores"
        ].str.replace("}", "")
        mentions_soc_media = mentions_soc_media.rename(
            columns={"title": "Title", "actor": "Author", "risk_scores": "Risk Score"}
        )
        mentions_soc_media.sort_values(
            by=["Risk Score", "Title"], ascending=[False, True], inplace=True
        )
        mentions_soc_media = mentions_soc_media[:10]
        # Translate title field to english
        # soc_med_most_act = translate(soc_med_most_act, ["Title"])
        mentions_soc_media["Title"] = mentions_soc_media["Title"].str[:200]
        mentions_soc_media = mentions_soc_media.replace(
            r"^\s*$", "Untitled", regex=True
        )
        return mentions_soc_media

    def dark_web_mentions_other(self):
        """Get dark web (non-social media) mentions."""
        non_soc_media_event_types = [
            "blog_content",
            "blog_post",
            "forum_post",
            "forum_profile",
            "forum_topic",
        ]
        mentions_dark_web = self.mentions.loc[
            self.mentions["event_type"].isin(non_soc_media_event_types)
        ]
        mentions_dark_web = mentions_dark_web[["title", "actor", "risk_scores"]]
        mentions_dark_web["risk_scores"] = mentions_dark_web["risk_scores"].str.replace(
            "{'score': ", ""
        )
        mentions_dark_web["risk_scores"] = mentions_dark_web["risk_scores"].str.replace(
            "}", ""
        )
        mentions_dark_web = mentions_dark_web.rename(
            columns={"title": "Title", "actor": "Author", "risk_scores": "Risk Score"}
        )
        mentions_dark_web.sort_values(
            by=["Risk Score", "Title"], ascending=[False, True], inplace=True
        )
        mentions_dark_web = mentions_dark_web[:10]
        # Translate title field to english
        # mentions_dark_web = translate(mentions_dark_web, ["Title"])
        mentions_dark_web["Title"] = mentions_dark_web["Title"].str[:200]
        mentions_dark_web = mentions_dark_web.replace(r"^\s*$", "Untitled", regex=True)
        return mentions_dark_web

    def dark_web_alerts_assets(self):
        """Get dark web asset alerts."""
        # Get events that involve domain/ip identifiers
        asset_ids = self.flare_asset_ids
        alerts_asset = self.asset_events
        # Catch scenario where there are no asset alerts
        if alerts_asset.empty:
            return pd.DataFrame(columns=["Site", "Title", "Asset"])
        alerts_asset = alerts_asset.explode("related_identifiers").reset_index(
            drop=True
        )
        alerts_asset = alerts_asset[
            alerts_asset["related_identifiers"].isin(asset_ids)
        ].reset_index(drop=True)
        alerts_asset = alerts_asset[["source", "title", "related_identifiers"]].rename(
            columns={"source": "Site", "title": "Title", "related_identifiers": "Asset"}
        )
        # Replace asset IDs with actual values
        alerts_asset["Asset"] = (
            alerts_asset["Asset"]
            .replace(self.flare_domain_dict)
            .replace(self.flare_ip_dict)
        )
        alerts_asset.sort_values(by=["Asset"], ascending=True, inplace=True)
        # Filter our social media platforms if specified
        if not self.soc_med_included:
            alerts_asset = alerts_asset[
                ~alerts_asset["Site"].isin(self.soc_med_platforms)
            ]
        alerts_asset["Title"] = alerts_asset["Title"].str[:200]
        return alerts_asset

    def dark_web_alerts_exec(self):
        """Get dark web events involving executive identifiers."""
        # Identify events that involve executive leadership identifiers
        exec_ids = self.flare_exec_ids
        alerts_exec = self.exec_events
        # Catch scenario where there are no executive alerts
        if alerts_exec.empty:
            return pd.DataFrame(columns=["Site", "Title", "Executive"])
        alerts_exec = alerts_exec.explode("related_identifiers").reset_index(drop=True)
        alerts_exec = alerts_exec[
            alerts_exec["related_identifiers"].isin(exec_ids)
        ].reset_index(drop=True)
        alerts_exec = alerts_exec[["source", "title", "related_identifiers"]].rename(
            columns={
                "source": "Site",
                "title": "Title",
                "related_identifiers": "Executive",
            }
        )
        # Replace executive IDs with actual names
        alerts_exec["Executive"] = alerts_exec["Executive"].replace(
            self.flare_exec_dict
        )
        alerts_exec.sort_values(by=["Executive"], ascending=True, inplace=True)
        alerts_exec["Title"] = alerts_exec["Title"].str[:200]
        return alerts_exec

    def dark_web_threat_actors(self):
        """Get the most active threat actors for the specified organization and report period."""
        # Calculate the top 10 threat actors with the most Flare events
        dark_web_bad_actors = self.all_events[["actor"]]
        dark_web_bad_actors.replace("", None, inplace=True)
        # Catch scenario where there are no Flare events
        if dark_web_bad_actors.empty:
            return pd.DataFrame(columns=["Actor", "Event Count"])
        # Fix "None" or blank threat actor fields
        dark_web_bad_actors["actor"] = dark_web_bad_actors["actor"].replace(
            "None", "Unknown"
        )
        dark_web_bad_actors["actor"] = dark_web_bad_actors["actor"].replace(
            "", "Unknown"
        )
        dark_web_bad_actors = dark_web_bad_actors.rename(columns={"actor": "Actor"})
        dark_web_bad_actors = (
            dark_web_bad_actors.groupby("Actor").size().reset_index(name="Event Count")
        )
        dark_web_bad_actors = dark_web_bad_actors.sort_values(
            by="Event Count", ascending=False
        ).reset_index(drop=True)
        dark_web_bad_actors = dark_web_bad_actors[:10]
        return dark_web_bad_actors

    def dark_web_alerts_threats(self):
        """Get dark web potential threat alerts."""
        event_types = [
            "bot",
            "bucket",
            "bucket_object",
            "domain",
            "service",
        ]  # v1.1 threat event types
        alerts_threats = self.alerts.loc[self.alerts["event_type"].isin(event_types)]
        # Catch scenario where there are no potential threat alerts
        if alerts_threats.empty:
            return pd.DataFrame(columns=["Site", "Threat Type", "Events"])
        alerts_threats = alerts_threats.rename(
            columns={
                "event_date": "date",
                "source": "Site",
                "event_type": "Threat Type",
            }
        )
        alerts_threats = alerts_threats[
            [
                "organizations_uid",
                "date",
                "Site",
                "Threat Type",
            ]
        ]
        alerts_threats = alerts_threats.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        alerts_threats = (
            alerts_threats.groupby(["Site", "Threat Type"])["Threat Type"]
            .count()
            .nlargest(10)
            .reset_index(name="Events")
        )
        alerts_threats["Threat Type"] = alerts_threats["Threat Type"].str[:200]
        # Make threats more readable
        threat_dict = {
            "bot": "Botnet Infected Device",
            "bucket": "Exposed Bucket",
            "bucket_object": "Exposed Bucket Object",
            "domain": "Typo-Squatting Domain",
            "service": "Exposed Service",
        }
        alerts_threats["Threat Type"] = alerts_threats["Threat Type"].replace(
            threat_dict
        )
        return alerts_threats

    def dark_web_sites(self):
        """Get the most active sites for this report period."""
        # Catch scenario where there are no Flare events
        if self.all_events.empty:
            return pd.DataFrame(columns=["Site", "Event Count"])
        dark_web_sites = self.all_events[["organizations_uid", "event_date", "source"]]
        dark_web_sites = dark_web_sites.rename(
            columns={
                "event_date": "date",
                "source": "Site",
            }
        )
        dark_web_sites = dark_web_sites.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        dark_web_sites = (
            dark_web_sites.groupby(["Site"])["Site"]
            .count()
            .nlargest(10)
            .reset_index(name="Event Count")
        )
        return dark_web_sites

    def dark_web_alerts_market(self):
        """Get dark web invite-only market alerts."""
        event_types = [
            "listing",
            "stealer_log",
        ]
        markets = self.alerts.loc[self.alerts["event_type"].isin(event_types)]
        # Catch scenario where there are no market alerts
        if markets.empty:
            return pd.DataFrame(columns=["Site", "Alert"])
        markets = markets[
            [
                "organizations_uid",
                "event_date",
                "source",
            ]
        ]
        markets = markets.rename(columns={"event_date": "date", "source": "Site"})
        markets = markets.drop(
            columns=["organizations_uid", "date"],
            errors="ignore",
        )
        markets = (
            markets.groupby(["Site"])["Site"]
            .count()
            .nlargest(10)
            .reset_index(name="Alerts")
        )
        return markets

    def top_cve_table(self):
        """Get top 10 CVEs for this report period, formatted for table."""
        top_cves = self.top_cves
        if top_cves is None or top_cves.empty:
            return pd.DataFrame(
                columns=["CVE", "Description", "EPSS Rating", "Identified By"]
            )
        top_cves["summary_short"] = top_cves["summary"].str[:500]
        top_cve_table = top_cves[["cve_id", "summary_short", "epss_score"]].copy()
        top_cve_table = top_cve_table.rename(
            columns={
                "cve_id": "CVE",
                "summary_short": "Description",
                "epss_score": "EPSS Rating",
            }
        )
        top_cve_table["Identified By"] = "Shodan"
        # Convert to float for proper sorting
        top_cve_table["EPSS Rating"] = top_cve_table["EPSS Rating"].astype(float)
        top_cve_table.sort_values(by=["EPSS Rating"], ascending=False, inplace=True)
        top_cve_table["EPSS Rating"] = top_cve_table["EPSS Rating"].astype(str)
        return top_cve_table

    def dark_web_counts_df(self):
        """Build dataframe of counts for certain dark web finding types."""
        count_dicts = []
        # Get count of invite-only market alerts
        markets = self.alerts.loc[
            self.alerts["event_type"].isin(
                [
                    "listing",
                    "stealer_log",
                ]
            )
        ]
        if len(markets) > 0:
            count_dicts.append(
                {
                    "Name": "INVITE ONLY MARKET",
                    "Value": len(markets),
                }
            )
        # Get count of social media mentions
        if self.soc_med_included:
            soc_med = self.mentions.loc[
                self.mentions["event_type"].isin(
                    [
                        "chat_message",
                        "social_media",
                        "social_media_account",
                    ]
                )
            ]
            if len(soc_med) > 0:
                count_dicts.append(
                    {
                        "Name": "SOCIAL MEDIA",
                        "Value": len(soc_med),
                    }
                )
        # Get count of dark web mentions
        dark_web_forum = self.mentions.loc[
            self.mentions["event_type"].isin(
                [
                    "blog_content",
                    "blog_post",
                    "forum_post",
                    "forum_profile",
                    "forum_topic",
                ]
            )
        ]
        if len(dark_web_forum) > 0:
            count_dicts.append(
                {
                    "Name": "DARK WEB FORUM",
                    "Value": len(dark_web_forum),
                }
            )
        # Get count of executive alerts
        alerts_exec = self.exec_events
        if len(alerts_exec) > 0:
            count_dicts.append(
                {
                    "Name": "EXECUTIVES",
                    "Value": len(alerts_exec),
                }
            )
        # Return results
        if count_dicts:
            circle_df = pd.DataFrame(count_dicts)
            return circle_df
        else:
            return 0

    def dark_web_event_types(self):
        """Get definitions for all event types."""
        return self.event_type_defs

"""Report-generation FastAPI routes ported from ATC-Framework CD-add-CODEOWNERS."""

# Standard Python Libraries
import logging
from typing import List
import uuid

# Third-Party Libraries
from dataAPI import report_schemas as schemas
from dataAPI.views import convert_date_to_string, convert_uuid_to_string, verify_api_key
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from fastapi import APIRouter, Depends, HTTPException, status
from home.models import (
    Alerts,
    Cidrs,
    DomainAlerts,
    DomainPermutations,
    Mentions,
    Organizations,
    ReportSummaryStats,
    RootDomains,
    ShodanAssets,
    SubDomains,
    TopCves,
    VwBreachcomp,
    VwBreachcompBreachdetails,
    VwBreachcompCredsbydate,
    VwDarkwebAssetalerts,
    VwDarkwebExecalerts,
    VwDarkwebInviteonlymarkets,
    VwDarkwebMentionsbydate,
    VwDarkwebMostactposts,
    VwDarkwebPotentialthreats,
    VwDarkwebSites,
    VwDarkwebSocmediaMostactposts,
    VwDarkwebThreatactors,
    VwIpsSubRootOrgInfo,
)

LOGGER = logging.getLogger(__name__)
report_router = APIRouter()


# --- query_domMasq_alerts(), Issue 562 ---
@report_router.post(
    "/domain_alerts_by_org_date",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.DomainAlertsTable],
    tags=["Get all domain_alerts table data for the specified org_uid and date range."],
)
def domain_alerts_by_org_date(
    data: schemas.GenInputOrgUIDDateRange, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get all domain_alerts table data for the specified org_uid and date range."""
    # Check for API key
    try:
        # If API key valid, make query
        domain_alerts_by_org_date_data = list(
            DomainAlerts.objects.filter(
                organizations_uid=data.org_uid,
                date__range=[data.start_date, data.end_date],
            ).values()
        )
        # Convert uuids to strings
        for row in domain_alerts_by_org_date_data:
            row["domain_alert_uid"] = convert_uuid_to_string(row["domain_alert_uid"])
            row["sub_domain_uid_id"] = convert_uuid_to_string(row["sub_domain_uid_id"])
            row["data_source_uid_id"] = convert_uuid_to_string(
                row["data_source_uid_id"]
            )
            row["organizations_uid_id"] = convert_uuid_to_string(
                row["organizations_uid_id"]
            )
            row["date"] = convert_date_to_string(row["date"])
        return domain_alerts_by_org_date_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_domMasq(), Issue 563 ---
@report_router.post(
    "/domain_permu_by_org_date",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.DomainPermuTable],
    tags=[
        "Get all domain_permutations table data for the specified org_uid and date range."
    ],
)
def domain_permu_by_org_date(
    data: schemas.GenInputOrgUIDDateRange, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get all domain_permutations table data for the specified org_uid and date range."""
    # Check for API key
    try:
        # If API key valid, make query
        domain_permu_by_org_date_data = list(
            DomainPermutations.objects.filter(
                organizations_uid=data.org_uid,
                date_active__range=[data.start_date, data.end_date],
            ).values()
        )
        # Convert uuids to strings
        for row in domain_permu_by_org_date_data:
            row["suspected_domain_uid"] = convert_uuid_to_string(
                row["suspected_domain_uid"]
            )
            row["organizations_uid_id"] = convert_uuid_to_string(
                row["organizations_uid_id"]
            )
            row["date_observed"] = convert_date_to_string(row["date_observed"])
            row["data_source_uid_id"] = convert_uuid_to_string(
                row["data_source_uid_id"]
            )
            row["sub_domain_uid_id"] = convert_uuid_to_string(row["sub_domain_uid_id"])
            row["date_active"] = convert_date_to_string(row["date_active"])
        return domain_permu_by_org_date_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- get_org_assets_count_past(), Issue 603 ---
@report_router.post(
    "/past_asset_counts_by_org",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.RSSTable],
    tags=["Get all RSS data for the specified org_uid and date."],
)
def past_asset_counts_by_org(
    data: schemas.GenInputOrgUIDDateSingle, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get all RSS data for the specified org_uid and date."""
    # Check for API key
    try:
        # If API key valid, make query
        past_asset_counts_by_org_data = list(
            ReportSummaryStats.objects.filter(
                organizations_uid=data.org_uid, end_date=data.date
            ).values()
        )
        # Convert uuids to strings
        for row in past_asset_counts_by_org_data:
            row["report_uid"] = convert_uuid_to_string(row["report_uid"])
            row["organizations_uid_id"] = convert_uuid_to_string(
                row["organizations_uid_id"]
            )
            row["start_date"] = convert_date_to_string(row["start_date"])
            row["end_date"] = convert_date_to_string(row["end_date"])
        return past_asset_counts_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_extra_ips(), Issue 612 ---
@report_router.post(
    "/extra_ips_by_org",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.ExtraIpsByOrg],
    tags=["Get all extra IPs for the specified organization."],
)
def extra_ips_by_org(
    data: schemas.GenInputOrgUIDSingle, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get all extra IPs for the specified organization."""
    # Check for API key
    try:
        # If API key valid, make query
        extra_ips_by_org_data = list(
            VwIpsSubRootOrgInfo.objects.filter(
                organizations_uid=data.org_uid,
                origin_cidr__isnull=True,
                i_current=True,
                sd_current=True,
            ).values("ip_hash", "ip")
        )
        return extra_ips_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_cidrs_by_org(), Issue 618 ---
@report_router.post(
    "/cidrs_by_org",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.CidrsByOrg],
    tags=["Get all CIDRs for a specified organization."],
)
def cidrs_by_org(
    data: schemas.GenInputOrgUIDSingle, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get all CIDRs for a specified organization."""
    # Check for API key
    try:
        # If API key valid, make query
        cidrs_by_org_data = list(
            Cidrs.objects.filter(organizations_uid=data.org_uid, current=True).values()
        )
        # Convert uuids to strings
        for row in cidrs_by_org_data:
            row["cidr_uid"] = convert_uuid_to_string(row["cidr_uid"])
            row["organizations_uid_id"] = convert_uuid_to_string(
                row["organizations_uid_id"]
            )
            row["data_source_uid_id"] = convert_uuid_to_string(
                row["data_source_uid_id"]
            )
            row["first_seen"] = convert_date_to_string(row["first_seen"])
            row["last_seen"] = convert_date_to_string(row["last_seen"])
        # Catch query no results scenario
        return cidrs_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_software(), Issue 620 ---
@report_router.post(
    "/software_by_org",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.SoftwareByOrg],
    tags=["Get all distinct software products for a specified organization."],
)
def software_by_org(
    data: schemas.GenInputOrgUIDSingle, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get all distinct software products for a specified organization."""
    # Check for API key
    try:
        # If API key valid, make query
        software_by_org_data = list(
            ShodanAssets.objects.filter(
                organizations_uid=data.org_uid, product__isnull=False
            )
            .values("product")
            .distinct()
        )
        return software_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_foreign_IPs(), Issue 621 ---
@report_router.post(
    "/foreign_ips_by_org",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.ForeignIpsByOrg],
    tags=["Get all foreign IPs for a specified organization."],
)
def foreign_ips_by_org(
    data: schemas.GenInputOrgUIDDateRange, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get all foreign IPs for a specified organization."""
    # Check for API key
    try:
        # If API key valid, make query
        foreign_ips_by_org_data = list(
            ShodanAssets.objects.filter(
                organizations_uid=data.org_uid,
                country_code__isnull=False,
                timestamp__range=(data.start_date, data.end_date),
            )
            .exclude(country_code="US")
            .values()
        )
        # Convert uuids to strings
        for row in foreign_ips_by_org_data:
            row["shodan_asset_uid"] = convert_uuid_to_string(row["shodan_asset_uid"])
            row["organizations_uid_id"] = convert_uuid_to_string(
                row["organizations_uid_id"]
            )
            row["timestamp"] = convert_date_to_string(row["timestamp"])
            row["data_source_uid_id"] = convert_uuid_to_string(
                row["data_source_uid_id"]
            )
        return foreign_ips_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_roots(), Issue 622 ---
@report_router.post(
    "/root_domains_by_org",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.RootDomainsByOrg],
    tags=["Get all root domains for a specified organization."],
)
def root_domains_by_org(
    data: schemas.GenInputOrgUIDSingle, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get all root domains for a specified organization."""
    # Check for API key
    try:
        # If API key valid, make query
        root_domains_by_org_data = list(
            RootDomains.objects.filter(
                organizations_uid=data.org_uid, enumerate_subs=True
            ).values("root_domain_uid", "root_domain")
        )
        # Convert uuids to strings
        for row in root_domains_by_org_data:
            row["root_domain_uid"] = convert_uuid_to_string(row["root_domain_uid"])
        return root_domains_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_creds_view(), Issue 623 ---
@report_router.post(
    "/breachcomp_by_org",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.VwBreachcomp],
    tags=["Get vw_breachcomp data for specified org and date range."],
)
def breachcomp_by_org(
    data: schemas.GenInputOrgUIDDateRange, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get vw_breachcomp data for specified org and date range."""
    # Check for API key
    try:
        # If API key valid, make query
        breachcomp_by_org_data = list(
            VwBreachcomp.objects.filter(
                organizations_uid=data.org_uid,
                modified_date__date__range=(data.start_date, data.end_date),
            ).values()
        )
        # Convert uuids to strings
        for row in breachcomp_by_org_data:
            row["credential_exposures_uid"] = convert_uuid_to_string(
                row["credential_exposures_uid"]
            )
            row["organizations_uid"] = convert_uuid_to_string(row["organizations_uid"])
            row["data_source_uid"] = convert_uuid_to_string(row["data_source_uid"])
            row["breach_date"] = convert_date_to_string(row["breach_date"])
            row["added_date"] = convert_date_to_string(row["added_date"])
            row["modified_date"] = convert_date_to_string(row["modified_date"])
        return breachcomp_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_credsbyday_view(), Issue 624 ---
@report_router.post(
    "/credsbydate_by_org",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.CredsbydateByOrg],
    tags=["Get vw_breachcomp_credsbydate data for specified org and date range."],
)
def credsbydate_by_org(
    data: schemas.GenInputOrgUIDDateRange, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get vw_breachcomp_credsbydate data for specified org and date range."""
    # Check for API key
    try:
        # If API key valid, make query
        credsbydate_by_org_data = list(
            VwBreachcompCredsbydate.objects.filter(
                organizations_uid=data.org_uid,
                mod_date__range=(data.start_date, data.end_date),
            ).values("mod_date", "no_password", "password_included")
        )
        # Convert uuids to strings
        for row in credsbydate_by_org_data:
            row["mod_date"] = convert_date_to_string(row["mod_date"])
        return credsbydate_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_breachdetails_view(), Issue 625 ---
@report_router.post(
    "/breachdetails_by_org",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.BreachdetailsByOrg],
    tags=["Get vw_breachcomp_breachdetails data for specified org and date range."],
)
def breachdetails_by_org(
    data: schemas.GenInputOrgUIDDateRange, tokens: str = Depends(verify_api_key)
):
    """Create API endpoint to get vw_breachcomp_breachdetails data for specified org and date range."""
    # Check for API key
    try:
        # If API key valid, make query
        breachdetails_by_org_data = list(
            VwBreachcompBreachdetails.objects.filter(
                organizations_uid=data.org_uid,
                mod_date__range=(data.start_date, data.end_date),
            ).values(
                "breach_name",
                "mod_date",
                "breach_date",
                "password_included",
                "number_of_creds",
            )
        )
        # Convert uuids to strings
        for row in breachdetails_by_org_data:
            row["mod_date"] = convert_date_to_string(row["mod_date"])
            row["breach_date"] = convert_date_to_string(row["breach_date"])
        return breachdetails_by_org_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- Issue 626 ---
# Query domain masquerading on the domain permutattions tables


# --- query_darkweb(), Issue 629 ---
@report_router.post(
    "/darkweb_data",
    tags=["Get darkweb data from various tables"],
)
def darkweb_data(data: schemas.DarkWebDataInput, tokens: str = Depends(verify_api_key)):
    """Create API Endpoint to query the darkweb data from various tables."""
    try:
        sdate = data.start_date
        edate = data.end_date
        if data.table == "mentions":
            mentions = list(
                Mentions.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )[:10]
            # Make fields serializable
            for row in mentions:
                row["mentions_uid"] = convert_uuid_to_string(row["mentions_uid"])
                row["date"] = convert_date_to_string(row["date"])
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["data_source_uid_id"] = convert_uuid_to_string(
                    row["data_source_uid_id"]
                )
            return mentions
        elif data.table == "alerts":
            alerts = list(
                Alerts.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in alerts:
                row["organizations_uid_id"] = convert_uuid_to_string(
                    row["organizations_uid_id"]
                )
                row["date"] = convert_date_to_string(row["date"])
                row["alerts_uid"] = convert_uuid_to_string(row["alerts_uid"])
                row["data_source_uid_id"] = convert_uuid_to_string(
                    row["data_source_uid_id"]
                )
            return alerts
        elif data.table == "vw_darkweb_mentionsbydate":
            mentionsbydate = list(
                VwDarkwebMentionsbydate.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in mentionsbydate:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return mentionsbydate
        elif data.table == "vw_darkweb_inviteonlymarkets":
            inviteonlymarkets = list(
                VwDarkwebInviteonlymarkets.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in inviteonlymarkets:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return inviteonlymarkets
        elif data.table == "vw_darkweb_socmedia_mostactposts":
            socmedia_mostactposts = list(
                VwDarkwebSocmediaMostactposts.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in socmedia_mostactposts:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return socmedia_mostactposts
        elif data.table == "vw_darkweb_mostactposts":
            mostactposts = list(
                VwDarkwebMostactposts.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in mostactposts:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return mostactposts
        elif data.table == "vw_darkweb_execalerts":
            execalerts = list(
                VwDarkwebExecalerts.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in execalerts:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return execalerts
        elif data.table == "vw_darkweb_assetalerts":
            assetalerts = list(
                VwDarkwebAssetalerts.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in assetalerts:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return assetalerts
        elif data.table == "vw_darkweb_threatactors":
            threatactors = list(
                VwDarkwebThreatactors.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in threatactors:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return threatactors
        elif data.table == "vw_darkweb_potentialthreats":
            potentialthreats = list(
                VwDarkwebPotentialthreats.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in potentialthreats:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return potentialthreats
        elif data.table == "vw_darkweb_sites":
            sites = list(
                VwDarkwebSites.objects.filter(
                    organizations_uid=data.org_uid, date__range=(sdate, edate)
                ).values()
            )
            # Make fields serializable
            for row in sites:
                row["organizations_uid"] = convert_uuid_to_string(
                    row["organizations_uid"]
                )
                row["date"] = convert_date_to_string(row["date"])
            return sites
    except Exception as error:
        LOGGER.error("Report API error in darkweb_data: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
        ) from error


# --- query_darkweb_cves(), Issue 630 ---
@report_router.post(
    "/darkweb_cves",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.TopCvesTable],
    tags=["Get all darkweb cve data"],
)
def darkweb_cves(tokens: str = Depends(verify_api_key)):
    """Return all top_cves rows (sync local port of ATC darkweb_cves_task)."""
    try:
        darkweb_cves_data = list(TopCves.objects.all().values())
        for row in darkweb_cves_data:
            row["top_cves_uid"] = convert_uuid_to_string(row["top_cves_uid"])
            row["data_source_uid_id"] = convert_uuid_to_string(
                row["data_source_uid_id"]
            )
            row["date"] = convert_date_to_string(row["date"])
        return darkweb_cves_data
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- execute_scorecard(), Issue 632 ---
@report_router.put(
    "/rss_insert",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    # response_model=None (nothing returned)
    tags=["Insert an organization's record into the report_summary_stats table"],
)
def rss_insert(data: schemas.RSSInsertInput, tokens: str = Depends(verify_api_key)):
    """Call API endpoint to insert an organization's record into the report_summary_stats table."""
    # Check for API key
    try:
        # If API key valid
        # Get Organizations.organization_uid object for the specified org
        specified_org_uid = Organizations.objects.get(
            organizations_uid=data.organizations_uid
        )
        try:
            # Check if record already exists
            ReportSummaryStats.objects.get(
                organizations_uid=specified_org_uid, start_date=data.start_date
            )
            # If it already exists, update
            ReportSummaryStats.objects.filter(
                organizations_uid=specified_org_uid,
                start_date=data.start_date,
            ).update(
                ip_count=data.ip_count,
                root_count=data.root_count,
                sub_count=data.sub_count,
                ports_count=data.num_ports,
                creds_count=data.creds_count,
                breach_count=data.breach_count,
                cred_password_count=data.cred_password_count,
                domain_alert_count=data.domain_alert_count,
                suspected_domain_count=data.suspected_domain_count,
                insecure_port_count=data.insecure_port_count,
                verified_vuln_count=data.verified_vuln_count,
                suspected_vuln_count=data.suspected_vuln_count,
                suspected_vuln_addrs_count=data.suspected_vuln_addrs_count,
                threat_actor_count=data.threat_actor_count,
                dark_web_alerts_count=data.dark_web_alerts_count,
                dark_web_mentions_count=data.dark_web_mentions_count,
                dark_web_executive_alerts_count=data.dark_web_executive_alerts_count,
                dark_web_asset_alerts_count=data.dark_web_asset_alerts_count,
                pe_number_score=data.pe_number_score,
                pe_letter_grade=data.pe_letter_grade,
                cidr_count=data.cidr_count,
                port_protocol_count=data.port_protocol_count,
                software_count=data.software_count,
                foreign_ips_count=data.foreign_ips_count,
            )
        except ReportSummaryStats.DoesNotExist:
            # Otherwise, create a new record
            ReportSummaryStats.objects.create(
                report_uid=uuid.uuid1(),
                organizations_uid=specified_org_uid,
                start_date=data.start_date,
                end_date=data.end_date,
                ip_count=data.ip_count,
                root_count=data.root_count,
                sub_count=data.sub_count,
                ports_count=data.num_ports,  # num_ports input -> ports_count
                creds_count=data.creds_count,
                breach_count=data.breach_count,
                cred_password_count=data.cred_password_count,
                domain_alert_count=data.domain_alert_count,
                suspected_domain_count=data.suspected_domain_count,
                insecure_port_count=data.insecure_port_count,
                verified_vuln_count=data.verified_vuln_count,
                suspected_vuln_count=data.suspected_vuln_count,
                suspected_vuln_addrs_count=data.suspected_vuln_addrs_count,
                threat_actor_count=data.threat_actor_count,
                dark_web_alerts_count=data.dark_web_alerts_count,
                dark_web_mentions_count=data.dark_web_mentions_count,
                dark_web_executive_alerts_count=data.dark_web_executive_alerts_count,
                dark_web_asset_alerts_count=data.dark_web_asset_alerts_count,
                pe_number_score=data.pe_number_score,
                pe_letter_grade=data.pe_letter_grade,
                cidr_count=data.cidr_count,
                port_protocol_count=data.port_protocol_count,
                software_count=data.software_count,
                foreign_ips_count=data.foreign_ips_count,
            )
    except Exception as error:
        LOGGER.error("Report API error in rss_insert: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
        ) from error


# --- query_subs(), Issue 633 (paginated) ---
@report_router.post(
    "/sub_domains_by_org",
    dependencies=[Depends(verify_api_key)],
    response_model=schemas.SubDomainPagedResult,
    tags=["Get all sub domains for a specified organization."],
)
def sub_domains_by_org(
    data: schemas.SubDomainPagedInput, tokens: str = Depends(verify_api_key)
):
    """Return subdomains for an org (sync local port of ATC sub_domains_by_org_task)."""
    try:
        total_data = list(
            SubDomains.objects.filter(
                root_domain_uid__organizations_uid=data.org_uid
            ).values(
                "sub_domain_uid",
                "sub_domain",
                "root_domain_uid_id",
                "data_source_uid_id",
                "dns_record_uid_id",
                "status",
                "first_seen",
                "last_seen",
                "current",
                "identified",
                "root_domain_uid__root_domain",
            )
        )
        paged_data = Paginator(total_data, data.per_page)
        try:
            single_page_data = paged_data.page(data.page)
        except PageNotAnInteger:
            single_page_data = paged_data.page(1)
        except EmptyPage:
            single_page_data = paged_data.page(paged_data.num_pages)

        single_page_data = list(single_page_data)
        for row in single_page_data:
            row["sub_domain_uid"] = convert_uuid_to_string(row["sub_domain_uid"])
            row["root_domain_uid_id"] = convert_uuid_to_string(
                row["root_domain_uid_id"]
            )
            row["data_source_uid_id"] = convert_uuid_to_string(
                row["data_source_uid_id"]
            )
            row["dns_record_uid_id"] = convert_uuid_to_string(row["dns_record_uid_id"])
            row["first_seen"] = convert_date_to_string(row["first_seen"])
            row["last_seen"] = convert_date_to_string(row["last_seen"])

        return {
            "total_pages": paged_data.num_pages,
            "current_page": data.page,
            "data": single_page_data,
        }
    except ObjectDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None


# --- query_previous_period(), Issue 634 ---
@report_router.post(
    "/rss_prev_period",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    response_model=List[schemas.RSSPrevPeriod],
    tags=[
        "Get previous report period report_summary_stats data for the specified organization"
    ],
)
def rss_prev_period(
    data: schemas.RSSPrevPeriodInput, tokens: str = Depends(verify_api_key)
):
    """Call API endpoint to get previous period report_summary_stats data for the specified organization."""
    # Check for API key
    try:
        # If API key valid
        # Make query
        rss_prev_period_data = list(
            ReportSummaryStats.objects.filter(
                organizations_uid=data.org_uid, end_date=data.prev_end_date
            ).values(
                "ip_count",
                "root_count",
                "sub_count",
                "cred_password_count",
                "suspected_vuln_addrs_count",
                "suspected_vuln_count",
                "insecure_port_count",
                "threat_actor_count",
            )
        )
        return rss_prev_period_data
    except Exception as error:
        LOGGER.error("Report API error in rss_prev_period: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
        ) from error

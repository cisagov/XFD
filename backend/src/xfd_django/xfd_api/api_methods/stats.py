"""Stats methods."""
# Standard Python Libraries
from datetime import datetime
import json
import uuid

# Third-Party Libraries
from django.forms.models import model_to_dict
from django.utils.timezone import now
from fastapi import HTTPException, Request
from redis import asyncio as aioredis
from xfd_api.auth import get_stats_org_ids
from xfd_api.helpers.stats_helpers import (
    get_stats_count_from_cache,
    get_total_count,
    safe_redis_mget,
)
from xfd_api.helpers.uuid_helpers import is_valid_uuid
from xfd_mini_dl.models import (
    HostSummary,
    Organization,
    PortScanServiceSummary,
    PortScanSummary,
    VulnScanSummary,
)

from ..auth import get_org_memberships, is_global_view_admin


# GET: /stats
async def get_stats(filter_data, current_user, redis_client, request: Request):
    """Compile all stats."""

    async def safe_fetch(fetch_fn, *args, **kwargs):
        """Safely fetch stats, returning an empty list on failure."""
        try:
            return await fetch_fn(*args, **kwargs)
        except Exception as e:
            print("Error fetching stats with {}: {}".format(fetch_fn.__name__, e))
            return []

    filtered_org_ids = get_stats_org_ids(current_user, filter_data)

    # Ensure organization_ids is not empty
    if not filtered_org_ids:
        raise HTTPException(
            status_code=404,
            detail="No organizations found for the user with the specified filters.",
        )

    # Fetch
    try:
        return {
            "result": {
                "domains": {
                    "services": await safe_fetch(
                        get_user_services_count,
                        filter_data,
                        current_user,
                        redis_client,
                        filtered_org_ids=filtered_org_ids,
                    ),
                    "ports": await safe_fetch(
                        get_user_ports_count,
                        filter_data,
                        current_user,
                        redis_client,
                        filtered_org_ids=filtered_org_ids,
                    ),
                    "num_vulnerabilities": await safe_fetch(
                        get_num_vulns,
                        filter_data,
                        current_user,
                        redis_client,
                        filtered_org_ids=filtered_org_ids,
                    ),
                    "total": await safe_fetch(get_total_count, filtered_org_ids),
                },
                "vulnerabilities": {
                    "severity": await safe_fetch(
                        get_severity_stats,
                        filter_data,
                        current_user,
                        redis_client,
                        filtered_org_ids=filtered_org_ids,
                    ),
                    "latest_vulnerabilities": await safe_fetch(
                        stats_latest_vulns,
                        filter_data,
                        current_user,
                        redis_client,
                        request,
                        filtered_org_ids=filtered_org_ids,
                    ),
                    "most_common_vulnerabilities": await safe_fetch(
                        stats_most_common_vulns,
                        filter_data,
                        current_user,
                        redis_client,
                        request,
                        filtered_org_ids=filtered_org_ids,
                    ),
                    "by_org": await safe_fetch(
                        get_by_org_stats,
                        filter_data,
                        current_user,
                        redis_client,
                        filtered_org_ids=filtered_org_ids,
                    ),
                },
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred: {}".format(e)
        )


async def get_user_services_count(
    filter_data, current_user, redis_client, filtered_org_ids=None
):
    """Retrieve services from Elasticache filtered by user."""
    try:
        if not filtered_org_ids:
            filtered_org_ids = get_stats_org_ids(current_user, filter_data)

            # Ensure organization_ids is not empty
            if not filtered_org_ids:
                raise HTTPException(
                    status_code=404,
                    detail="No organizations found for the user with the specified filters.",
                )

        services_data = await get_stats_count_from_cache(
            redis_client, "services_stats", filtered_org_ids
        )

        if not services_data:
            raise HTTPException(
                status_code=404,
                detail="No service data found for the user's organizations in cache.",
            )

        return services_data

    except aioredis.RedisError as redis_error:
        raise HTTPException(
            status_code=500, detail="Redis error: {}".format(redis_error)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred: {}".format(e)
        )


async def get_user_ports_count(
    filter_data, current_user, redis_client, filtered_org_ids=None
):
    """Retrieve ports from Elasticache filtered by user."""
    try:
        if not filtered_org_ids:
            filtered_org_ids = get_stats_org_ids(current_user, filter_data)

            # Ensure organization_ids is not empty
            if not filtered_org_ids:
                raise HTTPException(
                    status_code=404,
                    detail="No organizations found for the user with the specified filters.",
                )

        ports_data = await get_stats_count_from_cache(
            redis_client, "ports_stats", filtered_org_ids
        )

        if not ports_data:
            raise HTTPException(
                status_code=404,
                detail="No port data found for the user's organizations in cache.",
            )

        return ports_data

    except aioredis.RedisError as redis_error:
        raise HTTPException(
            status_code=500, detail="Redis error: {}".format(redis_error)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred: {}".format(e)
        )


async def get_num_vulns(filter_data, current_user, redis_client, filtered_org_ids=None):
    """Retrieve ports from Elasticache filtered by user."""
    try:
        if not filtered_org_ids:
            filtered_org_ids = get_stats_org_ids(current_user, filter_data)

            # Ensure organization_ids is not empty
            if not filtered_org_ids:
                raise HTTPException(
                    status_code=404,
                    detail="No organizations found for the user with the specified filters.",
                )

        num_vulns_data = await get_stats_count_from_cache(
            redis_client, "vulnerabilities_stats", filtered_org_ids
        )

        if not num_vulns_data:
            raise HTTPException(
                status_code=404,
                detail="No port data found for the user's organizations in cache.",
            )

        return num_vulns_data

    except aioredis.RedisError as redis_error:
        raise HTTPException(
            status_code=500, detail="Redis error: {}".format(redis_error)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred: {}".format(e)
        )


async def get_severity_stats(
    filter_data, current_user, redis_client, filtered_org_ids=None
):
    """Retrieve ports from Elasticache filtered by user."""
    try:
        if not filtered_org_ids:
            filtered_org_ids = get_stats_org_ids(current_user, filter_data)

            # Ensure organization_ids is not empty
            if not filtered_org_ids:
                raise HTTPException(
                    status_code=404,
                    detail="No organizations found for the user with the specified filters.",
                )

        severity_data = await get_stats_count_from_cache(
            redis_client, "severity_stats", filtered_org_ids
        )

        if not severity_data:
            raise HTTPException(
                status_code=404,
                detail="No severity data found for the user's organizations in cache.",
            )

        return severity_data

    except aioredis.RedisError as redis_error:
        raise HTTPException(
            status_code=500, detail="Redis error: {}".format(redis_error)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred: {}".format(e)
        )


async def stats_latest_vulns(
    filter_data,
    current_user,
    redis_client,
    request: Request,
    max_results=50,
    filtered_org_ids=None,
):
    """Retrieve the latest vulnerabilities from Elasticache filtered by user."""
    try:
        if not filtered_org_ids:
            filtered_org_ids = get_stats_org_ids(current_user, filter_data)

            # Ensure organization_ids is not empty
            if not filtered_org_ids:
                raise HTTPException(
                    status_code=404,
                    detail="No organizations found for the user with the specified filters.",
                )

        # Generate all Redis keys at once
        redis_keys = [
            "latest_vulnerabilities:{}".format(org_id) for org_id in filtered_org_ids
        ]

        # Use MGET to fetch all keys in a single operation
        results = await safe_redis_mget(
            redis_client, redis_keys, request.app.state.redis_semaphore
        )

        vulnerabilities = []

        # Process the results, skip None values
        for data in results:
            if data:
                vulnerabilities.extend(json.loads(data))

        # Limit the results to the maximum specified
        vulnerabilities = sorted(vulnerabilities, key=lambda x: x["created_at"])[
            :max_results
        ]

        if not vulnerabilities:
            raise HTTPException(
                status_code=404,
                detail="No vulnerabilities found for the user's organizations in cache.",
            )

        return vulnerabilities

    except aioredis.RedisError as redis_error:
        raise HTTPException(
            status_code=500, detail="Redis error: {}".format(redis_error)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred: {}".format(e),
        )


async def stats_most_common_vulns(
    filter_data,
    current_user,
    redis_client,
    request: Request,
    max_results=10,
    filtered_org_ids=None,
):
    """Retrieve the most common vulnerabilities from Elasticache filtered by user."""
    try:
        if not filtered_org_ids:
            filtered_org_ids = get_stats_org_ids(current_user, filter_data)

            # Ensure organization_ids is not empty
            if not filtered_org_ids:
                raise HTTPException(
                    status_code=404,
                    detail="No organizations found for the user with the specified filters.",
                )

        # Generate all Redis keys at once
        redis_keys = [
            "most_common_vulnerabilities:{}".format(org_id)
            for org_id in filtered_org_ids
        ]

        # Use MGET to fetch all keys in a single operation
        results = await safe_redis_mget(
            redis_client, redis_keys, request.app.state.redis_semaphore
        )

        vulnerabilities = []

        # Process the results, skip None values
        for data in results:
            if data:
                vulnerabilities.extend(json.loads(data))

        # Limit the results to the maximum specified
        vulnerabilities = sorted(vulnerabilities, key=lambda x: x["count"])[
            :max_results
        ]

        return vulnerabilities

    except aioredis.RedisError as redis_error:
        raise HTTPException(
            status_code=500, detail="Redis error: {}".format(redis_error)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred: {}".format(e),
        )


async def get_by_org_stats(
    filter_data, current_user, redis_client, filtered_org_ids=None
):
    """Fetch the count of open vulnerabilities grouped by organization from Redis."""
    try:
        if not filtered_org_ids:
            filtered_org_ids = get_stats_org_ids(current_user, filter_data)

            # Ensure organization_ids is not empty
            if not filtered_org_ids:
                raise HTTPException(
                    status_code=404,
                    detail="No organizations found for the user with the specified filters.",
                )

        # Initialize the results list
        by_org_data = []

        # Fetch data from Redis for each organization ID
        for org_id in filtered_org_ids:
            redis_key = "by_org_stats:{}".format(org_id)
            org_stats = await redis_client.get(redis_key)
            if org_stats:
                by_org_data.append(
                    json.loads(org_stats)
                )  # Directly append the Redis data

        if not by_org_data:
            raise HTTPException(
                status_code=404,
                detail="No organization data found in cache.",
            )

        return by_org_data

    except aioredis.RedisError as redis_error:
        raise HTTPException(
            status_code=500, detail="Redis error: {}".format(redis_error)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred: {}".format(e),
        )


def get_vs_condensed_trending_data(filters, current_user):
    """Query VS summary and return in a condensed format."""
    organization_id = filters.organization_id

    if not is_valid_uuid(organization_id):
        raise HTTPException(status_code=404, detail="Invalid organization ID.")

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found.")

    if (
        not is_global_view_admin(current_user)
        and not current_user.user_type == "regionalAdmin"
    ):
        org_ids = get_org_memberships(current_user)
        if uuid.UUID(organization_id) not in org_ids:
            raise HTTPException(
                status_code=404, detail="Access denied to requested organization."
            )

    if current_user.user_type == "regionalAdmin" and current_user.region_id:
        if organization.region_id != current_user.region_id:
            raise HTTPException(
                status_code=404, detail="Access denied to requested organization."
            )

    start_date = filters.start_date
    end_date = filters.end_date
    sources = filters.sources or []
    today = datetime.today().date()

    results = {}

    def replace_none_with_empty_list(results_dict):
        for key, value in results_dict.items():
            if value is None:
                results_dict[key] = []
        return results_dict

    def fetch_and_flatten(model, prefix, exclude_fields=None):
        exclude_fields = exclude_fields or []
        qs = model.objects.filter(organization=organization)

        if not start_date and not end_date:
            latest = qs.order_by("-summary_date").first()
            summaries = [latest] if latest else []
        elif start_date and not end_date:
            summaries = qs.filter(summary_date__range=(start_date, today)).order_by(
                "summary_date"
            )
        elif not start_date and end_date:
            summaries = qs.filter(summary_date=end_date).order_by("summary_date")
        else:
            summaries = qs.filter(summary_date__range=(start_date, end_date)).order_by(
                "summary_date"
            )

        if exclude_fields:
            summaries = summaries.defer(*exclude_fields)

        for obj in summaries:
            obj_dict = model_to_dict(obj, exclude=exclude_fields)
            for field, value in obj_dict.items():
                key = f"{prefix}_{field}"
                results.setdefault(key, []).append(value)

    if "host" in sources:
        fetch_and_flatten(HostSummary, "host_summary")

    if "port" in sources:
        fetch_and_flatten(PortScanSummary, "port_scan_summary")

    if "port_service" in sources:
        fetch_and_flatten(PortScanServiceSummary, "port_scan_service_summary")

    if "vs" in sources:
        exclude = ["included_tickets"] if not filters.enhanced_data else []
        fetch_and_flatten(VulnScanSummary, "vuln_scan_summary", exclude_fields=exclude)

    return replace_none_with_empty_list(results)


def get_vs_trending_data(filters, current_user):
    """Query VS scan data based on the user filters."""
    organization_id = filters.organization_id

    if not is_valid_uuid(organization_id):
        raise HTTPException(status_code=404, detail="Invalid organization ID.")

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found.")

    if (
        not is_global_view_admin(current_user)
        and not current_user.user_type == "regionalAdmin"
    ):
        org_ids = get_org_memberships(current_user)
        if uuid.UUID(organization_id) not in org_ids:
            raise HTTPException(
                status_code=404, detail="Access denied to requested organization."
            )

    if current_user.user_type == "regionalAdmin" and current_user.region_id:
        if organization.region_id != current_user.region_id:
            raise HTTPException(
                status_code=404, detail="Access denied to requested organization."
            )

    start_date = filters.start_date
    end_date = filters.end_date
    sources = filters.sources or []
    today = datetime.today().date()

    def fetch_summaries(model, exclude_fields=None):
        exclude_fields = exclude_fields or []
        qs = model.objects.filter(organization=organization)

        if not start_date and not end_date:
            latest = qs.order_by("-summary_date").first()
            return [model_to_dict(latest, exclude=exclude_fields)] if latest else []

        if start_date and not end_date:
            qs = qs.filter(summary_date__range=(start_date, today))
        elif not start_date and end_date:
            qs = qs.filter(summary_date=end_date)
        else:
            qs = qs.filter(summary_date__range=(start_date, end_date))

        qs = qs.order_by("summary_date")  # Order ascending by date

        if exclude_fields:
            qs = qs.defer(*exclude_fields)

        return [model_to_dict(obj, exclude=exclude_fields) for obj in qs]

    host_dicts = fetch_summaries(HostSummary) if "host" in sources else None

    ports_dicts = fetch_summaries(PortScanSummary) if "port" in sources else None

    port_services_dicts = (
        fetch_summaries(PortScanServiceSummary) if "port_service" in sources else None
    )

    vuln_scan_summaries = (
        fetch_summaries(
            VulnScanSummary,
            exclude_fields=["included_tickets"] if not filters.enhanced_data else [],
        )
        if "vs" in sources
        else None
    )

    return {
        "host_summaries": host_dicts,
        "port_scan_summaries": ports_dicts,
        "port_scan_service_summaries": port_services_dicts,
        "vuln_scan_summaries": vuln_scan_summaries,
    }


SUMMARY_CONFIG = {
    "host": {
        "model": HostSummary,
        "fields": [
            "host_done_count",
            "host_waiting_count",
            "host_running_count",
            "host_ready_count",
            "up_host_count",
            "down_host_count",
            "scanned_asset_count",
        ],
    },
    "port": {
        "model": PortScanSummary,
        "fields": [
            "open_port_count",
            "risky_port_count",
            "nmi_service_count",
            "unique_ip_count",
            "unique_service_count",
        ],
        "complex_fields": ["risky_service_group_counts"],
    },
    "vs": {
        "model": VulnScanSummary,
        "fields": [
            "assets_owned_count",
            "false_positive_count",
            "vulnerable_host_count",
            "unique_service_count",
            "unique_low_severity_count",
            "unique_medium_severity_count",
            "unique_high_severity_count",
            "unique_critical_severity_count",
            "risky_services_count",
            "unsupported_software_count",
            "unique_os_count",
            "low_severity_count",
            "medium_severity_count",
            "high_severity_count",
            "critical_severity_count",
            "critical_max_age",
            "high_max_age",
            "low_kev_count",
            "medium_kev_count",
            "high_kev_count",
            "critical_kev_count",
            "kev_max_age",
            "one_to_five_vulns_count",
            "six_to_nine_vulns_count",
            "ten_plus_vulns_count",
        ],
        "complex_fields": [
            "included_tickets",
            "top_5_occurring_cves",
            "top_5_occurring_kevs",
            "top_5_risky_hosts",
        ],
    },
}


def get_summary_dict(summary, numeric_fields, complex_fields=None):
    """Convert the summary to a returnable dictionary format."""
    if not summary:
        return None
    data = {field: getattr(summary, field, None) for field in numeric_fields}

    if complex_fields:
        for field in complex_fields:
            data[field] = getattr(summary, field, None)

    # Always include summary_date, start_date, and end_date if present
    for date_field in ["summary_date", "start_date", "end_date"]:
        if hasattr(summary, date_field):
            data[date_field] = getattr(summary, date_field)

    return data


def compute_deltas(
    base_summary, compare_summary, fields, base_missing=False, compare_missing=False
):
    """Calculate the differences between the two summaries metric fields."""
    delta = {}
    for field in fields:
        base_val = getattr(base_summary, field, 0) if base_summary else 0
        compare_val = getattr(compare_summary, field, 0) if compare_summary else 0

        base_val = base_val or 0
        compare_val = compare_val or 0
        count_change = compare_val - base_val

        if base_missing:
            percent_change = 100.0 if compare_val > 0 else 0.0
            note = "Base summary not found."
        elif compare_missing:
            percent_change = None
            note = "Compare summary not found."
        elif base_val == 0 and compare_val == 0:
            percent_change = 0.0
            note = None
        elif base_val == 0:
            percent_change = 100.0
            note = "Base value was 0; assumed 100% increase."
        else:
            percent_change = (count_change / base_val) * 100
            note = None

        delta[field] = {
            "count_change": count_change,
            "percent_change": round(percent_change, 2)
            if percent_change is not None
            else None,
        }

        if note:
            delta[field]["note"] = note

    return delta


def compare_risky_service_groups(base_dict, compare_dict):
    """Compare risky service group counts between two summaries."""
    base_dict = base_dict or {}
    compare_dict = compare_dict or {}

    all_keys = set(base_dict.keys()) | set(compare_dict.keys())
    result = {}

    for key in all_keys:
        base_val = base_dict.get(key, 0)
        compare_val = compare_dict.get(key, 0)
        count_change = compare_val - base_val

        if base_val == 0 and compare_val > 0:
            percent_change = 100.0
            note = "Base value was 0; assumed 100% increase."
        elif base_val == 0 and compare_val == 0:
            percent_change = 0.0
            note = None
        else:
            percent_change = (count_change / base_val) * 100
            note = None

        result[key] = {
            "base": base_val,
            "compare": compare_val,
            "count_change": count_change,
            "percent_change": round(percent_change, 2),
        }

        if note:
            result[key]["note"] = note

    return result


def compare_included_tickets(base_tickets, compare_tickets):
    """Identify open and closed tickets between the two summaries."""
    base_tickets = base_tickets or {}
    compare_tickets = compare_tickets or {}

    base_ids = set(base_tickets.keys())
    compare_ids = set(compare_tickets.keys())

    new_ids = compare_ids - base_ids
    closed_ids = base_ids - compare_ids

    severity_levels = ["none", "low", "medium", "high", "critical"]

    def init_counts():
        """Inititialize severity count dictionaries."""
        return {sev: 0 for sev in severity_levels}

    def count_severities(ticket_dict):
        """Count severities in the ticket dictionaries."""
        counts = init_counts()
        for ticket in ticket_dict.values():
            severity = ticket.get("severity", "none").lower()
            if severity in counts:
                counts[severity] += 1
        return counts

    def compute_counts(ticket_ids, ticket_dict, reference_counts):
        """Calculate the counts of the ticket severities."""
        by_severity = init_counts()
        kev_by_severity = init_counts()
        kev_count = 0

        for tid in ticket_ids:
            ticket = ticket_dict.get(tid, {})
            severity = ticket.get("severity", "none").lower()
            is_kev = ticket.get("is_kev", False)

            if severity in by_severity:
                by_severity[severity] += 1
                if is_kev:
                    kev_by_severity[severity] += 1
            if is_kev:
                kev_count += 1

        total = len(ticket_ids)

        by_severity_percent = {}
        for sev in severity_levels:
            ref_total = reference_counts.get(sev, 0)
            by_severity_percent[sev] = (
                round((by_severity[sev] / ref_total) * 100, 2) if ref_total else 0.0
            )

        return {
            "total_count": total,
            "by_severity": by_severity,
            "by_severity_percent": by_severity_percent,
            "kev_count": kev_count,
            "kev_by_severity": kev_by_severity,
        }

    # Base severity counts for denominator reference
    base_severity_counts = count_severities(base_tickets)
    compare_severity_counts = count_severities(compare_tickets)

    new_data = compute_counts(new_ids, compare_tickets, compare_severity_counts)
    closed_data = compute_counts(closed_ids, base_tickets, base_severity_counts)

    total_compare = len(compare_ids)
    total_base = len(base_ids)

    new_data["total_percent"] = (
        round((new_data["total_count"] / total_compare) * 100, 2)
        if total_compare
        else 0.0
    )
    closed_data["total_percent"] = (
        round((closed_data["total_count"] / total_base) * 100, 2) if total_base else 0.0
    )

    return {"new": new_data, "closed": closed_data, "note": None}


def get_summary_comparison(
    summary_type, organization, base_date, compare_date, enhanced_data=True
):
    """Return the Summary comparison dictionary."""
    config = SUMMARY_CONFIG[summary_type]
    model = config["model"]
    fields = config["fields"]

    base_summary = None
    compare_summary = None
    base_missing = False
    compare_missing = False

    try:
        base_summary = model.objects.get(
            organization=organization, summary_date=base_date
        )
    except model.DoesNotExist:
        base_missing = True

    if compare_date:
        try:
            compare_summary = model.objects.get(
                organization=organization, summary_date=compare_date
            )
        except model.DoesNotExist:
            compare_missing = True
    else:
        compare_summary = (
            model.objects.filter(
                organization=organization, summary_date__lte=now().date()
            )
            .order_by("-summary_date")
            .first()
        )
        if not compare_summary:
            compare_missing = True

    if base_missing and compare_missing:
        return None

    complex_fields = config.get("complex_fields", []) if enhanced_data else []

    result = {
        "base_summary": get_summary_dict(base_summary, fields, complex_fields)
        if base_summary
        else None,
        "compare_summary": get_summary_dict(compare_summary, fields, complex_fields)
        if compare_summary
        else None,
        "delta": compute_deltas(
            base_summary, compare_summary, fields, base_missing, compare_missing
        ),
    }

    # Add included_tickets detailed comparison ONLY for vuln summary
    if summary_type == "vs":
        included_tickets_base = (
            getattr(base_summary, "included_tickets", None) if base_summary else {}
        )
        included_tickets_compare = (
            getattr(compare_summary, "included_tickets", None)
            if compare_summary
            else {}
        )

        result["included_tickets_comparison"] = compare_included_tickets(
            included_tickets_base, included_tickets_compare
        )

    if summary_type == "port":
        base_group_counts = (
            getattr(base_summary, "risky_service_group_counts", None)
            if base_summary
            else {}
        )
        compare_group_counts = (
            getattr(compare_summary, "risky_service_group_counts", None)
            if compare_summary
            else {}
        )

        result["risky_service_group_comparison"] = compare_risky_service_groups(
            base_group_counts, compare_group_counts
        )

    return result


def get_stats_comparison_data(filters, current_user):
    """Calculate a comparison of two requested comparisons."""
    organization_id = filters.organization_id

    if not is_valid_uuid(organization_id):
        raise HTTPException(status_code=404, detail="Invalid organization ID.")

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found.")

    if (
        not is_global_view_admin(current_user)
        and not current_user.user_type == "regionalAdmin"
    ):
        org_ids = get_org_memberships(current_user)
        if uuid.UUID(organization_id) not in org_ids:
            raise HTTPException(
                status_code=404, detail="Access denied to requested organization."
            )  # User has no accessible organizations

    # Regional Admins can only view vulnerabilities in their region
    if current_user.user_type == "regionalAdmin" and current_user.region_id:
        if organization.region_id != current_user.region_id:
            raise HTTPException(
                status_code=404, detail="Access denied to requested organization."
            )

    base_date = filters.base_date
    compare_date = filters.compare_date
    sources = filters.sources
    enhanced_data = filters.enhanced_data if hasattr(filters, "enhanced_data") else True

    results = {}

    for source in sources:
        if source not in SUMMARY_CONFIG:
            continue

        summary_data = get_summary_comparison(
            source, organization, base_date, compare_date, enhanced_data=enhanced_data
        )

        if summary_data is not None:
            results[f"{source}_scans"] = summary_data

    return results

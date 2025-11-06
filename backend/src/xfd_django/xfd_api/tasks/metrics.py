"""Functions for collecting and storing app metrics."""

# Standard Python Libraries
from datetime import datetime, time, timedelta
from datetime import timezone as dt_timezone
import logging
import os

# Third-Party Libraries
import django

# Django Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    DateField,
    DurationField,
    Exists,
    ExpressionWrapper,
    FloatField,
    Func,
    IntegerField,
    OuterRef,
    Q,
    Value,
    When,
)
from django.db.models.functions import Cast, TruncDate
from django.utils import timezone as dj_timezone
from xfd_mini_dl.models import CustomerMetrics, Organization, Role, User

LOGGER = logging.getLogger(__name__)

EXTERNAL_ORG_BLOCKLIST = ("DHS", "NCATS")
REGIONS = (None,) + tuple(range(1, 11))
VALID_REGION_STRS = tuple(map(str, range(1, 11)))


def _region_int_from_char(field_name):
    """
    Convert CharField region_id -> Integer (1..10) or NULL.

    Treat empty string as NULL. Non-numeric -> NULL. Numeric outside 1..10 -> NULL.
    """
    return Case(
        When(
            **{field_name + "__in": VALID_REGION_STRS},
            then=Cast(field_name, IntegerField())
        ),
        default=Value(None),
        output_field=IntegerField(),
    )


def _yesterday_utc():
    now_utc = dj_timezone.now().astimezone(dt_timezone.utc)
    target_date = now_utc.date() - timedelta(days=1)
    start_dt = datetime.combine(target_date, time.min, tzinfo=dt_timezone.utc)
    end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt, target_date


def _collect_active_orgs_without_users():
    region_expr = _region_int_from_char("region_id")
    org_qs = (
        Organization.objects.filter(retired=False)
        .annotate(has_role=Exists(Role.objects.filter(organization_id=OuterRef("pk"))))
        .filter(has_role=False)
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in org_qs}


def _collect_external_active_orgs():
    region_expr = _region_int_from_char("region_id")
    qs = (
        Organization.objects.filter(retired=False)
        .exclude(Q(acronym__in=EXTERNAL_ORG_BLOCKLIST) | Q(acronym__startswith="DHS_"))
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in qs}


def _collect_external_retired_orgs():
    region_expr = _region_int_from_char("region_id")
    qs = (
        Organization.objects.filter(retired=True)
        .exclude(Q(acronym__in=EXTERNAL_ORG_BLOCKLIST) | Q(acronym__startswith="DHS_"))
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in qs}


def _collect_external_users():
    region_expr = _region_int_from_char("region_id")
    qs = (
        User.objects.exclude(email__icontains="dhs.gov")
        .exclude(user_type__in=("globalAdmin", "globalView"))
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in qs}


def _collect_cisa_users():
    region_expr = _region_int_from_char("region_id")
    qs = (
        User.objects.filter(email__iendswith="cisa.dhs.gov")
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in qs}


def _collect_users_without_org():
    region_expr = _region_int_from_char("region_id")
    qs = (
        User.objects.annotate(
            has_role=Exists(Role.objects.filter(user_id=OuterRef("pk")))
        )
        .filter(has_role=False)
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in qs}


def _collect_users_created(window_start, window_end):
    region_expr = _region_int_from_char("region_id")
    qs = (
        User.objects.filter(created_at__gte=window_start, created_at__lt=window_end)
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in qs}


def _collect_users_approved(window_start, window_end):
    region_expr = _region_int_from_char("region_id")
    qs = (
        User.objects.filter(
            date_approved__gte=window_start, date_approved__lt=window_end
        )
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in qs}


def _collect_active_users_30d(end_dt):
    """
    Users with last_logged_in >= (end_dt - 30 days).

    end_dt is the midnight after target_date (exclusive upper bound of the snapshot day).
    """
    threshold = end_dt - timedelta(days=30)
    region_expr = _region_int_from_char("region_id")
    qs = (
        User.objects.filter(last_logged_in__gte=threshold)
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(total=Count("id"))
    )
    return {row["region_num"]: row["total"] for row in qs}


def _collect_mean_wait_time_for_pending_users(end_dt):
    """
    Average wait time (in days, float) for users currently awaiting approval.

    Computes whole-day waits per user as:
        whole_days = end_dt.date() - created_at::date
    Returns dict[region] -> {'pending_count': int, 'avg_wait': float}
    """
    region_expr = _region_int_from_char("region_id")

    end_date_val = Value(end_dt.date(), output_field=DateField())

    delta = ExpressionWrapper(
        end_date_val - TruncDate("created_at"),
        output_field=DurationField(),
    )

    # Convert interval -> seconds using Postgres EXTRACT(EPOCH FROM ...)
    seconds = Func(
        delta,
        function="EXTRACT",
        template="EXTRACT(EPOCH FROM %(expressions)s)",
        output_field=FloatField(),
    )

    days = ExpressionWrapper(seconds / Value(86400.0), output_field=FloatField())

    qs = (
        User.objects.filter(invite_pending=True, created_at__lte=end_dt)
        .annotate(region_num=region_expr)
        .values("region_num")
        .annotate(
            pending_count=Count("id"),
            avg_wait=Avg(days),  # float days
        )
    )

    return {
        row["region_num"]: {
            "pending_count": row["pending_count"],
            "avg_wait": row["avg_wait"],
        }
        for row in qs
    }


@transaction.atomic
def collect_and_upsert_customer_metrics(event, context):
    """
    Compute metrics for yesterday (UTC) and upsert into customer_metrics.

    Creates one row per region 1..10, including a NULL region if it exists in data.
    """
    window_start, window_end, target_date = _yesterday_utc()

    LOGGER.info("Collecting customer metrics for %s (UTC).", target_date.isoformat())

    # Run all aggregations
    active_orgs_without_users = _collect_active_orgs_without_users()
    external_active_orgs = _collect_external_active_orgs()
    external_retired_orgs = _collect_external_retired_orgs()
    external_users = _collect_external_users()
    cisa_users = _collect_cisa_users()
    users_without_org = _collect_users_without_org()
    users_created = _collect_users_created(window_start, window_end)
    users_approved = _collect_users_approved(window_start, window_end)
    active_users = _collect_active_users_30d(window_end)
    pending_stats = _collect_mean_wait_time_for_pending_users(window_end)

    created_count = 0
    updated_count = 0

    for region in REGIONS:
        pend = pending_stats.get(region, {})
        defaults = {
            "active_orgs_without_users": active_orgs_without_users.get(region, 0),
            "external_active_orgs": external_active_orgs.get(region, 0),
            "external_retired_orgs": external_retired_orgs.get(region, 0),
            "external_users": external_users.get(region, 0),
            "cisa_users": cisa_users.get(region, 0),
            "users_without_org": users_without_org.get(region, 0),
            "users_created": users_created.get(region, 0),
            "users_approved": users_approved.get(region, 0),
            "users_invite_pending": pend.get("pending_count", 0),
            "mean_approval_time": pend.get("avg_wait"),
            "active_users": active_users.get(region, 0),
        }

        obj, created = CustomerMetrics.objects.update_or_create(
            date=target_date,
            region=region,
            defaults=defaults,
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    LOGGER.info(
        "Customer metrics upsert complete for %s. Created=%d, Updated=%d.",
        target_date.isoformat(),
        created_count,
        updated_count,
    )
    return {"date": target_date, "created": created_count, "updated": updated_count}

"""Elasticache tasks."""
# Standard Python Libraries
import json
import os

# Third-Party Libraries
import django
from django.conf import settings
from django.db.models import CharField, Count, F, Value
from django.db.models.functions import Concat
import redis

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

# Initialize Django
django.setup()

# Third-Party Libraries
from xfd_api.helpers.stats_helpers import populate_stats_cache
from xfd_mini_dl.models import Service, Vulnerability


def populate_services_cache(event, context):
    """Populate services cache."""
    return populate_stats_cache(
        model=Service,
        group_by_field="domain__organization_id",
        redis_key_prefix="services_stats",
        annotate_field="service",
        filters={
            "service__isnull": False,
            "domain__isnull": False,
            "domain__organization__isnull": False,
        },
    )


def populate_ports_cache(event, context):
    """Populate ports cache."""
    return populate_stats_cache(
        model=Service,
        group_by_field="domain__organization_id",
        redis_key_prefix="ports_stats",
        annotate_field="port",
        filters={
            "port__isnull": False,
            "domain__isnull": False,
            "domain__organization__isnull": False,
        },
    )


def populate_num_vulns_cache(event, context):
    """Populate num vulns cache."""
    return populate_stats_cache(
        model=Vulnerability,
        group_by_field="domain__organization_id",
        redis_key_prefix="vulnerabilities_stats",
        annotate_field="severity",
        custom_id=Concat(
            F("domain__name"),
            Value("|"),
            F("severity"),
            output_field=CharField(),
        ),
        filters={
            "state": "open",  # Include only open vulnerabilities
            "domain__isnull": False,
            "domain__organization__isnull": False,
        },
    )


def populate_latest_vulns_cache(event, context):
    """Populate Redis with the latest vulnerabilities for each organization."""
    try:
        # Connect to Redis
        redis_client = redis.StrictRedis(
            host=settings.ELASTICACHE_ENDPOINT,
            port=6379,
            db=0,
            decode_responses=True,
        )

        # Fetch and organize the latest vulnerabilities
        vulnerabilities = (
            Vulnerability.objects.filter(
                state="open",  # Only open vulnerabilities
                domain__isnull=False,
                domain__organization__isnull=False,
            )
            .select_related("domain", "domain__organization")
            .order_by("created_at")
        )

        # Organize vulnerabilities by organization
        vulnerabilities_by_org = {}
        for vuln in vulnerabilities:
            org_id = str(vuln.domain.organization.id)  # Organization ID
            vuln_data = {
                "created_at": vuln.created_at.isoformat(),
                "title": vuln.title,
                "description": vuln.description,
                "severity": vuln.severity,
            }
            if org_id not in vulnerabilities_by_org:
                vulnerabilities_by_org[org_id] = []
            vulnerabilities_by_org[org_id].append(vuln_data)

        # Store each organization's vulnerabilities in Redis
        for org_id, data in vulnerabilities_by_org.items():
            redis_key = "latest_vulnerabilities:{}".format(org_id)
            redis_client.set(redis_key, json.dumps(data))

        return {
            "status": "success",
            "message": "Cache populated with the latest vulnerabilities successfully.",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "An unexpected error occurred while populating the cache: {}".format(
                e
            ),
        }


def populate_most_common_vulns_cache(event, context):
    """Populate Redis with the most common vulnerabilities grouped by title, description, and severity."""
    try:
        # Connect to Redis
        redis_client = redis.StrictRedis(
            host=settings.ELASTICACHE_ENDPOINT,
            port=6379,
            db=0,
            decode_responses=True,
        )

        # Fetch and aggregate vulnerabilities
        vulnerabilities = (
            Vulnerability.objects.filter(
                state="open",  # Only open vulnerabilities
                domain__isnull=False,
                domain__organization__isnull=False,
            )
            .values("title", "description", "severity", "domain__organization_id")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Organize vulnerabilities by organization
        vulnerabilities_by_org = {}
        for vuln in vulnerabilities:
            org_id = str(vuln["domain__organization_id"])
            vuln_data = {
                "title": vuln["title"],
                "description": vuln["description"],
                "severity": vuln["severity"],
                "count": vuln["count"],
            }
            if org_id not in vulnerabilities_by_org:
                vulnerabilities_by_org[org_id] = []
            vulnerabilities_by_org[org_id].append(vuln_data)

        # Store each organization's vulnerabilities in Redis
        for org_id, data in vulnerabilities_by_org.items():
            redis_key = "most_common_vulnerabilities:{}".format(org_id)
            redis_client.set(redis_key, json.dumps(data))

        return {
            "status": "success",
            "message": "Cache populated with the most common vulnerabilities successfully.",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "An unexpected error occurred while populating the cache: {}".format(
                e
            ),
        }


def populate_severity_cache(event, context):
    """Populate Redis with severity statistics for vulnerabilities."""
    return populate_stats_cache(
        model=Vulnerability,
        group_by_field="domain__organization_id",  # Group by severity
        redis_key_prefix="severity_stats",
        annotate_field="severity",  # Default field for counting occurrences
        filters={
            "state": "open",  # Include only open vulnerabilities
            "domain__isnull": False,
            "domain__organization__isnull": False,
        },
    )


def populate_by_org_cache(event, context):
    """
    Populate Redis with the count of open vulnerabilities grouped by organization.

    Each organization's data is stored under its own Redis key.
    """
    try:
        # Connect to Redis
        redis_client = redis.StrictRedis(
            host=settings.ELASTICACHE_ENDPOINT,
            port=6379,
            db=0,
            decode_responses=True,
        )

        # Fetch and aggregate vulnerabilities grouped by organization
        vulnerabilities = (
            Vulnerability.objects.filter(
                state="open",
                domain__isnull=False,
                domain__organization__isnull=False,
            )
            .values("domain__organization__id", "domain__organization__name")
            .annotate(value=Count("id"))
            .order_by("-value")
        )

        # Organize data and store in Redis
        for vuln in vulnerabilities:
            org_id = str(vuln["domain__organization__id"])
            org_name = vuln["domain__organization__name"]
            redis_key = "by_org_stats:{}".format(org_id)
            data = {
                "id": org_name,  # Organization name as "id"
                "orgId": org_id,  # Organization ID
                "value": vuln["value"],  # Count of vulnerabilities
                "label": org_name,  # Organization name as "label"
            }
            redis_client.set(redis_key, json.dumps(data))

        return {
            "status": "success",
            "message": "Cache populated for byOrg successfully.",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "An unexpected error occurred while populating the cache: {}".format(
                e
            ),
        }

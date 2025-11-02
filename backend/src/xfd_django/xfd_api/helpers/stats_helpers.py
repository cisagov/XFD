"""Stats helper methods."""
# Standard Python Libraries
from collections import defaultdict
import json
import logging

# Third-Party Libraries
from django.conf import settings
from django.db.models import Count
import redis
from xfd_mini_dl.models import Domain

# Configure logging
LOGGER = logging.getLogger(__name__)


async def safe_redis_mget(redis_client, redis_keys, redis_semaphore):
    """Safely perform Redis MGET with concurrency limit."""
    async with redis_semaphore:
        return await redis_client.mget(*redis_keys)


async def get_stats_count_from_cache(redis_client, redis_key_prefix, filtered_org_ids):
    """Fetch and aggregate stats from Redis."""
    aggregated_stats = defaultdict(int)

    # Fetch data from Redis by organization ID
    redis_keys = [
        "{}:{}".format(redis_key_prefix, org_id) for org_id in filtered_org_ids
    ]
    redis_responses = await redis_client.mget(*redis_keys)

    for response in redis_responses:
        if isinstance(response, Exception):
            continue
        if response:
            stats_list = json.loads(response)
            for stat in stats_list:
                stat_id = stat["id"]
                # Handle the case where the stat ID is None.
                # None/Null values come from Redis as "0" and cannot be incremented.
                if stat_id in [None, "None"]:
                    stat_id = "None"
                    if stat["value"] == 0:
                        stat["value"] = 1
                aggregated_stats[stat_id] += stat["value"]

    return [
        {"id": stat_id, "value": value, "label": stat_id}
        for stat_id, value in aggregated_stats.items()
    ]


def populate_stats_cache(
    model,
    group_by_field,
    redis_key_prefix,
    annotate_field="id",
    custom_id=None,
    filters=None,
):
    """Populate Redis stats with custom ID fields."""
    try:
        # Connect to Redis
        redis_client = redis.StrictRedis(
            host=settings.ELASTICACHE_ENDPOINT,
            port=6379,
            db=0,
            decode_responses=True,
        )

        # Build queryset with optional filters
        queryset = model.objects.all()
        if filters:
            queryset = queryset.filter(**filters)

        # Apply custom ID annotation if provided
        if custom_id:
            queryset = queryset.annotate(custom_id=custom_id)

        # Aggregate and group data
        stats = (
            queryset.values(
                group_by_field, "custom_id" if custom_id else annotate_field
            )
            .annotate(value=Count(annotate_field))
            .order_by(group_by_field, "-value")
        )

        # Organize stats by grouping field
        stats_by_group = {}
        for item in stats:
            group_id = str(item[group_by_field])
            key = str(item["custom_id"]) if custom_id else str(item[annotate_field])
            count = item["value"]
            if group_id not in stats_by_group:
                stats_by_group[group_id] = []
            stats_by_group[group_id].append({"id": key, "value": count})

        # Store stats in Redis
        for group_id, data in stats_by_group.items():
            redis_key = "{}:{}".format(redis_key_prefix, group_id)
            redis_client.set(redis_key, json.dumps(data))

        return {
            "status": "success",
            "message": "Cache populated successfully for {}.".format(redis_key_prefix),
        }

    except Exception as e:
        LOGGER.error("Error populating stats cache: %s", e)
        return {
            "status": "error",
            "message": "An unexpected error occurred: {}".format(e),
        }


async def get_total_count(filtered_org_ids):
    """Retrieve the total count of domains associated with the filtered organizations."""
    try:
        # Query the database for the total count of domains in the filtered organizations
        total_count = Domain.objects.filter(organization__in=filtered_org_ids).count()
        return total_count

    except Exception as e:
        LOGGER.error("Unexpected error fetching total count: %s", e)
        return 0

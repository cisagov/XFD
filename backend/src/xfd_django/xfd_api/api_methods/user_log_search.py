"""User log search."""

# Standard Python Libraries
from datetime import datetime
import json
import re
import traceback
from typing import Any, Dict

# Third-Party Libraries
from django.db.models import Q
from fastapi import HTTPException
from xfd_mini_dl.models import Log

from ..auth import is_global_view_admin


def parse_query_string(query):
    """
    Parse a query string into a dictionary for JSONField filtering.

    Example Input: "user.id:12345 user.name:John Doe"
    Output: {"user__id": "12345", "user__name": "John Doe"}
    """
    result = {}
    # Match key:value pairs, allowing values with spaces
    pattern = re.compile(r'(\w+(\.\w+)*)\s*:\s*("[^"]+"|\'[^\']+\'|\S+)')
    matches = pattern.findall(query)

    for match in matches:
        key, _, value = match
        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        # Replace dots with double underscores for Django ORM
        orm_key = key.replace(".", "__")
        result[orm_key] = value
    return result


def generate_date_condition(filter_obj: Dict[str, Any]) -> Q:
    """Generate date condition."""
    operator = filter_obj.get("operator")
    value = filter_obj.get("value", "")

    try:
        date_obj = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("Invalid date format. Use ISO format.")

    if operator == "is":
        return Q(created_at__exact=date_obj)
    elif operator == "not":
        return ~Q(created_at__exact=date_obj)
    elif operator == "after":
        return Q(created_at__gt=date_obj)
    elif operator == "on_or_after":
        return Q(created_at__gte=date_obj)
    elif operator == "before":
        return Q(created_at__lt=date_obj)
    elif operator == "on_or_before":
        return Q(created_at__lte=date_obj)
    elif operator == "empty":
        return Q(created_at__isnull=True)
    elif operator == "not_empty":
        return Q(created_at__isnull=False)
    else:
        raise ValueError("Invalid date operator.")


def generate_filter_qs(search: Dict[str, Any]) -> Q:
    """Generate a Q object based on the search filters."""
    q = Q()
    if "eventType" in search and search["event_type"]:
        event_filter = search["event_type"]
        q &= Q(event_type__icontains=event_filter["value"])

    if "result" in search and search["result"]:
        result_filter = search["result"]
        q &= Q(result__icontains=result_filter["value"])

    if "timestamp" in search and search["timestamp"]:
        timestamp_filter = search["timestamp"]
        # Use the correct field name "createdAt" instead of "created_at"
        q &= generate_date_condition(timestamp_filter)

    if "payload" in search and search["payload"]:
        payload_filters = parse_query_string(search["payload"])
        for key, value in payload_filters.items():
            # This assumes your keys in the payload match your search keys.
            q &= Q(**{f"payload__{key}": value})

    return q


# POST: /log/search
def search_logs(search_data, current_user):
    """Search logs based on filters."""
    try:
        # Check if the user is a GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Convert Pydantic model to dict and remove None values
        search_dict = search_data.dict(exclude_unset=True)

        # Generate Q object for filters
        q_object = generate_filter_qs(search_dict)

        # As Django ORM is synchronous, use sync_to_async
        logs_qs = Log.objects.filter(q_object)

        # Get count
        count = logs_qs.count()

        # Serialize logs
        logs_serialized = []
        for log in logs_qs:
            try:
                payload_dict = json.loads(log.payload)
            except (ValueError, TypeError):
                # If somehow it's not valid JSON, just keep it as a string
                payload_dict = log.payload

            logs_serialized.append(
                {
                    "id": str(log.id),
                    "event_type": log.event_type,
                    "result": log.result,
                    "payload": payload_dict,
                    "created_at": log.created_at.isoformat(),
                }
            )

        return logs_serialized, count

    except ValueError as ve:
        raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

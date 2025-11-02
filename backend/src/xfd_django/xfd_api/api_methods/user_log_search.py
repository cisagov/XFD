"""User log search."""

# Standard Python Libraries
from datetime import timedelta
import json
import logging
import re
from typing import Any, Dict, Optional

# Third-Party Libraries
from dateutil.parser import parse  # type: ignore
from django.db.models import Q
from django.utils import timezone
from fastapi import HTTPException, status
from xfd_mini_dl.models import Log

from ..auth import is_global_view_admin
from ..schema_models.user_log_schema import LogSearch, LogSearchFilter

# Configure logging
LOGGER = logging.getLogger(__name__)


def parse_query_string(query):
    """Convert a query string into a dictionary for filtering."""
    pattern = re.compile(r'(\w+(\.\w+)*)\s*:\s*("[^"]+"|\'[^\']+\'|\S+)')
    matches = pattern.findall(query)
    result = {}
    for match in matches:
        key, _, value = match
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        orm_key = key.replace(".", "__")
        result[orm_key] = value
    return result


def safe_get(d, *keys):
    """Safely get a nested value from a dictionary, returning an empty dict if any key is missing."""
    for key in keys:
        if not isinstance(d, dict):
            return {}
        d = d.get(key, {})
    return d


def _get_payload(log):
    """Get the payload from a log, decoding from JSON if necessary."""
    payload = log.get("payload", {})
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return {}
    return payload if isinstance(payload, dict) else {}


def _find_first_value(sources, key, default=""):
    """Iterate through a list of source dicts and return the first value found for a key."""
    for source in sources:
        if source and source.get(key):
            return str(source.get(key, default))
    return default


ACTED_ON_USER_PATHS = [
    ("user",),
    ("removal_result", "role_deleted", "user"),
    ("removal_result", "user_deleted"),
    ("deny_result", "denied_user"),
    ("user_to_approve",),
    ("approval_results", "role_deleted", "user"),
]

PERFORMED_BY_USER_PATHS = [
    ("user_performed_assignment",),
    ("user_performed_removal",),
    ("user_performed_approval",),
    ("user_performed_invite",),
]

FIELD_HANDLERS = {
    "event_type": lambda log, payload: log.get("event_type", ""),
    "result": lambda log, payload: log.get("result", ""),
    "payload.role": lambda log, payload: payload.get("role", ""),
    "acted_on_user_name": {"source_paths": ACTED_ON_USER_PATHS, "key": "full_name"},
    "payload.user.full_name": {"source_paths": ACTED_ON_USER_PATHS, "key": "full_name"},
    "acted_on_user_email": {"source_paths": ACTED_ON_USER_PATHS, "key": "email"},
    "payload.user.email": {"source_paths": ACTED_ON_USER_PATHS, "key": "email"},
    "payload.user_performed_assignment.full_name": {
        "source_paths": PERFORMED_BY_USER_PATHS,
        "key": "full_name",
    },
    "payload.user_performed_assignment.email": {
        "source_paths": PERFORMED_BY_USER_PATHS,
        "key": "email",
    },
    "payload.user_performed_assignment.region_id": {
        "source_paths": PERFORMED_BY_USER_PATHS,
        "key": "region_id",
    },
    "payload.organization.name": {
        "source_paths": [("organization",), ("from_organization",)],
        "key": "name",
    },
    "payload.state": {
        "source_paths": [
            (),
            ("user_performed_assignment",),
            ("user_performed_removal",),
            ("user_performed_approval",),
            ("user_performed_invite",),
            ("user",),
        ],
        "key": "state",
    },
    "payload.user.user_type": {
        "source_paths": [("user",), ("user_to_approve",)],
        "key": "user_type",
    },
    "payload.user_to_approve.user_type": {
        "source_paths": [("user_to_approve",), ("user",)],
        "key": "user_type",
    },
}


def extract_log_value(field, log):
    """
    Extract the relevant value from a log entry based on the field.

    This function uses a handler mapping to dispatch to the correct extraction strategy.
    """
    handler = FIELD_HANDLERS.get(field)
    if not handler:
        return ""

    payload = _get_payload(log)

    if callable(handler):
        return handler(log, payload)

    if isinstance(handler, dict):
        source_paths = handler["source_paths"]
        key = handler["key"]

        sources = [safe_get(payload, *path) for path in source_paths]

        return _find_first_value(sources, key)

    return ""


def matches_date_filter(log_date, operator, filter_criteria_date):
    """Return True if log_date matches the date filter operator and value."""
    if operator in ["is", "equals"]:
        return log_date is not None and log_date == filter_criteria_date
    if operator in ["is not", "not"]:
        return log_date is None or log_date != filter_criteria_date
    if operator in ["is after", "after"]:
        return log_date is not None and log_date > filter_criteria_date
    if operator in ["is on or after", "on or after"]:
        return log_date is not None and log_date >= filter_criteria_date
    if operator in ["is before", "before"]:
        return log_date is not None and log_date < filter_criteria_date
    if operator in ["is on or before", "on or before"]:
        return log_date is not None and log_date <= filter_criteria_date
    return False


def matches_string_filter(log_value: str, operator: str, value: str) -> bool:
    """Check if a log value matches a string filter condition."""
    op = operator.replace(" ", "").lower()
    if op == "contains":
        return value.lower() in (log_value or "").lower()
    elif op in ("equals", "is"):
        return (log_value or "").lower() == (value or "").lower()
    elif op in ("startswith", "starts with"):
        return (log_value or "").lower().startswith((value or "").lower())
    elif op in ("endswith", "ends with"):
        return (log_value or "").lower().endswith((value or "").lower())
    elif op in ("isempty", "is empty"):
        return log_value is None or log_value == ""
    elif op in ("isnotempty", "is not empty"):
        return log_value is not None and log_value != ""
    elif op in ("isanyof", "is any of"):
        if not value:
            return False
        if isinstance(value, str):
            value_list = [v.strip().lower() for v in value.split(",")]
        else:
            value_list = [str(v).strip().lower() for v in value]
        return (log_value or "").lower() in value_list
    elif op == "doesnotcontain":
        return value.lower() not in (log_value or "").lower()
    elif op == "doesnotequal":
        return (log_value or "").lower() != (value or "").lower()
    return False


def generate_date_condition(filter_obj: Dict[str, Any]) -> Q:
    """Return a Q object for date-based log filtering."""
    operator = (
        filter_obj.get("operator", "")
        .replace("_", " ")
        .replace("-", " ")
        .lower()
        .strip()
    )
    value = filter_obj.get("value", "")
    # Exclude string-only operators from date logic
    if operator in ["doesnotcontain", "doesnotequal"]:
        raise ValueError("Operator not supported for date fields.")
    if operator in ["empty", "is empty"]:
        return Q(created_at__isnull=True)
    elif operator in ["not empty", "is not empty"]:
        return Q(created_at__isnull=False)
    operators_require_value = [
        "is",
        "equals",
        "not",
        "is not",
        "after",
        "is after",
        "on or after",
        "is on or after",
        "before",
        "is before",
        "on or before",
        "is on or before",
    ]
    if operator in operators_require_value and (value is None or value == ""):
        return Q()
    try:
        date_obj = parse(value)
        date_obj = date_obj.replace(second=0, microsecond=0)
        if timezone.is_naive(date_obj):
            date_obj = timezone.make_aware(date_obj, timezone.get_current_timezone())
        date_obj = date_obj.replace(second=0, microsecond=0)
    except Exception:
        raise ValueError("Invalid date format. Use ISO format.")
    if operator in ["is", "equals"]:
        start_dt = date_obj
        end_dt = start_dt + timedelta(minutes=1)
        return Q(created_at__gte=start_dt, created_at__lt=end_dt)
    elif operator in ["not", "is not"]:
        start_dt = date_obj
        end_dt = start_dt + timedelta(minutes=1)
        return ~Q(created_at__gte=start_dt, created_at__lt=end_dt)
    elif operator in ["after", "is after"]:
        return Q(created_at__gt=date_obj)
    elif operator in ["on or after", "is on or after"]:
        return Q(created_at__gte=date_obj)
    elif operator in ["before", "is before"]:
        return Q(created_at__lt=date_obj)
    elif operator in ["on or before", "is on or before"]:
        return Q(created_at__lte=date_obj)
    else:
        raise ValueError("Invalid date operator.")


def search_logs(search_data, current_user):
    """Search logs using filters and return serialized results."""
    try:
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")
        search_dict = search_data.dict(exclude_unset=True)
        q_object = Q()
        if "event_type" in search_dict and search_dict["event_type"]:
            operator = (
                search_dict["event_type"]
                .get("operator", "contains")
                .replace(" ", "")
                .lower()
            )
            value = search_dict["event_type"]["value"]
            if operator == "contains":
                q_object &= Q(event_type__icontains=value)
            elif operator in ("equals", "is"):
                q_object &= Q(event_type__iexact=value)
            elif operator == "doesnotcontain":
                q_object &= ~Q(event_type__icontains=value)
            elif operator == "doesnotequal":
                q_object &= ~Q(event_type__iexact=value)
        if "result" in search_dict and search_dict["result"]:
            operator = (
                search_dict["result"]
                .get("operator", "contains")
                .replace(" ", "")
                .lower()
            )
            value = search_dict["result"]["value"]
            if operator == "contains":
                q_object &= Q(result__icontains=value)
            elif operator in ("equals", "is"):
                q_object &= Q(result__iexact=value)
            elif operator == "doesnotcontain":
                q_object &= ~Q(result__icontains=value)
            elif operator == "doesnotequal":
                q_object &= ~Q(result__iexact=value)
        if "timestamp" in search_dict and search_dict["timestamp"]:
            q_object &= generate_date_condition(search_dict["timestamp"])
        if "payload" in search_dict and search_dict["payload"]:
            payload_filters = parse_query_string(search_dict["payload"])
            for key, value in payload_filters.items():
                q_object &= Q(**{f"payload__{key}": value})
        logs_qs = Log.objects.filter(q_object)
        count = logs_qs.count()
        logs_serialized = []
        for log in logs_qs:
            try:
                payload_dict = json.loads(log.payload)
            except (ValueError, TypeError):
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
        LOGGER.exception("Unhandled error occurred: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _normalize_operator(operator: str) -> str:
    """Clean and standardizes the operator string."""
    op = re.sub(r"([a-z])([A-Z])", r"\1 \2", operator)
    return op.replace("_", " ").replace("-", " ").lower().strip()


def _parse_and_prepare_date(date_str: Optional[str]):
    """Parse a date string and returns a timezone-aware datetime object."""
    if not isinstance(date_str, str) or not date_str:
        return None
    try:
        dt = parse(date_str).replace(second=0, microsecond=0)
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except (ValueError, TypeError):
        return None


def _apply_timestamp_filter(log: dict, operator: str, filter_value: str) -> bool:
    """Apply a filter specifically for the timestamp field."""
    log_date = _parse_and_prepare_date(log.get("created_at"))

    if operator == "is empty":
        return log_date is None
    if operator == "is not empty":
        return log_date is not None

    if operator in ["doesnotcontain", "doesnotequal"]:
        return True

    filter_date = _parse_and_prepare_date(filter_value)

    if not log_date or not filter_date:
        return False

    return matches_date_filter(log_date, operator, filter_date)


def _log_matches_all_filters(log: dict, filters: dict) -> bool:
    """Check if a single log entry matches all provided filter conditions."""
    for field, condition in filters.items():
        value = getattr(condition, "value", "") or ""
        operator = _normalize_operator(getattr(condition, "operator", ""))

        if field == "timestamp":
            if not _apply_timestamp_filter(log, operator, value):
                return False
        else:
            log_value = extract_log_value(field, log)
            if not matches_string_filter(log_value, operator, value):
                return False

    return True


def search_logs_filtered(search_data: LogSearchFilter, current_user):
    """Apply advanced filters to logs and return paginated results."""
    try:
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        base_search = LogSearch()
        all_logs, _ = search_logs(base_search, current_user)

        filtered_logs = [
            log
            for log in all_logs
            if _log_matches_all_filters(log, search_data.filters)
        ]

        page = search_data.page
        page_size = search_data.page_size
        start = (page - 1) * page_size
        end = start + page_size

        return filtered_logs[start:end], len(filtered_logs)

    except ValueError as ve:
        LOGGER.exception("ValueError occurred: %s", ve)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        LOGGER.exception("Unhandled error occurred: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

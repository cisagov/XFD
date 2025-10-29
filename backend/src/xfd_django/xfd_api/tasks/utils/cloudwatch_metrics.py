"""Cloudwatch Metrics wrappers."""
# Standard Python Libraries
import functools
import json
import logging
import time

LOGGER = logging.getLogger(__name__)


def emit_redshift_metric(query_name: str, duration_s: float, rows: int, success=True):
    """
    Emit timing metrics to CloudWatch via Embedded Metrics Format (EMF).

    Appears automatically if logs go to CloudWatch.
    """
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "CyHy/Workers/Redshift",
                    "Dimensions": [["QueryName", "Success"]],
                    "Metrics": [
                        {"Name": "DurationSeconds", "Unit": "Seconds"},
                        {"Name": "RowCount", "Unit": "Count"},
                    ],
                }
            ],
        },
        "QueryName": query_name,
        "Success": str(success),
        "DurationSeconds": duration_s,
        "RowCount": rows,
    }
    # Print JSON to stdout so CloudWatch Logs automatically picks it up.
    print(json.dumps(payload))  # noqa


def emit_django_metric(stage: str, count: int, duration_s: float, success=True):
    """Emit CloudWatch EMF metrics for Django ORM operations."""
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "CyHy/Worker/Functions",
                    "Dimensions": [["Stage", "Success"]],
                    "Metrics": [
                        {"Name": "DurationSeconds", "Unit": "Seconds"},
                        {"Name": "RecordCount", "Unit": "Count"},
                    ],
                }
            ],
        },
        "Stage": stage,
        "Success": str(success),
        "DurationSeconds": duration_s,
        "RecordCount": count,
    }
    print(json.dumps(payload))  # noqa


def cloudwatch_metric(stage_name=None):
    """
    Time entire function execution and emit CloudWatch metrics.

    Usage:
        @cloudwatch_metric()
        def my_function(...):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            stage = stage_name or func.__name__
            start = time.perf_counter()
            success = True
            try:
                return func(*args, **kwargs)
            except Exception as e:
                success = False
                LOGGER.exception("Error in %s: %s", stage, e)
                raise
            finally:
                duration = time.perf_counter() - start
                emit_django_metric(stage, 1, duration, success)

        return wrapper

    return decorator

"""Prune scan_results table."""
# Standard Python Libraries
from datetime import timedelta
import os

# Third-Party Libraries
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError
from django.utils import timezone
from xfd_mini_dl.models import ScanResult

# TODO: Add SCAN_METRICS_RETENTION_PERIOD to parameter store


def handler():
    """Prune records from scan_results table older than retention period."""
    try:
        retention_days = int(os.getenv("SCAN_METRICS_RETENTION_PERIOD", "90"))
        cutoff = timezone.now() - timedelta(days=retention_days)
        deleted, _ = ScanResult.objects.filter(scanned_at__lt=cutoff).delete()
        return {
            "status_code": 200,
            "body": "[prune_scan_results] Deleted {} records older than {}.".format(
                deleted, cutoff.date().isoformat()
            ),
        }

    except ImproperlyConfigured as ic:
        return {
            "status_code": 500,
            "body": "[prune_scan_results] Configuration error: {}".format(ic),
        }

    except DatabaseError as db_err:
        return {
            "status_code": 500,
            "body": "[prune_scan_results] Database error during prune_scan_results: {}".format(
                db_err
            ),
        }

    except Exception as e:
        return {
            "status_code": 500,
            "body": "[prune_scan_results] Unexpected error: {}".format(e),
        }

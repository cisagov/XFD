"""Task for synchronizing vulnerability scanning data.

This module handles fetching, processing, and saving vulnerability scans,
port scans, hosts, and tickets from Databricks into the Django models.
"""

# Standard Python Libraries
from datetime import datetime, timezone
import logging
from logging import FileHandler
import os
from time import monotonic
import uuid

# Third-Party Libraries
from xfd_api.tasks.utils.cloudwatch_metrics import cloudwatch_metric
from xfd_api.tasks.utils.datetime_utils import freeze_window
from xfd_api.tasks.utils.vs_port_scans import (
    create_port_scan_summaries_bulk,
    fetch_port_scans_from_databricks,
)
from xfd_api.tasks.utils.vs_requests import fetch_org_id_dict_fast
from xfd_api.tasks.utils.vs_tickets import fetch_tickets_from_databricks
from xfd_api.tasks.utils.vs_vuln_scans import (
    create_vuln_scan_summary,
    fetch_vuln_scan_chunks_frozen,
)
from xfd_api.utils.scan_utils.alerting import ScanExecutionError
from xfd_mini_dl.models import NMIServiceGroup, RiskyServiceGroup

LOGGER = logging.getLogger(__name__)

IS_LOCAL = os.getenv("IS_LOCAL")
SCAN_NAME = "VulnScanningSync"
VS_PULL_DATE_RANGE = os.getenv("VS_PULL_DATE_RANGE", "2")


def _get_run_id(event: dict) -> str:
    """Return an event-provided ID where available, otherwise generate one."""
    return str(
        event.get("run_id")
        or event.get("message_id")
        or event.get("request_id")
        or uuid.uuid4()
    )


def _log_phase_started(run_id: str, phase: str, **details) -> float:
    """Log a lifecycle-phase start and return a monotonic start time."""
    LOGGER.info(
        "VS sync phase started | run_id=%s | phase=%s | details=%s",
        run_id,
        phase,
        details,
    )
    return monotonic()


def _log_phase_finished(
    run_id: str,
    phase: str,
    started_at: float,
    **details,
) -> None:
    """Log a lifecycle-phase completion with elapsed time."""
    LOGGER.info(
        "VS sync phase finished | run_id=%s | phase=%s | "
        "elapsed_seconds=%.2f | details=%s",
        run_id,
        phase,
        monotonic() - started_at,
        details,
    )


def setup_vuln_sync_logging(
    filename: str = "/tmp/vuln_scanning_sync.log",  # nosec B108
    logger_name: str = "xfd",  # Use the main logger
) -> None:
    """Attach a file handler that reuses the unified formatter & filters. Runs once."""
    # Don't add twice
    if any(
        isinstance(handler, FileHandler)
        and getattr(handler, "baseFilename", "").endswith(filename)
        for handler in LOGGER.handlers
    ):
        return

    # Find a formatter to reuse: prefer a handler on the unified logger, else root
    def _find_formatter_and_filters():
        for current_logger in (logging.getLogger(logger_name), logging.getLogger()):
            for handler in current_logger.handlers:
                if handler.formatter:
                    return handler.formatter, list(handler.filters) or []
        # Fallback: no configured handlers yet
        return (
            logging.Formatter(
                "[%(asctime)s.%(msecs)03d] %(levelname)s "
                "[%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
                "%Y-%m-%d %H:%M:%S",
            ),
            [],
        )

    formatter, filters = _find_formatter_and_filters()

    file_handler = FileHandler(filename)
    file_handler.setLevel(LOGGER.getEffectiveLevel())
    file_handler.setFormatter(formatter)
    for filter in filters:  # reuse any handler-level filters (e.g., redaction)
        file_handler.addFilter(filter)

    # Also inherit logger-level filters
    for filter in LOGGER.filters:
        file_handler.addFilter(filter)

    LOGGER.addHandler(file_handler)


def handler(event):
    """Handle execution of the vulnerability scanning sync task.

    This function serves as the entry point for triggering the synchronization
    process. It calls the `main` function and returns the appropriate response
    based on the execution outcome.

    Args:
        event (dict): The event data that triggers the function.

    Returns:
        dict: Response containing the status code and message.
    """
    event = dict(event or {})  # Ensure event is a dict for logging
    run_id = _get_run_id(event)
    event["run_id"] = run_id  # Ensure run_id is in the event for downstream logging

    LOGGER.info(
        "VS sync handler received event | run_id=%s | event_keys=%s | "
        "vs_pull_date_range=%s",
        run_id,
        sorted(event.keys()) if isinstance(event, dict) else [],
        VS_PULL_DATE_RANGE,
    )

    LOGGER.info("VS_PULL_DATE_RANGE: %s", VS_PULL_DATE_RANGE)

    try:
        main(event)

        LOGGER.info(
            "VS sync handler completed successfully | run_id=%s",
            run_id,
        )

        return {"status_code": 200, "body": "VS Sync completed successfully"}
    except Exception as e:
        LOGGER.exception(
            "VS sync handler failed | run_id=%s | error=%s",
            run_id,
            e,
        )
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e


# TODO: CRASM-3389: Add automated testing to VulnScanningSync
@cloudwatch_metric()
def main(event):  # pylint: disable=R0915
    """Execute the vulnerability scanning synchronization task."""
    run_id = event.get("run_id") or _get_run_id(event)
    sync_started_at = monotonic()

    setup_vuln_sync_logging()

    LOGGER.info(
        "VS sync started | run_id=%s | vs_pull_date_range=%s",
        run_id,
        VS_PULL_DATE_RANGE,
    )
    LOGGER.info("Started VulnScanningSync scan...")

    # Use fixed window + deterministic keyset on (time, _id)
    ps_start_dt = event.get("start_datetime")
    ps_end_dt = event.get("end_datetime")
    org_list = event.get("org_list")

    LOGGER.info(
        "VS sync event parsed | run_id=%s | org_list_present=%s | "
        "provided_org_count=%d | provided_start_datetime=%s | "
        "provided_end_datetime=%s",
        run_id,
        org_list is not None,
        len(org_list) if org_list else 0,
        ps_start_dt,
        ps_end_dt,
    )

    org_ids = [org.get("id") for org in org_list if org.get("id")]

    phase_started_at = _log_phase_started(
        run_id,
        "fetch_org_id_dict_fast",
        requested_org_count=len(org_ids),
    )
    org_id_dict = fetch_org_id_dict_fast(org_ids=org_ids)
    _log_phase_finished(
        run_id,
        "fetch_org_id_dict_fast",
        phase_started_at,
        resolved_org_count=len(org_id_dict),
    )

    # Normalize start_datetime
    if isinstance(ps_start_dt, (int, float)):  # timestamp
        LOGGER.info(
            "VS sync normalizing start_datetime timestamp | run_id=%s",
            run_id,
        )
        ps_start_dt = datetime.fromtimestamp(ps_start_dt, tz=timezone.utc)
    elif isinstance(ps_start_dt, str):  # ISO string
        LOGGER.info(
            "VS sync normalizing start_datetime ISO string | run_id=%s",
            run_id,
        )
        ps_start_dt = datetime.fromisoformat(ps_start_dt).astimezone(timezone.utc)

    # Normalize end_timestamp
    if isinstance(ps_end_dt, (int, float)):  # timestamp
        LOGGER.info(
            "VS sync normalizing end_datetime timestamp | run_id=%s",
            run_id,
        )
        ps_end_dt = datetime.fromtimestamp(ps_end_dt, tz=timezone.utc)
    elif isinstance(ps_end_dt, str):  # ISO string
        LOGGER.info(
            "VS sync normalizing end_datetime ISO string | run_id=%s",
            run_id,
        )
        ps_end_dt = datetime.fromisoformat(ps_end_dt).astimezone(timezone.utc)

    # If either is missing, fallback to freeze_window
    used_fallback_window = False
    if not (ps_start_dt and ps_end_dt):
        used_fallback_window = True

        phase_started_at = _log_phase_started(
            run_id,
            "freeze_window",
            pull_date_range_days=VS_PULL_DATE_RANGE,
        )
        ps_start_dt, ps_end_dt = freeze_window(int(VS_PULL_DATE_RANGE))
        _log_phase_finished(
            run_id,
            "freeze_window",
            phase_started_at,
            start_datetime=str(ps_start_dt),
            end_datetime=str(ps_end_dt),
        )

    LOGGER.info(
        "VS sync window resolved | run_id=%s | start_datetime=%s | "
        "end_datetime=%s | used_fallback_window=%s",
        run_id,
        ps_start_dt,
        ps_end_dt,
        used_fallback_window,
    )

    LOGGER.info("Frozen port-scan window: [%s .. %s]", ps_start_dt, ps_end_dt)

    LOGGER.info(
        "Processing organizations | run_id=%s | organization_count=%d",
        run_id,
        len(org_id_dict),
    )
    LOGGER.info("Processing %d organizations", len(org_id_dict))

    # Start Vuln Scan
    phase_started_at = _log_phase_started(
        run_id,
        "fetch_vuln_scan_chunks_frozen",
        organization_count=len(org_id_dict),
        start_datetime=str(ps_start_dt),
        end_datetime=str(ps_end_dt),
    )
    try:
        fetch_vuln_scan_chunks_frozen(ps_start_dt, ps_end_dt, org_id_dict)
        _log_phase_finished(
            run_id,
            "fetch_vuln_scan_chunks_frozen",
            phase_started_at,
            organization_count=len(org_id_dict),
        )
    except Exception as e:
        LOGGER.exception(
            "VS vuln scan phase failed | run_id=%s | elapsed_seconds=%.2f | "
            "error=%s",
            run_id,
            monotonic() - phase_started_at,
            e,
        )
        raise ScanExecutionError(SCAN_NAME, str(e), event) from e

    LOGGER.info("Prefetching risky and NMI service groups...")

    phase_started_at = _log_phase_started(
        run_id,
        "prefetch_service_groups",
    )

    # Prefetch risky service groups
    risky_service_groups = {
        rsg.service_name: rsg.group for rsg in RiskyServiceGroup.objects.all()
    }

    # Prefetch NMI service groups
    nmi_service_groups = {
        nsg.service_name: nsg.group for nsg in NMIServiceGroup.objects.all()
    }

    _log_phase_finished(
        run_id,
        "prefetch_service_groups",
        phase_started_at,
        risky_service_group_count=len(risky_service_groups),
        nmi_service_group_count=len(nmi_service_groups),
    )

    phase_started_at = _log_phase_started(
        run_id,
        "fetch_port_scans_from_databricks",
        organization_count=len(org_id_dict),
        start_datetime=str(ps_start_dt),
        end_datetime=str(ps_end_dt),
    )
    try:
        fetch_port_scans_from_databricks(
            org_id_dict,
            risky_service_groups,
            nmi_service_groups,
            ps_start_dt,
            ps_end_dt,
        )
        _log_phase_finished(
            run_id,
            "fetch_port_scans_from_databricks",
            phase_started_at,
            organization_count=len(org_id_dict),
        )
    except Exception as e:
        LOGGER.exception(
            "VS port scan phase failed | run_id=%s | elapsed_seconds=%.2f | "
            "error=%s",
            run_id,
            monotonic() - phase_started_at,
            e,
        )
        raise

    # Create summaries with individual error handling
    LOGGER.info("Creating port scan summaries in bulk...")

    phase_started_at = _log_phase_started(
        run_id,
        "create_port_scan_summaries_bulk",
        organization_count=len(org_id_dict),
    )
    try:
        create_port_scan_summaries_bulk(org_ids=list(org_id_dict.values()))
        _log_phase_finished(
            run_id,
            "create_port_scan_summaries_bulk",
            phase_started_at,
            organization_count=len(org_id_dict),
        )
        LOGGER.info("Finished port scan summaries (bulk)")
    except Exception as e:
        LOGGER.exception(
            "Port scan summary phase failed | run_id=%s | elapsed_seconds=%.2f | "
            "error=%s",
            run_id,
            monotonic() - phase_started_at,
            e,
        )

    # Process Tickets (Chunked)
    phase_started_at = _log_phase_started(
        run_id,
        "fetch_tickets_from_databricks",
        organization_count=len(org_id_dict),
        start_datetime=str(ps_start_dt),
        end_datetime=str(ps_end_dt),
    )
    try:
        fetch_tickets_from_databricks(
            org_id_dict,
            risky_service_groups,
            nmi_service_groups,
            ps_start_dt,
            ps_end_dt,
        )
        _log_phase_finished(
            run_id,
            "fetch_tickets_from_databricks",
            phase_started_at,
            organization_count=len(org_id_dict),
        )
    except Exception as e:
        LOGGER.exception(
            "Ticket sync phase failed | run_id=%s | elapsed_seconds=%.2f | error=%s",
            run_id,
            monotonic() - phase_started_at,
            e,
        )
        raise

    LOGGER.info("Ticket sync has completed for requested orgs")

    LOGGER.info("Creating vulnerability scan summary...")

    phase_started_at = _log_phase_started(
        run_id,
        "create_vuln_scan_summaries",
        organization_count=len(org_id_dict),
    )

    for org_id in org_id_dict.values():
        org_summary_started_at = monotonic()

        LOGGER.info(
            "Vuln scan summary started | run_id=%s | org_id=%s",
            run_id,
            org_id,
        )

        try:
            create_vuln_scan_summary(org_id=org_id)

            LOGGER.info(
                "Vuln scan summary finished | run_id=%s | org_id=%s | "
                "elapsed_seconds=%.2f",
                run_id,
                org_id,
                monotonic() - org_summary_started_at,
            )
        except Exception as e:
            LOGGER.exception(
                "Vuln scan summary failed | run_id=%s | org_id=%s | "
                "elapsed_seconds=%.2f | error=%s",
                run_id,
                org_id,
                monotonic() - org_summary_started_at,
                e,
            )

    _log_phase_finished(
        run_id,
        "create_vuln_scan_summaries",
        phase_started_at,
        organization_count=len(org_id_dict),
    )

    LOGGER.info("Finished vulnerability scan summary")

    LOGGER.info(
        "VS sync completed | run_id=%s | total_elapsed_seconds=%.2f",
        run_id,
        monotonic() - sync_started_at,
    )

    return {"status_code": 200, "body": "Vuln Scan Sync completed successfully"}

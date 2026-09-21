"""Operator-facing summaries for recent-scan WAS report batches."""

# Standard Python Libraries
from collections import Counter
from dataclasses import dataclass
import logging
from typing import Iterable

# First-Party Libraries
from was_reports.data.daily_report_tracker import TrackerReportCandidate

UNSPECIFIED_TEMPLATE = "Unspecified"


@dataclass(frozen=True)
class BatchPreflightSummary:
    """Counts for the report candidates selected before batch processing."""

    candidates: int
    template_counts: tuple[tuple[str, int], ...]
    qualys_error_overlays: int
    pdf_reports: int = 0
    notification_only: int = 0


def summarize_candidates(
    candidates: Iterable[TrackerReportCandidate],
) -> BatchPreflightSummary:
    """Return stable preflight counts for the supplied report candidates."""
    candidate_list = list(candidates)
    template_counts = Counter(
        (candidate.template or "").strip() or UNSPECIFIED_TEMPLATE
        for candidate in candidate_list
    )
    qualys_error_overlays = sum(
        1
        for candidate in candidate_list
        if (candidate.qualys_error or "").strip()
    )
    return BatchPreflightSummary(
        candidates=len(candidate_list),
        template_counts=tuple(sorted(template_counts.items())),
        qualys_error_overlays=qualys_error_overlays,
        pdf_reports=sum(
            candidate.template not in {"All NWS", "FCEB All NWS"}
            for candidate in candidate_list
        ),
        notification_only=sum(
            candidate.template in {"All NWS", "FCEB All NWS"}
            for candidate in candidate_list
        ),
    )


def log_preflight_summary(
    logger: logging.Logger,
    summary: BatchPreflightSummary,
    days_back: int | None,
) -> None:
    """Log the selected date scope and report composition before processing."""
    date_scope = "all eligible tracker history"
    if days_back is not None:
        date_scope = "the last {} calendar days".format(days_back)

    logger.info(
        "Report preflight selected %d candidate(s) from %s.",
        summary.candidates,
        date_scope,
    )
    if summary.template_counts:
        logger.info(
            "Report templates: %s.",
            ", ".join(
                "{}={}".format(template_name, count)
                for template_name, count in summary.template_counts
            ),
        )
    else:
        logger.info("Report templates: none.")
    logger.info(
        "Qualys error overlays: %d.",
        summary.qualys_error_overlays,
    )
    logger.info(
        "PDF reports: %d; notification-only emails: %d.",
        summary.pdf_reports,
        summary.notification_only,
    )


def log_candidate_progress(
    logger: logging.Logger,
    candidate_index: int,
    candidate_count: int,
    stakeholder_tag: str,
) -> None:
    """Log a simple fraction for one candidate in the report worker phase."""
    logger.info(
        "Phase 3/5: Processing report candidate %d/%d for tag %s.",
        candidate_index,
        candidate_count,
        stakeholder_tag,
    )

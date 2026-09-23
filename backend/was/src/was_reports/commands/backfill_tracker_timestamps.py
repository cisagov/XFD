"""Preview or explicitly fill missing tracker timestamps without refreshing reports."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from lxml import etree
from lxml.builder import E

from was_reports.qualys.qualys_client import QualysRequest, create_qualys_client
from was_reports.tracker.qualys_scans import (
    execution_detail_bounds,
    normalize_schedule_name,
    parse_xml,
    response_count,
    response_has_more_records,
)
from was_reports.tracker.update_service import convert_qualys_date
from was_reports.utils.database import close, connect

EASTERN = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class TimestampCandidate:
    """Capture immutable identity and previously observed timestamps for safe writes."""

    tracker_id: int
    schedule_id: int | None
    tag: str
    scan_name: str
    scan_start_date: date
    scan_execution_key: str | None
    scan_started_at: datetime | None
    scan_ended_at: datetime | None


def load_candidates(since: date, until: date, tag: str | None, limit: int,
                    after_id: int = 0) -> list[TimestampCandidate]:
    """Read a bounded selection, never locking or changing tracker rows."""
    connection = connect()
    try:
        connection.set_session(readonly=True)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, schedule_id, tag, scan_name, scan_start_date,
                       scan_execution_key, scan_started_at, scan_ended_at
                FROM was_daily_report_tracker
                WHERE scan_start_date >= %s
                  AND scan_start_date <= %s AND id > %s
                  AND (scan_started_at IS NULL OR scan_ended_at IS NULL)
                  AND NULLIF(BTRIM(scan_name), '') IS NOT NULL
                  AND (%s IS NULL OR tag = %s)
                ORDER BY id ASC
                LIMIT %s
                """, (since, until, after_id, tag, tag, limit),
            )
            return [TimestampCandidate(*row) for row in cursor.fetchall()]
    finally:
        close(connection)


def search_matching_scans(client, since: date, until: date,
                          names: set[str]) -> dict[tuple[str, date], list]:
    """Collect exact named parent/single matches; never mistake a slice for a run."""
    matches = {}
    offset = 1
    lower_bound = datetime.combine(since, time.min, tzinfo=EASTERN).astimezone(timezone.utc)
    upper_bound = datetime.combine(until + timedelta(days=1), time.min, tzinfo=EASTERN).astimezone(timezone.utc)
    while True:
        request = E.ServiceRequest(
            E.preferences(E.limitResults("1000"), E.startFromOffset(str(offset))),
            E.filters(
                E.Criteria((lower_bound - timedelta(seconds=1)).isoformat(), field="launchedDate", operator="GREATER"),
                E.Criteria(upper_bound.isoformat(), field="launchedDate", operator="LESSER"),
                E.Criteria("VULNERABILITY", field="type", operator="EQUALS"),
            ),
        )
        response = client.request(QualysRequest(
            endpoint="/search/was/wasscan", payload=etree.tostring(request, encoding="unicode"),
            http_method="POST",
        ))
        root = parse_xml(response, "timestamp backfill scan search")
        if root.findtext("responseCode") != "SUCCESS":
            raise RuntimeError("Qualys timestamp search did not return SUCCESS.")
        for scan in root.findall("./data/WasScan"):
            raw_name = scan.findtext("name") or ""
            name = normalize_schedule_name(raw_name)
            if (scan.findtext("multi") or "").strip().lower() not in {"true", "false"}:
                continue
            if " Slice" in name or name not in names or " Run #" not in name:
                continue
            if not name.rsplit(" Run #", 1)[1].isdigit() or scan.findtext("status") != "FINISHED":
                continue
            launch = scan.findtext("launchedDate")
            if not launch:
                continue
            try:
                parsed = datetime.fromisoformat(launch.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    continue
                scan_day = convert_qualys_date(launch)
            except ValueError:
                continue
            if scan_day < since or scan_day > until:
                continue
            key = (name, scan_day)
            identifier = scan.findtext("id")
            if not identifier or not identifier.isdigit():
                continue
            existing = matches.setdefault(key, [])
            if not any(identifier and identifier == other.findtext("id") for other in existing):
                existing.append(scan)
        print("Timestamp scan search: offset {}; {} records; {} matching identities.".format(
            offset, response_count(root), len(matches)
        ))
        if not response_has_more_records(root):
            return matches
        count = response_count(root)
        if count <= 0:
            raise RuntimeError("Timestamp backfill pagination did not advance.")
        offset += count


def proposed_timestamps(candidate: TimestampCandidate, scans: list, bounds):
    """Return reliable missing values, refusing ambiguity or existing-start conflict."""
    if len(scans) != 1:
        return None
    parts = normalize_schedule_name(scans[0].findtext("name") or "").split(" - ")
    if len(parts) < 3 or parts[1] != candidate.tag:
        return None
    start, end = bounds
    if start is None:
        return None
    if candidate.scan_started_at is not None and candidate.scan_started_at != start:
        return None
    if candidate.scan_ended_at is not None and (
        candidate.scan_ended_at < start or (end is not None and candidate.scan_ended_at != end)
    ):
        return None
    if candidate.scan_started_at is not None and end is None:
        return None
    return start, end


def apply_proposals(proposals: list[tuple[TimestampCandidate, datetime, datetime | None]]) -> list:
    """Atomically fill only unchanged, still-missing fields using optimistic guards."""
    connection = connect()
    updated = []
    try:
        with connection.cursor() as cursor:
            for candidate, start, end in proposals:
                cursor.execute(
                    """
                    UPDATE was_daily_report_tracker
                    SET scan_started_at = COALESCE(scan_started_at, %s),
                        scan_ended_at = COALESCE(scan_ended_at, %s)
                    WHERE id = %s AND schedule_id IS NOT DISTINCT FROM %s
                      AND tag IS NOT DISTINCT FROM %s
                      AND scan_name IS NOT DISTINCT FROM %s
                      AND scan_start_date = %s
                      AND scan_execution_key IS NOT DISTINCT FROM %s
                      AND scan_started_at IS NOT DISTINCT FROM %s
                      AND scan_ended_at IS NOT DISTINCT FROM %s
                      AND (scan_started_at IS NULL OR (scan_ended_at IS NULL AND %s IS NOT NULL))
                    RETURNING id, scan_started_at, scan_ended_at
                    """,
                    (start, end, candidate.tracker_id, candidate.schedule_id, candidate.tag,
                     candidate.scan_name, candidate.scan_start_date, candidate.scan_execution_key,
                     candidate.scan_started_at, candidate.scan_ended_at, end),
                )
                updated_row = cursor.fetchone()
                if updated_row is not None:
                    updated.append(updated_row)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        close(connection)
    return updated


def run_backfill(since: date, tag: str | None, limit: int, apply: bool = False,
                 until: date | None = None, after_id: int = 0,
                 confirm_name_date_matches: bool = False) -> dict:
    """Preview bounded identity matches by default; apply only on explicit request."""
    if apply and not confirm_name_date_matches:
        raise ValueError("Apply requires --confirm-name-date-matches after reviewing the mapping.")
    until = until or datetime.now(EASTERN).date()
    if limit < 1 or after_id < 0 or until < since:
        raise ValueError("Require positive limit, nonnegative after-id, and until >= since.")
    candidates = load_candidates(since, until, tag, limit, after_id)
    proposals = []
    scan_ids = {}
    if candidates:
        client = create_qualys_client()
        matches = search_matching_scans(
            client, since, until, {normalize_schedule_name(row.scan_name) for row in candidates}
        )
        cache = {}
        for candidate in candidates:
            key = (normalize_schedule_name(candidate.scan_name), candidate.scan_start_date)
            # Cache detail responses across duplicate tracker rows without losing
            # each row's independent conflict checks.
            scans = matches.get(key, [])
            if len(scans) == 1:
                identifier = scans[0].findtext("id")
                if identifier not in cache:
                    cache[identifier] = execution_detail_bounds(client, scans[0])
                proposed = proposed_timestamps(candidate, scans, cache[identifier])
                if proposed is not None:
                    proposals.append((candidate, *proposed))
                    scan_ids[candidate.tracker_id] = identifier
    updated = apply_proposals(proposals) if apply and proposals else []
    return {"mode": "apply" if apply else "preview", "candidates": len(candidates),
            "proposed": len(proposals), "skipped": len(candidates) - len(proposals),
            "updated": len(updated), "updated_rows": updated,
            "proposals": proposals,
            "qualys_scan_ids": scan_ids,
            "next_after_id": max((row.tracker_id for row in candidates), default=after_id),
            "tracker_ids": [row.tracker_id for row, start, end in proposals]}


def main() -> None:
    """Expose explicit preview/apply controls without report side effects."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--tag")
    parser.add_argument("--until", type=date.fromisoformat)
    parser.add_argument("--after-id", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-name-date-matches", action="store_true")
    arguments = parser.parse_args()
    if arguments.apply and not arguments.confirm_name_date_matches:
        parser.error("--apply requires --confirm-name-date-matches after preview review")
    print("Matching uses exact numbered name, Eastern date, and tag, not a verified Qualys schedule relation.")
    result = run_backfill(arguments.since, arguments.tag, arguments.limit, arguments.apply,
                          arguments.until, arguments.after_id, arguments.confirm_name_date_matches)
    print("{}: {} candidates; {} proposed; {} skipped; {} updated.".format(
        result["mode"], result["candidates"], result["proposed"], result["skipped"], result["updated"]
    ))
    print("Proposed tracker IDs: {}".format(", ".join(map(str, result["tracker_ids"])) or "none"))
    print("Next page: --after-id {}".format(result["next_after_id"]))
    for candidate, started, ended in result["proposals"]:
        print("Tracker {} / schedule {} / Qualys scan {} / tag {} / name {}: original start={} end={}; proposed start={} end={}".format(
            candidate.tracker_id, candidate.schedule_id, result["qualys_scan_ids"][candidate.tracker_id],
            candidate.tag, candidate.scan_name, candidate.scan_started_at, candidate.scan_ended_at,
            candidate.scan_started_at or started, candidate.scan_ended_at or ended,
        ))
    for identifier, started, ended in result["updated_rows"]:
        print("Updated tracker {}: start={} end={}".format(identifier, started, ended))


if __name__ == "__main__":
    main()

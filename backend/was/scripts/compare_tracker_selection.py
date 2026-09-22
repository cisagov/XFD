"""Compare schedule selection only, without tracker writes or report generation.

The hash-pinned authoritative archive function is AST-extracted without import effects.
AM tag lookups are replaced with included schedule tag IDs. Missing next-launch
dates receive a neutral value in BOTH paths: this isolates candidate selection,
not ad-hoc lookup success. No scan-search or final report parity is claimed.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import redirect_stdout
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import io
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unicodedata
from zoneinfo import ZoneInfo
from zipfile import ZipFile

from lxml import etree
from lxml.builder import E
from lxml.objectify import fromstring
import pandas as pd

from was_reports.data.daily_report_tracker import latest_tracker_pull_date
from was_reports.qualys.qualys_client import QualysRequest, create_qualys_client
from was_reports.tracker import qualys_scans
from was_reports.utils.database import connect

LEGACY_ARCHIVE = Path(__file__).resolve().parents[2] / "WAS Automation Export 2026-05-06.zip"
LEGACY_MEMBER = (
    "WAS Automation Export 2025-05-06/update_tracker/update_tracker/"
    "utils/qualys_api_search/search_schedules.py"
)
LEGACY_SOURCE_SHA256 = "7378ea44dbeaa395a3ecf6901aa4f36703d76240815e319ccfea4c632ed66eb8"
NEUTRAL_NEXT_DATE = "2099-01-01T00:00:00Z"


def legacy_name(schedule_name: str) -> tuple[str, str]:
    """Reproduce legacy Unicode-dash-run substitution without a regex dependency."""
    characters = []
    previous_dash = False
    for character in schedule_name:
        is_dash = unicodedata.category(character) == "Pd"
        if not is_dash or not previous_dash:
            characters.append("-" if is_dash else character)
        previous_dash = is_dash
    parts = "".join(characters).split(" - ")
    return parts[1], parts[2]


def load_legacy_function(namespace: dict) -> object:
    """Compile only search_schedules, never its network/database import setup."""
    with ZipFile(LEGACY_ARCHIVE) as archive:
        source = archive.read(LEGACY_MEMBER)
    if hashlib.sha256(source).hexdigest() != LEGACY_SOURCE_SHA256:
        raise ValueError("Authoritative legacy schedule source hash does not match.")
    tree = ast.parse(source.decode("utf-8"))
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "search_schedules"]
    if len(functions) != 1:
        raise RuntimeError("Expected exactly one legacy search_schedules function.")
    module = ast.Module(body=functions, type_ignores=[])
    exec(compile(module, "{}!{}".format(LEGACY_ARCHIVE, LEGACY_MEMBER), "exec"), namespace)
    return namespace["search_schedules"]


class ReplayClient:
    """Apply the actual request's selection criteria to one immutable snapshot."""

    def __init__(self, records: list[str]):
        self.records = records
        self.calls = 0

    def request(self, request: object, payload: object = None, **kwargs: object) -> str:
        """Serve schedule searches only, refusing other endpoints or criteria."""
        endpoint = request.endpoint if isinstance(request, QualysRequest) else request
        if str(endpoint).strip("/") != "search/was/wasscanschedule":
            raise ValueError("Only schedule search replay is allowed.")
        content = request.payload if isinstance(request, QualysRequest) else payload
        root = etree.fromstring(content.encode()) if isinstance(content, str) else content
        criteria = root.findall("./filters/Criteria")
        selected = []
        for record in self.records:
            schedule = etree.fromstring(record.encode())
            accepted = True
            for criterion in criteria:
                field = criterion.get("field")
                value = schedule.findtext(str(field).replace(".", "/")) or ""
                expected = criterion.text or ""
                operation = criterion.get("operator")
                if operation == "GREATER":
                    # Date-only endpoint criteria mean midnight UTC.
                    actual_date = datetime.fromisoformat(value.replace("Z", "+00:00")) \
                        if value else None
                    expected_date = datetime.fromisoformat(expected.replace("Z", "+00:00"))
                    if expected_date.tzinfo is None:
                        expected_date = expected_date.replace(tzinfo=timezone.utc)
                    if actual_date is not None and actual_date.tzinfo is None:
                        actual_date = actual_date.replace(tzinfo=timezone.utc)
                    accepted = accepted and actual_date is not None and actual_date > expected_date
                elif operation == "NOT EQUALS":
                    accepted = accepted and value != expected
                elif operation == "EQUALS":
                    # Captured endpoint already guarantees this filter even if
                    # its projection omits type from each schedule record.
                    accepted = accepted and (value == expected or (
                        field == "type" and not value and expected == "VULNERABILITY"))
                else:
                    raise ValueError("Unsupported replay criterion.")
            if accepted:
                selected.append(schedule)
        offset = int(root.findtext("./preferences/startFromOffset") or "1") - 1
        limit = int(root.findtext("./preferences/limitResults") or "50")
        page = selected[offset:offset + limit]
        response = E.ServiceResponse(
            E.count(str(len(page))),
            E.hasMoreRecords("true" if offset + limit < len(selected) else "false"),
            E.data(*page),
        )
        self.calls += 1
        return etree.tostring(response, encoding="unicode")


def compare(snapshot: dict, days: int = 2) -> dict:
    """Replay both selectors with equal cutoffs and recent tracker identity sets."""
    anchor = datetime.fromisoformat(snapshot["anchor"])
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    if days < 1:
        raise ValueError("Comparison lookback must be positive.")
    cutoff = anchor - timedelta(days=days)
    pull_dates = pd.to_datetime(
        [pd.Timestamp(row[2]) if row[2] else pd.NaT for row in snapshot["tracker_rows"]],
        utc=True,
    )
    recent_rows = [row for row, pull_date in zip(snapshot["tracker_rows"], pull_dates)
                   if pd.notna(pull_date) and pull_date >= pd.Timestamp(cutoff)]
    previous = {int(row[0]) for row in recent_rows if row[0] is not None}
    records = []
    tag_ids = {}
    adaptations = {"neutral_next_dates": 0, "missing_tag_ids": 0}
    for raw in snapshot["schedules"]:
        schedule = etree.fromstring(raw.encode())
        try:
            tag, _ = legacy_name(schedule.findtext("name") or "")
            tag_ids[tag] = qualys_scans.schedule_tag_id(schedule)
        except (LookupError, ValueError, IndexError):
            adaptations["missing_tag_ids"] += 1
            continue
        if not schedule.findtext("nextLaunchDate"):
            etree.SubElement(schedule, "nextLaunchDate").text = NEUTRAL_NEXT_DATE
            adaptations["neutral_next_dates"] += 1
        records.append(etree.tostring(schedule, encoding="unicode"))
    legacy_client = ReplayClient(records)
    current_client = ReplayClient(records)

    def stakeholder(name, tag_id, next_date, launched_date, schedule_id, cadence):
        """Replace the legacy value-only model without importing setup modules."""
        return SimpleNamespace(name=name, tag_id=tag_id, next_scan_date=next_date,
                               launched_date=launched_date, schedule_id=schedule_id,
                               cadence=cadence)

    namespace = {"E": E, "fromstring": fromstring, "qgc": legacy_client,
                 "RESULTS_LIMIT": 50, "INPUT_DATE": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "INPUT_DATE_DT": pd.Timestamp(cutoff),
                 "TRACKER": pd.DataFrame({
                     "DataPullDate": pull_dates,
                     "Schedule ID": [int(row[0]) if row[0] is not None else None
                                     for row in snapshot["tracker_rows"]],
                 }),
                 "make_stakeholder_info": legacy_name,
                 "get_tag_id": tag_ids.__getitem__, "Stakeholder": stakeholder,
                 "sys": sys, "log_exception": lambda **kwargs: None}
    legacy_evaluation_error = None
    legacy_function = load_legacy_function(namespace)
    with redirect_stdout(io.StringIO()):
        try:
            legacy = legacy_function()
        except (AttributeError, SystemExit) as error:
            # Preserve the archived failure instead of substituting an
            # invented zero-candidate outcome for its empty-page behavior.
            legacy = {}
            legacy_evaluation_error = type(error).__name__
    current = qualys_scans.search_schedules(current_client, cutoff, previous)
    legacy_pairs = {(tag, item.schedule_id) for tag, item in legacy.items()}
    current_pairs = {(item.tag, item.schedule_id) for item in current.values()}
    details = []
    statuses = {int(etree.fromstring(raw.encode()).findtext("id")):
                etree.fromstring(raw.encode()).findtext("./lastScan/status")
                for raw in records}
    for item in current.values():
        if (item.tag, item.schedule_id) in legacy_pairs:
            continue
        recorded_days = sorted({row[1] for row in recent_rows
                                if row[0] == item.schedule_id and row[1] is not None})
        launch_day = datetime.fromisoformat(item.launched_date.replace("Z", "+00:00"))
        eastern_day = launch_day.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        details.append({"tag": item.tag, "schedule_id": item.schedule_id,
                        "launch_day_eastern": eastern_day, "recorded_scan_days": recorded_days,
                        "legacy_excluded_schedule_id": item.schedule_id in previous,
                        "last_scan_status": statuses.get(item.schedule_id),
                        "legacy_kept_other_schedule_for_tag": item.tag in legacy,
                        "same_scan_day_recorded": eastern_day in recorded_days})
    return {"lookback_days": days, "cutoff": cutoff.isoformat(),
            "legacy_valid": legacy_evaluation_error is None,
            "legacy_evaluation_error": legacy_evaluation_error,
            "legacy_provenance": {"archive": str(LEGACY_ARCHIVE), "member": LEGACY_MEMBER,
                                  "source_sha256": LEGACY_SOURCE_SHA256,
                                  "baseline_lookback_hours": 48,
                                  "comparative_lookback_days": days,
                                  "adaptations": ["AST function only, no archive module setup",
                                                  "AM tag lookup replaced by included tag ID",
                                                  "Missing next date neutralized in both paths",
                                                  "Tracker snapshot supplied as pandas columns",
                                                  "Archive date-only API cutoff preserved"]},
            "legacy_selected": [{"tag": tag, "schedule_id": int(item.schedule_id),
                                 "launched_date": item.launched_date}
                                for tag, item in legacy.items()],
            "current_selected": [{"execution_key": key, **asdict(item)}
                                 for key, item in current.items()],
            "legacy_tags": len(legacy) if legacy_evaluation_error is None else None,
            "current_executions": len(current),
            "current_tags": len({item.tag for item in current.values()}),
            "legacy_schedule_requests_replayed": legacy_client.calls,
            "current_schedule_requests_replayed": current_client.calls,
            "both_tag_schedule_pairs": (len(legacy_pairs & current_pairs)
                                        if legacy_evaluation_error is None else None),
            "legacy_only": (sorted(legacy_pairs - current_pairs)
                            if legacy_evaluation_error is None else None),
            "current_only": details if legacy_evaluation_error is None else None,
            "adaptations": adaptations}


def capture() -> dict:
    """Read one repeatable-read DB snapshot and capture broad schedule pages once."""
    connection = connect()
    try:
        connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
        anchor = latest_tracker_pull_date(connection)
        # Legacy truncates the schedule API cutoff to its date, even when the
        # tracker anchor carries time. Capture that entire lower-bound day.
        cutoff = (anchor - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
        with connection.cursor() as cursor:
            cursor.execute("SELECT schedule_id, scan_start_date, data_pull_date "
                           "FROM was_daily_report_tracker "
                           "WHERE data_pull_date >= %s AND schedule_id IS NOT NULL",
                           (cutoff.date(),))
            rows = [[int(row[0]), row[1].isoformat() if row[1] else None,
                     row[2].isoformat() if row[2] else None] for row in cursor.fetchall()]
    finally:
        connection.close()
    client = create_qualys_client()
    records = []
    offset = 1
    calls = 0
    while True:
        response = client.request(QualysRequest(
            endpoint="/search/was/wasscanschedule",
            payload=qualys_scans.build_schedule_search_payload(cutoff, offset),
            http_method="POST"))
        root = qualys_scans.parse_xml(response, "comparison schedule capture")
        records.extend(etree.tostring(item, encoding="unicode")
                       for item in root.findall("./data/WasScanSchedule"))
        calls += 1
        count = qualys_scans.response_count(root)
        if not qualys_scans.response_has_more_records(root):
            break
        if count < 1:
            raise RuntimeError("Schedule page did not advance.")
        offset += count
    return {"anchor": anchor.isoformat(), "tracker_rows": rows,
            "schedules": records, "capture_schedule_requests": calls,
            "captured_at": datetime.now(timezone.utc).isoformat()}


def save_private(path: Path, value: dict) -> None:
    """Create a new restrictive local artifact, never overwrite an existing file."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2)


def main() -> None:
    """Capture or reuse inputs and write schedule-only comparison evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, help="Replay existing local snapshot offline")
    arguments = parser.parse_args()
    snapshot = json.loads(arguments.snapshot.read_text()) if arguments.snapshot else capture()
    if not arguments.snapshot:
        save_private(arguments.output.with_suffix(".snapshot.json"), snapshot)
    results = {"scope": "schedule selection only; NOT report counts or full scan parity",
               "capture_schedule_requests": snapshot["capture_schedule_requests"],
               "comparisons": [compare(snapshot, days) for days in (2, 3)]}
    save_private(arguments.output, results)
    for result in results["comparisons"]:
        print("{} days: legacy {} tags; current {} executions / {} tags; shared {} pairs".format(
            result["lookback_days"], result["legacy_tags"], result["current_executions"],
            result["current_tags"], result["both_tag_schedule_pairs"]))


if __name__ == "__main__":
    main()

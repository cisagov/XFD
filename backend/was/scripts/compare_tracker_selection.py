"""Compare schedule selection only, without tracker writes or report generation.

The checked-in legacy function is AST-extracted to avoid module import effects.
AM tag lookups are replaced with included schedule tag IDs. Missing next-launch
dates receive a neutral value in BOTH paths: this isolates candidate selection,
not ad-hoc lookup success. No scan-search or final report parity is claimed.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unicodedata
from zoneinfo import ZoneInfo

from lxml import etree
from lxml.builder import E
from lxml.objectify import fromstring

from was_reports.data.daily_report_tracker import latest_tracker_pull_date
from was_reports.qualys.qualys_client import QualysRequest, create_qualys_client
from was_reports.tracker import qualys_scans
from was_reports.utils.database import connect

LEGACY_ROOT = Path(__file__).resolve().parents[1] / "update_tracker/update_tracker"
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
    path = LEGACY_ROOT / "utils/qualys_api_search/search_schedules.py"
    tree = ast.parse(path.read_text())
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "search_schedules"]
    if len(functions) != 1:
        raise RuntimeError("Expected exactly one legacy search_schedules function.")
    module = ast.Module(body=functions, type_ignores=[])
    exec(compile(module, str(path), "exec"), namespace)
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


def compare(snapshot: dict, days: int) -> dict:
    """Replay both selectors with equal cutoffs and recent tracker identity sets."""
    anchor = datetime.fromisoformat(snapshot["anchor"])
    cutoff = anchor - timedelta(days=days)
    previous = {int(row[0]) for row in snapshot["tracker_rows"]
                if row[2] >= cutoff.date().isoformat()}
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
                 "PREVIOUS_IDS": previous, "make_stakeholder_info": legacy_name,
                 "get_tag_id": tag_ids.__getitem__, "Stakeholder": stakeholder,
                 "sys": sys, "log_exception": lambda **kwargs: None}
    with redirect_stdout(io.StringIO()):
        legacy = load_legacy_function(namespace)()
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
        recorded_days = sorted({row[1] for row in snapshot["tracker_rows"]
                                if row[0] == item.schedule_id and row[1] is not None
                                and row[2] >= cutoff.date().isoformat()})
        launch_day = datetime.fromisoformat(item.launched_date.replace("Z", "+00:00"))
        eastern_day = launch_day.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        details.append({"tag": item.tag, "schedule_id": item.schedule_id,
                        "launch_day_eastern": eastern_day, "recorded_scan_days": recorded_days,
                        "legacy_excluded_schedule_id": item.schedule_id in previous,
                        "last_scan_status": statuses.get(item.schedule_id),
                        "legacy_kept_other_schedule_for_tag": item.tag in legacy,
                        "same_scan_day_recorded": eastern_day in recorded_days})
    return {"lookback_days": days, "cutoff": cutoff.isoformat(),
            "legacy_tags": len(legacy), "current_executions": len(current),
            "current_tags": len({item.tag for item in current.values()}),
            "legacy_schedule_requests_replayed": legacy_client.calls,
            "current_schedule_requests_replayed": current_client.calls,
            "both_tag_schedule_pairs": len(legacy_pairs & current_pairs),
            "legacy_only": sorted(legacy_pairs - current_pairs),
            "current_only": details, "adaptations": adaptations}


def capture() -> dict:
    """Read one repeatable-read DB snapshot and capture broad schedule pages once."""
    connection = connect()
    try:
        connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
        anchor = latest_tracker_pull_date(connection)
        cutoff = anchor - timedelta(days=3)
        with connection.cursor() as cursor:
            cursor.execute("SELECT schedule_id, scan_start_date, data_pull_date "
                           "FROM was_daily_report_tracker "
                           "WHERE data_pull_date >= %s AND schedule_id IS NOT NULL",
                           (cutoff.date(),))
            rows = [[int(row[0]), row[1].isoformat() if row[1] else None,
                     row[2].isoformat()] for row in cursor.fetchall()]
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

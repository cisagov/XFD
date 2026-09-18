"""Convert and import legacy WAS daily tracker workbooks."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass, fields
from datetime import date, datetime
import hashlib
from itertools import chain
import json
from pathlib import Path
from typing import Callable, Iterator, Sequence, TYPE_CHECKING

# Third-Party Libraries
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from psycopg2.extras import execute_values

# First-Party Libraries
from was_reports.data.daily_report_tracker import DailyReportTrackerRow
from was_reports.utils.database import close, connect

if TYPE_CHECKING:
    from psycopg2.extensions import connection


WORKBOOK_HEADERS = (
    "DataPullDate",
    "Tag",
    "Scan Name",
    "Assignee",
    "Status",
    "Result",
    "Report Sent Date",
    "Report/Scan Notes",
    "Scan Start Date",
    "Next Scan Date",
    "POC",
    "POC Email",
    "Customer Notes",
    "NWS",
    "Template",
    "Recent NWS",
    "Remove NWS",
    "Password",
    "Schedule ID",
    "Qualys Error",
)

DATABASE_COLUMNS = (
    "data_pull_date",
    "tag",
    "scan_name",
    "assignee_id",
    "assignee",
    "status",
    "result",
    "report_sent_date",
    "report_scan_notes",
    "scan_start_date",
    "next_scan_date",
    "poc",
    "poc_email",
    "customer_notes",
    "nws",
    "template",
    "recent_nws",
    "remove_nws",
    "legacy_password",
    "schedule_id",
    "scan_execution_key",
    "qualys_error",
    "assignee_email_status",
)

FINGERPRINT_FIELDS = tuple(
    field.name
    for field in fields(DailyReportTrackerRow)
    if field.name
    in {
        "data_pull_date",
        "tag",
        "scan_name",
        "assignee",
        "status",
        "result",
        "report_sent_date",
        "report_scan_notes",
        "scan_start_date",
        "next_scan_date",
        "poc",
        "poc_email",
        "customer_notes",
        "nws",
        "template",
        "recent_nws",
        "remove_nws",
        "legacy_password",
        "schedule_id",
        "qualys_error",
    }
)

IMPORT_UPDATE_COLUMNS = tuple(
    column
    for column in DATABASE_COLUMNS
    if column not in {"scan_execution_key", "assignee_email_status"}
)

TrackerImportKey = tuple[str, ...]


@dataclass(frozen=True)
class TrackerImportResult:
    """Summary counts for one daily tracker workbook import."""

    source_rows: int
    inserted_rows: int
    updated_rows: int
    workbook_duplicates: int
    database_duplicates: int
    blank_rows: int
    unknown_assignees: tuple[str, ...]


StatusCallback = Callable[[str], None]


def report_status(callback: StatusCallback | None, message: str) -> None:
    """Send one import progress message when status reporting is enabled."""
    if callback is not None:
        callback(message)


def normalized_text(value: object) -> str | None:
    """Return trimmed cell text or None for an empty cell."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def tracker_date(value: object, field_name: str) -> date | None:
    """Convert one supported workbook date value to a date."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        converted_value = from_excel(value)
        if isinstance(converted_value, datetime):
            return converted_value.date()
        if isinstance(converted_value, date):
            return converted_value

    text = str(value).strip()
    for date_format in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError as error:
        raise ValueError(
            "{} contains unsupported date value '{}'.".format(field_name, text)
        ) from error


def schedule_identifier(value: object) -> int | None:
    """Convert one workbook schedule ID to an integer."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError("Schedule ID contains a Boolean value.")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("Schedule ID contains a non-integer value.")
        return int(value)
    try:
        return int(str(value).strip())
    except ValueError as error:
        raise ValueError("Schedule ID contains a non-integer value.") from error


def append_legacy_report_marker(notes: str | None, marker: str) -> str:
    """Preserve a non-date legacy report marker in tracker notes."""
    marker_note = "Legacy Report Sent Date value: {}".format(marker)
    if notes:
        return "{}\n{}".format(notes, marker_note)
    return marker_note


def workbook_values_to_row(values: Sequence[object]) -> DailyReportTrackerRow:
    """Convert one workbook row to the Postgres tracker representation."""
    if len(values) != len(WORKBOOK_HEADERS):
        raise ValueError("Tracker workbook row has an unexpected column count.")

    report_notes = normalized_text(values[7])
    report_sent_date = None
    report_sent_value = normalized_text(values[6])
    if report_sent_value:
        try:
            report_sent_date = tracker_date(report_sent_value, "Report Sent Date")
        except ValueError:
            report_notes = append_legacy_report_marker(
                report_notes,
                report_sent_value,
            )

    return DailyReportTrackerRow(
        data_pull_date=tracker_date(values[0], "DataPullDate"),
        tag=normalized_text(values[1]),
        scan_name=normalized_text(values[2]),
        assignee=normalized_text(values[3]),
        status=normalized_text(values[4]),
        result=normalized_text(values[5]),
        report_sent_date=report_sent_date,
        report_scan_notes=report_notes,
        scan_start_date=tracker_date(values[8], "Scan Start Date"),
        next_scan_date=tracker_date(values[9], "Next Scan Date"),
        poc=normalized_text(values[10]),
        poc_email=normalized_text(values[11]),
        customer_notes=normalized_text(values[12]),
        nws=normalized_text(values[13]),
        template=normalized_text(values[14]),
        recent_nws=normalized_text(values[15]),
        remove_nws=normalized_text(values[16]),
        legacy_password=normalized_text(values[17]),
        schedule_id=schedule_identifier(values[18]),
        qualys_error=normalized_text(values[19]),
    )


def fingerprint_value(value: object) -> object:
    """Return a stable JSON value for one tracker field."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def tracker_fingerprint(row: DailyReportTrackerRow) -> str:
    """Return a deterministic fingerprint for one converted tracker row."""
    values = [
        fingerprint_value(getattr(row, field_name))
        for field_name in FINGERPRINT_FIELDS
    ]
    serialized_values = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized_values).hexdigest()


def tracker_import_key(row: DailyReportTrackerRow) -> TrackerImportKey:
    """Identify one imported scan execution using the best workbook fields."""
    if row.schedule_id is not None and row.scan_start_date is not None:
        return (
            "schedule-execution",
            str(row.schedule_id),
            row.scan_start_date.isoformat(),
        )
    return ("fingerprint", tracker_fingerprint(row))


def legacy_scan_execution_key(
    row: DailyReportTrackerRow,
    fingerprint: str,
) -> str:
    """Return a stable execution key for a newly imported tracker row."""
    import_key = tracker_import_key(row)
    if import_key[0] == "schedule-execution":
        return "legacy-import:{}:{}".format(import_key[1], import_key[2])
    return "legacy-import:{}".format(fingerprint)


def validate_headers(values: Sequence[object]) -> None:
    """Require the known tracker headers and permit only blank trailing cells."""
    actual_headers = tuple(normalized_text(value) for value in values)
    expected_headers = tuple(WORKBOOK_HEADERS)
    if actual_headers[: len(expected_headers)] != expected_headers:
        raise ValueError("Workbook headers do not match the WAS daily tracker.")
    if any(actual_headers[len(expected_headers) :]):
        raise ValueError("Workbook contains unexpected columns after Qualys Error.")


def read_workbook_rows(input_path: Path) -> Iterator[tuple[int, Sequence[object]]]:
    """Yield nonblank workbook rows after validating the first worksheet."""
    if not input_path.is_file():
        raise ValueError("Tracker workbook does not exist: {}".format(input_path))
    workbook = load_workbook(input_path, read_only=True, data_only=True)
    try:
        worksheet = workbook.active
        rows = worksheet.iter_rows(values_only=True)
        try:
            header_values = next(rows)
        except StopIteration as error:
            raise ValueError("Tracker workbook is empty.") from error
        validate_headers(header_values)
        for row_number, values in enumerate(rows, 2):
            source_values = values[: len(WORKBOOK_HEADERS)]
            if not any(normalized_text(value) for value in source_values):
                yield row_number, ()
                continue
            yield row_number, source_values
    finally:
        workbook.close()


def existing_tracker_rows(
    conn: connection,
) -> dict[TrackerImportKey, tuple[int, ...]]:
    """Return stored tracker IDs grouped by workbook scan execution."""
    query = """
        SELECT
            id, data_pull_date, tag, scan_name, assignee, status, result,
            report_sent_date, report_scan_notes, scan_start_date,
            next_scan_date, poc, poc_email, customer_notes, nws, template,
            recent_nws, remove_nws, legacy_password, schedule_id, qualys_error
        FROM was_daily_report_tracker
        WHERE scan_execution_key LIKE 'legacy-import:%'
    """
    tracker_ids: dict[TrackerImportKey, list[int]] = {}
    with conn.cursor() as cursor:
        cursor.execute(query)
        while True:
            rows = cursor.fetchmany(1000)
            if not rows:
                break
            for values in rows:
                row = workbook_values_to_row(values[1:])
                tracker_ids.setdefault(tracker_import_key(row), []).append(
                    int(values[0])
                )
    duplicate_keys = [
        import_key
        for import_key, identifiers in tracker_ids.items()
        if len(identifiers) > 1
    ]
    if duplicate_keys:
        raise ValueError(
            "Existing legacy tracker duplicates require reconciliation before "
            "import. Found {} duplicated import execution key(s).".format(
                len(duplicate_keys)
            )
        )
    return {
        import_key: tuple(identifiers)
        for import_key, identifiers in tracker_ids.items()
    }


def assignee_identifiers(conn: connection) -> dict[str, int]:
    """Return assignee IDs keyed by normalized stored name."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, name FROM was_assignees")
        rows = cursor.fetchall()
    return {str(name).strip().casefold(): int(identifier) for identifier, name in rows}


def database_values(
    row: DailyReportTrackerRow,
    assignee_id: int | None,
    fingerprint: str,
) -> tuple[object, ...]:
    """Return insert values for one converted tracker row."""
    return (
        row.data_pull_date,
        row.tag,
        row.scan_name,
        assignee_id,
        row.assignee,
        row.status,
        row.result,
        row.report_sent_date,
        row.report_scan_notes,
        row.scan_start_date,
        row.next_scan_date,
        row.poc,
        row.poc_email,
        row.customer_notes,
        row.nws,
        row.template,
        row.recent_nws,
        row.remove_nws,
        row.legacy_password,
        row.schedule_id,
        legacy_scan_execution_key(row, fingerprint),
        row.qualys_error,
        "held",
    )


def insert_converted_rows(
    conn: connection,
    rows: Sequence[tuple[object, ...]],
    status_callback: StatusCallback | None = None,
) -> int:
    """Insert rows, atomically overwriting a concurrently matched import."""
    if not rows:
        return 0
    conflict_assignments = []
    for column in IMPORT_UPDATE_COLUMNS:
        if column == "report_sent_date":
            conflict_assignments.append(
                "report_sent_date = COALESCE(EXCLUDED.report_sent_date, "
                "was_daily_report_tracker.report_sent_date)"
            )
        else:
            conflict_assignments.append("{} = EXCLUDED.{}".format(column, column))
    query = """
        INSERT INTO was_daily_report_tracker ({})
        VALUES %s
        ON CONFLICT (scan_execution_key)
            WHERE scan_execution_key IS NOT NULL
        DO UPDATE SET {}, updated_at = NOW()
        RETURNING id
    """.format(
        ", ".join(DATABASE_COLUMNS),
        ", ".join(conflict_assignments),
    )
    inserted_count = 0
    with conn.cursor() as cursor:
        for start_index in range(0, len(rows), 500):
            inserted_rows = execute_values(
                cursor,
                query,
                rows[start_index : start_index + 500],
                page_size=500,
                fetch=True,
            )
            inserted_count += len(inserted_rows)
            processed_count = min(start_index + 500, len(rows))
            if processed_count % 5000 == 0 or processed_count == len(rows):
                report_status(
                    status_callback,
                    "Tracker import: staged {} of {} new rows.".format(
                        processed_count,
                        len(rows),
                    ),
                )
    return inserted_count


def update_converted_rows(
    conn: connection,
    rows: Sequence[tuple[object, ...]],
    status_callback: StatusCallback | None = None,
) -> int:
    """Overwrite workbook-controlled fields on matching tracker rows."""
    if not rows:
        return 0
    assignments = []
    for column in IMPORT_UPDATE_COLUMNS:
        if column == "report_sent_date":
            assignments.append(
                "report_sent_date = COALESCE(imported.report_sent_date, "
                "tracker.report_sent_date)"
            )
        else:
            assignments.append(
                "{} = imported.{}".format(column, column)
            )
    query = """
        UPDATE was_daily_report_tracker AS tracker
        SET {}, updated_at = NOW()
        FROM (VALUES %s) AS imported ({}, tracker_id)
        WHERE tracker.id = imported.tracker_id
        RETURNING tracker.id
    """.format(", ".join(assignments), ", ".join(IMPORT_UPDATE_COLUMNS))
    updated_count = 0
    with conn.cursor() as cursor:
        for start_index in range(0, len(rows), 500):
            updated_rows = execute_values(
                cursor,
                query,
                rows[start_index : start_index + 500],
                page_size=500,
                fetch=True,
            )
            updated_count += len(updated_rows)
            processed_count = min(start_index + 500, len(rows))
            if processed_count % 5000 == 0 or processed_count == len(rows):
                report_status(
                    status_callback,
                    "Tracker import: staged {} of {} matching rows for "
                    "overwrite.".format(processed_count, len(rows)),
                )
    return updated_count


def import_tracker_workbook(
    input_path: Path,
    status_callback: StatusCallback | None = None,
) -> TrackerImportResult:
    """Convert and atomically insert or overwrite daily tracker workbook rows."""
    report_status(status_callback, "Tracker import: opening and validating workbook.")
    row_iterator = read_workbook_rows(input_path)
    try:
        first_row = next(row_iterator)
    except StopIteration:
        first_row = None
    report_status(status_callback, "Tracker import: workbook headers are valid.")
    report_status(
        status_callback,
        "Tracker import: connecting to Postgres and loading duplicate checks.",
    )
    try:
        conn = connect()
    except Exception:
        row_iterator.close()
        raise
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "LOCK TABLE was_daily_report_tracker IN SHARE ROW EXCLUSIVE MODE"
            )
        existing_rows_by_key = existing_tracker_rows(conn)
        report_status(
            status_callback,
            "Tracker import: loaded {} existing tracker execution keys.".format(
                len(existing_rows_by_key)
            ),
        )
        assignees = assignee_identifiers(conn)
        report_status(
            status_callback,
            "Tracker import: loaded {} assignee mappings.".format(len(assignees)),
        )
        report_status(status_callback, "Tracker import: converting workbook rows.")
        converted_by_key: dict[
            TrackerImportKey,
            tuple[DailyReportTrackerRow, str],
        ] = {}
        unknown_assignees: set[str] = set()
        source_rows = 0
        workbook_duplicates = 0
        blank_rows = 0

        workbook_rows = row_iterator
        if first_row is not None:
            workbook_rows = chain((first_row,), row_iterator)
        for row_number, values in workbook_rows:
            if not values:
                blank_rows += 1
                continue
            source_rows += 1
            try:
                row = workbook_values_to_row(values)
            except ValueError as error:
                raise ValueError("Workbook row {}: {}".format(row_number, error)) from error
            if source_rows % 5000 == 0:
                report_status(
                    status_callback,
                    "Tracker import: processed {} nonblank workbook rows.".format(
                        source_rows
                    ),
                )
            fingerprint = tracker_fingerprint(row)
            import_key = tracker_import_key(row)
            if import_key in converted_by_key:
                workbook_duplicates += 1
            converted_by_key[import_key] = (row, fingerprint)

        converted_rows: list[tuple[object, ...]] = []
        rows_to_update: list[tuple[object, ...]] = []
        updated_import_keys = 0
        for import_key, (row, fingerprint) in converted_by_key.items():
            assignee_id = None
            if row.assignee:
                assignee_id = assignees.get(row.assignee.casefold())
                if assignee_id is None:
                    unknown_assignees.add(row.assignee)
            values = database_values(row, assignee_id, fingerprint)
            existing_ids = existing_rows_by_key.get(import_key, ())
            if existing_ids:
                updated_import_keys += 1
                update_values = tuple(
                    values[DATABASE_COLUMNS.index(column)]
                    for column in IMPORT_UPDATE_COLUMNS
                )
                rows_to_update.extend(
                    update_values + (tracker_id,) for tracker_id in existing_ids
                )
            else:
                converted_rows.append(values)

        report_status(
            status_callback,
            "Tracker import: conversion complete; {} new rows and {} matching "
            "rows are ready to stage in Postgres.".format(
                len(converted_rows),
                updated_import_keys,
            ),
        )
        updated_physical_rows = update_converted_rows(
            conn,
            rows_to_update,
            status_callback=status_callback,
        )
        if updated_physical_rows != len(rows_to_update):
            raise RuntimeError("A matching tracker row disappeared during import.")
        inserted_rows = insert_converted_rows(
            conn,
            converted_rows,
            status_callback=status_callback,
        )
        database_duplicates = len(converted_rows) - inserted_rows
        report_status(
            status_callback,
            "Tracker import: committing the complete transaction.",
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        close(conn)

    return TrackerImportResult(
        source_rows=source_rows,
        inserted_rows=inserted_rows,
        updated_rows=updated_import_keys,
        workbook_duplicates=workbook_duplicates,
        database_duplicates=database_duplicates,
        blank_rows=blank_rows,
        unknown_assignees=tuple(sorted(unknown_assignees, key=str.casefold)),
    )

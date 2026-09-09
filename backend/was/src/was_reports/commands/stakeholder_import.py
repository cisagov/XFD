"""Prepare and import WAS stakeholder CSV records."""

# Standard Python Libraries
import argparse
import csv
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

# Third-Party Libraries
from psycopg2.extras import execute_values

# First-Party Libraries
from was_reports.utils.database import close, connect
from was_reports.utils.logging_config import configure_logging


SOURCE_TO_DATABASE = (
    ("Tag", "tag"),
    ("Customer Name", "customer_name"),
    ("Comments", "comments"),
    ("Location Notes", "location_notes"),
    ("CI Type", "ci_type"),
    ("Testing Sector", "testing_sector"),
    ("Subtype", "subtype"),
    ("Distro Email", "distro_email"),
    ("Tech POC Email", "tech_poc_email"),
    ("WAS Report POC", "was_report_poc"),
    ("Frequency", "frequency"),
    ("# of Web Apps", "num_web_apps"),
    ("# of Web Apps Last Updated", "web_apps_last_updated"),
    ("Last Scanned", "last_scanned"),
    ("Next Scheduled", "next_scheduled"),
    ("Onboarding Date", "onboarding_date"),
    ("Parent Tag", "parent_tag"),
    ("Ticket", "ticket"),
    ("Elections", "elections"),
    ("FCEB", "fceb"),
    ("Manual Report", "manual_report"),
    ("Retired", "retired"),
    ("State", "state"),
    ("Report Password", "report_password"),
)
EXPECTED_SOURCE_HEADERS = (
    "Tag",
    "# of Web Apps",
    "# of Web Apps Last Updated",
    "CI Type",
    "Comments",
    "Customer Name",
    "Distro Email",
    "Elections",
    "FCEB",
    "Frequency",
    "Last Scanned",
    "Location Notes",
    "Manual Report",
    "Next Scheduled",
    "Onboarding Date",
    "Parent Tag",
    "Report Password",
    "Retired",
    "State",
    "Subtype",
    "Tech POC Email",
    "Testing Sector",
    "Ticket",
    "WAS Report POC",
)
BOOLEAN_SOURCE_HEADERS = frozenset({"Elections", "FCEB", "Manual Report", "Retired"})
BOOLEAN_DATABASE_COLUMNS = frozenset({"elections", "fceb", "manual_report", "retired"})
INTEGER_DATABASE_COLUMNS = frozenset(
    {
        "num_web_apps",
        "web_apps_last_updated",
        "last_scanned",
        "next_scheduled",
        "onboarding_date",
    }
)
DEFAULT_NULL_TOKEN = "\\N"


def read_source_rows(input_path: Path) -> list[dict[str, str]]:
    """Read and validate the complete source CSV before any output or insert."""
    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != EXPECTED_SOURCE_HEADERS:
            raise ValueError("CSV headers or column order do not match the export.")
        rows = list(reader)

    tag_rows: dict[str, int] = {}
    for row_number, row in enumerate(rows, 2):
        if None in row:
            raise ValueError("Row {} contains extra CSV fields.".format(row_number))
        tag = row["Tag"].strip()
        if not tag:
            raise ValueError("Row {} has a blank stakeholder tag.".format(row_number))
        if tag in tag_rows:
            raise ValueError(
                "Duplicate stakeholder tag at rows {} and {}.".format(
                    tag_rows[tag], row_number
                )
            )
        tag_rows[tag] = row_number

    for row_number, row in enumerate(rows, 2):
        parent_tag = row["Parent Tag"].strip()
        if parent_tag and parent_tag not in tag_rows:
            raise ValueError(
                "Row {} references missing parent tag {}.".format(
                    row_number, parent_tag
                )
            )
    return rows


def hierarchy_depths(rows: list[dict[str, str]]) -> dict[str, int]:
    """Calculate hierarchy depth and reject circular parent relationships."""
    parents = {row["Tag"].strip(): row["Parent Tag"].strip() for row in rows}
    depths: dict[str, int] = {}

    def calculate_depth(tag: str, active_tags: set[str]) -> int:
        """Calculate one tag depth while detecting circular references."""
        if tag in depths:
            return depths[tag]
        if tag in active_tags:
            raise ValueError("Circular parent relationship includes {}.".format(tag))
        parent_tag = parents[tag]
        if not parent_tag:
            depths[tag] = 0
        else:
            depths[tag] = calculate_depth(parent_tag, active_tags | {tag}) + 1
        return depths[tag]

    for stakeholder_tag in parents:
        calculate_depth(stakeholder_tag, set())
    return depths


def normalize_value(header: str, value: str, null_token: str) -> str:
    """Convert blank values and normalize supported Boolean values."""
    if not value.strip():
        if header in BOOLEAN_SOURCE_HEADERS:
            return "FALSE"
        return null_token
    if header in BOOLEAN_SOURCE_HEADERS:
        normalized = value.strip().lower()
        if normalized not in {"true", "false"}:
            raise ValueError("{} contains an unsupported Boolean value.".format(header))
        return normalized.upper()
    if value == null_token:
        raise ValueError("A source value conflicts with the configured NULL token.")
    return value


def prepare_rows(
    source_rows: list[dict[str, str]], null_token: str
) -> list[tuple[str, ...]]:
    """Return normalized rows in database order with parents before children."""
    depths = hierarchy_depths(source_rows)
    ordered_rows = sorted(
        enumerate(source_rows),
        key=lambda item: (depths[item[1]["Tag"].strip()], item[0]),
    )
    return [
        tuple(
            normalize_value(source_column, row[source_column], null_token)
            for source_column, _ in SOURCE_TO_DATABASE
        )
        for _, row in ordered_rows
    ]


def write_prepared_csv(prepared_rows: list[tuple[str, ...]], output_path: Path) -> None:
    """Write a prepared CSV atomically with owner-only file permissions."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=".was-stakeholder-import-",
            suffix=".csv",
            dir=str(output_path.parent),
            delete=False,
        ) as csv_file:
            temporary_path = Path(csv_file.name)
            os.chmod(temporary_path, 0o600)
            writer = csv.writer(csv_file)
            writer.writerow([database for _, database in SOURCE_TO_DATABASE])
            writer.writerows(prepared_rows)
        os.replace(temporary_path, output_path)
        os.chmod(output_path, 0o600)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def database_value(column: str, value: str, null_token: str) -> object:
    """Convert one prepared CSV value into its PostgreSQL parameter type."""
    if value == null_token:
        return None
    if column in BOOLEAN_DATABASE_COLUMNS:
        return value == "TRUE"
    if column in INTEGER_DATABASE_COLUMNS:
        try:
            return int(value)
        except ValueError as error:
            raise ValueError(
                "{} contains a non-integer value.".format(column)
            ) from error
    return value


def import_prepared_rows(
    prepared_rows: list[tuple[str, ...]], null_token: str
) -> tuple[int, int]:
    """Insert new stakeholders atomically without changing existing records."""
    if not prepared_rows:
        return 0, 0
    columns = [database for _, database in SOURCE_TO_DATABASE]
    database_rows = [
        tuple(
            database_value(column, value, null_token)
            for column, value in zip(columns, row)
        )
        for row in prepared_rows
    ]
    query = """
        INSERT INTO was_stakeholders ({})
        VALUES %s
        ON CONFLICT (tag) DO NOTHING
        RETURNING tag
    """.format(
        ", ".join(columns)
    )

    conn = connect()
    try:
        with conn.cursor() as cursor:
            inserted_rows = execute_values(
                cursor,
                query,
                database_rows,
                page_size=500,
                fetch=True,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        close(conn)

    inserted_count = len(inserted_rows)
    return inserted_count, len(database_rows) - inserted_count


def prepare_stakeholder_csv(
    input_path: Path,
    output_path: Path,
    null_token: str = DEFAULT_NULL_TOKEN,
) -> list[tuple[str, ...]]:
    """Validate and prepare a stakeholder CSV for database import."""
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output paths must be different.")
    if not null_token:
        raise ValueError("The NULL token must not be empty.")
    source_rows = read_source_rows(input_path)
    prepared_rows = prepare_rows(source_rows, null_token)
    write_prepared_csv(prepared_rows, output_path)
    return prepared_rows


def parse_arguments(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse standalone CSV preparation arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--null-token", default=DEFAULT_NULL_TOKEN)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Prepare a normalized stakeholder import CSV without inserting it."""
    configure_logging()
    arguments = parse_arguments(argv)
    prepared_rows = prepare_stakeholder_csv(
        input_path=arguments.input,
        output_path=arguments.output,
        null_token=arguments.null_token,
    )
    print(
        "Prepared {} stakeholder rows at {}.".format(
            len(prepared_rows), arguments.output
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

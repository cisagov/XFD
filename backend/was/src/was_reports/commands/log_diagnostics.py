"""Summarize structured WAS batch logs without changing application state."""

# Standard Python Libraries
import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Iterable
from uuid import UUID


def batch_identifier(value: str) -> str:
    """Require a canonical UUID batch identifier."""
    try:
        return str(UUID(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Batch ID must be a UUID.") from error


def positive_limit(value: str) -> int:
    """Require a positive diagnostic output limit."""
    try:
        limit = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Limit must be a positive integer.") from error
    if limit < 1:
        raise argparse.ArgumentTypeError("Limit must be a positive integer.")
    return limit


def parse_args(argv=None):
    """Parse one read-only batch-log diagnostic request."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/output/logs/batches"),
        help="Root containing one directory per batch ID.",
    )
    parser.add_argument("--batch-id", type=batch_identifier)
    parser.add_argument("--latest", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("summary", "errors", "tag"),
        default="summary",
    )
    parser.add_argument("--tag")
    parser.add_argument("--limit", type=positive_limit, default=200)
    arguments = parser.parse_args(argv)
    if bool(arguments.batch_id) == bool(arguments.latest):
        parser.error("Specify exactly one of --batch-id or --latest.")
    if arguments.mode == "tag" and not (arguments.tag or "").strip():
        parser.error("Tag mode requires --tag.")
    if arguments.mode != "tag" and arguments.tag is not None:
        parser.error("--tag requires --mode tag.")
    return arguments


def latest_batch_directory(root: Path) -> Path:
    """Return the most recently modified canonical batch directory."""
    candidates = []
    if root.is_dir():
        for path in root.iterdir():
            if not path.is_dir():
                continue
            try:
                UUID(path.name)
                modified = path.stat().st_mtime
            except (ValueError, OSError):
                continue
            candidates.append((modified, path.name, path))
    if not candidates:
        raise ValueError("No structured WAS batch log directories were found.")
    return max(candidates)[2]


def resolve_batch_directory(root: Path, identifier: str | None) -> Path:
    """Resolve a canonical batch directory without permitting path traversal."""
    resolved_root = root.resolve()
    if identifier is None:
        return latest_batch_directory(resolved_root)
    path = resolved_root / str(UUID(identifier))
    if not path.is_dir():
        raise ValueError("No logs were found for batch {}.".format(identifier))
    return path


def read_records(batch_directory: Path) -> tuple[list[dict[str, object]], int]:
    """Read valid structured records and count malformed lines."""
    records = []
    malformed = 0
    for path in sorted(batch_directory.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            malformed += 1
            continue
        for line in lines:
            try:
                record = json.loads(line)
            except (TypeError, ValueError):
                malformed += 1
                continue
            if not isinstance(record, dict):
                malformed += 1
                continue
            record["log_file"] = path.name
            records.append(record)
    records.sort(
        key=lambda record: (
            str(record.get("time") or ""),
            str(record.get("role") or ""),
            int(record.get("line") or 0),
        )
    )
    return records, malformed


def _display_value(record: dict[str, object], name: str) -> str:
    """Return one compact printable diagnostic value."""
    value = str(record.get(name) or "-").replace("\n", " ").replace("\r", " ")
    return value[:4096]


def print_records(records: Iterable[dict[str, object]], limit: int) -> None:
    """Print the newest bounded records in a stable troubleshooting format."""
    available = list(records)
    selected = available[-limit:]
    for record in selected:
        print(
            "{} {} role={} worker={} phase={} tag={} tracker={} run={} "
            "event={} {}".format(
                _display_value(record, "time"),
                _display_value(record, "level"),
                _display_value(record, "role"),
                _display_value(record, "worker"),
                _display_value(record, "phase"),
                _display_value(record, "tag"),
                _display_value(record, "tracker_id"),
                _display_value(record, "report_run_id"),
                _display_value(record, "event"),
                _display_value(record, "message"),
            )
        )
    if len(selected) < len(available):
        print("Showing the newest {} matching records.".format(limit))


def print_summary(
    batch_directory: Path,
    records: list[dict[str, object]],
    malformed: int,
    limit: int,
) -> None:
    """Print batch counts followed by bounded actionable failures."""
    levels = Counter(_display_value(record, "level") for record in records)
    events = Counter(
        _display_value(record, "event")
        for record in records
        if _display_value(record, "event") != "-"
    )
    roles = Counter(_display_value(record, "role") for record in records)
    print("Batch ID: {}".format(batch_directory.name))
    print("Log directory: {}".format(batch_directory))
    print("Structured records: {}; malformed records: {}".format(len(records), malformed))
    print(
        "Levels: {}".format(
            ", ".join(
                "{}={}".format(name, count)
                for name, count in sorted(levels.items())
            ) or "none"
        )
    )
    print(
        "Roles: {}".format(
            ", ".join(
                "{}={}".format(name, count)
                for name, count in sorted(roles.items())
            ) or "none"
        )
    )
    print(
        "Events: {}".format(
            ", ".join(
                "{}={}".format(name, count)
                for name, count in sorted(events.items())
            ) or "none"
        )
    )
    failures = [
        record
        for record in records
        if _display_value(record, "level") in {"ERROR", "CRITICAL"}
    ]
    print("Error and critical records: {}".format(len(failures)))
    print_records(failures, limit)


def main(argv=None) -> int:
    """Run one read-only structured-log diagnostic."""
    arguments = parse_args(argv)
    batch_directory = resolve_batch_directory(
        arguments.root,
        arguments.batch_id,
    )
    records, malformed = read_records(batch_directory)
    if not records:
        plain_logs = sorted(path.name for path in batch_directory.glob("*.log*"))
        print("Batch ID: {}".format(batch_directory.name))
        print("No structured records were found.")
        if plain_logs:
            print("Plain logs: {}".format(", ".join(plain_logs)))
        return 1
    if arguments.mode == "summary":
        print_summary(batch_directory, records, malformed, arguments.limit)
        return 0
    if arguments.mode == "errors":
        selected = [
            record
            for record in records
            if _display_value(record, "level") in {"ERROR", "CRITICAL"}
        ]
    else:
        requested_tag = arguments.tag.strip().upper()
        selected = [
            record
            for record in records
            if _display_value(record, "tag").upper() == requested_tag
        ]
    print("Batch ID: {}".format(batch_directory.name))
    print("Matching records: {}; malformed records: {}".format(len(selected), malformed))
    print_records(selected, arguments.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

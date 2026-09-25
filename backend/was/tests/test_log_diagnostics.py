"""Tests for read-only structured batch-log diagnostics."""

# Standard Python Libraries
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

# First-Party Libraries
from was_reports.commands import log_diagnostics

BATCH_ID = "00000000-0000-0000-0000-000000000042"


def record(level: str, tag: str, event: str, message: str) -> dict[str, object]:
    """Return one structured diagnostic fixture."""
    return {
        "time": "2026-09-25T12:00:00+00:00",
        "level": level,
        "logger": "test",
        "source": "test.py",
        "line": 1,
        "message": message,
        "batch_id": BATCH_ID,
        "role": "worker",
        "worker": "1",
        "phase": "report_generation",
        "tag": tag,
        "tracker_id": 42,
        "report_run_id": 84,
        "event": event,
    }


class LogDiagnosticsTests(unittest.TestCase):
    """Verify deterministic, non-mutating troubleshooting output."""

    def make_batch(self, root: Path) -> Path:
        """Create one private batch fixture with valid and malformed events."""
        batch = root / BATCH_ID
        batch.mkdir()
        events = [
            record("INFO", "TAG1", "report_started", "started"),
            record("ERROR", "TAG1", "report_generation_failed", "failed safely"),
            record("WARNING", "TAG2", "qualys_retry", "retrying"),
        ]
        payload = "\n".join(json.dumps(event) for event in events)
        (batch / "worker-01.jsonl").write_text(
            payload + "\nnot-json\n", encoding="utf-8"
        )
        return batch

    def test_summary_groups_levels_events_and_errors(self) -> None:
        """Summarize a batch and print only actionable error details."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_batch(root)
            output = StringIO()
            with redirect_stdout(output):
                result = log_diagnostics.main(
                    ["--root", str(root), "--batch-id", BATCH_ID]
                )
        self.assertEqual(result, 0)
        self.assertIn("ERROR=1", output.getvalue())
        self.assertIn("report_generation_failed=1", output.getvalue())
        self.assertIn("Error and critical records: 1", output.getvalue())
        self.assertIn("malformed records: 1", output.getvalue())
        self.assertNotIn("retrying", output.getvalue())

    def test_error_and_tag_filters_are_exact(self) -> None:
        """Filter errors by level and tags by normalized exact identity."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_batch(root)
            errors = StringIO()
            with redirect_stdout(errors):
                log_diagnostics.main(
                    [
                        "--root", str(root), "--batch-id", BATCH_ID,
                        "--mode", "errors",
                    ]
                )
            tags = StringIO()
            with redirect_stdout(tags):
                log_diagnostics.main(
                    [
                        "--root", str(root), "--batch-id", BATCH_ID,
                        "--mode", "tag", "--tag", "tag2",
                    ]
                )
        self.assertIn("failed safely", errors.getvalue())
        self.assertNotIn("retrying", errors.getvalue())
        self.assertIn("retrying", tags.getvalue())
        self.assertNotIn("failed safely", tags.getvalue())

    def test_latest_ignores_non_uuid_directories(self) -> None:
        """Select only canonical batch directories for latest diagnostics."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "not-a-batch").mkdir()
            batch = self.make_batch(root)
            self.assertEqual(log_diagnostics.latest_batch_directory(root), batch)

    def test_batch_id_rejects_path_traversal(self) -> None:
        """Require UUID identities before joining a requested path."""
        with self.assertRaises(Exception):
            log_diagnostics.batch_identifier("../logs")


if __name__ == "__main__":
    unittest.main()

"""Tests for csv_utils.py."""
from __future__ import annotations

# Third-Party Libraries
import pytest
from xfd_api.utils import csv_utils


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("=1+1", "'=1+1"),
        ("  -2", "'  -2"),
        ("\t+SUM(A1:A2)", "'\t+SUM(A1:A2)"),
        ('@HYPERLINK("http://…")', '\'@HYPERLINK("http://…")'),
        (" normal", " normal"),
        ("'already-text", "'already-text"),  # leading apostrophe stays as-is
        (123, 123),  # numbers unchanged
        (None, None),
    ],
)
def test_sanitize_for_excel(raw, expected):
    """Test csv_utils.sanitize_strings_for_excel against various inputs."""
    assert csv_utils.sanitize_strings_for_excel(raw) == expected

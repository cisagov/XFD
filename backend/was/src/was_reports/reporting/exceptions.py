"""Stable report-processing exceptions safe for operational classification."""


class ReportXmlSizeLimitError(ValueError):
    """Indicate that a streamed Qualys XML report exceeds its disk limit."""

    def __init__(self, actual_bytes: int, maximum_bytes: int) -> None:
        """Store safe size diagnostics without retaining report contents."""
        self.actual_bytes = actual_bytes
        self.maximum_bytes = maximum_bytes
        super().__init__(
            "Qualys report XML size {} bytes exceeds the configured {} byte "
            "disk safety limit.".format(actual_bytes, maximum_bytes)
        )


class ReportXmlDiskSpaceError(OSError):
    """Indicate that streaming must stop to preserve free disk capacity."""


class ReportXmlUnsafeContentError(ValueError):
    """Indicate that downloaded XML contains a prohibited DTD declaration."""

"""Entry point. See OpenCTI-connector.md §7b for design, README.md for how to run this locally."""

# Standard Python Libraries
import sys

from .config import ConfigError
from .connector import VsVulnscanEnrichmentConnector

if __name__ == "__main__":
    try:
        connector = VsVulnscanEnrichmentConnector()
    except ConfigError as e:
        # Fail closed and loud (§10c) -- not a stack trace to dig through.
        print(f"[vs-vulnscan-enrichment] refusing to start: {e}", file=sys.stderr)
        sys.exit(1)

    # INTERNAL_ENRICHMENT connectors block on listen(), not schedule_iso() -- there's no
    # duration_period/watermark here, each invocation is triggered per-entity (§7b).
    connector.helper.listen(connector.process_message)

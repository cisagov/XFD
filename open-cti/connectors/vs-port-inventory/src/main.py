"""Entry point. See OpenCTI-connector.md §7c for design, README.md for how to run this locally."""

# Standard Python Libraries
import sys
import time

from .config import ConfigError
from .connector import VsPortInventoryConnector

if __name__ == "__main__":
    try:
        connector = VsPortInventoryConnector()
    except ConfigError as e:
        # Fail closed and loud (§10c/§9c) -- not a stack trace to dig through.
        print(f"[vs-port-inventory] refusing to start: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        connector.helper.schedule_iso(
            message_callback=connector.run,
            duration_period=connector.config.duration_period,
        )
    except KeyboardInterrupt:
        connector.helper.connector_logger.info("Stopping VS Port Inventory connector")
        connector.helper.stop()
        time.sleep(1)
        sys.exit(0)

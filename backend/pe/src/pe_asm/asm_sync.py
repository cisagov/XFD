"""A tool for gathering pe asm data.

Usage:
    pe-asm-sync PHASE [--log-level=LEVEL] [--orgs=ORGS]

Options:
  -h --help                         Show this message.
  -v --version                      Show version information.
  PHASE                             Which phase of the remote ASM Sync process to run. Valid
                                    values are "import_s3" or "enumerate". "import_s3" upserts the
                                    latest CyHy data from the S3 bucket. "enumerate" runs the part
                                    of the script that enumerates assets from that latest CyHy data.
  -l --log-level=LEVEL              If specified, then the log level will be set to
                                    the specified value.  Valid values are "debug", "info",
                                    "warning", "error", and "critical".
                                    [default: info]
  -o --orgs=ORGS                    The cyhy_db_name(s) of the organizations to collect data for.
                                    This option is only used for the SQS version of the ASM Sync.
                                    Org names must match the ID in the cyhy-db. E.g. DHS,DHS_ICE,DOC.
                                    [default: all]
"""

# Standard Python Libraries
import logging
import sys
from typing import Any, Dict

# Third-Party Libraries
import docopt
from pe_asm._version import __version__
from pe_asm.remote_step.asm_sync_remote import run_asm_sync_remote
from pe_asm.remote_step.asm_sync_remote_helpers.import_cyhy_from_s3 import (
    import_cyhy_from_s3,
)
import pe_reports
from schema import And, Schema, SchemaError, Use

# Setup logging
LOGGER = logging.getLogger(__name__)


def run_asm_sync(phase, orgs_list):
    """Run either the ASM Sync local or remote scripts."""
    if phase == "import_s3":
        # Import latest CyHy data from S3 and upsert into PE DB
        import_cyhy_from_s3()
    elif phase == "enumerate":
        # Enumerate the latest CyHy data that's been brought in from S3
        run_asm_sync_remote(orgs_list)
    else:
        LOGGER.error(
            'Unsupported ASM Sync phase, options are "import_s3" or "enumerate"'
        )


def main():
    """Set up logging and call the run_asm_sync function."""
    args: Dict[str, str] = docopt.docopt(__doc__, version=__version__)
    # Validate and convert arguments as needed
    schema: Schema = Schema(
        {
            "--log-level": And(
                str,
                Use(str.lower),
                lambda n: n in ("debug", "info", "warning", "error", "critical"),
                error="Possible values for --log-level are "
                + "debug, info, warning, error, and critical.",
            ),
            str: object,  # Don't care about other keys, if any
        }
    )
    try:
        validated_args: Dict[str, Any] = schema.validate(args)
    except SchemaError as err:
        # Exit because one or more of the arguments were invalid
        LOGGER.error(err, file=sys.stderr)
        sys.exit(1)
    # Assign validated arguments to variables
    log_level: str = validated_args["--log-level"]
    # Set up logging
    logging.basicConfig(
        filename=pe_reports.CENTRAL_LOGGING_FILE,
        filemode="a",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S",
        level=log_level.upper(),
    )
    # Run ASM Sync
    run_asm_sync(
        validated_args["PHASE"],
        validated_args["--orgs"],
    )
    # Stop logging and clean up
    logging.shutdown()

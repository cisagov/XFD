"""PE scan CLI (dnstwist only for now).

Usage:
    pe-source DATA_SOURCE [--log-level=LEVEL] [--orgs=ORG_LIST]

Arguments:
    DATA_SOURCE                     Source to collect data from. Valid value: "dnstwist".

Options:
    -h --help                       Show this message.
    -v --version                    Show version information.
    -l --log-level=LEVEL            Log level: debug, info, warning, error, critical.
                                    [default: info]
    -o --orgs=ORG_LIST              Comma-separated org cyhy_db_name values, DEMO, or all.
                                    [default: all]
"""

# Standard Python Libraries
import logging
import os
import sys
from typing import Any, Dict

# Third-Party Libraries
import docopt
from schema import And, Schema, SchemaError, Use

# cisagov Libraries
import pe_reports
from pe_source._version import __version__
from pe_source.dnstwistscript import run_dnstwist

LOGGER = logging.getLogger(__name__)


def run_pe_script(source, orgs_list):
    """Collect data from the source specified."""
    if source != "dnstwist":
        LOGGER.error("Unsupported scan type: %s", source)
        sys.exit(1)
    run_dnstwist(orgs_list)


def main():
    """Set up logging and run the requested scan."""
    args: Dict[str, str] = docopt.docopt(__doc__, version=__version__)
    schema: Schema = Schema(
        {
            "--log-level": And(
                str,
                Use(str.lower),
                lambda n: n in ("debug", "info", "warning", "error", "critical"),
                error="Possible values for --log-level are "
                + "debug, info, warning, error, and critical.",
            ),
            str: object,
        }
    )
    try:
        validated_args: Dict[str, Any] = schema.validate(args)
    except SchemaError as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        filename=pe_reports.CENTRAL_LOGGING_FILE,
        filemode="a",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        level=validated_args["--log-level"].upper(),
    )
    if os.getenv("PE_LOG_TO_STDERR", "").lower() in {"1", "true", "yes"}:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%m/%d/%Y %H:%M:%S",
            )
        )
        logging.getLogger().addHandler(stderr_handler)

    run_pe_script(validated_args["DATA_SOURCE"], validated_args["--orgs"])
    logging.shutdown()


if __name__ == "__main__":
    main()

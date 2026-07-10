"""PE scan CLI (dnstwist only for now).

Usage:
    pe-source DATA_SOURCE [--log-level=LEVEL] [--orgs=ORG_LIST]

Arguments:
    DATA_SOURCE  Source to collect data from. Valid value: "dnstwist", "shodan".

Options:
    -h --help                       Show this message.
    -v --version                    Show version information.
    -l --log-level=LEVEL            Log level: debug, info, warning, error, critical.
                                    [default: info]
    -o --orgs=ORG_LIST  Comma-separated org cyhy_db_name values, DEMO, or all.
                         [default: all]
"""

# Standard Python Libraries
import logging
import os
import sys
from typing import Any, Dict

# Third-Party Libraries
import docopt
import pe_reports
from pe_source._version import __version__
from pe_source.dnstwist import run_dnstwist
from pe_source.shodan.shodan_script import Get_shodan
from schema import And, Schema, SchemaError, Use

LOGGER = logging.getLogger(__name__)


def run_pe_script(source, orgs_list):
    """Collect data from the source specified."""
    # Run the specified scan
    if source == "dnstwist":
        run_dnstwist(orgs_list)
    elif source == "shodan":
        shodan = Get_shodan(orgs_list)
        shodan.run_shodan()
    else:
        LOGGER.error("Unsupported scan type: %s", source)
        sys.exit(1)


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
        sys.stderr.write("{}\n".format(err))
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

"""PE scan CLI.

Usage:
    pe-source DATA_SOURCE [--log-level=LEVEL] [--orgs=ORG_LIST]

Arguments:
    DATA_SOURCE  Source to collect data from. Valid values: "dnsmonitor", "dnstwist", "shodan", "flare_events", "flare_ident_prune", "flare_ident_refresh", "flare_creds.

Options:
    -h --help                       Show this message.
    -v --version                    Show version information.
    -l --log-level=LEVEL            Log level: debug, info, warning, error, critical.
                                    [default: info]
    -o --orgs=ORG_LIST              Comma-separated org cyhy_db_name values, "DEMO", or "all".
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
from pe_source.dnsmonitor.dnsmonitor_script import run_dnsmonitor
from pe_source.dnstwist import run_dnstwist
from pe_source.flare_events import run_flare_events
from pe_source.flare_creds.flare_creds_script import run_flare_creds
from pe_source.flare_ident_prune.flare_ident_prune import run_flare_ident_prune
from pe_source.flare_ident_refresh.flare_ident_refresh import run_flare_ident_refresh
from pe_source.shodan.shodan_script import Get_shodan
from schema import And, Schema, SchemaError, Use

LOGGER = logging.getLogger(__name__)


def run_pe_script(source, orgs_list):
    """Collect data from the source specified."""
    # Run the specified script
    if source == "dnsmonitor":
        run_dnsmonitor(orgs_list)
    elif source == "dnstwist":
        run_dnstwist(orgs_list)
    elif source == "flare_events":
        if not os.environ.get("FLARE_API_KEY", "").strip():
            LOGGER.error(
                "FLARE_API_KEY is not set. peScanController assigns one validated "
                "key per flare_events worker container."
            )
            sys.exit(1)
        run_flare_events(orgs_list)
    elif source == "flare_creds":
            if not os.environ.get("FLARE_API_KEY", "").strip():
                LOGGER.error(
                    "FLARE_API_KEY is not set. peScanController assigns one validated "
                    "key per flare_creds worker container."
                )
                sys.exit(1)
            run_flare_creds(orgs_list)
    elif source == "flare_ident_prune":
        if not os.environ.get("FLARE_API_KEY", "").strip():
            LOGGER.error(
                "FLARE_API_KEY is not set. peScanController assigns one validated "
                "key per flare_ident_prune worker container."
            )
            sys.exit(1)
        run_flare_ident_prune(orgs_list)
    elif source == "flare_ident_refresh":
        if not os.environ.get("FLARE_API_KEY", "").strip():
            LOGGER.error(
                "FLARE_API_KEY is not set. peScanController assigns one validated "
                "key per flare_ident_refresh worker container."
            )
            sys.exit(1)
        run_flare_ident_refresh(orgs_list)
    elif source == "shodan":
        if not os.environ.get("PE_SHODAN_API_KEY", "").strip():
            LOGGER.error(
                "PE_SHODAN_API_KEY is not set. peScanController assigns one "
                "validated key per shodan worker container."
            )
            sys.exit(1)
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

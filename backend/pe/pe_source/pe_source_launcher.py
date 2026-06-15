"""
The main file to launch all P&E data collection scripts.

Usage:
    pe_source_launcher.py DATA_SOURCE [--log-level=LEVEL] [--orgs=ORG_LIST] [--key_num=KEY_NUM] [--soc_med_included]

Arguments:
    DATA_SOURCE                     Data source to collect data from. Valid values are "dnsmonitor", "dnsmonitor",
                                    "dnstwist", "flare_events", "flare_creds", "shodan_vulns", and "shodan_top_cves".

Options:
    -h --help                       Show this message.
    -v --version                    Show version information.
    -l --log-level=LEVEL            The desired log level. If specified, valid values are
                                    "debug", "info", "warning", "error", and "critical".
                                    [default: info]
    -o --orgs=ORG_LIST              A comma-separated list of organizations to collect data for.
                                    If specified, organizations in the list must use the abbreviations
                                    in the cyhy-db (e.g. DHS, DHS_CISA). Enter "all" to collect data
                                    for all P&E report customer organizations. Enter "demo" to collect
                                    data for all non-pe customer organizations.
                                    [default: all]
    -kn --key_num=KEY_NUM           The number of the data source's API key to use for the script
                                    if applicable.
                                    [default: 1]
    -sc --soc_med_included          Include social media sites/posts during in data collection.
"""

# Standard Python Libraries
from datetime import timedelta
import logging
import os
import sys
import time
from typing import Any, Dict

# Third-Party Libraries
import docopt
from schema import And, Schema, SchemaError, Use

# cisagov Libraries
from pe_source._version import __version__
from pe_source.dnsmonitor.dnsmonitor_script import run_dnsmonitor
from pe_source.dnstwist.dnstwist_script import run_dnstwist
from pe_source.flare.flare_creds import run_flare_creds
from pe_source.flare.flare_events import run_flare_events
from pe_source.flare.flare_ident_prune import run_flare_ident_prune
from pe_source.flare.flare_ident_refresh import run_flare_ident_refresh
from pe_source.shodan.shodan_top_cves import run_shodan_top_cves
from pe_source.shodan.shodan_vulns import run_shodan_vulns

# Setup Logging
LOGGER = logging.getLogger(__name__)


def run_pe_source(source, orgs_list, key_num, soc_med_included):
    """Run the specified data collection script."""
    # Determine list of organizations to run the script on
    if orgs_list != "all" and orgs_list != "demo":
        # If list specified, use those orgs
        orgs_list = orgs_list.split(",")
        if len(orgs_list) == 1:
            orgs_list_str = orgs_list[0]
        else:
            orgs_list_str = f"{orgs_list[0]} - {orgs_list[-1]}"
    else:
        # If no list specified, use all orgs
        orgs_list_str = "All P&E Report orgs"

    # Log data collection script starting details
    script_full_names = {
        "dnsmonitor": "DNSMonitor",
        "dnstwist": "DNSTwist",
        "flare_events": "Flare Events",
        "flare_creds": "Flare Leaked Credentials",
        "flare_ident_prune": "Flare Identifier Prune",
        "flare_ident_refresh": "Flare Identifier Refresh",
        "shodan_vulns": "Shodan Vulnerabilities",
        "shodan_top_cves": "Shodan Top CVEs",
    }
    script_name = script_full_names.get(source)
    LOGGER.info(f"--- {script_name} Scan Starting ---")
    LOGGER.info(f"Running {script_name} script on these orgs: {orgs_list}")
    script_start_time = time.time()

    # Run the specified scans
    if source == "dnsmonitor":
        run_dnsmonitor(orgs_list)
    elif source == "dnstwist":
        run_dnstwist(orgs_list)
    elif source == "flare_events":
        LOGGER.info(f"Using Flare API key number: {key_num}")
        os.environ["FLARE_KEY_NUM"] = key_num
        run_flare_events(orgs_list)
    elif source == "flare_creds":
        LOGGER.info(f"Using Flare API key number: {key_num}")
        os.environ["FLARE_KEY_NUM"] = key_num
        run_flare_creds(orgs_list)
    elif source == "flare_ident_prune":
        LOGGER.info(f"Using Flare API key number: {key_num}")
        os.environ["FLARE_KEY_NUM"] = key_num
        run_flare_ident_prune(orgs_list)
    elif source == "flare_ident_refresh":
        LOGGER.info(f"Using Flare API key number: {key_num}")
        os.environ["FLARE_KEY_NUM"] = key_num
        run_flare_ident_refresh(orgs_list)
    elif source == "shodan_vulns":
        run_shodan_vulns(orgs_list)
    elif source == "shodan_top_cves":
        run_shodan_top_cves(orgs_list)
    else:
        LOGGER.error("Not a valid script name.")
        sys.exit(1)

    # Log data collection script completion details
    script_end_time = time.time()
    LOGGER.info(
        f"Execution time for {script_name} scan ({orgs_list_str}): {str(timedelta(seconds=(script_end_time - script_start_time)))} (H:M:S)"
    )
    LOGGER.info(f"--- {script_name} Scan Complete ---")


def main():
    """Set up logging and call the run_pe_source function."""
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
        filename="./pe_reports_logging.log",
        filemode="a",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S",
        level=log_level.upper(),
    )

    # Run P&E script for the specified data source
    run_pe_source(
        validated_args["DATA_SOURCE"],
        validated_args["--orgs"],
        validated_args["--key_num"],
        validated_args["--soc_med_included"],
    )

    # Stop logging and clean up
    logging.shutdown()


if __name__ == "__main__":
    main()

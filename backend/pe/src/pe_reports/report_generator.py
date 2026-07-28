"""cisagov/pe-reports: A tool for creating Posture & Exposure reports.

Usage:
    pe-reports REPORT_DATE OUTPUT_DIRECTORY [--log-level=LEVEL] [--soc_med_included] [--orgs=ORG_LIST]

Options:
    -h --help                       Show this message.
    REPORT_DATE                     Date of the report, format YYYY-MM-DD
    OUTPUT_DIRECTORY                The directory where the final PDF
                                    reports should be saved.
    -l --log-level=LEVEL            If specified, then the log level will be set to
                                    the specified value.  Valid values are "debug", "info",
                                    "warning", "error", and "critical". [default: info]
    -s --soc_med_included           Include social media posts from Cybersixgill in the report.
    -o --orgs=ORG_LIST              A comma-separated list of orgs to generate P&E reports for.
                                    If not specified, reports will be generated for all
                                    orgs P&E delivers reports to. Orgs in the list must match the
                                    IDs in the cyhy-db. E.g. DHS,DHS_ICE,DOC.
                                    Other options include:
                                    'demo' = all demo orgs,
                                    'all' = all orgs P&E delivers reports to.
                                    [default: all]
"""

# Standard Python Libraries
from datetime import timedelta
import logging
import os
import sys
import time
from typing import Any, Dict
import warnings

# Third-Party Libraries
import boto3
from botocore.exceptions import ClientError
import docopt
import fitz
import pandas as pd
from schema import And, Schema, SchemaError, Use

from ._version import __version__
from .asm_generator import create_summary
from .data.db_query import (
    connect,
    get_demo_orgs,
    get_orgs,
    get_specific_orgs,
    refresh_asset_counts_vw,
)
from .pages import init
from .reportlab_generator import report_gen

# Setup logging
LOGGER = logging.getLogger(__name__)
ACCESSOR_AWS_PROFILE = os.getenv("ACCESSOR_PROFILE")
REPORTS_BUCKET_NAME = os.getenv("REPORTS_BUCKET_NAME", "cisa-crossfeed-staging-reports")


def _should_upload_to_s3(bucket: str) -> bool:
    """Skip S3 backup uploads for local report runs (files stay on disk)."""
    if os.getenv("IS_LOCAL", "").lower() in ("1", "true", "yes"):
        return False
    if not bucket or bucket == "local-reports":
        return False
    return True


def _configure_console_logging(log_level: str) -> None:
    """Mirror report progress to stderr (docker logs) in addition to the log file."""
    level = getattr(logging, log_level.upper())
    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stderr:
            handler.setLevel(level)
            handler.setFormatter(formatter)
            return
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(level)
    root.addHandler(console)


def _suppress_noisy_warnings() -> None:
    """Hide known-benign library warnings during local/sparse-data runs."""
    warnings.filterwarnings(
        "ignore",
        message="pandas only supports SQLAlchemy connectable.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message="The 'origin' keyword does not take effect.*",
        category=RuntimeWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message="Attempting to set identical low and high ylims.*",
        category=UserWarning,
    )


def upload_file_to_s3(file_name, datestring, bucket, excel_org):
    """Upload a file to an S3 bucket."""
    if not _should_upload_to_s3(bucket):
        LOGGER.debug("Skipping S3 upload for %s", file_name)
        return
    if ACCESSOR_AWS_PROFILE:
        session = boto3.Session(profile_name=ACCESSOR_AWS_PROFILE)
        s3_client = session.client("s3")
    else:
        s3_client = boto3.client("s3")
    # If S3 object_name was not specified, use file_name
    object_name = f"{datestring}/{os.path.basename(file_name)}"
    if excel_org is not None:
        object_name = f"{datestring}/{excel_org}-raw-data/{os.path.basename(file_name)}"

    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
        if response is None:
            LOGGER.info(f"Success uploading {file_name.split('/')[-1]} to S3.")
        else:
            LOGGER.info(response)
    except ClientError as e:
        LOGGER.error(e)


def embed(
    output_directory,
    org_code,
    datestring,
    file,
    cred_json,
    da_json,
    vuln_json,
    mi_json,
    cred_xlsx,
    da_xlsx,
    vuln_xlsx,
    mi_xlsx,
):
    """Embeds raw data into PDF and encrypts file."""
    del output_directory, org_code, datestring  # kept for call-site compatibility
    doc = fitz.open(file)
    # Get the summary page of the PDF on page 4
    page = doc[4]
    output = file

    # Open CSV data as binary
    cc = open(cred_json, "rb").read()
    da = open(da_json, "rb").read()
    ma = open(vuln_json, "rb").read()
    if mi_json:
        mi = open(mi_json, "rb").read()

    # Open CSV data as binary
    cc_xl = open(cred_xlsx, "rb").read()
    da_xl = open(da_xlsx, "rb").read()
    ma_xl = open(vuln_xlsx, "rb").read()
    if mi_xlsx:
        mi_xl = open(mi_xlsx, "rb").read()

    # Insert link to CSV data in summary page of PDF.
    # Use coordinates to position them on the bottom.
    p1 = fitz.Point(300, 607)
    p2 = fitz.Point(300, 635)
    p3 = fitz.Point(300, 663)
    p4 = fitz.Point(300, 691)
    p5 = fitz.Point(340, 607)
    p6 = fitz.Point(340, 635)
    p7 = fitz.Point(340, 663)
    p8 = fitz.Point(340, 691)

    # Embed and add push-pin graphic
    page.add_file_annot(
        p1, cc, "compromised_credentials.json", desc="Open JSON", icon="Paperclip"
    )
    page.add_file_annot(
        p2, da, "domain_alerts.json", desc="Open JSON", icon="Paperclip"
    )
    page.add_file_annot(p3, ma, "vuln_alerts.json", desc="Open JSON", icon="Paperclip")
    if mi_json:
        page.add_file_annot(
            p4, mi, "mention_incidents.json", desc="Open JSON", icon="Paperclip"
        )
    page.add_file_annot(
        p5, cc_xl, "compromised_credentials.xlsx", desc="Open Excel", icon="Graph"
    )
    page.add_file_annot(
        p6, da_xl, "domain_alerts.xlsx", desc="Open Excel", icon="Graph"
    )
    page.add_file_annot(p7, ma_xl, "vuln_alerts.xlsx", desc="Open Excel", icon="Graph")
    if mi_xlsx:
        page.add_file_annot(
            p8, mi_xl, "mention_incidents.xlsx", desc="Open Excel", icon="Graph"
        )

    # Save doc and set garbage=4 to reduce PDF size using all 4 methods:
    # Remove unused objects, compact xref table, merge duplicate objects,
    # and check stream objects for duplication
    temp_output = f"{file}.embed.tmp"
    doc.save(
        temp_output,
        garbage=4,
        deflate=True,
    )
    doc.close()
    os.replace(temp_output, file)
    tooLarge = False
    # Throw error if file size is greater than 20MB
    filesize = os.path.getsize(file)
    if filesize >= 20000000:
        tooLarge = True

    return filesize, tooLarge, output


def generate_reports(orgs_list, datestring, output_directory, soc_med_included=False):
    """Process steps for generating report data."""
    # Determine list of organizations to run on
    conn = connect()
    if not conn:
        return 1

    requested_orgs = orgs_list
    if orgs_list == "all":
        pe_orgs = get_orgs(conn)
    elif orgs_list == "demo":
        pe_orgs = get_demo_orgs(conn)
    else:
        requested_orgs = [org.strip() for org in orgs_list.split(",") if org.strip()]
        pe_orgs = get_specific_orgs(conn, requested_orgs)

    if not pe_orgs:
        LOGGER.error(
            "No matching organizations found for request: %s. "
            "For local dev, run `make -C backend/pe syncdb-populate` and verify "
            "cyhy_db_name values.",
            requested_orgs,
        )
        return 1

    if orgs_list == "all":
        orgs_list_log = f"All P&E Report orgs, {pe_orgs[0][2]} - {pe_orgs[-1][2]}"
    elif orgs_list == "demo":
        orgs_list_log = f"All demo orgs, {pe_orgs[0][2]} - {pe_orgs[-1][2]}"
    elif len(pe_orgs) == 1:
        orgs_list_log = pe_orgs[0][2]
    else:
        orgs_list_log = f"{pe_orgs[0][2]} - {pe_orgs[-1][2]}"

    # alphabetize org list for consistent order
    pe_orgs = sorted(pe_orgs, key=lambda d: d[2])

    # Refresh breach-comp materialized views used by report metrics.
    LOGGER.info("Refreshing breach-comp materialized views")
    refresh_asset_counts_vw()
    LOGGER.info("Finished refreshing breach-comp materialized views")

    # Ensure there's a list of organizations to generate reports for
    generated_reports = 0
    if pe_orgs:
        LOGGER.info(
            f"Generating PE reports for {len(pe_orgs)} requested organizations ({orgs_list_log})"
        )
        for org_idx, org in enumerate(pe_orgs):
            # Assign organization values
            org_uid = org[0]
            org_name = org[1]
            org_code = org[2]
            premium = org[8]
            LOGGER.info(
                f"-- Generating report for {org_code} ({org_idx + 1} of {len(pe_orgs)}) --"
            )
            # Create org output folder
            org_output_dir = f"{output_directory}/{org_code}"
            if not os.path.exists(org_output_dir):
                os.mkdir(org_output_dir)
            # WIP retrieve PE score for this org
            pe_scores_df = pd.DataFrame()
            if not pe_scores_df.empty:
                score = pe_scores_df.loc[
                    pe_scores_df["cyhy_db_name"] == org_code, "PE_score"
                ].item()
                grade = pe_scores_df.loc[
                    pe_scores_df["cyhy_db_name"] == org_code, "letter_grade"
                ].item()
            else:
                score = "NA"
                grade = "NA"
            LOGGER.info("Collecting metrics and charts for %s", org_code)
            # Calculate charts, metrics, and raw data files
            (
                chevron_dict,
                scorecard_dict,
                summary_dict,
                cred_json,
                da_json,
                vuln_json,
                mi_json,
                cred_xlsx,
                da_xlsx,
                vuln_xlsx,
                mi_xlsx,
            ) = init(
                datestring,
                org_name,
                org_code,
                org_uid,
                premium,
                score,
                grade,
                output_directory,
                soc_med_included,
            )
            LOGGER.info("Finished collecting metrics and charts for %s", org_code)
            # Create ASM Summary
            LOGGER.info("Creating ASM summary")
            summary_pdf = f"{output_directory}/{org_code}/Posture-and-Exposure-ASM-Summary_{org_code}_{scorecard_dict['end_date'].strftime('%Y-%m-%d')}.pdf"
            summary_json_filename = f"{output_directory}/{org_code}/ASM_Summary.json"
            summary_excel_filename = f"{output_directory}/{org_code}/ASM_Summary.xlsx"
            asm_xlsx = create_summary(
                org_uid,
                summary_pdf,
                summary_dict,
                summary_pdf,
                summary_json_filename,
                summary_excel_filename,
                datestring,
            )
            LOGGER.info("Finished creating ASM summary")

            output_filename = f"{output_directory}/{org_code}/Posture_and_Exposure_Report-{org_code}-{datestring}.pdf"
            chevron_dict["filename"] = output_filename
            LOGGER.info("Rendering PDF for %s", org_code)
            report_gen(chevron_dict, soc_med_included)
            LOGGER.info("Embedding data into PDF for %s", org_code)
            pdf = output_filename
            # Embed raw data files
            (filesize, tooLarge, output) = embed(
                output_directory,
                org_code,
                datestring,
                pdf,
                cred_json,
                da_json,
                vuln_json,
                mi_json,
                cred_xlsx,
                da_xlsx,
                vuln_xlsx,
                mi_xlsx,
            )
            # Log a message if the report is too large
            # Current mailer can't send files larger than 20MB
            if tooLarge:
                LOGGER.info(
                    "%s is too large. File size: %s Limit: 20MB", org_code, filesize
                )
            # Upload backup copies of files to S3 bucket
            bucket_name = REPORTS_BUCKET_NAME
            # Upload excel files
            upload_file_to_s3(cred_xlsx, datestring, bucket_name, org_code)
            upload_file_to_s3(da_xlsx, datestring, bucket_name, org_code)
            upload_file_to_s3(vuln_xlsx, datestring, bucket_name, org_code)
            if premium:
                upload_file_to_s3(mi_xlsx, datestring, bucket_name, org_code)
            upload_file_to_s3(asm_xlsx, datestring, bucket_name, org_code)
            # Upload report
            upload_file_to_s3(output, datestring, bucket_name, None)
            # Upload ASM Summary
            upload_file_to_s3(summary_pdf, datestring, bucket_name, None)

            LOGGER.info("Completed report for %s", org_code)
            # Keep track of sucessful report generations
            generated_reports += 1
    else:
        LOGGER.error(
            "Connection to pe database failed and/or there are 0 organizations stored."
        )

    # Log overall stats
    LOGGER.info(f"In total, {generated_reports}/{len(pe_orgs)} reports were generated")
    LOGGER.info(
        f"Generated reports have been output to the directory: {output_directory}"
    )


def main():
    """Generate PDF reports."""
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
        # Exit if one or more of the arguments were invalid
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.ERROR, stream=sys.stderr, format="%(message)s"
            )
        LOGGER.error("%s", err)
        sys.exit(1)
    # Assign validated arguments to variables
    log_level: str = validated_args["--log-level"]
    _suppress_noisy_warnings()
    _configure_console_logging(log_level)
    # Log start message
    LOGGER.info("--- PE Report Generation Starting ---")
    LOGGER.info("Posture & Exposure Report, Version : %s", __version__)
    report_gen_start_time = time.time()
    # Create output directory
    if not os.path.exists(validated_args["OUTPUT_DIRECTORY"]):
        os.mkdir(validated_args["OUTPUT_DIRECTORY"])
    # Generate reports
    generate_reports(
        validated_args["--orgs"],
        validated_args["REPORT_DATE"],
        validated_args["OUTPUT_DIRECTORY"],
        validated_args["--soc_med_included"],
    )
    # log end message
    report_gen_end_time = time.time()
    report_gen_exe_time = str(
        timedelta(seconds=(report_gen_end_time - report_gen_start_time))
    )
    LOGGER.info(
        f"Execution time for PE report generation: {report_gen_exe_time} (H:M:S)"
    )
    LOGGER.info("--- PE Report Generation Complete ---")
    # Stop logging and clean up
    logging.shutdown()

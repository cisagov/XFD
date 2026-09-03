"""CLI for exporting a stakeholder WAS report as sanitized XML."""

# Standard Python Libraries
import argparse
from pathlib import Path
import sys
from typing import List, Optional

# Third-Party Libraries
from lxml import etree, objectify  # nosec B410

# First-Party Libraries
from was_reports.commands.report_generator import validate_stakeholder_tag
from was_reports.qualys.qualys_client import QualysClient, create_qualys_client
from was_reports.qualys.report_data import (
    create_webapp_xml_report,
    delete_report,
    get_report_xml,
    get_tag_id,
)
from was_reports.utils.env import getenv


def sanitize_report_xml(report_xml: str) -> bytes:
    """Remove Qualys company and user metadata from downloaded report XML."""
    parser = objectify.makeparser(resolve_entities=False, no_network=True)
    root = objectify.fromstring(report_xml.encode("utf-8"), parser=parser)
    header = root.find("HEADER")
    if header is None:
        raise ValueError("Downloaded Qualys report does not contain a HEADER element.")

    for element_name in ("COMPANY_INFO", "USER_INFO"):
        element = header.find(element_name)
        if element is not None:
            header.remove(element)

    return etree.tostring(root, encoding="UTF-8", xml_declaration=True)


def resolve_output_path(output_directory: Path, filename: str) -> Path:
    """Return a safe XML output path contained by the output directory."""
    normalized_filename = filename.strip()
    if not normalized_filename:
        raise ValueError("Output filename is required.")
    if Path(normalized_filename).name != normalized_filename:
        raise ValueError("Output filename must not contain directory components.")
    if not normalized_filename.lower().endswith(".xml"):
        normalized_filename = "{}.xml".format(normalized_filename)
    return output_directory / normalized_filename


def export_xml_report(
    client: QualysClient,
    stakeholder_tag: str,
    template_path: Path,
    output_path: Path,
) -> Path:
    """Create, download, sanitize, and save a Qualys XML report."""
    tag_id = get_tag_id(client, stakeholder_tag)
    report_id = create_webapp_xml_report(
        client=client,
        report_name=stakeholder_tag,
        tag_id=tag_id,
        template_path=template_path,
    )

    try:
        report_xml = get_report_xml(client, report_id)
        sanitized_xml = sanitize_report_xml(report_xml)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(sanitized_xml)
    finally:
        delete_report(client, report_id)

    return output_path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse XML export command-line arguments."""
    default_resource_root = getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES")
    default_output_directory = getenv(
        "WAS_OUTPUT_DIRECTORY", "/output"
    )

    parser = argparse.ArgumentParser(
        description="Export a sanitized Qualys WAS report as XML."
    )
    parser.add_argument(
        "-t",
        "--tag",
        required=True,
        help="Stakeholder tag to export.",
    )
    parser.add_argument(
        "--filename",
        help="Output filename. Defaults to <STAKEHOLDER_TAG>_report.xml.",
    )
    parser.add_argument(
        "--resource-root",
        default=default_resource_root,
        help="Directory containing production Qualys XML templates.",
    )
    parser.add_argument(
        "--output-directory",
        default=default_output_directory,
        help="Directory where the XML report is written.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the stakeholder XML export command."""
    args = parse_args(argv)
    stakeholder_tag = validate_stakeholder_tag(args.tag)
    filename = args.filename or "{}_report.xml".format(stakeholder_tag)
    output_path = resolve_output_path(Path(args.output_directory), filename)
    client = create_qualys_client()
    export_xml_report(
        client=client,
        stakeholder_tag=stakeholder_tag,
        template_path=Path(args.resource_root) / "assets" / "was_report.xml",
        output_path=output_path,
    )
    sys.stdout.write("XML report written to {}.\n".format(str(output_path)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

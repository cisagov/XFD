#!/usr/bin/env python3
"""Run the production WAS pipeline offline with representative Qualys XML."""

# Standard Python Libraries
import argparse
import base64
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
from typing import List, Optional

# Third-Party Libraries
from lxml import etree  # nosec B410
from pikepdf import PasswordError, Pdf

# First-Party Libraries
from was_reports.reporting import (
    chart_renderer,
    latex_renderer,
    pdf_security,
    report_artifacts,
    report_comparison,
    report_metrics,
    report_template_data,
    report_transformer,
    report_workspace,
)

TEST_ENCRYPTION_VALUE = "".join(("Offline", "Validation", "123!"))
EXPECTED_ATTACHMENTS = {
    "assets/vulnerability-list-OFFLINE.csv",
    "assets/vulns-by-webapp-OFFLINE.csv",
    "assets/webapp-overview-OFFLINE.csv",
    "assets/links-crawled-OFFLINE.csv",
    "assets/rejected-links-OFFLINE.csv",
    "assets/emails-found-OFFLINE.csv",
    "assets/ssn-and-cc-found.csv",
    "assets/information-gathered-listOFFLINE.csv",
}


class OfflineQualysClient:
    """Return empty sensitive-finding responses without network access."""

    def request(self, qualys_request) -> str:
        """Return a valid response containing no Qualys findings."""
        return "<ServiceResponse><data /></ServiceResponse>"


def _add_text_element(parent, name: str, value: str):
    """Append an XML element containing text and return it."""
    element = etree.SubElement(parent, name)
    element.text = value
    return element


def _add_information_finding(web_application, qid: str, value: str) -> None:
    """Add one base64-encoded information-gathered fixture finding."""
    information_list = web_application.find("INFORMATION_GATHERED_LIST")
    finding = etree.SubElement(information_list, "INFORMATION_GATHERED")
    _add_text_element(finding, "ID", "info-{}".format(qid))
    _add_text_element(finding, "QID", qid)
    _add_text_element(finding, "LAST_TIME_DETECTED", "26 Aug 2026 01:00PM UTC")
    encoded_value = base64.b64encode(value.encode("utf-8")).decode("ascii")
    _add_text_element(finding, "DATA", encoded_value)


def _add_qid_definition(glossary_list, qid: str, title: str) -> None:
    """Add glossary metadata required by the CSV transformer."""
    definition = etree.SubElement(glossary_list, "QID")
    _add_text_element(definition, "QID", qid)
    _add_text_element(definition, "SEVERITY", "1")
    _add_text_element(definition, "TITLE", title)
    _add_text_element(definition, "GROUP", "INFO")
    _add_text_element(definition, "DESCRIPTION", "Offline fixture description")
    _add_text_element(definition, "IMPACT", "Offline fixture impact")
    _add_text_element(definition, "SOLUTION", "Offline fixture solution")


def build_offline_report_xml(fixture_path: Path) -> bytes:
    """Augment the transformer fixture with every report-rendering section."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(  # nosec B320
        fixture_path.read_bytes(),
        parser=parser,
    )
    header = etree.Element("HEADER")
    _add_text_element(header, "GENERATION_DATETIME", "26 Aug 2026 01:00PM UTC")
    _add_text_element(header, "NAME", "OFFLINE")
    root.insert(0, header)

    summary = etree.Element("SUMMARY")
    global_summary = etree.SubElement(summary, "GLOBAL_SUMMARY")
    _add_text_element(global_summary, "SECURITY_RISK", "High")
    _add_text_element(global_summary, "INFORMATION_GATHERED", "4")
    _add_text_element(global_summary, "WEB_APPLICATIONS", "1")
    _add_text_element(global_summary, "SENSITIVE_CONTENT", "0")
    summary_stats = etree.SubElement(summary, "SUMMARY_STATS")
    summary_stat = etree.SubElement(summary_stats, "SUMMARY_STAT")
    _add_text_element(summary_stat, "WEB_APPLICATION", "Example Application")
    for level, value in enumerate((0, 0, 0, 1, 0), start=1):
        _add_text_element(summary_stat, "LEVEL{}".format(level), str(value))
    root.insert(1, summary)

    web_application = root.find("./RESULTS/WEB_APPLICATION")
    special_information = (
        ("150009", "https://example.gov/one\nhttps://example.gov/two"),
        ("150054", "user@example.gov"),
        ("150041", "https://example.gov/rejected"),
    )
    for finding_qid, finding_value in special_information:
        _add_information_finding(web_application, finding_qid, finding_value)

    glossary_list = root.find("./GLOSSARY/QID_LIST")
    first_qid = glossary_list.find("QID")
    first_qid.find("GROUP").text = "SQL"
    _add_text_element(first_qid, "OWASP", "A3")
    for definition_qid, definition_title in (
        ("150009", "Links Crawled"),
        ("150054", "Emails Found"),
        ("150041", "Rejected Links"),
    ):
        _add_qid_definition(glossary_list, definition_qid, definition_title)

    appendix = etree.SubElement(root, "APPENDIX")
    appendix_application = etree.SubElement(appendix, "WEB_APPLICATION")
    _add_text_element(appendix_application, "NAME", "Example Application")
    _add_text_element(appendix_application, "URL", "https://example.gov")
    _add_text_element(appendix_application, "OPERATING_SYSTEM", "Linux")
    _add_text_element(appendix_application, "SCOPE", "ALL")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def run_offline_smoke(
    resource_root: Path,
    fixture_path: Path,
    output_directory: Path,
) -> Path:
    """Generate, encrypt, and verify a representative offline WAS PDF."""
    current_time = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)
    report_xml = build_offline_report_xml(fixture_path)
    output_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as workspace_parent:
        with report_workspace.isolated_report_workspace(
            resource_root=resource_root,
            workspace_root=Path(workspace_parent),
            stakeholder_tag="OFFLINE",
        ) as workspace:
            asset_directory = workspace / "assets"
            private_output = workspace / "docs"
            transformation = report_transformer.transform_report_to_csv(
                report_xml=report_xml,
                stakeholder_tag="OFFLINE",
                asset_directory=asset_directory,
                current_time=current_time,
            )
            metrics = report_metrics.calculate_finding_metrics(
                report_xml,
                current_time,
            )
            chart_renderer.render_report_charts(
                finding_metrics=metrics,
                ages=transformation.ages,
                severities=transformation.severities,
                asset_directory=asset_directory,
            )
            generated_artifacts = report_artifacts.generate_report_artifacts(
                report_xml=report_xml,
                stakeholder_tag="OFFLINE",
                asset_directory=asset_directory,
                client=OfflineQualysClient(),
            )
            template_data = report_template_data.build_template_data(
                report_xml=report_xml,
                stakeholder_tag="OFFLINE",
                organization_name="Offline Validation Organization",
                artifacts=report_template_data.TemplateArtifactInputs(
                    vulnerability_details=transformation.vulnerability_filename,
                    information_details=transformation.information_filename,
                    generated=generated_artifacts,
                ),
                finding_ages=report_template_data.FindingAgeInputs(
                    critical_days=26,
                    urgent_days=0,
                ),
                web_application_count=35,
                current_time=current_time,
            )
            render_result = latex_renderer.render_report_pdf(
                template_path=workspace / "NEW_BIG.mustache",
                template_data=template_data,
                stakeholder_tag="OFFLINE",
                working_directory=workspace,
                output_directory=private_output,
                report_date=current_time.date(),
            )
            encrypted_path = pdf_security.encrypt_pdf_in_place(
                render_result.pdf_path,
                TEST_ENCRYPTION_VALUE,
            )
            final_path = pdf_security.publish_encrypted_pdf(
                encrypted_path,
                output_directory,
            )

    try:
        Pdf.open(final_path)
    except PasswordError:
        pass
    else:
        raise RuntimeError("Offline WAS PDF was published without encryption.")
    with Pdf.open(final_path, password=TEST_ENCRYPTION_VALUE) as report_pdf:
        if len(report_pdf.pages) < 1:
            raise RuntimeError("Offline WAS PDF does not contain any pages.")
        embedded_attachments = report_comparison.attachment_hashes(report_pdf)
        if set(embedded_attachments) != EXPECTED_ATTACHMENTS:
            raise RuntimeError(
                "Offline WAS PDF attachment inventory does not match expectations."
            )
    return final_path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse offline smoke-test paths."""
    parser = argparse.ArgumentParser(
        description="Generate an offline production-pipeline WAS PDF."
    )
    parser.add_argument("--resource-root", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the offline report smoke test and print only its output path."""
    arguments = parse_args(argv)
    output_path = run_offline_smoke(
        resource_root=arguments.resource_root,
        fixture_path=arguments.fixture,
        output_directory=arguments.output_directory,
    )
    sys.stdout.write("{}\n".format(str(output_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

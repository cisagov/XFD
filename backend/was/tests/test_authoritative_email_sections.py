"""Compare customer output with the authoritative September 21 source files."""

import hashlib
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import unittest
from xml.etree import ElementTree
from zipfile import ZipFile

from was_mailer.authoritative_email_sections import SECTIONS, SOURCE_ZIP_SHA256
from was_mailer.customer_email_templates import section_names, substitute_values
from was_mailer.message import customer_report_body, report_email_subject


class TextCollector(HTMLParser):
    """Collect visible HTML text to compare it with DOCX text."""

    def __init__(self) -> None:
        """Initialize the parser and visible-text accumulator."""
        super().__init__()
        self.parts = []

    def handle_data(self, data: str) -> None:
        """Record visible data without interpreting it as HTML."""
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Keep paragraph and break boundaries when extracting text."""
        if tag in {"div", "br", "li"}:
            self.parts.append("\n")


class AuthoritativeEmailTests(unittest.TestCase):
    """Protect source wording, flowchart branches, formatting, and escaping."""

    def test_source_docx_text_matches_every_component(self) -> None:
        """Extract expected text independently from every original DOCX."""
        source = Path(__file__).parents[1] / "WAS_EMAIL_templates_Newest9_21.zip"
        if not source.exists():
            self.skipTest("Operator source ZIP is not distributed with the package")
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(), SOURCE_ZIP_SHA256
        )
        namespace = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        }
        with ZipFile(source) as archive:
            for name, section in SECTIONS.items():
                with self.subTest(component=name):
                    raw = archive.read("WAS_email_templates/{}.docx".format(name))
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), section["sha256"])
                    with ZipFile(BytesIO(raw)) as document:
                        root = ElementTree.fromstring(
                            document.read("word/document.xml")
                        )
                    paragraphs = []
                    for paragraph in root.findall(".//w:body/w:p", namespace):
                        text = "".join(
                            node.text or ""
                            if node.tag.endswith("}t")
                            else "\n"
                            if node.tag.endswith("}br")
                            else ""
                            for node in paragraph.iter()
                        )
                        level = paragraph.find("w:pPr/w:numPr/w:ilvl", namespace)
                        if level is not None:
                            depth = int(level.attrib["{" + namespace["w"] + "}val"])
                            text = "  " * depth + "- " + text
                        paragraphs.append(text)
                    self.assertEqual(section["text"], "\n".join(paragraphs))

    def test_html_preserves_every_source_word(self) -> None:
        """HTML formatting must not change the source component wording."""
        for name, section in SECTIONS.items():
            with self.subTest(component=name):
                collector = TextCollector()
                collector.feed(section["html"])
                html_words = " ".join("".join(collector.parts).replace("•", "").split())
                text_words = " ".join(
                    line.lstrip().removeprefix("- ")
                    for line in section["text"].splitlines()
                )
                self.assertEqual(html_words, " ".join(text_words.split()))

    def test_flowchart_orders_conditional_sections(self) -> None:
        """Qualys errors precede NWS, warning, removals, and shared closing."""
        self.assertEqual(
            section_names("Targets Removed", True, True, True),
            [
                "results_part1",
                "qualys_scan_error",
                "nws_notification",
                "nws_webapp_removal_warning",
                "targets_removed",
                "results_part2",
            ],
        )
        self.assertEqual(
            section_names("FCEB Action Required", True, True, True),
            [
                "results_part1",
                "qualys_scan_error",
                "nws_notification",
                "results_part2",
            ],
        )
        for template in ("All NWS", "FCEB All NWS"):
            self.assertEqual(
                section_names(template, True, True, True),
                [
                    "report_not_generated",
                    "results_part2",
                ],
            )

    def test_subjects_follow_flowchart_verbatim(self) -> None:
        """Use separate results, action, removal, and no-report subjects."""
        expected = {
            "Results": "TAG - WAS Results",
            "Action Required": "TAG - WAS Results - Action Required",
            "FCEB Action Required": "TAG - WAS Results - Action Required",
            "Targets Removed": "TAG - WAS Results - Targets Removed",
            "All NWS": "TAG - WAS Report Not Generated - Action Required",
            "FCEB All NWS": "TAG - WAS Report Not Generated - Action Required",
        }
        for template, subject in expected.items():
            self.assertEqual(report_email_subject("TAG", template), subject)

    def test_placeholder_content_cannot_inject_html_or_other_placeholders(self) -> None:
        """Do not interpret customer values as HTML or recursively replace them."""
        result = substitute_values(
            "&lt;poc_names&gt; &lt;tag&gt;",
            {"poc_names": "<script> & <tag>", "tag": "EXAMPLE"},
            True,
        )
        self.assertEqual(result, "&lt;script&gt; &amp; &lt;tag&gt; EXAMPLE")

    def test_customer_body_uses_source_dates_and_closing(self) -> None:
        """Fill scan dates and preserve the exact new source salutation."""
        body = customer_report_body(
            "TAG",
            "Sample POC",
            "Results",
            "Sample Analyst",
            None,
            None,
            None,
            None,
            1790006400,
            1790611200,
        )
        self.assertTrue(body.startswith("WAS Results for TAG\n\nSample POC,\n"))
        self.assertIn(
            "scan that began at September 21, 2026 at 12:00 PM Eastern Time.", body
        )
        self.assertIn(
            "Your next scan is scheduled for September 28, 2026 at 12:00 PM Eastern Time.",
            body,
        )
        self.assertIn(
            "If you have questions, please email at reports@cisa.dhs.gov.", body
        )
        self.assertIn(
            "Regards,\n\nSample Analyst\nWeb Application Scanning (WAS)", body
        )
        self.assertNotIn("<last_scan_date>", body)

    def test_approved_questions_override_preserves_other_contacts(self) -> None:
        """Apply the user's exact correction in both MIME bodies, nowhere else."""
        for html in (False, True):
            body = customer_report_body(
                "TAG", "Sample POC", "Targets Removed", "Sample Analyst",
                "https://example.gov", "2,1,1", "https://example.gov", None,
                None, None, html=html,
            )
            self.assertIn("If you have questions, please email at reports@cisa.dhs.gov.", body)
            self.assertNotIn("If you have questions, please email at vulnerability@cisa.dhs.gov.", body)
            self.assertIn("updated list of targets to vulnerability@cisa.dhs.gov.", body)
            self.assertIn("reports@cyber.dhs.gov", body)

    def test_all_nws_keeps_authoritative_policy_and_closing(self) -> None:
        """Honor the user's explicit verbatim decision for both All NWS variants."""
        for template in ("All NWS", "FCEB All NWS"):
            body = customer_report_body(
                "TAG",
                "Sample POC",
                template,
                "Sample Analyst",
                "https://example.gov",
                "1,1,0",
                None,
                None,
                None,
                None,
            )
            self.assertIn("will be removed from the scan target list", body)
            self.assertIn("Email: reports@cyber.dhs.gov", body)
            self.assertNotIn("Attached is a report", body)

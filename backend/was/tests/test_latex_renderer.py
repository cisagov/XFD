"""Tests for legacy-compatible Mustache and LaTeX report rendering."""

# Standard Python Libraries
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

# First-Party Libraries
from was_reports.reporting import latex_renderer


class LatexRendererTests(unittest.TestCase):
    """Validate deterministic LaTeX rendering and compilation behavior."""

    def test_escape_latex_preserves_legacy_mapping(self) -> None:
        """Escape the same special characters as the original generator."""
        escaped_value = latex_renderer.escape_latex("A&B_1[ok]<tag>")

        self.assertEqual(
            escaped_value,
            "A\\&B\\_1{[}ok{]}\\textless{}tag\\textgreater{}",
        )

    def test_organization_name_width_preserves_thresholds(self) -> None:
        """Preserve every legacy title-width threshold."""
        cases = (
            (13, "6cm"),
            (14, "8.5cm"),
            (25, "10cm"),
            (35, "12cm"),
            (40, "13cm"),
            (45, "16cm"),
            (55, "18cm"),
        )
        for name_length, expected_width in cases:
            with self.subTest(name_length=name_length):
                self.assertEqual(
                    latex_renderer.organization_name_width("A" * name_length),
                    expected_width,
                )

    def test_render_latex_template_uses_legacy_name_and_unescapes_html(self) -> None:
        """Render Mustache data into the legacy dated LaTeX filename."""
        with tempfile.TemporaryDirectory() as directory:
            working_directory = Path(directory)
            template_path = working_directory / "report.mustache"
            template_path.write_text(
                "{{=<< >>=}}Name: <<Name>>",
                encoding="utf-8",
            )

            tex_path = latex_renderer.render_latex_template(
                template_path=template_path,
                template_data={"Name": "CISA &amp; Partner"},
                stakeholder_tag="CUSTOMER",
                working_directory=working_directory,
                report_date=date(2026, 8, 27),
            )

            self.assertEqual(tex_path.name, "CUSTOMER_report_2026-08-27.tex")
            self.assertEqual(
                tex_path.read_text(encoding="utf-8"),
                "Name: CISA &amp; Partner",
            )

    def test_render_rejects_unsafe_stakeholder_tag(self) -> None:
        """Prevent stakeholder data from changing the report output path."""
        with tempfile.TemporaryDirectory() as directory:
            working_directory = Path(directory)
            template_path = working_directory / "report.mustache"
            template_path.write_text("report", encoding="utf-8")

            with self.assertRaises(ValueError):
                latex_renderer.render_latex_template(
                    template_path=template_path,
                    template_data={},
                    stakeholder_tag="../CUSTOMER",
                    working_directory=working_directory,
                )

    def test_compile_latex_runs_twice_and_requires_pdf(self) -> None:
        """Run the required two XeLaTeX passes and return the generated PDF."""
        commands = []

        def command_runner(command, **options) -> None:
            """Record the command and create output after the second pass."""
            commands.append((command, options))
            if len(commands) == 2:
                output_directory = Path(command[1].split("=", 1)[1])
                (output_directory / "CUSTOMER_report_2026-08-27.pdf").write_bytes(
                    b"%PDF-1.4"
                )

        with tempfile.TemporaryDirectory() as directory:
            working_directory = Path(directory)
            output_directory = working_directory / "docs"
            tex_path = working_directory / "CUSTOMER_report_2026-08-27.tex"
            tex_path.write_text("report", encoding="utf-8")

            pdf_path = latex_renderer.compile_latex_pdf(
                tex_path=tex_path,
                output_directory=output_directory,
                command_runner=command_runner,
            )

        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][0][0], "xelatex")
        self.assertTrue(commands[0][1]["check"])
        self.assertEqual(pdf_path.name, "CUSTOMER_report_2026-08-27.pdf")

    def test_compile_latex_propagates_command_failure(self) -> None:
        """Stop immediately when XeLaTeX reports a compilation failure."""
        def command_runner(command, **options) -> None:
            """Simulate a failed XeLaTeX process."""
            raise subprocess.CalledProcessError(1, command)

        with tempfile.TemporaryDirectory() as directory:
            working_directory = Path(directory)
            tex_path = working_directory / "report.tex"
            tex_path.write_text("report", encoding="utf-8")

            with self.assertRaises(subprocess.CalledProcessError):
                latex_renderer.compile_latex_pdf(
                    tex_path=tex_path,
                    output_directory=working_directory / "docs",
                    command_runner=command_runner,
                )

    def test_cleanup_removes_only_known_temporary_files(self) -> None:
        """Remove LaTeX intermediates without deleting the generated PDF."""
        with tempfile.TemporaryDirectory() as directory:
            working_directory = Path(directory)
            output_directory = working_directory / "docs"
            output_directory.mkdir()
            tex_path = working_directory / "report.tex"
            tex_path.write_text("report", encoding="utf-8")
            pdf_path = output_directory / "report.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")
            for extension in latex_renderer.LATEX_TEMPORARY_EXTENSIONS:
                (output_directory / "report{}".format(extension)).write_text(
                    "temporary",
                    encoding="utf-8",
                )

            latex_renderer.cleanup_latex_files(tex_path, output_directory)

            self.assertFalse(tex_path.exists())
            self.assertTrue(pdf_path.exists())
            for extension in latex_renderer.LATEX_TEMPORARY_EXTENSIONS:
                self.assertFalse(
                    (output_directory / "report{}".format(extension)).exists()
                )


if __name__ == "__main__":
    unittest.main()

"""Regression tests for the production-only WAS runtime boundary."""

# Standard Python Libraries
from pathlib import Path
import unittest


WAS_ROOT = Path(__file__).resolve().parents[1]


class ProductionBoundaryTests(unittest.TestCase):
    """Prevent supported commands from regaining historical dependencies."""

    def test_dockerfile_excludes_historical_runtime_directories(self) -> None:
        """Package only source-owned production modules in the image."""
        dockerfile = (WAS_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertNotIn("COPY was_report", dockerfile)
        self.assertNotIn("COPY update_tracker", dockerfile)
        self.assertNotIn("WAS_REPORT_GENERATION", dockerfile)
        self.assertIn("COPY src ./src", dockerfile)

    def test_production_source_has_no_historical_runtime_hooks(self) -> None:
        """Reject imports, paths, and flags that execute historical code."""
        forbidden_values = (
            "WAS_report_creator",
            "UPDATE_TRACKER_ROOT",
            "/app/update_tracker",
            "/app/was_report",
            "--use-legacy-pipeline",
            "from main import main as update_tracker_main",
        )
        source_files = sorted((WAS_ROOT / "src").rglob("*.py"))

        for source_file in source_files:
            source = source_file.read_text(encoding="utf-8")
            for forbidden_value in forbidden_values:
                self.assertNotIn(
                    forbidden_value,
                    source,
                    msg="{} contains {}".format(
                        source_file.relative_to(WAS_ROOT),
                        forbidden_value,
                    ),
                )

    def test_console_entrypoints_use_installed_source_packages(self) -> None:
        """Route every installed command to a package under src."""
        setup_source = (WAS_ROOT / "setup.py").read_text(encoding="utf-8")

        self.assertNotIn("was_report.", setup_source)
        self.assertNotIn("update_tracker.", setup_source)
        self.assertIn("was_reports.commands.batch_runner:main", setup_source)
        self.assertIn("was_mailer.email_reports:main", setup_source)

    def test_requirements_exclude_historical_only_dependencies(self) -> None:
        """Keep historical GUI, workbook, and Mongo packages out of runtime."""
        requirements = {
            line.strip().split("==", 1)[0].split(">=", 1)[0].lower()
            for line in (WAS_ROOT / "requirements.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        historical_only_dependencies = {
            "configparser",
            "customtkinter",
            "docker",
            "docopt",
            "fpdf",
            "openpyxl",
            "pyarrow",
            "pymongo",
            "python-docx",
            "pytz",
            "regex",
            "tqdm",
        }

        self.assertTrue(
            requirements.isdisjoint(historical_only_dependencies),
            msg="Historical-only packages remain in requirements.txt",
        )


if __name__ == "__main__":
    unittest.main()

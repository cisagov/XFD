"""Setup for the WAS reporting Python package."""

# Standard Python Libraries
from pathlib import Path

# Third-Party Libraries
from setuptools import find_packages, setup

ROOT = Path(__file__).parent


def load_requirements(path: Path) -> list[str]:
    """Read a requirements file, expanding included requirement files."""
    requirements: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            included_path = path.parent / line[3:].strip()
            requirements.extend(load_requirements(included_path))
            continue
        requirements.append(line)
    return requirements


setup(
    name="was_reporting",
    version="0.1.0",
    description="Web Application Scanning report generation and delivery",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    package_data={
        "was_reports.resources": [
            "*.mustache",
            "*.pdf",
            "assets/*",
            "assets/fonts/*",
        ],
    },
    install_requires=load_requirements(ROOT / "requirements.txt"),
    entry_points={
        "console_scripts": [
            "was-admin=was_reports.commands.admin_cli:main",
            "was-mailer=was_mailer.email_reports:main",
            "was-compare-reports=was_reports.reporting.report_comparison:main",
            "was-report-batch=was_reports.commands.batch_runner:main",
            "was-reports=was_reports.commands.report_generator:main",
            "was-export-xml=was_reports.commands.xml_export_cli:main",
            "was-inventory=was_reports.commands.inventory_cli:main",
            "was-special-cases=was_reports.commands.special_cases_cli:main",
            "was-tracker=was_reports.commands.tracker_cli:main",
            "was-update-tracker=was_reports.commands.update_tracker_cli:main",
        ],
    },
    python_requires=">=3.12",
)

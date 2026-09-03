"""CLI boundary for running WAS report generation."""

# Standard Python Libraries
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from tempfile import gettempdir
from typing import List, Optional

# Third-Party Libraries
from was_reports.utils.env import getenv

DEFAULT_WORKSPACE_ROOT = str(Path(gettempdir()) / "was-report-workspaces")


def validate_stakeholder_tag(stakeholder_tag: str) -> str:
    """Validate and normalize the stakeholder tag supplied by the caller."""
    normalized_tag = stakeholder_tag.strip()
    if not normalized_tag:
        raise ValueError("Stakeholder tag is required.")
    return normalized_tag


def resolve_report_password(
    stakeholder_tag: str,
    report_password: Optional[str],
    create_missing_password: bool = False,
) -> str:
    """Resolve the password from CLI input or Postgres stakeholder data."""
    if report_password:
        return report_password

    stored_password = lookup_report_password(stakeholder_tag)
    if stored_password:
        return stored_password

    if create_missing_password:
        return create_report_password(stakeholder_tag)

    raise RuntimeError(
        "No report password found for stakeholder tag {}.".format(
            stakeholder_tag
        )
    )


def lookup_report_password(stakeholder_tag: str) -> Optional[str]:
    """Read a stakeholder report password from Postgres."""
    # Third-Party Libraries
    from was_reports.data.stakeholders import get_report_password

    return get_report_password(stakeholder_tag)


def create_report_password(stakeholder_tag: str) -> str:
    """Create and store a report password for a stakeholder tag."""
    # Third-Party Libraries
    from was_reports.data.stakeholders import create_report_password_for_tag

    return create_report_password_for_tag(stakeholder_tag)


def rotate_report_password(stakeholder_tag: str) -> str:
    """Generate and store a new report password for a stakeholder tag."""
    # Third-Party Libraries
    from was_reports.data.stakeholders import rotate_report_password_for_tag

    return rotate_report_password_for_tag(stakeholder_tag)


def generate_production_report(
    stakeholder_tag: str,
    resource_root: Path,
    workspace_root: Path,
    output_directory: Path,
    python_executable: str,
    report_password: str,
) -> Path:
    """Run the production report pipeline and return its encrypted PDF."""
    # Third-Party Libraries
    from was_reports.qualys.qualys_client import create_qualys_client
    from was_reports.reporting.report_service import generate_encrypted_report
    from was_reports.utils.qualys_config import (
        load_qualys_credentials_from_environment,
    )

    credentials = load_qualys_credentials_from_environment()
    client = create_qualys_client(credentials)
    return generate_encrypted_report(
        client=client,
        credentials=credentials,
        stakeholder_tag=stakeholder_tag,
        resource_root=resource_root,
        workspace_root=workspace_root,
        output_directory=output_directory,
        python_executable=python_executable,
        current_time=datetime.now(timezone.utc),
        report_password=report_password,
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments for WAS report generation."""
    default_resource_root = getenv(
        "WAS_RESOURCE_ROOT",
        "/WAS_REPORT_RESOURCES",
    )
    default_output_directory = getenv(
        "WAS_OUTPUT_DIRECTORY", "/output"
    )
    default_workspace_root = getenv(
        "WAS_WORKSPACE_ROOT",
        DEFAULT_WORKSPACE_ROOT,
    )

    parser = argparse.ArgumentParser(
        description="Generate a WAS PDF report for one stakeholder tag."
    )
    parser.add_argument(
        "-t",
        "--tag",
        required=True,
        help="Stakeholder tag to report on.",
    )
    parser.add_argument(
        "--report-password",
        "--encrypt",
        dest="report_password",
        help="Password used to encrypt the PDF report.",
    )
    parser.add_argument(
        "--create-missing-password",
        action="store_true",
        help=(
            "Create and save a stakeholder report password when one is absent."
        ),
    )
    parser.add_argument(
        "--change-password",
        action="store_true",
        help=(
            "Generate and store a new stakeholder report password, then exit."
        ),
    )
    parser.add_argument(
        "--resource-root",
        default=default_resource_root,
        help=(
            "Directory containing production WAS templates and report assets."
        ),
    )
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable used for report helper subprocesses.",
    )
    parser.add_argument(
        "--output-directory",
        default=default_output_directory,
        help="Directory where generated WAS PDF reports are written.",
    )
    parser.add_argument(
        "--workspace-root",
        default=default_workspace_root,
        help="Temporary root for isolated production report workspaces.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run WAS report generation from CLI arguments."""
    args = parse_args(argv)
    stakeholder_tag = validate_stakeholder_tag(args.tag)
    resource_root = Path(args.resource_root)

    if args.change_password:
        rotate_report_password(stakeholder_tag)
        return 0

    report_password = resolve_report_password(
        stakeholder_tag=stakeholder_tag,
        report_password=args.report_password,
        create_missing_password=args.create_missing_password,
    )
    generate_production_report(
        stakeholder_tag=stakeholder_tag,
        resource_root=resource_root,
        workspace_root=Path(args.workspace_root),
        output_directory=Path(args.output_directory),
        python_executable=args.python_executable,
        report_password=report_password,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

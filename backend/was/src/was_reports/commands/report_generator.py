"""CLI boundary for running WAS report generation."""

# Standard Python Libraries
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess  # nosec B404
import sys
from tempfile import gettempdir
from typing import List, Optional

# Third-Party Libraries
from was_reports.utils.env import getenv
from was_reports.utils.outputs import expected_pdf_output_path, require_output_file
from was_reports.utils.qualys_config import (
    ensure_qualys_config_file,
    validate_qualys_config,
)

LEGACY_CONFIG_PATH = Path("/WAS_REPORT_GENERATION/docs/was_config.txt")
DEFAULT_WORKSPACE_ROOT = str(Path(gettempdir()) / "was-report-workspaces")
UNENCRYPTED_SENTINEL = "N/A"


def validate_stakeholder_tag(stakeholder_tag: str) -> str:
    """Validate and normalize the stakeholder tag supplied by the caller."""
    normalized_tag = stakeholder_tag.strip()
    if not normalized_tag:
        raise ValueError("Stakeholder tag is required.")
    return normalized_tag


def resolve_report_password(
    stakeholder_tag: str,
    report_password: Optional[str],
    allow_unencrypted: bool,
    create_missing_password: bool = False,
) -> str:
    """Resolve the report password from CLI input or Postgres stakeholder data."""
    if report_password:
        return report_password

    stored_password = lookup_report_password(stakeholder_tag)
    if stored_password:
        return stored_password

    if create_missing_password:
        return create_report_password(stakeholder_tag)

    if allow_unencrypted:
        return UNENCRYPTED_SENTINEL

    raise RuntimeError(
        "No report password found for stakeholder tag {}.".format(stakeholder_tag)
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


def prepare_legacy_config(config_path: Path) -> None:
    """Place the Qualys config where the legacy creator currently expects it."""
    ensured_config_path = ensure_qualys_config_file(config_path)
    validate_qualys_config(ensured_config_path)

    LEGACY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if ensured_config_path.resolve() == LEGACY_CONFIG_PATH.resolve():
        return

    shutil.copyfile(str(ensured_config_path), str(LEGACY_CONFIG_PATH))


def build_legacy_command(
    python_executable: str,
    script_path: Path,
    stakeholder_tag: str,
) -> List[str]:
    """Build the legacy command without placing its password in arguments."""
    return [
        python_executable,
        str(script_path),
        "-t",
        stakeholder_tag,
    ]


def build_legacy_input(report_password: str) -> str:
    """Build responses for the frozen legacy encryption prompts."""
    if report_password == UNENCRYPTED_SENTINEL:
        return "N\n"
    return "Y\n{}\n".format(report_password)


def run_legacy_report(
    python_executable: str,
    legacy_root: Path,
    stakeholder_tag: str,
    report_password: str,
) -> subprocess.CompletedProcess:
    """Run the legacy WAS report creator from its asset directory."""
    script_path = legacy_root / "WAS_report_creator.py"
    if not script_path.exists():
        raise FileNotFoundError(
            "Legacy WAS report creator not found at {}.".format(str(script_path))
        )

    command = build_legacy_command(
        python_executable=python_executable,
        script_path=script_path,
        stakeholder_tag=stakeholder_tag,
    )
    return subprocess.run(  # nosec B603
        command,
        cwd=str(legacy_root),
        check=True,
        input=build_legacy_input(report_password),
        text=True,
    )


def generate_report(
    stakeholder_tag: str,
    config_path: Path,
    legacy_root: Path,
    output_directory: str,
    python_executable: str,
    report_password: str,
) -> Path:
    """Run the legacy generator and return the verified PDF output path."""
    prepare_legacy_config(config_path)
    run_legacy_report(
        python_executable=python_executable,
        legacy_root=legacy_root,
        stakeholder_tag=stakeholder_tag,
        report_password=report_password,
    )
    output_path = expected_pdf_output_path(
        stakeholder_tag=stakeholder_tag,
        output_directory=output_directory,
    )
    return require_output_file(output_path)


def generate_production_report(
    stakeholder_tag: str,
    config_path: Path,
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
    from was_reports.utils.qualys_config import load_qualys_credentials

    credentials = load_qualys_credentials(config_path)
    client = create_qualys_client(config_path)
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
    default_config_path = getenv(
        "WAS_CONFIG_PATH", "/WAS_REPORT_GENERATION/docs/was_config.txt"
    )
    default_legacy_root = getenv("WAS_LEGACY_ROOT", "/WAS_REPORT_GENERATION")
    default_resource_root = getenv("WAS_RESOURCE_ROOT", "/WAS_REPORT_RESOURCES")
    default_output_directory = getenv(
        "WAS_OUTPUT_DIRECTORY", "/WAS_REPORT_GENERATION/docs"
    )
    default_workspace_root = getenv("WAS_WORKSPACE_ROOT", DEFAULT_WORKSPACE_ROOT)

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
        "--allow-unencrypted",
        action="store_true",
        help="Allow an unencrypted frozen-legacy comparison report.",
    )
    parser.add_argument(
        "--create-missing-password",
        action="store_true",
        help="Create and save a stakeholder report password when one is absent.",
    )
    parser.add_argument(
        "--change-password",
        action="store_true",
        help="Generate and store a new stakeholder report password, then exit.",
    )
    parser.add_argument(
        "--config-path",
        default=default_config_path,
        help="Path to was_config.txt.",
    )
    parser.add_argument(
        "--legacy-root",
        default=default_legacy_root,
        help="Directory containing the frozen WAS_report_creator.py.",
    )
    parser.add_argument(
        "--resource-root",
        default=default_resource_root,
        help="Directory containing production WAS templates and report assets.",
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
    parser.add_argument(
        "--use-extracted-pipeline",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--use-legacy-pipeline",
        action="store_true",
        help="Use the frozen legacy script for controlled report comparison.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run WAS report generation from CLI arguments."""
    args = parse_args(argv)
    stakeholder_tag = validate_stakeholder_tag(args.tag)
    config_path = Path(args.config_path)
    legacy_root = Path(args.legacy_root)
    resource_root = Path(args.resource_root)

    if args.change_password:
        rotate_report_password(stakeholder_tag)
        return 0

    report_password = resolve_report_password(
        stakeholder_tag=stakeholder_tag,
        report_password=args.report_password,
        allow_unencrypted=args.allow_unencrypted,
        create_missing_password=args.create_missing_password,
    )
    if args.use_legacy_pipeline:
        generate_report(
            stakeholder_tag=stakeholder_tag,
            config_path=config_path,
            legacy_root=legacy_root,
            output_directory=args.output_directory,
            python_executable=args.python_executable,
            report_password=report_password,
        )
        return 0

    if args.allow_unencrypted:
        raise ValueError("The production WAS pipeline requires PDF encryption.")

    generate_production_report(
        stakeholder_tag=stakeholder_tag,
        config_path=config_path,
        resource_root=resource_root,
        workspace_root=Path(args.workspace_root),
        output_directory=Path(args.output_directory),
        python_executable=args.python_executable,
        report_password=report_password,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

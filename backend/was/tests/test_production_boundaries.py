"""Regression tests for the production-only WAS runtime boundary."""

# Standard Python Libraries
from pathlib import Path
import unittest

WAS_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WAS_ROOT.parents[1]


class ProductionBoundaryTests(unittest.TestCase):
    """Prevent supported commands from regaining historical dependencies."""

    def test_dockerfile_excludes_historical_runtime_directories(self) -> None:
        """Package only source-owned production modules in the image."""
        dockerfile = (WAS_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertNotIn("COPY was_report", dockerfile)
        self.assertNotIn("COPY update_tracker", dockerfile)
        self.assertNotIn("WAS_REPORT_GENERATION", dockerfile)
        self.assertIn("COPY src ./src", dockerfile)

    def test_dockerfile_uses_pinned_python_and_non_root_runtime(self) -> None:
        """Keep the production runtime reproducible and least privileged."""
        dockerfile = (WAS_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn(
            "FROM python:3.12.13-slim-trixie@sha256:",
            dockerfile,
        )
        self.assertIn("USER was-reporting", dockerfile)

    def test_docker_build_context_is_an_explicit_allowlist(self) -> None:
        """Keep local reports, logs, exports, and environment files out of builds."""
        dockerignore_lines = [
            line.strip()
            for line in (WAS_ROOT / ".dockerignore")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        required_inputs = {
            "!Dockerfile",
            "!requirements.txt",
            "!setup.py",
            "!schema/",
            "!schema/**",
            "!src/",
            "!src/**",
            "!worker/",
            "!worker/**",
        }

        self.assertEqual(dockerignore_lines[0], "**")
        self.assertTrue(required_inputs.issubset(dockerignore_lines))
        self.assertFalse(
            any(
                line.startswith("!")
                and line.lower().endswith((".csv", ".xlsx", ".zip", ".env"))
                for line in dockerignore_lines
            )
        )

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

    def test_authoritative_schema_defines_required_special_cases(self) -> None:
        """Keep required deletion exemptions in the authoritative database SQL."""
        schema_source = (
            WAS_ROOT / "schema" / "stakeholders_table_creation.sql"
        ).read_text(encoding="utf-8")
        special_cases_section = schema_source.split(
            "CREATE TABLE was_special_cases", 1
        )[1].split("ALTER TABLE was_report_runs", 1)[0]

        self.assertIn(
            "INSERT INTO was_special_cases (value)",
            special_cases_section,
        )
        for value in ("CROSSFEED", "CBOE", "SCCCS"):
            self.assertIn("('{}')".format(value), special_cases_section)
        self.assertIn("ON CONFLICT (value) DO UPDATE SET", special_cases_section)
        self.assertIn("active = TRUE", special_cases_section)

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

    def test_runtime_requirements_are_exactly_pinned(self) -> None:
        """Prevent production dependency resolution from drifting between builds."""
        requirement_lines = [
            line.strip()
            for line in (WAS_ROOT / "requirements.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertTrue(requirement_lines)
        self.assertTrue(all("==" in line for line in requirement_lines))

    def test_was_instance_policy_uses_exact_resources(self) -> None:
        """Keep WAS cross-service permissions narrowly scoped."""
        terraform_source = (
            REPOSITORY_ROOT / "infrastructure" / "was-reporting.tf"
        ).read_text(encoding="utf-8")

        self.assertNotIn('"s3:DeleteObject"', terraform_source)
        self.assertIn("/was_reports/*", terraform_source)
        self.assertIn("/capacity/*", terraform_source)
        self.assertIn('Action   = "sts:AssumeRole"', terraform_source)
        self.assertIn("Resource = var.was_reporting_ses_role_arn", terraform_source)

    def test_was_first_boot_uses_only_the_dedicated_minimal_bootstrap(self) -> None:
        """Keep manifest installation separate from Terraform first boot."""
        terraform_source = (
            REPOSITORY_ROOT / "infrastructure" / "was-reporting.tf"
        ).read_text(encoding="utf-8")
        bootstrap_source = (
            REPOSITORY_ROOT / "infrastructure" / "was-reporting-bootstrap.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("was-reporting-bootstrap.sh", terraform_source)
        self.assertNotIn("open-cti/install-deps.sh", terraform_source)
        self.assertIn("apt-get install", bootstrap_source)
        self.assertIn("git", bootstrap_source)
        self.assertIn("make", bootstrap_source)
        self.assertIn("openssh-client", bootstrap_source)
        self.assertIn("python3", bootstrap_source)
        self.assertNotIn("awscli", bootstrap_source)
        self.assertNotIn("docker-ce", bootstrap_source)

    def test_operator_runbook_uses_develop_and_pinned_uv_environment(self) -> None:
        """Keep checkout updates and the named Python environment reproducible."""
        operator_runbook = (
            REPOSITORY_ROOT
            / "backend"
            / "was"
            / "docs"
            / "operator-setup-and-commands.md"
        ).read_text(encoding="utf-8")
        rebuild_runbook = (
            REPOSITORY_ROOT / "backend" / "was" / "docs" / "host-rebuild-cycle.md"
        ).read_text(encoding="utf-8")

        self.assertIn("git clone --branch develop --single-branch", operator_runbook)
        self.assertIn("git@github.com:cisagov/XFD.git was_report", operator_runbook)
        self.assertIn("git pull --ff-only origin develop", operator_runbook)
        self.assertNotIn("git pull --ff-only origin cd_WAS_update", operator_runbook)
        for documentation in (operator_runbook, rebuild_runbook):
            self.assertIn("$HOME/code/was_report", documentation)
            self.assertNotIn("$HOME/code/cd_WAS_update", documentation)
            self.assertIn('"$HOME/.local/bin/uv" venv', documentation)
            self.assertIn("--python 3.12.14", documentation)
            self.assertIn("--seed", documentation)
            self.assertIn("../../was_report/bin/python -m pip --version", documentation)
            self.assertIn("make host-shell-preview", documentation)
            self.assertIn("make host-shell-install APPLY=1", documentation)
            self.assertIn("make host-operator-scripts-preview", documentation)
            self.assertIn("make host-operator-scripts-install APPLY=1", documentation)

    def test_was_arn_validations_reject_wildcards_without_newer_functions(self) -> None:
        """Keep IAM resources exact and Terraform 1.0.7 compatible."""
        variables_source = (REPOSITORY_ROOT / "infrastructure" / "vars.tf").read_text(
            encoding="utf-8"
        )
        kms_validation = variables_source.split(
            'variable "was_reporting_reports_kms_key_arn"', 1
        )[1].split('variable "was_reporting_ses_role_arn"', 1)[0]
        ses_validation = variables_source.split(
            'variable "was_reporting_ses_role_arn"', 1
        )[1].split('variable "was_reporting_ami_id"', 1)[0]

        for validation in (kms_validation, ses_validation):
            self.assertNotIn("startswith(", validation)
            self.assertNotIn("nullable", validation)
            self.assertIn("replace(", validation)
            self.assertIn('"*", ""', validation)
            self.assertIn('"?", ""', validation)
            self.assertIn("for index in range(12)", validation)
            self.assertNotIn("tonumber(", validation)


if __name__ == "__main__":
    unittest.main()

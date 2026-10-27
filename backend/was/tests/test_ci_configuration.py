"""Regression tests for the isolated WAS continuous-integration job."""

# Standard Python Libraries
from pathlib import Path
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "was.yml"


class WasCiConfigurationTests(unittest.TestCase):
    """Keep WAS tests enabled with an isolated PostgreSQL service."""

    def setUp(self) -> None:
        """Load the tracked workflow without reading runtime environment files."""
        self.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_workflow_runs_complete_was_test_target(self) -> None:
        """Run the same unit and integration suite used by local development."""
        self.assertIn('python-version: "3.12"', self.workflow)
        self.assertIn("backend/was/requirements.txt", self.workflow)
        self.assertIn("make test PYTHON=python ROOT_PYTHON=python", self.workflow)

    def test_workflow_uses_only_isolated_postgresql_configuration(self) -> None:
        """Enable database tests without production credentials or metadata access."""
        self.assertIn("image: postgres:17.6", self.workflow)
        self.assertIn("POSTGRES_DB: was_test_ci", self.workflow)
        self.assertIn("WAS_TEST_DATABASE_DSN:", self.workflow)
        self.assertIn("/was_test_ci", self.workflow)
        self.assertIn('AWS_EC2_METADATA_DISABLED: "true"', self.workflow)
        self.assertNotIn("secrets.", self.workflow)
        self.assertNotIn("env-file", self.workflow)


if __name__ == "__main__":
    unittest.main()

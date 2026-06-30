"""Tests for PE environment-based configuration."""

# Standard Python Libraries
import os
import unittest

# Third-Party Libraries
from pe_reports.data.config import config, staging_config


class PeConfigTests(unittest.TestCase):
    """Verify PE config helpers read environment variables."""

    def setUp(self):
        """Save and override PE-related environment variables."""
        self.env = {
            "PE_DB_NAME": "pe",
            "PE_DB_USERNAME": "pe_user",
            "PE_DB_PASSWORD": "pe-test-password",  # nosec B105
            "DB_HOST": "db.example",
            "PE_API_URL": "http://127.0.0.1:8000",
            "PE_API_KEY": "abc123",
        }
        self._saved = {key: os.environ.get(key) for key in self.env}
        os.environ.update(self.env)

    def tearDown(self):
        """Restore the original environment."""
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_postgres_config_reads_env(self):
        """Postgres config should map PE_DB_* and DB_HOST from the environment."""
        db = config()
        self.assertEqual(db["host"], "db.example")
        self.assertEqual(db["database"], "pe")
        self.assertEqual(db["user"], "pe_user")
        self.assertEqual(db["password"], "pe-test-password")

    def test_api_config_normalizes_apiv1_prefix(self):
        """API config should normalize PE_API_URL to include /apiv1/."""
        api = staging_config(section="pe_api")
        self.assertEqual(api["pe_api_url"], "http://127.0.0.1:8000/apiv1/")
        self.assertEqual(api["pe_api_key"], "abc123")


if __name__ == "__main__":
    unittest.main()

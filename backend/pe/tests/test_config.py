"""Tests for PE environment-based configuration."""

# Standard Python Libraries
import os
import unittest

from pe_reports.data.config import config, staging_config


class PeConfigTests(unittest.TestCase):
  def setUp(self):
    self.env = {
      "PE_DB_NAME": "pe",
      "PE_DB_USERNAME": "pe_user",
      "PE_DB_PASSWORD": "secret",
      "DB_HOST": "db.example",
      "PE_API_URL": "http://127.0.0.1:8000",
      "PE_API_KEY": "abc123",
    }
    self._saved = {key: os.environ.get(key) for key in self.env}
    os.environ.update(self.env)

  def tearDown(self):
    for key, value in self._saved.items():
      if value is None:
        os.environ.pop(key, None)
      else:
        os.environ[key] = value

  def test_postgres_config_reads_env(self):
    db = config()
    self.assertEqual(db["host"], "db.example")
    self.assertEqual(db["database"], "pe")
    self.assertEqual(db["user"], "pe_user")
    self.assertEqual(db["password"], "secret")

  def test_api_config_normalizes_apiv1_prefix(self):
    api = staging_config(section="pe_api")
    self.assertEqual(api["pe_api_url"], "http://127.0.0.1:8000/apiv1/")
    self.assertEqual(api["pe_api_key"], "abc123")


if __name__ == "__main__":
  unittest.main()

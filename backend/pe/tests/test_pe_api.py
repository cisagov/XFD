"""Tests for the in-container PE FastAPI surface."""

# Standard Python Libraries
import os
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pe_reports_django.settings")
os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
from fastapi.testclient import TestClient
from pe_reports_django.asgi import app


class PeApiTests(unittest.TestCase):
  def setUp(self):
    self.client = TestClient(app)

  def test_health_does_not_require_auth(self):
    response = self.client.get("/apiv1/health")
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json(), {"status": "ok"})

  def test_protected_endpoint_requires_api_key(self):
    response = self.client.get("/apiv1/organizations_demo_or_report_on")
    self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
  unittest.main()

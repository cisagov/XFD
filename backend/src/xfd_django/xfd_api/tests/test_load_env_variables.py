"""Tests for load_env_variables."""
# Standard Python Libraries
import io
import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

# Third-Party Libraries
import pytest
from xfd_django.helpers.load_env_variables import load_django_config

# Ensure /app/src is on sys.path for imports like xfd_django.helpers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


@pytest.fixture
def fake_env_file(tmp_path):
    """Create a temporary env.json file."""
    data = {
        "DB_HOST": "localhost",
        "DB_NAME": "testdb",
        "IS_LOCAL": True,
        "JWT_SECRET": "testsecret",
    }
    env_path = tmp_path / "env.json"
    env_path.write_text(json.dumps(data))
    return env_path


def test_load_local_env(monkeypatch, fake_env_file):
    """Ensure local env.json loads and sets environment variables."""
    # Pretend we're running locally
    monkeypatch.setenv("IS_LOCAL", "true")

    # Point the loader to our temporary env.json
    with patch("xfd_django.helpers.load_env_variables.Path.resolve") as mock_resolve:
        mock_resolve.return_value = fake_env_file
        load_django_config()

    assert os.getenv("DB_HOST") == "localhost"
    assert os.getenv("JWT_SECRET") == "testsecret"
    assert os.getenv("DB_NAME") == "testdb"


def test_s3_cache_load(monkeypatch, tmp_path):
    """Ensure that cached env.json is used instead of fetching from S3."""
    cache_path = "/tmp/env.json"  # nosec B108
    cached_data = {"DB_HOST": "cached-db", "DB_NAME": "cached"}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cached_data, f)

    # Make cache fresh (younger than TTL)
    os.utime(cache_path, (time.time(), time.time()))

    monkeypatch.delenv("IS_LOCAL", raising=False)
    monkeypatch.setenv("DJANGO_CONFIG_BUCKET", "test-bucket")
    monkeypatch.setenv("DJANGO_CONFIG_KEY", "env.json")

    with patch("boto3.client") as mock_boto:
        load_django_config(ttl_seconds=3600)

    # Verify S3 was NOT called since cache was used
    mock_boto.assert_not_called()
    assert os.getenv("DB_HOST") == "cached-db"


def test_s3_fallback_to_stale_cache(monkeypatch):
    """If S3 fails, use existing stale cached config."""
    cache_path = "/tmp/env.json"  # nosec B108
    stale_data = {"DB_HOST": "stale-db"}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(stale_data, f)
    os.utime(cache_path, (time.time() - 9999, time.time() - 9999))

    monkeypatch.delenv("IS_LOCAL", raising=False)
    monkeypatch.setenv("DJANGO_CONFIG_BUCKET", "test-bucket")

    # Mock boto3 to throw error
    with patch("boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_client.get_object.side_effect = Exception("S3 failure")
        mock_boto.return_value = mock_client

        load_django_config(ttl_seconds=1)

    assert os.getenv("DB_HOST") == "stale-db"


def test_s3_fetch_and_cache(monkeypatch):
    """Ensure fresh S3 fetch is cached and injected."""
    body = json.dumps({"DB_HOST": "from-s3", "DB_NAME": "fetched"}).encode("utf-8")

    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": io.BytesIO(body)}

    monkeypatch.delenv("IS_LOCAL", raising=False)
    monkeypatch.setenv("DJANGO_CONFIG_BUCKET", "test-bucket")

    with patch("boto3.client", return_value=mock_client):
        load_django_config(ttl_seconds=1)

    assert os.getenv("DB_HOST") == "from-s3"
    assert os.path.exists("/tmp/env.json")  # nosec B108

"""Test PE scan execution."""
# Standard Python Libraries
import os
from unittest.mock import patch

# pe_scanExecution creates an ECS client at import time; CI has no default region.
os.environ.setdefault("AWS_REGION", "us-east-1")

# Third-Party Libraries
import pytest
from xfd_api.tasks.pe_scanExecution import handler, start_desired_tasks
from xfd_mini_dl.models import Scan, ScanTask


@pytest.fixture(autouse=True)
def pe_ecs_mode(monkeypatch):
    """PE scan execution tests target the Fargate path, not local Docker workers."""
    monkeypatch.delenv("IS_LOCAL", raising=False)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_pe_shodan_insufficient_api_keys_blocks():
    """PE Shodan won't run if not enough keys for desired count."""
    scan = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)

    with patch("xfd_api.tasks.pe_scanExecution.ecs_client.run_task") as mock_run:
        start_desired_tasks(
            scan_type="shodan",
            desired_count=3,
            scan_id=str(scan.id),
            organizations=[],
            shodan_api_keys=["key1", "key2"],
        )
        mock_run.assert_not_called()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_pe_starts_ecs_task():
    """PE scan starts a Fargate task with the correct overrides."""
    scan = Scan.objects.create(name="dnstwist", concurrent_tasks=1, frequency=86400)

    with patch("xfd_api.tasks.pe_scanExecution.ecs_client.run_task") as mock_run:
        start_desired_tasks(
            scan_type="dnstwist",
            desired_count=1,
            scan_id=str(scan.id),
            organizations=[],
        )
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["count"] == 1
        overrides = call_kwargs["overrides"]["containerOverrides"][0]["environment"]
        assert {"name": "SERVICE_TYPE", "value": "dnstwist"} in overrides


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_pe_handler_returns_400_without_scan_type():
    """PE handler rejects events missing scanType."""
    result = handler({}, None)
    assert result["status_code"] == 400


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_pe_handler_shodan_fails_if_api_keys_insufficient():
    """PE handler returns 400 when Shodan keys are insufficient."""
    scan = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)

    with patch("xfd_api.tasks.pe_scanExecution.ecs_client.run_task") as mock_run:
        result = handler(
            {
                "scanType": "shodan",
                "scanId": str(scan.id),
                "desiredCount": 3,
                "apiKeyList": "k1,k2",
            },
            None,
        )
        mock_run.assert_not_called()
        assert result["status_code"] == 400


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_pe_concurrency_blocked_when_max_reached():
    """PE respects global concurrency limits from ScanTask records."""
    scan_a = Scan.objects.create(name="dnstwist", concurrent_tasks=2, frequency=86400)
    for i in range(2):
        ScanTask.objects.create(
            scan=scan_a, concurrency_index=i + 1, status="started", type="fargate"
        )

    scan_b = Scan.objects.create(name="dnstwist", concurrent_tasks=2, frequency=86400)

    with patch("xfd_api.tasks.pe_scanExecution.ecs_client.run_task") as mock_run:
        start_desired_tasks(
            scan_type="dnstwist",
            desired_count=1,
            scan_id=str(scan_b.id),
            organizations=[],
        )
        mock_run.assert_not_called()

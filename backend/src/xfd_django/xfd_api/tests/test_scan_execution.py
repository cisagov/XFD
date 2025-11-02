"""Test scan execution."""
# Standard Python Libraries
import os
from unittest.mock import patch

# Third-Party Libraries
import pytest
from xfd_api.tasks.scanExecution import handler, start_desired_tasks
from xfd_mini_dl.models import Scan, ScanTask


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_concurrency_blocked_when_max_reached():
    """If 3 tasks are already running for 'shodan' and max is 3, no more should start."""
    scan_a = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)
    for i in range(3):
        ScanTask.objects.create(
            scan=scan_a, concurrency_index=i + 1, status="started", type="fargate"
        )

    scan_b = Scan.objects.create(name="shodan", concurrent_tasks=2, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        start_desired_tasks(
            scan_type="shodan",
            desired_count=2,
            scan_id=str(scan_b.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["key1", "key2"],
        )
        mock_run.assert_not_called()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_partial_launch_allowed():
    """If 2 running and max is 3, then 1 more can be started."""
    scan_a = Scan.objects.create(name="shodan", concurrent_tasks=2, frequency=86400)
    for i in range(2):
        ScanTask.objects.create(
            scan=scan_a, concurrency_index=i + 1, status="started", type="fargate"
        )

    scan_b = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.return_value = {"tasks": [{"taskArn": "arn:task-1"}]}
        start_desired_tasks(
            scan_type="shodan",
            desired_count=3,
            scan_id=str(scan_b.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["key1", "key2", "key3"],
        )
        mock_run.assert_called_once()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_exact_fill_should_block_followup():
    """If 2 tasks already running from this scan, further attempts should be blocked."""
    scan = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)
    for i in range(2):
        ScanTask.objects.create(
            scan=scan, concurrency_index=i + 1, status="started", type="fargate"
        )

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        start_desired_tasks(
            scan_type="shodan",
            desired_count=2,
            scan_id=str(scan.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["key1", "key2", "key3"],
        )
        mock_run.assert_not_called()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_no_conflict_if_same_name_no_overlap():
    """If another scan of same name has 0 running, tasks can still start from a new scan."""
    Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)
    scan_b = Scan.objects.create(name="shodan", concurrent_tasks=2, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.side_effect = [
            {"tasks": [{"taskArn": "arn:task-1"}]},
            {"tasks": [{"taskArn": "arn:task-2"}]},
        ]
        start_desired_tasks(
            scan_type="shodan",
            desired_count=2,
            scan_id=str(scan_b.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["key1", "key2"],
        )
        assert mock_run.call_count == 2


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_insufficient_api_keys_blocks():
    """Test Shodan won't run if not enough keys for concurrent tasks."""
    scan = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        start_desired_tasks(
            scan_type="shodan",
            desired_count=3,
            scan_id=str(scan.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["key1", "key2"],
        )
        mock_run.assert_not_called()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_non_shodan_uses_batch_size_10():
    """Test Non-shodan scans call ECS in batches of 10."""
    scan = Scan.objects.create(name="censys", concurrent_tasks=10, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.return_value = {
            "tasks": [{"taskArn": "arn:task-{}".format(i)} for i in range(10)]
        }
        start_desired_tasks(
            scan_type="censys",
            desired_count=10,
            scan_id=str(scan.id),
            organizations=[],
            is_pe=False,
        )
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        command_options = args[0]  # first positional arg
        assert command_options["count"] == 10


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_followup_scan_should_start_one_more():
    """If Scan A starts 2 and Scan B (same name) tries again, it should launch only 1 more."""
    scan_a = Scan.objects.create(name="shodan", concurrent_tasks=2, frequency=86400)
    for i in range(2):
        ScanTask.objects.create(
            scan=scan_a, concurrency_index=i + 1, status="started", type="fargate"
        )

    scan_b = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.return_value = {"tasks": [{"taskArn": "arn:task-3"}]}
        start_desired_tasks(
            scan_type="shodan",
            desired_count=3,  # wants 3
            scan_id=str(scan_b.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["key1", "key2", "key3"],
        )
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        command_options = args[0]
        assert command_options["count"] == 1
        assert command_options["SHODAN_API_KEY"] == "key3"

    # Also check that the ScanTask was created with concurrency_index=3
    task = ScanTask.objects.filter(scan=scan_b).first()
    assert task is not None
    assert task.concurrency_index == 3


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_respects_concurrent_limit_across_scans():
    """Test a non-shodan scan will respect the conurrent tasks of other tasks named the same."""
    scan_a = Scan.objects.create(name="censys", concurrent_tasks=2, frequency=86400)
    scan_b = Scan.objects.create(name="censys", concurrent_tasks=1, frequency=86400)

    for i in range(2):
        ScanTask.objects.create(
            scan=scan_a, concurrency_index=i + 1, status="started", type="fargate"
        )

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        start_desired_tasks(
            scan_type="censys",
            desired_count=1,
            scan_id=str(scan_b.id),
            organizations=[],
            is_pe=False,
        )
        mock_run.assert_not_called()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_can_run_if_capacity_available():
    """Test censys can run if capacity available."""
    scan_a = Scan.objects.create(name="censys", concurrent_tasks=2, frequency=86400)
    scan_b = Scan.objects.create(name="censys", concurrent_tasks=2, frequency=86400)
    ScanTask.objects.create(
        scan=scan_a, concurrency_index=1, status="started", type="fargate"
    )

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.return_value = {"tasks": [{"taskArn": "arn:task-1"}]}
        start_desired_tasks(
            scan_type="censys",
            desired_count=2,
            scan_id=str(scan_b.id),
            organizations=[],
            is_pe=False,
        )
        mock_run.assert_called_once()
        assert len(mock_run.return_value["tasks"]) == 1


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_manual_run_pending_ignores_frequency():
    """Test manual run ignores frequency."""
    scan = Scan.objects.create(
        name="censys", concurrent_tasks=1, frequency=1, manual_run_pending=True
    )

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.return_value = {"tasks": [{"taskArn": "arn:task-x"}]}
        handler(
            {
                "scanType": "censys",
                "desiredCount": 1,
                "scanId": str(scan.id),
                "organizations": [],
                "isPe": False,
            },
            None,
        )
        mock_run.assert_called_once()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_fails_if_api_keys_insufficient():
    """Test Shodan fails if API key is insufficient."""
    scan = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)
    os.environ["PE_SHODAN_API_KEYS"] = "k1,k2"
    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        result = handler(
            {
                "scanType": "shodan",
                "scanId": str(scan.id),
                "desiredCount": 3,
                "organizations": [],
                "isPe": False,
            },
            None,
        )
        mock_run.assert_not_called()
        assert result["status_code"] == 400


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_assigns_correct_concurrency_index():
    """Test availablity indexes are assigned correctly."""
    scan = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)
    # Occupy index 2
    ScanTask.objects.create(
        scan=scan, concurrency_index=2, status="started", type="fargate"
    )

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.side_effect = [
            {"tasks": [{"taskArn": "arn:task-x1"}]},
            {"tasks": [{"taskArn": "arn:task-x2"}]},
        ]
        start_desired_tasks(
            scan_type="shodan",
            desired_count=3,
            scan_id=str(scan.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["key1", "key2", "key3"],
        )
        tasks = ScanTask.objects.filter(
            scan=scan, fargate_task_arn__startswith="arn:task-x"
        )
        assert all(task.concurrency_index in [1, 3] for task in tasks)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_local_cap_blocks_even_if_global_not_hit():
    """Test local cap blocks even if global not hit."""
    scan = Scan.objects.create(name="shodan", concurrent_tasks=2, frequency=86400)
    for i in range(2):
        ScanTask.objects.create(
            scan=scan, concurrency_index=i + 1, status="started", type="fargate"
        )

    # Another scan with same name wants to start 1
    Scan.objects.create(name="shodan", concurrent_tasks=5, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        start_desired_tasks(
            scan_type="shodan",
            desired_count=1,
            scan_id=str(scan.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["key1"],
        )
        mock_run.assert_not_called()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_large_batch_triggers_multiple_calls():
    """Test censys large batch triggers multiple calls."""
    scan = Scan.objects.create(name="censys", concurrent_tasks=30, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.return_value = {
            "tasks": [{"taskArn": "arn:task-{}".format(i)} for i in range(10)]
        }
        start_desired_tasks(
            scan_type="censys",
            desired_count=25,
            scan_id=str(scan.id),
            organizations=[],
            is_pe=False,
        )
        assert mock_run.call_count == 3


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_multiple_scans_respect_global_concurrency_cap():
    """Two scans with same name shouldn't exceed global cap."""
    scan1 = Scan.objects.create(name="shodan", concurrent_tasks=2, frequency=86400)
    scan2 = Scan.objects.create(name="shodan", concurrent_tasks=3, frequency=86400)

    with patch("xfd_api.tasks.scanExecution.ECSClient.run_command") as mock_run:
        mock_run.side_effect = [
            {"tasks": [{"taskArn": "arn:task-1"}, {"taskArn": "arn:task-2"}]},
            {"tasks": [{"taskArn": "arn:task-3"}]},
        ]

        start_desired_tasks(
            scan_type="shodan",
            desired_count=2,
            scan_id=str(scan1.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["k1", "k2"],
        )

        start_desired_tasks(
            scan_type="shodan",
            desired_count=3,
            scan_id=str(scan2.id),
            organizations=[],
            is_pe=False,
            shodan_api_keys=["k1", "k2", "k3"],
        )

        assert mock_run.call_count == 2

        all_tasks = list(
            ScanTask.objects.filter(scan__name="shodan").order_by("concurrency_index")
        )
        assert len(all_tasks) == 3
        assert {t.concurrency_index for t in all_tasks} == {1, 2, 3}
        assert all(t.fargate_task_arn.startswith("arn:task-") for t in all_tasks)

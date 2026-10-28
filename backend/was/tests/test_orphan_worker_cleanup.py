"""Verify preview-first, label-scoped cleanup of orphaned WAS workers."""

# Standard Python Libraries
from datetime import datetime, timedelta, timezone
import json
import subprocess
import unittest
from unittest.mock import call, patch

# Third-Party Libraries
from was_reports.commands.orphan_worker_cleanup import (
    OWNER_LABEL,
    RUN_ID_LABEL,
    WORKER_INDEX_LABEL,
    WORKFLOW_LABEL,
    cleanup_orphaned_workers,
    coordinator_is_present,
    identity_from_name,
    inspection_reports_stopped,
    list_owned_container_ids,
    runtime_at,
    stop_and_remove,
    validated_worker,
)

RUN_ID = "00000000-0000-0000-0000-000000000001"
OWNER_ID = "00000000-0000-0000-0000-000000000002"
CONTAINER_ID = "a" * 64
OBSERVED_AT = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)


def worker_document(
    *,
    workflow: str = "production",
    started_at: str = "2026-10-21T05:00:00Z",
    include_identity_labels: bool = True,
) -> dict:
    """Build one Docker inspection document for a valid WAS worker."""
    prefix = "was-batch" if workflow == "production" else "was-capacity"
    labels = {OWNER_LABEL: OWNER_ID}
    if include_identity_labels:
        labels.update(
            {
                RUN_ID_LABEL: RUN_ID,
                WORKFLOW_LABEL: workflow,
                WORKER_INDEX_LABEL: "4",
            }
        )
    return {
        "Id": CONTAINER_ID,
        "Name": "/{}-{}-4".format(prefix, RUN_ID),
        "Config": {"Labels": labels},
        "State": {"Running": True, "StartedAt": started_at},
    }


class OrphanWorkerCleanupTests(unittest.TestCase):
    """Exercise container identity, coordinator, age, and apply safeguards."""

    @patch("was_reports.commands.orphan_worker_cleanup.docker_command")
    def test_discovery_uses_only_the_was_owner_label(self, docker_command):
        """Never discover containers through an unfiltered Docker listing."""
        docker_command.return_value = subprocess.CompletedProcess(
            [], 0, stdout="abc\ndef\n", stderr=""
        )

        self.assertEqual(list_owned_container_ids("/usr/bin/docker"), ["abc", "def"])
        self.assertEqual(
            docker_command.call_args,
            call(
                "/usr/bin/docker",
                [
                    "ps",
                    "--filter",
                    "label=was.capacity.owner",
                    "--format",
                    "{{.ID}}",
                ],
            ),
        )

    def test_worker_identity_accepts_new_and_legacy_labels(self):
        """Support exact old names while requiring any new labels to agree."""
        current = validated_worker(worker_document())
        legacy = validated_worker(worker_document(include_identity_labels=False))

        self.assertEqual(current, legacy)
        self.assertEqual(current.coordinator_session, "was-production-" + RUN_ID)
        self.assertEqual(
            identity_from_name("was-capacity-{}-4".format(RUN_ID)),
            ("capacity", RUN_ID, 4),
        )

    def test_worker_identity_rejects_partial_or_disagreeing_labels(self):
        """Fail closed when durable identity labels are incomplete or inconsistent."""
        partial = worker_document()
        del partial["Config"]["Labels"][WORKER_INDEX_LABEL]
        with self.assertRaisesRegex(ValueError, "incomplete"):
            validated_worker(partial)

        mismatch = worker_document()
        mismatch["Config"]["Labels"][WORKFLOW_LABEL] = "capacity"
        with self.assertRaisesRegex(ValueError, "do not match"):
            validated_worker(mismatch)

    def test_worker_identity_rejects_unknown_or_noncanonical_ownership(self):
        """A label alone cannot authorize cleanup without exact WAS identity."""
        invalid_owner = worker_document()
        invalid_owner["Config"]["Labels"][OWNER_LABEL] = "not-a-uuid"
        with self.assertRaisesRegex(ValueError, "ownership label"):
            validated_worker(invalid_owner)

        unknown_name = worker_document()
        unknown_name["Name"] = "/unrelated-container"
        with self.assertRaisesRegex(ValueError, "unknown WAS worker name"):
            validated_worker(unknown_name)

    def test_stopped_inspection_is_a_normal_exit_race(self):
        """Recognize a worker that ended after running-container discovery."""
        document = worker_document()
        document["State"]["Running"] = False

        self.assertTrue(inspection_reports_stopped(document))

    @patch("was_reports.commands.orphan_worker_cleanup.workflow_pane_states")
    def test_dead_or_missing_coordinator_is_absent(self, pane_states):
        """Treat retained dead panes as absent while retaining live coordinators."""
        pane_states.side_effect = [[], [{"pane_dead": True}], [{"pane_dead": False}]]

        self.assertFalse(
            coordinator_is_present("/usr/bin/tmux", "production", "session")
        )
        self.assertFalse(
            coordinator_is_present("/usr/bin/tmux", "production", "session")
        )
        self.assertTrue(
            coordinator_is_present("/usr/bin/tmux", "production", "session")
        )

    @patch("was_reports.commands.orphan_worker_cleanup.workflow_pane_states")
    def test_ambiguous_coordinator_state_fails_closed(self, pane_states):
        """Never classify duplicate coordinator panes as absent."""
        pane_states.return_value = [{"pane_dead": True}, {"pane_dead": True}]
        with self.assertRaisesRegex(RuntimeError, "exactly one pane"):
            coordinator_is_present("/usr/bin/tmux", "production", "session")

    @patch("was_reports.commands.orphan_worker_cleanup.stop_and_remove")
    @patch("was_reports.commands.orphan_worker_cleanup.coordinator_is_present")
    @patch("was_reports.commands.orphan_worker_cleanup.inspect_container")
    @patch("was_reports.commands.orphan_worker_cleanup.list_owned_container_ids")
    @patch("was_reports.commands.orphan_worker_cleanup.require_executable")
    def test_preview_reports_old_orphan_without_mutation(
        self,
        require_executable,
        list_container_ids,
        inspect_container,
        coordinator_present,
        stop_and_remove,
    ):
        """Default cleanup performs inspection only, even for an eligible orphan."""
        require_executable.side_effect = lambda name: "/usr/bin/" + name
        list_container_ids.return_value = [CONTAINER_ID]
        inspect_container.return_value = worker_document()
        coordinator_present.return_value = False

        result = cleanup_orphaned_workers(now=OBSERVED_AT)

        self.assertEqual(result, 0)
        stop_and_remove.assert_not_called()
        inspect_container.assert_called_once_with("/usr/bin/docker", CONTAINER_ID)

    @patch("was_reports.commands.orphan_worker_cleanup.stop_and_remove")
    @patch("was_reports.commands.orphan_worker_cleanup.coordinator_is_present")
    @patch("was_reports.commands.orphan_worker_cleanup.inspect_container")
    @patch("was_reports.commands.orphan_worker_cleanup.list_owned_container_ids")
    @patch("was_reports.commands.orphan_worker_cleanup.require_executable")
    def test_apply_rechecks_and_removes_exact_old_orphan(
        self,
        require_executable,
        list_container_ids,
        inspect_container,
        coordinator_present,
        stop_and_remove,
    ):
        """Applied cleanup repeats both identity and coordinator checks before removal."""
        require_executable.side_effect = lambda name: "/usr/bin/" + name
        list_container_ids.return_value = [CONTAINER_ID]
        inspect_container.side_effect = [worker_document(), worker_document()]
        coordinator_present.side_effect = [False, False]

        result = cleanup_orphaned_workers(apply=True, now=OBSERVED_AT)

        self.assertEqual(result, 0)
        self.assertEqual(inspect_container.call_count, 2)
        self.assertEqual(coordinator_present.call_count, 2)
        stop_and_remove.assert_called_once()
        removed_worker = stop_and_remove.call_args.args[1]
        self.assertEqual(removed_worker.container_id, CONTAINER_ID)

    @patch("was_reports.commands.orphan_worker_cleanup.stop_and_remove")
    @patch("was_reports.commands.orphan_worker_cleanup.coordinator_is_present")
    @patch("was_reports.commands.orphan_worker_cleanup.inspect_container")
    @patch("was_reports.commands.orphan_worker_cleanup.list_owned_container_ids")
    @patch("was_reports.commands.orphan_worker_cleanup.require_executable")
    def test_live_or_under_age_workers_are_retained(
        self,
        require_executable,
        list_container_ids,
        inspect_container,
        coordinator_present,
        stop_and_remove,
    ):
        """Require both the age threshold and coordinator absence."""
        require_executable.side_effect = lambda name: "/usr/bin/" + name
        list_container_ids.return_value = ["young", "active"]
        inspect_container.side_effect = [
            worker_document(started_at="2026-10-21T17:00:00Z"),
            worker_document(),
        ]
        coordinator_present.return_value = True

        cleanup_orphaned_workers(apply=True, now=OBSERVED_AT)

        coordinator_present.assert_called_once()
        stop_and_remove.assert_not_called()

    @patch("was_reports.commands.orphan_worker_cleanup.stop_and_remove")
    @patch("was_reports.commands.orphan_worker_cleanup.coordinator_is_present")
    @patch("was_reports.commands.orphan_worker_cleanup.inspect_container")
    @patch("was_reports.commands.orphan_worker_cleanup.list_owned_container_ids")
    @patch("was_reports.commands.orphan_worker_cleanup.require_executable")
    def test_identity_change_or_reappearing_coordinator_prevents_removal(
        self,
        require_executable,
        list_container_ids,
        inspect_container,
        coordinator_present,
        stop_and_remove,
    ):
        """Close apply-time races instead of relying on the previewed state."""
        require_executable.side_effect = lambda name: "/usr/bin/" + name
        list_container_ids.return_value = [CONTAINER_ID]
        changed = worker_document()
        changed["Config"]["Labels"][
            OWNER_LABEL
        ] = "00000000-0000-0000-0000-000000000003"
        inspect_container.side_effect = [worker_document(), changed]
        coordinator_present.return_value = False

        cleanup_orphaned_workers(apply=True, now=OBSERVED_AT)

        stop_and_remove.assert_not_called()

        inspect_container.side_effect = [worker_document(), worker_document()]
        coordinator_present.side_effect = [False, True]
        cleanup_orphaned_workers(apply=True, now=OBSERVED_AT)
        stop_and_remove.assert_not_called()

    @patch("was_reports.commands.orphan_worker_cleanup.stop_and_remove")
    @patch("was_reports.commands.orphan_worker_cleanup.coordinator_is_present")
    @patch("was_reports.commands.orphan_worker_cleanup.inspect_container")
    @patch("was_reports.commands.orphan_worker_cleanup.list_owned_container_ids")
    @patch("was_reports.commands.orphan_worker_cleanup.require_executable")
    def test_worker_exit_races_are_skipped_without_failure(
        self,
        require_executable,
        list_container_ids,
        inspect_container,
        coordinator_present,
        stop_and_remove,
    ):
        """Do not fail periodic cleanup when a worker finishes naturally."""
        require_executable.side_effect = lambda name: "/usr/bin/" + name
        list_container_ids.return_value = [CONTAINER_ID]
        stopped = worker_document()
        stopped["State"]["Running"] = False
        inspect_container.return_value = stopped

        self.assertEqual(cleanup_orphaned_workers(now=OBSERVED_AT), 0)
        coordinator_present.assert_not_called()
        stop_and_remove.assert_not_called()

        inspect_container.side_effect = [worker_document(), stopped]
        coordinator_present.return_value = False
        self.assertEqual(
            cleanup_orphaned_workers(apply=True, now=OBSERVED_AT),
            0,
        )
        stop_and_remove.assert_not_called()

    @patch("was_reports.commands.orphan_worker_cleanup.docker_command")
    def test_stop_failure_does_not_force_remove(self, docker_command):
        """Do not proceed to removal when Docker cannot stop the exact worker."""
        docker_command.return_value = subprocess.CompletedProcess(
            [], 1, stdout="", stderr="daemon failure"
        )
        worker = validated_worker(worker_document())

        with self.assertRaisesRegex(RuntimeError, "Unable to stop"):
            stop_and_remove("/usr/bin/docker", worker)
        self.assertEqual(docker_command.call_count, 1)
        command = docker_command.call_args.args[1]
        self.assertEqual(
            command,
            ["stop", "--time", "30", CONTAINER_ID],
        )
        self.assertNotIn("prune", " ".join(command))
        self.assertNotIn("containerd-shim", " ".join(command))

    def test_future_start_time_fails_closed(self):
        """Reject clock-inconsistent metadata rather than treating it as old."""
        worker = validated_worker(worker_document(started_at="2026-10-22T05:00:00Z"))
        with self.assertRaisesRegex(ValueError, "future"):
            runtime_at(worker, OBSERVED_AT)

    def test_exact_age_boundary_is_eligible(self):
        """Treat the configured maximum runtime as an inclusive boundary."""
        worker = validated_worker(worker_document(started_at="2026-10-21T06:00:00Z"))
        self.assertEqual(runtime_at(worker, OBSERVED_AT), timedelta(hours=12))

    def test_inspection_payload_round_trip_is_valid_json(self):
        """Keep the test fixture representative of Docker's JSON response."""
        payload = json.dumps([worker_document()])
        self.assertEqual(json.loads(payload)[0]["Id"], CONTAINER_ID)


if __name__ == "__main__":
    unittest.main()

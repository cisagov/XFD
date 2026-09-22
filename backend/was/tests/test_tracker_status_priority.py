"""Regression checks for operator-approved scan-result precedence."""

from itertools import permutations
import unittest

from was_reports.tracker.item_builder import combined_status_and_result


class TrackerStatusPriorityTests(unittest.TestCase):
    """Keep result selection deterministic and incomplete data fail-closed."""

    def test_result_precedence_is_order_independent(self) -> None:
        """Every pair follows the approved hierarchy regardless of slice order."""
        hierarchy = [
            ("SCAN_RESULTS_INVALID", "Scan Results Invalid"),
            ("SCAN_INTERNAL_ERROR", "Scan Internal Error"),
            ("NO_WEB_SERVICE", "No Web Service"),
            ("NO_HOST_ALIVE", "No Host Alive"),
            ("SERVICE_ERROR", "Service Error"),
            ("TIME_LIMIT_REACHED", "Time Limit Reached"),
            ("SUCCESSFUL", "Successful"),
        ]
        for position, (winner, label) in enumerate(hierarchy):
            for loser, unused_label in hierarchy[position:]:
                for results in permutations([winner, loser]):
                    with self.subTest(results=results):
                        expected_status = "Error" if position < 2 else "Finished"
                        self.assertEqual(
                            combined_status_and_result(["FINISHED"] * 2, list(results)),
                            (expected_status, label),
                        )

    def test_error_slices_do_not_select_first_error_arbitrarily(self) -> None:
        """Multiple terminal errors retain the most important specific result."""
        for results in permutations(["SCAN_INTERNAL_ERROR", "SCAN_RESULTS_INVALID"]):
            self.assertEqual(
                combined_status_and_result(["ERROR", "ERROR"], list(results)),
                ("Error", "Scan Results Invalid"),
            )

    def test_incomplete_inputs_never_become_successful(self) -> None:
        """Missing, unknown, processing, and contradictory states remain unsafe."""
        cases = [
            ([], []),
            (["FINISHED"], []),
            (["FINISHED"], [""]),
            (["FINISHED"], ["NEW_UNKNOWN_RESULT"]),
            (["FINISHED"], ["PROCESSING"]),
            (["SUBMITTED"], ["SUCCESSFUL"]),
            (["ERROR"], ["SUCCESSFUL"]),
        ]
        for statuses, results in cases:
            with self.subTest(statuses=statuses, results=results):
                self.assertEqual(
                    combined_status_and_result(statuses, results),
                    ("Error", "Scan Incomplete"),
                )

    def test_running_slice_takes_precedence_over_terminal_result(self) -> None:
        """Wait for all slices even when another slice has a known terminal error."""
        self.assertEqual(
            combined_status_and_result(
                ["ERROR", "RUNNING"], ["SCAN_RESULTS_INVALID", "PROCESSING"]
            ),
            ("Running", "Running"),
        )

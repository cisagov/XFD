"""Interactive numbered menu for operator-facing WAS workflows."""

# Standard Python Libraries
from datetime import date
from getpass import getpass
import logging
import select
import signal
import subprocess  # nosec B404
import sys
from threading import Event, Thread
from typing import Callable

# Third-Party Libraries
from pyfiglet import Figlet

# First-Party Libraries
from was_reports.commands import (
    batch_runner,
    on_demand_cli,
    standalone_cli,
    report_generator,
    stakeholders_cli,
    tracker_cli,
    update_tracker_cli,
)
from was_reports.utils.logging_config import configure_logging
from was_reports.utils.operation_cancellation import (
    OperationCancelledError,
    clear_operation_cancellation,
    request_operation_cancellation,
    raise_if_operation_cancelled,
)
from was_reports.utils.passwords import (
    CUSTOMER_PASSWORD_REQUIREMENTS,
    validate_customer_provided_report_password,
)

from was_reports.utils.stakeholder_options import STAKEHOLDER_OPTIONS

LOGGER = logging.getLogger(__name__)
InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]
SecretInputFunction = Callable[[str], str]


class OperationCancellationMonitor:
    """Watch interactive input for a cooperative cancellation request."""

    def __init__(self, output_function: OutputFunction) -> None:
        """Initialize cancellation monitoring for the active terminal."""
        self.output = output_function
        self.stop_event = Event()
        self.thread = Thread(
            target=self._run,
            daemon=True,
            name="was-menu-cancellation-monitor",
        )

    def start(self) -> bool:
        """Start monitoring only when standard input is an interactive terminal."""
        if not sys.stdin.isatty():
            return False
        self.thread.start()
        return True

    def stop(self) -> None:
        """Stop monitoring before the menu accepts its next selection."""
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=1)

    def _run(self) -> None:
        """Request cancellation when the operator enters b on its own line."""
        while not self.stop_event.is_set():
            try:
                readable, unused_writable, unused_errors = select.select(
                    [sys.stdin],
                    [],
                    [],
                    0.2,
                )
            except (OSError, ValueError):
                return
            if not readable or self.stop_event.is_set():
                continue
            value = sys.stdin.readline()
            if not value:
                return
            if value.strip().lower() == "b":
                request_operation_cancellation()
                self.output(
                    "Cancellation requested. Waiting for the next safe checkpoint..."
                )
                return
            self.output("Operation is running. Enter b and press Enter to cancel.")


def write_output(message: str) -> None:
    """Write one operator-facing line without buffering progress messages."""
    sys.stdout.write("{}\n".format(message))
    sys.stdout.flush()


def clear_terminal() -> None:
    """Clear the visible terminal viewport without deleting scrollback."""
    if not sys.stdout.isatty():
        return
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


class WasOperatorMenu:
    """Interactive WAS menu backed by the existing command modules."""

    def __init__(
        self,
        input_function: InputFunction = input,
        output_function: OutputFunction = write_output,
        secret_input_function: SecretInputFunction = getpass,
    ) -> None:
        """Initialize menu input and output boundaries."""
        self.input = input_function
        self.output = output_function
        self.secret_input = secret_input_function

    def prompt_required(self, prompt: str) -> str:
        """Prompt until the operator supplies a nonempty value."""
        while True:
            value = self.input(prompt).strip()
            if value:
                return value
            self.output("A value is required.")

    def prompt_optional(self, prompt: str, default: str | None = None) -> str:
        """Return optional input or its displayed default value."""
        value = self.input(prompt).strip()
        if value:
            return value
        return default or ""

    def prompt_positive_integer(
        self,
        prompt: str,
        default: int | None = None,
    ) -> int:
        """Prompt for a positive integer with an optional default value."""
        while True:
            raw_value = self.input(prompt).strip()
            if not raw_value and default is not None:
                return default
            if not raw_value:
                self.output("A whole number greater than zero is required.")
                continue
            try:
                parsed_value = int(raw_value)
            except ValueError:
                self.output("Enter a whole number greater than zero.")
                continue
            if parsed_value > 0:
                return parsed_value
            self.output("Enter a whole number greater than zero.")

    def prompt_nonnegative_integer(self, prompt: str, default: int) -> int:
        """Prompt for a whole number that may be zero."""
        while True:
            raw_value = self.input(prompt).strip()
            if not raw_value:
                return default
            try:
                parsed_value = int(raw_value)
            except ValueError:
                self.output("Enter a whole number of zero or greater.")
                continue
            if parsed_value >= 0:
                return parsed_value
            self.output("Enter a whole number of zero or greater.")

    def prompt_row_limit(self, prompt: str, default: int = 200) -> str:
        """Prompt for a positive row limit or all rows."""
        while True:
            raw_value = self.input(prompt).strip()
            if not raw_value:
                return str(default)
            if raw_value.lower() == "all":
                return "all"
            try:
                parsed_value = int(raw_value)
            except ValueError:
                self.output("Enter a whole number greater than zero, or all.")
                continue
            if parsed_value > 0:
                return str(parsed_value)
            self.output("Enter a whole number greater than zero, or all.")

    def prompt_optional_nonnegative_integer(self, prompt: str) -> str:
        """Prompt for an optional whole number of zero or greater."""
        while True:
            raw_value = self.input(prompt).strip()
            if not raw_value:
                return ""
            try:
                parsed_value = int(raw_value)
            except ValueError:
                self.output("Enter a whole number of zero or greater, or leave blank.")
                continue
            if parsed_value >= 0:
                return str(parsed_value)
            self.output("Enter a whole number of zero or greater, or leave blank.")

    def prompt_optional_positive_integer(self, prompt: str) -> str:
        """Prompt for an optional positive whole number."""
        while True:
            raw_value = self.input(prompt).strip()
            if not raw_value or raw_value.lower() == "all":
                return ""
            try:
                parsed_value = int(raw_value)
            except ValueError:
                self.output("Enter a whole number greater than zero, or all.")
                continue
            if parsed_value > 0:
                return str(parsed_value)
            self.output("Enter a whole number greater than zero, or all.")

    def confirm(self, prompt: str) -> bool:
        """Return whether the operator explicitly answered yes."""
        answer = self.input("{} [y/N]: ".format(prompt)).strip().lower()
        return answer in {"y", "yes"}

    def pause(self) -> None:
        """Wait for the operator before redisplaying a menu."""
        self.input("Press Enter to continue...")

    def run_submenu_action(
        self,
        menu_name: str,
        action: Callable[[], None],
    ) -> None:
        """Return prompt interruptions to their owning submenu."""
        try:
            action()
        except KeyboardInterrupt:
            LOGGER.info("WAS submenu input cancelled by operator: %s", menu_name)
            self.output(
                "\nInput cancelled. Returning to {}.".format(menu_name)
            )

    def execute(
        self,
        operation_name: str,
        command: Callable[[], int],
        show_success: bool = True,
        cancellable: bool = False,
    ) -> int:
        """Execute one command while keeping unexpected failures in the menu."""
        cancellation_monitor = OperationCancellationMonitor(self.output)
        clear_operation_cancellation()
        monitor_started = False
        previous_interrupt_handler = None
        interrupt_handler_installed = False
        interrupt_requested = Event()

        def handle_operation_interrupt(
            unused_signal_number,
            unused_frame,
        ) -> None:
            """Convert Ctrl+C into a cooperative operation cancellation request."""
            if interrupt_requested.is_set():
                return
            interrupt_requested.set()
            request_operation_cancellation()
            self.output(
                "\nCancellation requested. Waiting for the next safe checkpoint..."
            )

        if cancellable:
            monitor_started = cancellation_monitor.start()
            try:
                previous_interrupt_handler = signal.getsignal(signal.SIGINT)
                signal.signal(signal.SIGINT, handle_operation_interrupt)
                interrupt_handler_installed = True
            except ValueError:
                LOGGER.debug("SIGINT handler unavailable outside the main thread.")
            if monitor_started:
                self.output(
                    "Operation started. Enter b and press Enter, or press Ctrl+C, "
                    "to cancel safely."
                )
        try:
            exit_code = command()
        except SystemExit as error:
            exit_code = int(error.code or 0)
        except OperationCancelledError:
            LOGGER.info("WAS menu operation cancelled by operator: %s", operation_name)
            self.output("Operation cancelled safely. Returning to the previous menu.")
            return 130
        except KeyboardInterrupt:
            LOGGER.info("WAS menu operation interrupted by operator: %s", operation_name)
            self.output("Operation interrupted. Returning to the previous menu.")
            return 130
        except Exception:
            LOGGER.exception("WAS menu operation failed: %s", operation_name)
            self.output("Operation failed. Review the WAS logs for details.")
            return 1
        finally:
            if interrupt_handler_installed:
                signal.signal(signal.SIGINT, previous_interrupt_handler)
            if monitor_started:
                cancellation_monitor.stop()
            clear_operation_cancellation()

        if exit_code == 0 and show_success:
            self.output("Operation completed successfully.")
        else:
            self.output("Operation exited with status {}.".format(exit_code))
        return exit_code

    def prompt_prefilled_value(
        self,
        column_name: str,
        current_value: object,
    ) -> str:
        """Prompt with an editable current value when using an interactive TTY."""
        current_text = "" if current_value is None else str(current_value)
        prompt = "{} [current: {}]: ".format(
            column_name,
            "NULL" if current_value is None else current_text,
        )
        if self.input is not input:
            entered_value = self.input(prompt).strip()
            return entered_value if entered_value else current_text
        try:
            # Standard Python Libraries
            import readline
        except ImportError:
            entered_value = self.input(prompt).strip()
            return entered_value if entered_value else current_text
        readline.set_startup_hook(lambda: readline.insert_text(current_text))
        try:
            return self.input(prompt).strip()
        finally:
            readline.set_startup_hook()

    def print_menu(
        self,
        title: str,
        options: list[str],
        show_banner: bool = False,
    ) -> None:
        """Display navigation first as zero, preserving action numbering."""
        clear_terminal()
        if show_banner:
            self.print_banner()
        self.output("")
        self.output(title)
        self.output("=" * len(title))
        navigation = {"Quit", "Back to main menu", "Cancel"}
        for option in options:
            if option in navigation:
                self.output("0) {}".format(option))
        actions = [option for option in options if option not in navigation]
        for index, option in enumerate(actions, start=1):
            self.output("{}) {}".format(index, option))
        self.output("")

    def print_banner(self) -> None:
        """Display the WAS Reporting application banner."""
        banner = Figlet(font="small", width=100).renderText("WAS REPORTING")
        self.output(banner.rstrip())

    def run(self) -> int:
        """Display the main menu until the operator exits."""
        while True:
            self.print_menu(
                "WAS Reporting Operations",
                [
                    "Report generation",
                    "Report tracker",
                    "Stakeholder management",
                    "Quit",
                ],
                show_banner=True,
            )
            selection = self.input("Please enter your selection: ").strip()
            if selection == "0":
                self.output("Exiting WAS reporting operations.")
                return 0
            elif selection == "1":
                self.report_menu()
            elif selection == "2":
                self.tracker_menu()
            elif selection == "3":
                self.stakeholder_menu()
            else:
                self.output("Invalid selection.")

    def report_menu(self) -> None:
        """Display report generation operations."""
        while True:
            self.print_menu(
                "Report Generation",
                [
                    "Run the complete recent scan batch",
                    "Process eligible automated tracker reports",
                    "Process an eligible manual tracker report",
                    "Generate an on-demand report to S3 (optional email)",
                    "Generate a standalone report for a Qualys tag NOT in the stakeholder database",
                    "Run a parallel capacity load test (one container, multiple processes)",
                    "Back to main menu",
                ],
            )
            selection = (
                self.input("Please enter your selection [0/b = main menu]: ")
                .strip()
                .lower()
            )
            if selection == "1":
                self.run_submenu_action("Report Generation", self.run_daily_batch)
            elif selection == "2":
                self.run_submenu_action(
                    "Report Generation",
                    self.run_automated_reports,
                )
            elif selection == "3":
                self.run_submenu_action(
                    "Report Generation",
                    lambda: self.run_single_report(manual=True),
                )
            elif selection == "4":
                self.run_submenu_action(
                    "Report Generation",
                    self.run_on_demand_report,
                )
            elif selection == "5":
                self.run_submenu_action("Report Generation", self.run_standalone_report)
            elif selection == "6":
                self.run_submenu_action("Report Generation", self.run_capacity_test)
            elif selection in {"0", "b"}:
                return
            else:
                self.output("Invalid selection.")

    def run_capacity_test(self) -> None:
        """Launch the existing parallel coordinator with explicit test recipients."""
        self.output(
            "This menu uses worker processes inside this container. For separate worker "
            "containers matching the production batch, use make capacity-start on the host."
        )
        self.output(
            "Capacity tests use the isolated TEST_WAS_DB database, not the production tracker. "
            "This performs real Qualys, S3, and SES operations. All reports and summaries "
            "go only to the explicit test recipients, never customer POCs."
        )
        worker_value = self.input("Parallel workers [30; allowed 1-30]: ").strip() or "30"
        try:
            workers = int(worker_value)
        except ValueError:
            self.output("Workers must be a whole number from 1 through 30.")
            return
        if not 1 <= workers <= 30:
            self.output("Workers must be a whole number from 1 through 30.")
            return
        recipients = self.prompt_required("Test assignee email address(es), comma/semicolon separated: ")
        label = self.prompt_optional("Workload label [capacity-trial]: ") or "capacity-trial"
        if not self.confirm(
            "Start a NEW capacity test with {} workers and send all reports and summaries to {}?".format(
                workers, recipients
            )
        ):
            self.output("Operation cancelled.")
            return
        arguments = [
            sys.executable, "-m", "was_reports.commands.capacity_test",
            "--workers", str(workers), "--test-recipients", recipients,
            "--workload-label", label, "--apply",
        ]
        self.execute(
            "parallel capacity load test",
            lambda: self.run_capacity_subprocess(arguments),
            cancellable=True,
        )
        self.pause()

    def run_capacity_subprocess(self, arguments: list[str]) -> int:
        """Keep capacity environment and signal changes isolated from the menu."""
        raise_if_operation_cancelled()
        process = subprocess.Popen(  # nosec B603
            arguments, stdin=subprocess.DEVNULL, start_new_session=True
        )
        try:
            while True:
                raise_if_operation_cancelled()
                try:
                    return process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    continue
        except BaseException:
            if process.poll() is None:
                self.output("Stopping the capacity coordinator and waiting for worker cleanup...")
                process.terminate()
            process.wait()
            raise

    def run_standalone_report(self) -> None:
        """Make the non-enrollment and explicit delivery boundary visible."""
        self.output(
            "Standalone targets do not enter the stakeholder database, daily tracker, or automatic batches."
        )
        tag = self.prompt_required(
            "Exact Qualys tag name (not an enrolled stakeholder): "
        )
        email = self.prompt_optional(
            "Delivery email(s), email-enabled analysts only [reuse saved; required for new target]: "
        )
        arguments = ["--tag", tag]
        if email:
            arguments.extend(["--delivery-email", email])
        send = self.confirm("Email the report after archiving to S3?")
        if send:
            arguments.append("--send-email")
        self.output(
            "New targets receive a stored generated PDF password. Existing targets retain their exact password and delivery address."
        )
        if not self.confirm(
            "Generate standalone report for {}, archive to S3, {}?".format(
                tag,
                (
                    "email to " + (email or "the saved target address")
                    if send
                    else "no email"
                ),
            )
        ):
            self.output("Operation cancelled.")
            return
        self.execute(
            "standalone report",
            lambda: standalone_cli.main(arguments),
            cancellable=True,
        )
        self.pause()

    def run_on_demand_report(self) -> None:
        """Confirm explicit recipients before delegating an on-demand request."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        arguments = ["--tag", stakeholder_tag, "--create-missing-password"]
        send_email = self.confirm("Email the report after archiving to S3?")
        recipient_summary = "no email"
        if send_email:
            recipients = self.prompt_required(
                "Active WAS assignee email address(es): "
            )
            arguments.extend(["--send-email", "--test-recipients", recipients])
            recipient_summary = "email to {}".format(recipients)
        tracker_id = self.prompt_optional("Existing tracker row ID [none]: ")
        if tracker_id:
            arguments.extend(["--tracker-id", tracker_id])
        else:
            self.output(
                "A new report run will be recorded without changing scan tracker rows."
            )
        if not self.confirm(
            "Generate a NEW report for {}, archive to S3, {}?".format(
                stakeholder_tag, recipient_summary
            )
        ):
            self.output("Operation cancelled.")
            return
        self.execute(
            "on-demand report",
            lambda: on_demand_cli.main(arguments),
            cancellable=True,
        )
        self.pause()

    def run_daily_batch(self) -> None:
        """Execute a test-recipient or customer-delivery recent-scan batch."""
        arguments = [
            "--recent-scans",
            "--create-missing-password",
            "--continue-on-error",
            "--send-email",
            "--send-assignee-digests",
        ]
        self.output("0) Cancel")
        self.output("1) Test batch using an email-enabled test recipient override")
        self.output("2) Production batch using customer email addresses")
        delivery_selection = self.input("Please select the delivery mode: ").strip()
        if delivery_selection not in {"1", "2"}:
            self.output("Operation cancelled.")
            return
        report_limit = self.prompt_optional_positive_integer(
            "Maximum eligible reports [all]: "
        )
        if report_limit:
            arguments.extend(["--limit", report_limit])
            self.output("This batch is limited to {} reports.".format(report_limit))
        else:
            self.output("This batch will process all eligible reports.")
        if delivery_selection == "1":
            recipients = self.prompt_required(
                "Email-enabled functional-test recipient address(es): "
            )
            self.output(
                "Customer addresses will not be used. Successful tracker rows will "
                "be recorded as sent."
            )
            if not self.confirm(
                "Generate, upload, and email all eligible reports only to {}?".format(
                    recipients
                )
            ):
                self.output("Operation cancelled.")
                return
            arguments.extend(["--test-recipients", recipients])
        elif delivery_selection == "2":
            self.output(
                "WARNING: This will email eligible reports to customer technical and "
                "distribution contacts."
            )
            confirmation = self.input(
                "Type SEND CUSTOMER REPORTS to run the production batch: "
            ).strip()
            if confirmation != "SEND CUSTOMER REPORTS":
                self.output("Operation cancelled.")
                return
        self.execute(
            "recent-scan batch",
            lambda: batch_runner.main(arguments),
            cancellable=True,
        )
        self.pause()

    def require_existing_stakeholder(self, tag: str) -> dict[str, object] | None:
        """Stop before collecting further inputs if the stakeholder is absent."""
        record = self.load_and_display_stakeholder(tag)
        if record is None:
            self.pause()
        return record

    def run_automated_reports(self) -> None:
        """Process all eligible automated tracker rows without tag filtering."""
        days = self.prompt_optional("Scan window in days [7, or all]: ", default="7")
        if not self.confirm(
            "Generate and email ALL eligible automated tracker reports to customer contacts?"
        ):
            self.output("Operation cancelled.")
            return
        arguments = [
            "--recent-scans",
            "--skip-tracker-refresh",
            "--days-back",
            days,
            "--create-missing-password",
            "--send-email",
            "--continue-on-error",
        ]
        self.execute(
            "automated tracker reports",
            lambda: batch_runner.main(arguments),
            cancellable=True,
        )
        self.pause()

    def view_customer_tracker(self) -> None:
        """Show all history for a tag, optionally including descendant tags."""
        tag = self.prompt_required("Customer tag: ")
        arguments = ["show", "--tag", tag, "--all-dates", "--limit", "all"]
        if self.confirm("Include child tags (all descendants)?"):
            arguments.append("--include-children")
        self.execute("customer tracker history", lambda: tracker_cli.main(arguments))
        self.pause()

    def update_tracker_row(self) -> None:
        """Review supported corrections without resetting execution or sent state."""
        from was_reports.data.tracker_corrections import (
            EDITABLE_FIELDS,
            TEMPLATES,
            correct_tracker_row,
        )

        tracker_id = self.prompt_positive_integer("Tracker row ID: ")
        inspected = {}

        def load() -> int:
            """Keep missing rows or database failures inside the menu boundary."""
            try:
                inspected["record"] = tracker_cli.get_tracker_record_by_id_from_db(
                    tracker_id
                )
            except KeyError:
                self.output("Tracker row {} was not found.".format(tracker_id))
                return 1
            return 0

        if self.execute("tracker correction lookup", load, show_success=False):
            self.pause()
            return
        record = inspected["record"]
        tracker_cli.display_tracker_record(record, output=self.output)
        self.output(
            "Only unclaimed, unsent rows may be corrected. Identity, passwords and delivery history are protected."
        )
        self.output(
            "Customer delivery addresses are maintained in Stakeholder Management, not tracker POC fields."
        )
        self.output("Editable fields: " + ", ".join(EDITABLE_FIELDS))
        field = self.prompt_required("Field to correct [CANCEL]: ").strip().lower()
        if field == "cancel":
            return
        if field not in EDITABLE_FIELDS:
            self.output("That field is protected or unknown.")
            return
        if field == "status":
            self.output("Options: Finished, Error, Processing")
        elif field == "template":
            self.output("Options: " + ", ".join(sorted(TEMPLATES)))
        self.output(
            "Enter keeps the current value; CLEAR removes nullable metadata; CANCEL stops."
        )
        value = self.prompt_prefilled_value(field, record.get(field))
        if value == ("" if record.get(field) is None else str(record[field])):
            self.output("No tracker changes were entered.")
            return
        if value.upper() == "CANCEL":
            return
        value = None if value.upper() == "CLEAR" else value
        if not self.confirm(
            "Apply this correction to tracker row {}?".format(tracker_id)
        ):
            return

        def save() -> int:
            """Explain guarded correction refusals without changing run history."""
            try:
                correct_tracker_row(tracker_id, {field: value}, expected=record)
            except ValueError as error:
                self.output(str(error))
                return 1
            return 0

        self.execute("tracker correction", save)
        self.pause()

    def run_single_report(self, manual: bool) -> None:
        """Generate and email one automatic or manual stakeholder report."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        report_type = "manual" if manual else "automatic"
        if not self.confirm(
            "Generate and email the {} report for {}?".format(
                report_type,
                stakeholder_tag,
            )
        ):
            self.output("Operation cancelled.")
            return
        arguments = [
            "--recent-scans",
            "--tag",
            stakeholder_tag,
            "--create-missing-password",
            "--send-email",
        ]
        if manual:
            arguments.extend(
                [
                    "--skip-tracker-refresh",
                    "--include-manual",
                    "--continue-on-error",
                    "--limit",
                    "1",
                ]
            )
        self.execute(
            "{} stakeholder report".format(report_type),
            lambda: batch_runner.main(arguments),
            cancellable=True,
        )
        self.pause()

    def tracker_menu(self) -> None:
        """Display report tracker operations."""
        actions = [
            ("View tracker table", self.view_tracker),
            ("View one tracker row", self.view_tracker_row),
            ("View persisted report errors", self.view_errors),
            ("Record a manual report sent date", self.record_manual_sent_date),
            ("Export tracker CSV", self.export_tracker),
            ("Import tracker rows from XLSX", self.import_tracker),
            ("View all tracker entries for a customer tag", self.view_customer_tracker),
            ("Correct a tracker row", self.update_tracker_row),
            ("Refresh the report tracker from API", self.refresh_tracker),
        ]
        while True:
            self.print_menu(
                "Report Tracker",
                [label for label, _ in actions] + ["Back to main menu"],
            )
            selection = (
                self.input("Please enter your selection [0/b = main menu]: ")
                .strip()
                .lower()
            )
            if selection in {"0", "b"}:
                return
            if selection.isdigit() and 1 <= int(selection) <= len(actions):
                self.run_submenu_action(
                    "Report Tracker", actions[int(selection) - 1][1]
                )
            else:
                self.output("Invalid selection.")

    def view_tracker(self) -> None:
        """Prompt for optional tracker filters and display matching rows."""
        days_back = self.prompt_nonnegative_integer(
            "Days back [7]: ",
            default=7,
        )
        assignee = self.prompt_optional(
            "Assignee name (exact stored name, case-insensitive) [all]: "
        )
        report_status = self.prompt_optional(
            "Report status [all/manual/pending/sent]: "
        ).lower()
        row_limit = self.prompt_row_limit("Rows to display [200, or all]: ")
        arguments = [
            "show",
            "--days-back",
            str(days_back),
            "--limit",
            row_limit,
        ]
        if assignee:
            arguments.extend(["--assignee", assignee])
        if report_status and report_status != "all":
            arguments.extend(["--report-status", report_status])
        self.execute("tracker table", lambda: tracker_cli.main(arguments))
        self.pause()

    def view_tracker_row(self) -> None:
        """Display one tracker row and allow complete field inspection."""
        tracker_id = self.prompt_positive_integer("Tracker row ID: ")
        record_holder: dict[str, dict[str, object]] = {}

        def load_tracker_row() -> int:
            """Load and display one safe tracker database row."""
            record = tracker_cli.get_tracker_record_by_id_from_db(tracker_id)
            record_holder["record"] = record
            tracker_cli.display_tracker_record(record, output=self.output)
            return 0

        if self.execute(
            "tracker row lookup",
            load_tracker_row,
            show_success=False,
        ):
            self.pause()
            return
        self.display_full_tracker_fields(record_holder["record"])
        self.pause()

    def display_full_tracker_fields(
        self,
        record: dict[str, object],
    ) -> None:
        """Allow full untruncated tracker field output for inspection."""
        self.output(
            "Enter a field name to print its complete value for copying. "
            "Press Enter to return."
        )
        while True:
            requested_field = self.input(
                "Field to print in full [return]: "
            ).strip()
            if not requested_field:
                return
            normalized_field = requested_field.lower().replace("-", "_")
            if normalized_field not in record:
                self.output(
                    "Unknown field. Available fields: {}".format(
                        ", ".join(record)
                    )
                )
                continue
            self.output("Full value for {}:".format(normalized_field))
            self.output(
                tracker_cli.tracker_record_display_value(
                    record[normalized_field]
                )
            )

    def view_errors(self) -> None:
        """Prompt for error filters and display persisted failures."""
        days_back = self.prompt_nonnegative_integer(
            "Days back [7]: ",
            default=7,
        )
        stakeholder_tag = self.prompt_optional("Stakeholder tag [all]: ")
        arguments = ["errors", "--days-back", str(days_back)]
        if stakeholder_tag:
            arguments.extend(["--tag", stakeholder_tag])
        self.execute("report errors", lambda: tracker_cli.main(arguments))
        self.pause()

    def record_manual_sent_date(self) -> None:
        """Prompt for and record one manual tracker report sent date."""
        self.output(
            "First, display manual tracker rows so you can select the tracker ID."
        )
        days_back = self.prompt_nonnegative_integer(
            "Days back [30]: ",
            default=30,
        )
        assignee = self.prompt_optional(
            "Assignee name (exact stored name, case-insensitive) [all]: "
        )
        row_limit = self.prompt_row_limit("Rows to display [200, or all]: ")
        show_arguments = [
            "show",
            "--days-back",
            str(days_back),
            "--report-status",
            "manual",
            "--limit",
            row_limit,
        ]
        if assignee:
            show_arguments.extend(["--assignee", assignee])
        if self.execute(
            "manual tracker table",
            lambda: tracker_cli.main(show_arguments),
        ):
            self.pause()
            return
        tracker_id = self.prompt_positive_integer("Tracker row ID: ")
        sent_date = self.prompt_optional(
            "Sent date [{}]: ".format(date.today().isoformat()),
            default=date.today().isoformat(),
        )
        if not self.confirm(
            "Mark tracker row {} sent on {}?".format(tracker_id, sent_date)
        ):
            self.output("Operation cancelled.")
            return
        arguments = [
            "mark-sent",
            "--tracker-id",
            str(tracker_id),
            "--sent-date",
            sent_date,
            "--confirm",
        ]
        self.execute("manual sent date", lambda: tracker_cli.main(arguments))
        self.pause()

    def export_tracker(self) -> None:
        """Export locally, directly to S3, or to approved analysts."""
        self.print_menu(
            "Tracker Export Destination",
            [
                "Save to local output",
                "Save directly to S3",
                "Email to approved analysts",
                "Cancel",
            ],
        )
        destination = self.input("Please enter your selection: ").strip().lower()
        if destination in {"0", "b"}:
            return
        if destination not in {"1", "2", "3"}:
            self.output("Invalid selection.")
            return
        arguments = ["export-csv"]
        if destination == "1":
            self.output(
                "Local tracker CSV uses the legacy format and may contain report passwords. Handle it as sensitive."
            )
            path = self.prompt_optional(
                "Output path [/output/was-daily-tracker.csv]: ",
                default="/output/was-daily-tracker.csv",
            )
            arguments.extend(["--output", path])
        elif destination == "2":
            arguments.append("--s3")
        else:
            email = self.prompt_required("Email-enabled analyst address(es): ")
            arguments.extend(["--email-assignee", email])
        if destination != "1":
            self.output("S3 and emailed tracker exports exclude report passwords.")
        days_back = self.prompt_nonnegative_integer("Days back [7]: ", default=7)
        assignee = self.prompt_optional("Assignee name [all]: ")
        arguments.extend(["--days-back", str(days_back)])
        if assignee:
            arguments.extend(["--assignee", assignee])
        if not self.confirm("Export the selected tracker rows to this destination?"):
            return
        self.execute("tracker CSV export", lambda: tracker_cli.main(arguments))
        self.pause()

    def import_tracker(self) -> None:
        """Prompt for and import only new rows from a tracker workbook."""
        self.output(
            "Place the XLSX file in "
            "~/code/cd_WAS_update/backend/was on the EC2 before importing."
        )
        self.output(
            "From the workstation, use: scp -P 7777 -i ~/.ssh/accessor_rsa "
            '"/local/path/FILE.xlsx" '
            "ubuntu@127.0.0.1:~/code/cd_WAS_update/backend/was/"
        )
        input_path = self.prompt_optional(
            "Input XLSX path "
            "[/backend/was/WAS_TRACKER_DailyReports_UpdatedDaily.xlsx]: ",
            default="/backend/was/WAS_TRACKER_DailyReports_UpdatedDaily.xlsx",
        )
        self.output(
            "Dates and legacy report-status markers will be converted during "
            "the import. Matching schedule/date rows will be overwritten. Imported "
            "history will not trigger reports or assignee emails."
        )
        if not self.confirm("Convert and import this daily tracker workbook?"):
            self.output("Operation cancelled.")
            return
        arguments = ["import-xlsx", "--input", input_path, "--confirm"]
        self.execute(
            "daily tracker workbook import",
            lambda: tracker_cli.main(arguments),
        )
        self.pause()

    def stakeholder_menu(self) -> None:
        """Display stakeholder management in operator workflow order."""
        actions = [
            ("View a stakeholder row", self.view_stakeholder_row),
            ("Update a stakeholder row", self.update_stakeholder_row),
            (
                "Update a stakeholder's point of contact information",
                self.update_stakeholder_contacts,
            ),
            ("Add new stakeholder by CLI", self.add_stakeholder),
            ("Import new stakeholders from CSV", self.import_stakeholders),
            ("Export stakeholders to CSV", self.export_stakeholders),
            (
                "Retrieve a stakeholder report password",
                self.retrieve_stakeholder_password,
            ),
            ("Rotate a stakeholder report password", self.rotate_stakeholder_password),
            (
                "Manually enter stakeholder report password",
                self.set_customer_provided_password,
            ),
        ]
        while True:
            self.print_menu(
                "Stakeholder Management",
                [label for label, _ in actions] + ["Back to main menu"],
            )
            selection = (
                self.input("Please enter your selection [0/b = main menu]: ")
                .strip()
                .lower()
            )
            if selection in {"0", "b"}:
                return
            if selection.isdigit() and 1 <= int(selection) <= len(actions):
                self.run_submenu_action(
                    "Stakeholder Management", actions[int(selection) - 1][1]
                )
            else:
                self.output("Invalid selection.")

    def load_and_display_stakeholder(
        self,
        stakeholder_tag: str,
    ) -> dict[str, object] | None:
        """Load and display one stakeholder without exposing its password."""
        record_holder: dict[str, dict[str, object]] = {}

        def load_stakeholder() -> int:
            """Load and display the current stakeholder row."""
            try:
                record = stakeholders_cli.get_stakeholder_record_by_tag(stakeholder_tag)
            except KeyError:
                self.output(
                    "Stakeholder tag {} was not found. No changes made.".format(
                        stakeholder_tag
                    )
                )
                return 1
            record_holder["record"] = record
            stakeholders_cli.display_stakeholder_record(
                record,
                output=self.output,
            )
            return 0

        if self.execute(
            "stakeholder lookup",
            load_stakeholder,
            show_success=False,
        ):
            return None
        return record_holder["record"]

    def view_stakeholder_row(self) -> None:
        """Display a stakeholder and allow complete field-value inspection."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        record = self.load_and_display_stakeholder(stakeholder_tag)
        if record is not None:
            self.display_full_stakeholder_fields(record)
        self.pause()

    def update_stakeholder_row(self) -> None:
        """Display one stakeholder and guide updates through every field."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        record = self.load_and_display_stakeholder(stakeholder_tag)
        if record is None:
            self.pause()
            return

        self.output(
            "Review each editable column in database order. Press Enter to "
            "keep the current value, edit the prefilled value, use CLEAR for "
            "SQL NULL, or enter CANCEL to stop."
        )
        self.output(
            "Use INTERNATIONAL for the state of an international stakeholder."
        )
        updates: dict[str, object] = {}
        for column_name in stakeholders_cli.STAKEHOLDER_EDIT_COLUMNS:
            current_value = record[column_name]
            current_text = "" if current_value is None else str(current_value)
            while True:
                raw_value = self.prompt_prefilled_value(
                    column_name,
                    current_value,
                )
                if raw_value == current_text:
                    break
                if raw_value.upper() == "CANCEL":
                    self.output("Operation cancelled.")
                    return
                if raw_value.upper() == "CLEAR":
                    if (
                        column_name
                        in stakeholders_cli.REQUIRED_STAKEHOLDER_FIELDS
                    ):
                        self.output(
                            "Invalid value: {} cannot be cleared.".format(
                                column_name
                            )
                        )
                        continue
                    if current_value is not None:
                        updates[column_name] = None
                    break
                try:
                    normalized_value = (
                        stakeholders_cli.normalize_stakeholder_update(
                            column_name,
                            raw_value,
                        )
                    )
                except ValueError as error:
                    self.output("Invalid value: {}".format(str(error)))
                    continue
                if normalized_value != current_value:
                    updates[column_name] = normalized_value
                break

        if not updates:
            self.output("No stakeholder changes were entered.")
            self.pause()
            return
        if not self.confirm(
            "Update {} field(s) for {}?".format(len(updates), stakeholder_tag)
        ):
            self.output("Operation cancelled.")
            return

        def update_stakeholder() -> int:
            """Persist validated changes and display the resulting row."""
            stakeholders_cli.update_stakeholder_fields_for_tag(
                tag=stakeholder_tag,
                updates=updates,
            )
            updated_record = stakeholders_cli.get_stakeholder_record_by_tag(
                stakeholder_tag
            )
            self.output("Updated stakeholder row:")
            stakeholders_cli.display_stakeholder_record(
                updated_record,
                output=self.output,
            )
            return 0

        self.execute(
            "stakeholder field update",
            update_stakeholder,
        )
        self.pause()

    def display_full_stakeholder_fields(
        self,
        record: dict[str, object],
    ) -> None:
        """Allow full untruncated field output for operator inspection."""
        self.output(
            "Enter a field name to print its complete value for copying. "
            "Press Enter to return."
        )
        while True:
            requested_field = self.input(
                "Field to print in full [return]: "
            ).strip()
            if not requested_field:
                return
            normalized_field = requested_field.lower().replace("-", "_")
            if normalized_field not in record:
                self.output(
                    "Unknown field. Available fields: {}".format(
                        ", ".join(record)
                    )
                )
                continue
            self.output("Full value for {}:".format(normalized_field))
            self.output(
                stakeholders_cli.stakeholder_display_value(
                    normalized_field,
                    record[normalized_field],
                )
            )

    def prompt_contact_update(
        self, label: str, current_value: object = None
    ) -> tuple[str | None, bool]:
        """Prefill current contact data; require CLEAR to remove it."""
        value = self.prompt_prefilled_value(label, current_value)
        if value == ("" if current_value is None else str(current_value)):
            return None, False
        if value.upper() == "CLEAR":
            return None, True
        return value, False

    def update_stakeholder_contacts(self) -> None:
        """Collect and submit selected stakeholder contact updates."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        record = self.require_existing_stakeholder(stakeholder_tag)
        if record is None:
            return
        report_poc, clear_report_poc = self.prompt_contact_update(
            "WAS report POC", record.get("was_report_poc")
        )
        tech_email, clear_tech_email = self.prompt_contact_update(
            "Technical POC email", record.get("tech_poc_email")
        )
        distro_email, clear_distro_email = self.prompt_contact_update(
            "Distribution email", record.get("distro_email")
        )
        arguments = ["update-contacts", "--tag", stakeholder_tag]
        field_options = [
            ("was-report-poc", report_poc, clear_report_poc),
            ("tech-poc-email", tech_email, clear_tech_email),
            ("distro-email", distro_email, clear_distro_email),
        ]
        for option_name, option_value, clear_value in field_options:
            if option_value is not None:
                arguments.extend(["--{}".format(option_name), option_value])
            elif clear_value:
                arguments.append("--clear-{}".format(option_name))
        if len(arguments) == 3:
            self.output("No stakeholder contact changes were entered.")
            return
        if not self.confirm("Apply these stakeholder contact changes?"):
            self.output("Operation cancelled.")
            return
        arguments.append("--confirm")
        self.execute(
            "stakeholder contact update",
            lambda: stakeholders_cli.main(arguments),
        )
        self.pause()

    def export_stakeholders(self) -> None:
        """Export stakeholders with optional sensitive password confirmation."""
        self.print_menu(
            "Stakeholder Export Destination",
            [
                "Save to local output",
                "Save directly to S3",
                "Email to approved analysts",
                "Cancel",
            ],
        )
        destination = self.input("Please enter your selection: ").strip()
        if destination in {"0", "b"}:
            return
        if destination not in {"1", "2", "3"}:
            self.output("Invalid selection.")
            return
        arguments = ["export-csv"]
        if destination == "1":
            output_path = self.prompt_optional(
                "Output path [/output/was-stakeholders.csv]: ",
                default="/output/was-stakeholders.csv",
            )
            arguments.extend(["--output", output_path])
        elif destination == "2":
            arguments.append("--s3")
        else:
            assignee_email = self.prompt_required(
                "Active WAS assignee email address(es): "
            )
            arguments.extend(["--email-assignee", assignee_email])
        if self.confirm("Include sensitive report passwords?"):
            confirmation = self.input(
                "Type EXPORT PASSWORDS to confirm the sensitive export: "
            ).strip()
            if confirmation != "EXPORT PASSWORDS":
                self.output("Sensitive export cancelled.")
                return
            arguments.extend(
                ["--include-report-passwords", "--confirm-sensitive-export"]
            )
        self.execute(
            "stakeholder CSV export",
            lambda: stakeholders_cli.main(arguments),
        )
        self.pause()

    def rotate_stakeholder_password(self) -> None:
        """Generate and store a new stakeholder PDF report password."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        if self.require_existing_stakeholder(stakeholder_tag) is None:
            return
        if not self.confirm(
            "Rotate the report password for {}?".format(stakeholder_tag)
        ):
            self.output("Operation cancelled.")
            return
        password_holder: dict[str, str] = {}

        def rotate_password() -> int:
            """Rotate the password and retain it only for terminal output."""
            password_holder["password"] = report_generator.rotate_report_password(
                stakeholder_tag
            )
            return 0

        exit_code = self.execute(
            "stakeholder password rotation",
            rotate_password,
            show_success=False,
        )
        if exit_code == 0:
            self.output(
                "Operation completed successfully. The new password is {}".format(
                    password_holder["password"]
                )
            )
        self.pause()

    def retrieve_stakeholder_password(self) -> None:
        """Display one stored stakeholder report password after confirmation."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        if self.require_existing_stakeholder(stakeholder_tag) is None:
            return
        if not self.confirm(
            "Display the report password for {}?".format(stakeholder_tag)
        ):
            self.output("Operation cancelled.")
            return
        password_holder: dict[str, str] = {}

        def retrieve_password() -> int:
            """Retrieve the password without writing it to application logs."""
            report_password = report_generator.lookup_report_password(stakeholder_tag)
            if not report_password:
                self.output(
                    "No report password is configured for stakeholder tag {}.".format(
                        stakeholder_tag
                    )
                )
                return 1
            password_holder["password"] = report_password
            return 0

        exit_code = self.execute(
            "stakeholder password retrieval",
            retrieve_password,
            show_success=False,
        )
        if exit_code == 0:
            self.output(
                "The report password for {} is {}".format(
                    stakeholder_tag,
                    password_holder["password"],
                )
            )
        self.pause()

    def set_customer_provided_password(self) -> None:
        """Securely add or replace a customer-provided report password."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        if self.require_existing_stakeholder(stakeholder_tag) is None:
            return
        self.output(
            "The password will be hidden and will not be written to application logs."
        )
        self.output(
            "Password requirements: {}.".format(CUSTOMER_PASSWORD_REQUIREMENTS)
        )
        report_password = self.secret_input("Customer-provided report password: ")
        confirmed_password = self.secret_input("Re-enter report password: ")
        if report_password != confirmed_password:
            self.output("Passwords do not match. No change was made.")
            self.pause()
            return
        try:
            validate_customer_provided_report_password(report_password)
        except ValueError as error:
            self.output("Password not accepted: {}".format(error))
            self.pause()
            return
        if not self.confirm(
            "Add or replace the report password for {}?".format(stakeholder_tag)
        ):
            self.output("Operation cancelled. No change was made.")
            return

        def store_password() -> int:
            """Store the password without returning or logging its value."""
            report_generator.set_report_password(
                stakeholder_tag,
                report_password,
            )
            return 0

        exit_code = self.execute(
            "customer-provided stakeholder password update",
            store_password,
            show_success=False,
        )
        if exit_code == 0:
            self.output(
                "Operation completed successfully. The customer-provided report "
                "password was stored for {}.".format(stakeholder_tag)
            )
        self.pause()

    def show_stakeholder_options(self, field: str) -> None:
        """Display known enum options without changing legacy validation rules."""
        choices = STAKEHOLDER_OPTIONS.get(field.replace("-", "_"), ())
        if choices:
            self.output("Options for {}: {}".format(field, ", ".join(choices)))

    def new_stakeholder_tag_available(self, tag: str) -> bool:
        """Reject an existing tag before collecting creation fields."""
        def check() -> int:
            """Treat a lookup failure differently from a confirmed missing tag."""
            try:
                stakeholders_cli.get_stakeholder_record_by_tag(tag)
            except KeyError:
                return 0
            self.output("That stakeholder already exists. Use Update a stakeholder row.")
            return 1

        return self.execute("new stakeholder tag lookup", check, show_success=False) == 0

    def add_stakeholder(self) -> None:
        """Collect all operator-managed fields for one new stakeholder."""
        tag = self.prompt_required("Stakeholder tag: ")
        if not self.new_stakeholder_tag_available(tag):
            return
        arguments = [
            "add",
            "--tag",
            tag,
            "--customer-name",
            self.prompt_required("Customer name: "),
        ]
        optional_text_fields = (
            ("comments", "Comments [blank]: "),
            ("location-notes", "Location notes [blank]: "),
            ("distro-email", "Distribution email addresses [blank]: "),
            ("tech-poc-email", "Technical POC email addresses [blank]: "),
            ("was-report-poc", "WAS report POC [blank]: "),
            ("subtype", "Subtype [blank]: "),
            ("parent-tag", "Parent tag [blank]: "),
            ("ticket", "Ticket [blank]: "),
        )
        for option_name, prompt in optional_text_fields:
            self.show_stakeholder_options(option_name)
            value = self.prompt_optional(prompt)
            if value:
                arguments.extend(["--{}".format(option_name), value])

        required_text_fields = (
            ("ci-type", "CI type: "),
            ("testing-sector", "Testing sector: "),
            ("frequency", "Report frequency: "),
        )
        for option_name, prompt in required_text_fields:
            self.show_stakeholder_options(option_name)
            arguments.extend(
                ["--{}".format(option_name), self.prompt_required(prompt)]
            )

        self.output(
            "Use INTERNATIONAL for the state of an international stakeholder."
        )
        arguments.extend(
            ["--state", self.prompt_required("State or INTERNATIONAL: ")]
        )

        num_web_apps = self.prompt_optional_nonnegative_integer(
            "Number of web applications [blank]: "
        )
        if num_web_apps:
            arguments.extend(["--num-web-apps", num_web_apps])

        date_fields = (
            (
                "web-apps-last-updated",
                "Web application count last updated, YYYY-MM-DD or epoch [blank]: ",
            ),
            ("last-scanned", "Last scanned, YYYY-MM-DD or epoch [blank]: "),
            ("next-scheduled", "Next scheduled, YYYY-MM-DD or epoch [blank]: "),
            ("onboarding-date", "Onboarding date, YYYY-MM-DD or epoch [blank]: "),
        )
        for option_name, prompt in date_fields:
            value = self.prompt_optional(prompt)
            if value:
                arguments.extend(["--{}".format(option_name), value])

        boolean_fields = (
            ("elections", "Is this an elections stakeholder?"),
            ("fceb", "Is this an FCEB stakeholder?"),
            ("manual-report", "Does this stakeholder require manual reports?"),
            ("retired", "Is this stakeholder retired?"),
        )
        for option_name, prompt in boolean_fields:
            if self.confirm(prompt):
                arguments.append("--{}".format(option_name))

        self.output("A report password will be generated automatically.")
        if not self.confirm("Create this stakeholder?"):
            self.output("Operation cancelled.")
            return
        arguments.append("--confirm")
        self.execute(
            "single stakeholder creation",
            lambda: stakeholders_cli.main(arguments),
        )
        self.pause()

    def import_stakeholders(self) -> None:
        """Prompt for and run an insert-only stakeholder CSV import."""
        input_path = self.prompt_optional(
            "Input CSV path [/backend/was/WAS_Stakeholders_export.csv]: ",
            default="/backend/was/WAS_Stakeholders_export.csv",
        )
        prepared_output = self.prompt_optional(
            "Prepared CSV path [/output/WAS_Stakeholders_import_ready.csv]: ",
            default="/output/WAS_Stakeholders_import_ready.csv",
        )
        self.output("Existing stakeholder tags will be skipped, not overwritten.")
        if not self.confirm("Prepare and import this stakeholder CSV?"):
            self.output("Operation cancelled.")
            return
        arguments = [
            "import-csv",
            "--input",
            input_path,
            "--prepared-output",
            prepared_output,
            "--confirm",
        ]
        self.execute(
            "stakeholder CSV import",
            lambda: stakeholders_cli.main(arguments),
        )
        self.pause()

    def refresh_tracker(self) -> None:
        """Refresh recent Qualys tracker data without destructive app deletion."""
        stakeholder_tag = self.prompt_optional("Stakeholder tag [all]: ")
        if not self.confirm("Refresh recent Qualys tracker data?"):
            self.output("Operation cancelled.")
            return
        arguments = []
        if stakeholder_tag:
            arguments.extend(["--tag", stakeholder_tag])
        self.execute(
            "daily tracker refresh",
            lambda: update_tracker_cli.main(arguments),
            cancellable=True,
        )
        self.pause()


def main() -> int:
    """Run the interactive WAS operator menu."""
    configure_logging()
    menu = WasOperatorMenu()
    try:
        return menu.run()
    except (EOFError, KeyboardInterrupt):
        menu.output("\nExiting WAS reporting operations.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

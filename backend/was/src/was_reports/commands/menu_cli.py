"""Interactive numbered menu for operator-facing WAS workflows."""

# Standard Python Libraries
from datetime import date
import logging
import sys
from typing import Callable

# Third-Party Libraries
from pyfiglet import Figlet

# First-Party Libraries
from was_reports.commands import (
    batch_runner,
    inventory_cli,
    report_generator,
    stakeholders_cli,
    tracker_cli,
    update_tracker_cli,
)

LOGGER = logging.getLogger(__name__)
InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


class WasOperatorMenu:
    """Interactive WAS menu backed by the existing command modules."""

    def __init__(
        self,
        input_function: InputFunction = input,
        output_function: OutputFunction = print,
    ) -> None:
        """Initialize menu input and output boundaries."""
        self.input = input_function
        self.output = output_function

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

    def confirm(self, prompt: str) -> bool:
        """Return whether the operator explicitly answered yes."""
        answer = self.input("{} [y/N]: ".format(prompt)).strip().lower()
        return answer in {"y", "yes"}

    def pause(self) -> None:
        """Wait for the operator before redisplaying a menu."""
        self.input("Press Enter to continue...")

    def execute(self, operation_name: str, command: Callable[[], int]) -> int:
        """Execute one command while keeping unexpected failures in the menu."""
        try:
            exit_code = command()
        except SystemExit as error:
            exit_code = int(error.code or 0)
        except Exception:
            LOGGER.exception("WAS menu operation failed: %s", operation_name)
            self.output("Operation failed. Review the WAS logs for details.")
            return 1

        if exit_code == 0:
            self.output("Operation completed successfully.")
        else:
            self.output(
                "Operation exited with status {}.".format(exit_code)
            )
        return exit_code

    def print_menu(self, title: str, options: list[str]) -> None:
        """Display one numbered menu."""
        self.output("")
        self.output(title)
        self.output("=" * len(title))
        for option_index, option_text in enumerate(options, start=1):
            self.output("{}) {}".format(option_index, option_text))
        self.output("")

    def print_banner(self) -> None:
        """Display the WAS Reporting application banner."""
        banner = Figlet(font="small", width=100).renderText("WAS REPORTING")
        self.output(banner.rstrip())

    def run(self) -> int:
        """Display the main menu until the operator exits."""
        self.print_banner()
        while True:
            self.print_menu(
                "WAS Reporting Operations",
                [
                    "Report generation",
                    "Daily tracker",
                    "Stakeholder management",
                    "Qualys operations",
                    "Quit",
                ],
            )
            selection = self.input("Please enter your selection: ").strip()
            if selection == "1":
                self.report_menu()
            elif selection == "2":
                self.tracker_menu()
            elif selection == "3":
                self.stakeholder_menu()
            elif selection == "4":
                self.qualys_menu()
            elif selection == "5":
                self.output("Exiting WAS reporting operations.")
                return 0
            else:
                self.output("Invalid selection.")

    def report_menu(self) -> None:
        """Display report generation operations."""
        while True:
            self.print_menu(
                "Report Generation",
                [
                    "Run the complete recent-scan batch",
                    "Generate and email one automatic report",
                    "Generate and email one manual report",
                    "Back to main menu",
                ],
            )
            selection = self.input("Please enter your selection: ").strip()
            if selection == "1":
                self.run_daily_batch()
            elif selection == "2":
                self.run_single_report(manual=False)
            elif selection == "3":
                self.run_single_report(manual=True)
            elif selection == "4":
                return
            else:
                self.output("Invalid selection.")

    def run_daily_batch(self) -> None:
        """Confirm and execute the complete recent-scan report batch."""
        if not self.confirm(
            "Generate, upload, and email all eligible recent-scan reports?"
        ):
            self.output("Operation cancelled.")
            return
        arguments = [
            "--recent-scans",
            "--create-missing-password",
            "--continue-on-error",
            "--send-email",
            "--send-assignee-digests",
        ]
        self.execute("recent-scan batch", lambda: batch_runner.main(arguments))
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
        )
        self.pause()

    def tracker_menu(self) -> None:
        """Display daily tracker operations."""
        while True:
            self.print_menu(
                "Daily Tracker",
                [
                    "View tracker table",
                    "View persisted report errors",
                    "Record a manual report sent date",
                    "Export tracker CSV",
                    "Back to main menu",
                ],
            )
            selection = self.input("Please enter your selection: ").strip()
            if selection == "1":
                self.view_tracker()
            elif selection == "2":
                self.view_errors()
            elif selection == "3":
                self.record_manual_sent_date()
            elif selection == "4":
                self.export_tracker()
            elif selection == "5":
                return
            else:
                self.output("Invalid selection.")

    def view_tracker(self) -> None:
        """Prompt for optional tracker filters and display matching rows."""
        days_back = self.prompt_nonnegative_integer(
            "Days back [7]: ",
            default=7,
        )
        assignee = self.prompt_optional("Assignee name [all]: ")
        report_status = self.prompt_optional(
            "Report status [all/manual/pending/sent]: "
        ).lower()
        arguments = ["show", "--days-back", str(days_back)]
        if assignee:
            arguments.extend(["--assignee", assignee])
        if report_status and report_status != "all":
            arguments.extend(["--report-status", report_status])
        self.execute("tracker table", lambda: tracker_cli.main(arguments))
        self.pause()

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
        """Prompt for and export daily tracker rows to CSV."""
        output_path = self.prompt_optional(
            "Output path [/output/was-daily-tracker.csv]: ",
            default="/output/was-daily-tracker.csv",
        )
        days_back = self.prompt_nonnegative_integer("Days back [7]: ", default=7)
        assignee = self.prompt_optional("Assignee name [all]: ")
        arguments = [
            "export-csv",
            "--days-back",
            str(days_back),
            "--output",
            output_path,
        ]
        if assignee:
            arguments.extend(["--assignee", assignee])
        self.execute("tracker CSV export", lambda: tracker_cli.main(arguments))
        self.pause()

    def stakeholder_menu(self) -> None:
        """Display stakeholder management operations."""
        while True:
            self.print_menu(
                "Stakeholder Management",
                [
                    "Update POC names and email addresses",
                    "Export stakeholders",
                    "Rotate a stakeholder report password",
                    "Back to main menu",
                ],
            )
            selection = self.input("Please enter your selection: ").strip()
            if selection == "1":
                self.update_stakeholder_contacts()
            elif selection == "2":
                self.export_stakeholders()
            elif selection == "3":
                self.rotate_stakeholder_password()
            elif selection == "4":
                return
            else:
                self.output("Invalid selection.")

    def prompt_contact_update(self, label: str) -> tuple[str | None, bool]:
        """Prompt for a contact value, no change, or explicit clearing."""
        value = self.input("{} [Enter keeps current, CLEAR removes]: ".format(label))
        normalized_value = value.strip()
        if not normalized_value:
            return None, False
        if normalized_value.upper() == "CLEAR":
            return None, True
        return normalized_value, False

    def update_stakeholder_contacts(self) -> None:
        """Collect and submit selected stakeholder contact updates."""
        stakeholder_tag = self.prompt_required("Stakeholder tag: ")
        report_poc, clear_report_poc = self.prompt_contact_update("WAS report POC")
        tech_email, clear_tech_email = self.prompt_contact_update("Technical POC email")
        distro_email, clear_distro_email = self.prompt_contact_update(
            "Distribution email"
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
        output_path = self.prompt_optional(
            "Output path [/output/was-stakeholders.csv]: ",
            default="/output/was-stakeholders.csv",
        )
        arguments = ["export-csv", "--output", output_path]
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
        if not self.confirm(
            "Rotate the report password for {}?".format(stakeholder_tag)
        ):
            self.output("Operation cancelled.")
            return
        arguments = ["--tag", stakeholder_tag, "--change-password"]
        self.execute(
            "stakeholder password rotation",
            lambda: report_generator.main(arguments),
        )
        self.pause()

    def qualys_menu(self) -> None:
        """Display safe Qualys read and tracker-refresh operations."""
        while True:
            self.print_menu(
                "Qualys Operations",
                [
                    "View stakeholder inventory",
                    "Refresh the daily tracker",
                    "Back to main menu",
                ],
            )
            selection = self.input("Please enter your selection: ").strip()
            if selection == "1":
                self.output(
                    "Querying Qualys for stakeholder inventory. "
                    "This may take several minutes; please wait..."
                )
                self.execute("Qualys inventory", lambda: inventory_cli.main([]))
                self.pause()
            elif selection == "2":
                self.refresh_tracker()
            elif selection == "3":
                return
            else:
                self.output("Invalid selection.")

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
        )
        self.pause()


def main() -> int:
    """Run the interactive WAS operator menu."""
    logging.basicConfig(level=logging.INFO)
    menu = WasOperatorMenu()
    try:
        return menu.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting WAS reporting operations.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

"""Special requirement lists for the WAS update tracker."""

# First-Party Libraries
from was_reports.data.assignees import list_active_assignee_names
from was_reports.data.special_cases import list_active_special_case_names
from was_reports.utils.database import close, connect

conn = connect()
try:
    ASSIGNEES = list_active_assignee_names(conn)
    KEEP_NWS = list_active_special_case_names(conn)
finally:
    close(conn)

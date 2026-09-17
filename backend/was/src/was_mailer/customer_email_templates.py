"""Composable customer-email sections derived from the supplied Outlook templates."""

ALLOWLIST_NOTICE = (
    "Please be sure to review and revise your allowlist for CISA WAS source "
    "IP's as our scanner IP's have recently changed: {allowlist_url}"
)

REPORT_ATTACHMENT_NOTICE = (
    "Attached is a report containing the results from your most recent Web "
    "Application Scanning (WAS) vulnerability scan. You should use the same "
    "password as before. If you have yet to receive a password, please let us know."
)

NO_REPORT_NOTICE = (
    "Your most recent Web Application Scanning (WAS) vulnerability scan found "
    "no accessible web services. No PDF report was generated."
)

NWS_EXPLANATION = (
    "NWS means No Web Service. During the scan, our scanner could not reach an "
    "accessible web service for the target."
)

INACCESSIBLE_TARGETS_WITH_COUNTS = (
    "Results indicate that {inaccessible_count} out of {total_count} web "
    "applications from your scan are inaccessible by our scanner. The "
    "inaccessible target(s) is/are:"
)

INACCESSIBLE_TARGETS = (
    "Results indicate that the following web applications from your scan are "
    "inaccessible by our scanner:"
)

INACCESSIBLE_REASONS_HEADING = (
    "A few common reasons why the web applications are inaccessible are:"
)

INACCESSIBLE_REASONS = (
    "The web applications are not publicly accessible via the internet and can "
    "only be reached in your internal network.",
    "Your firewalls are blocking our traffic. We recommend safelisting CISA "
    "CyHy source IP addresses.",
    "The target web applications may have been down for maintenance or "
    "experiencing connectivity issues during the time of the scan.",
    "The target web applications are behind a login page. Web applications that "
    "require authentication may either completely fail to scan or return with "
    "limited findings.",
)

TWO_SCAN_REMOVAL_NOTICE = (
    "In accordance with DHS CyHy WAS policy, if web applications fail to resolve "
    "to a web service for 2 consecutive scans, they will be removed from the list "
    "of scan targets. Please provide an updated list of targets. Once we receive "
    "an updated list of targets, they will be scanned as part of your next "
    "regularly scheduled scan."
)

FCEB_RETENTION_NOTICE = (
    "FCEB web applications remain enrolled during inaccessible scans and are "
    "removed only at the customer's request."
)

APPENDIX_NOTICE = (
    "Additional details regarding findings, links crawled, vulnerabilities by "
    "webapp and severity, sensitive data found, etc., can be found under Appendix "
    "C: Attachments. To access the attachments embedded within the report, open "
    "the report with a dedicated PDF reader, such as Adobe Acrobat, and "
    "double-click on the paper clip icon to the left of the attachment name. A "
    "helpful list of scan report and WAS FAQs can be found here: {faq_url}"
)

PASSWORD_SUPPORT_NOTICE = (
    "Please have a technical POC contact reports@cisa.dhs.gov should you "
    "need a copy of, or to update your WAS report password."
)

QUESTIONS_NOTICE = (
    "If you have any additional questions or concerns, please let us know."
)

NEXT_SCAN_NOTICE = "Your next scan is scheduled for {next_scan_date}."

QUALYS_ERROR_HEADING = (
    "A Qualys internal error prevented the scan from completing for the following "
    "web applications, so they do not have updated results in this report:"
)

QUALYS_ERROR_RESCAN_NOTICE = (
    "If you would like a rescan before your next regularly scheduled scan, "
    "please provide a preferred date and time for an ad hoc scan."
)

SENSITIVE_DATA_NOTICE = (
    "Qualys is currently unable to provide the sensitive-data attachment for "
    "Social Security number and credit-card findings. This temporary notice will "
    "be removed after Qualys restores the capability."
)

REMOVED_TARGETS_HEADING = (
    "Web applications removed from Qualys after two consecutive inaccessible scans:"
)

TARGETS_REMOVED_REQUEST_NOTICE = (
    "Please provide an updated list of targets to request additional targets. "
    "Once we receive the updated list, the targets will be scanned as part of "
    "your next regularly scheduled scan."
)

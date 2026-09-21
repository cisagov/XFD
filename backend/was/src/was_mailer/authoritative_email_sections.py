"""Exact text and run formatting extracted from the September 21 DOCX files.

Source: WAS_EMAIL_templates_Newest9_21.zip. Each entry records the original
DOCX SHA-256. Dynamic angle-bracket placeholders are replaced during composition.
Do not rewrite customer wording without an updated approved source document.
"""

SOURCE_ZIP_SHA256 = "262796c823b7bf5b17897ca427755756fa710663fd1c9339bbecd28546739c2f"

SECTIONS = {
    "nws_notification": {
        "sha256": "2ea676a1fc28862c65809013792b9c7da41dc9566fd9cf2af98ca3a9292c9d0f",
        "text": "<num_nws_webapps> out of <num_total_webapps> web "
        "applications from your scan were inaccessible by our "
        "scanner. The inaccessible target(s) is/are:\n"
        "\n"
        "<list_nws_webapps>\n"
        "\n"
        "This may be due to:\n"
        "- The application(s) no longer being publicly "
        "accessible\n"
        "- The application(s) have been decommissioned\n"
        "- Scanner traffic being blocked (e.g., firewall or "
        "safelisting restrictions)\n"
        "  - https://rules.vm.cyber.dhs.gov/was.txt",
        "html": "<div><strong>&lt;num_nws_webapps&gt; </strong>out of "
        "<strong>&lt;num_total_webapps&gt;</strong> web "
        "applications from your scan were inaccessible by our "
        "scanner. The inaccessible target(s) "
        "is/are:<br><br>&lt;list_nws_webapps&gt;<br><br>This may "
        "be due to:</div>\n"
        '<ul style="margin:0;padding-left:18pt">\n'
        "<li>The application(s) no longer being publicly "
        "accessible\n"
        "</li>\n"
        "<li>The application(s) have been decommissioned\n"
        "</li>\n"
        "<li>Scanner traffic being blocked (e.g., firewall or "
        "safelisting restrictions)\n"
        "<ul "
        'style="margin:0;padding-left:18pt"><li>https://rules.vm.cyber.dhs.gov/was.txt</li></ul>\n'
        "</li></ul>",
    },
    "nws_webapp_removal_warning": {
        "sha256": "80e3b216c09adb41f9228dcaa676adc64e8bcf9f645d3621127cffaa48d7ad21",
        "text": "Per DHS CyHy WAS policy, web applications "
        "that fail to resolve for two consecutive "
        "scans will be removed from the scan target "
        "list. Please provide an updated list to "
        "vulnerability@cisa.dhs.gov; new targets will "
        "be included in your next scheduled scan.",
        "html": "<div>Per DHS CyHy WAS policy, web "
        "applications that fail to resolve for two "
        "consecutive scans will be removed from the "
        "scan target list. Please provide an updated "
        "list to vulnerability@cisa.dhs.gov; new "
        "targets will be included in your next "
        "scheduled scan.</div>",
    },
    "qualys_scan_error": {
        "sha256": "076f5cafa93ab273a216b0bd30a3f5a8c58234d3b327b5813c2943715ddb6e52",
        "text": "Please Note: Our scanners experienced an internal "
        "error causing the assessment of the following "
        "webapp(s) not to complete. If you would like a rescan "
        "prior to your next regularly scheduled scan date, "
        "please provide a date and time for an ad hoc scan:\n"
        "\n"
        "<list_error_webapps>",
        "html": "<div><strong>Please Note:</strong> Our scanners "
        "experienced an internal error causing the assessment "
        "of the following webapp(s) not to complete. If you "
        "would like a rescan prior to your next regularly "
        "scheduled scan date, please provide a date and time "
        "for an ad hoc "
        "scan:<br><br>&lt;list_error_webapps&gt;</div>",
    },
    "report_not_generated": {
        "sha256": "52809a02748c0b8867eb2f5ca0b5624299ed677803d18661f686d71a04057861",
        "text": "WAS Report for <tag> could not be generated\n"
        "\n"
        "<poc_names>,\n"
        "\n"
        "A Web Application Scanning (WAS) vulnerability "
        "report could not be generated for your most recent "
        "scan on <last_scan_date>. This is because ALL "
        "target(s) provided for your scan were inaccessible "
        "by our scanners.\n"
        "\n"
        "The inaccessible target(s) is/are:\n"
        "\n"
        "<list_nws_webapps>\n"
        "\n"
        "This may be due to:\n"
        "- The application(s) no longer being publicly "
        "accessible\n"
        "- The application(s) have been decommissioned\n"
        "- Scanner traffic being blocked (e.g., firewall or "
        "safelisting restrictions)\n"
        "  - https://rules.vm.cyber.dhs.gov/was.txt\n"
        "\n"
        "Per DHS CyHy WAS policy, web applications that fail "
        "to resolve for two consecutive scans will be "
        "removed from the scan target list. Please provide "
        "an updated list; new targets will be included in "
        "your next scheduled scan.\n"
        "\n"
        "For your reference, a helpful list of scan report "
        "and WAS FAQs can be found here: "
        "https://www.cisa.gov/cyber-hygiene-services\n",
        "html": '<div><span style="font-size:15pt"><strong>WAS '
        "Report for &lt;tag&gt; could not be "
        "generated</strong></span></div>\n"
        "<div><br></div>\n"
        "<div>&lt;poc_names&gt;,<br><br>A Web Application "
        "Scanning (WAS) vulnerability report <u>could not be "
        "generated</u> for your most recent scan on "
        "<strong>&lt;last_scan_date&gt;</strong>. This is "
        "because <u>ALL target(s) provided for your scan "
        "were inaccessible by our scanners.</u><br><br>The "
        "inaccessible target(s) "
        "is/are:<br><br>&lt;list_nws_webapps&gt;<br><br>This "
        "may be due to:</div>\n"
        '<ul style="margin:0;padding-left:18pt">\n'
        "<li>The application(s) no longer being publicly "
        "accessible\n"
        "</li>\n"
        "<li>The application(s) have been decommissioned\n"
        "</li>\n"
        "<li>Scanner traffic being blocked (e.g., firewall "
        "or safelisting restrictions)\n"
        "<ul "
        'style="margin:0;padding-left:18pt"><li>https://rules.vm.cyber.dhs.gov/was.txt</li></ul>\n'
        "</li></ul>\n"
        "<div><br>Per DHS CyHy WAS policy, web applications "
        "that fail to resolve for <u>two consecutive "
        "scans</u> will be <strong>removed from the scan "
        "target list</strong>. Please provide an updated "
        "list; new targets will be included in your next "
        "scheduled scan.<br><br>For your reference, a "
        "helpful list of scan report and WAS FAQs can be "
        "found here: "
        "https://www.cisa.gov/cyber-hygiene-services</div>\n"
        "<div><br></div>",
    },
    "results_part1": {
        "sha256": "81d3730eb35d5f486bd24c4ad9866b7c2d33f12d803a49e75b90bab8e1bfeb78",
        "text": "WAS Results for <tag>\n"
        "\n"
        "<poc_names>,\n"
        "\n"
        "Attached is a report containing the results from your most "
        "recent Web Application Scanning (WAS) vulnerability scan "
        "that began at <last_scan_date>.\n"
        "\n"
        "Important Note: Attachment 7 (Sensitive Data – Social "
        "Security and Credit Card Numbers) will not be populated "
        "for this scan cycle due to vendor maintenance. We "
        "apologize for any inconvenience and are happy to assist "
        "with any questions.\n"
        "\n"
        "Additional details regarding findings, links crawled, "
        "vulnerabilities by webapp and severity, sensitive data "
        "found, etc., can be found under Appendix C: Attachments. "
        "To access the attachments embedded within the report, open "
        "the report with a dedicated PDF reader (such as Adobe "
        "Acrobat), and double-click on the paper clip icon to the "
        "left of the attachment name. A helpful list of scan report "
        "and WAS FAQs can be found here: "
        "https://www.cisa.gov/cyber-hygiene-services",
        "html": '<div><span style="font-size:15pt"><strong>WAS Results for '
        "&lt;tag&gt;</strong></span></div>\n"
        "<div><br></div>\n"
        "<div>&lt;poc_names&gt;,<br><br>Attached is a report "
        "containing the results from your most recent Web "
        "Application Scanning (WAS) vulnerability scan that began "
        "at <strong>&lt;last_scan_date&gt;</strong>.<br><br><span "
        'style="background-color:#ffff00"><strong>Important '
        "Note:</strong></span><span "
        'style="background-color:#ffff00"> </span><span '
        'style="background-color:#ffff00"><em>Attachment 7 '
        "(Sensitive Data – Social Security and Credit Card Numbers) "
        "</em></span><span "
        'style="background-color:#ffff00"><u><em>will '
        "not</em></u></span><span "
        'style="background-color:#ffff00"><em> be populated for '
        "this scan cycle due to vendor maintenance. We apologize "
        "for any inconvenience and are happy to assist with any "
        "questions.</em></span><br><br><strong>Additional details "
        "regarding findings, links crawled, vulnerabilities by "
        "webapp and severity, sensitive data found, etc., can be "
        "found under Appendix C: Attachments. </strong>To access "
        "the attachments embedded within the report, open the "
        "report with a dedicated PDF reader (such as Adobe "
        "Acrobat), and <u>double-click on the paper clip icon</u> "
        "to the left of the attachment name. A helpful list of scan "
        "report and WAS FAQs can be found here: <a "
        'style="color:#467886;text-decoration:underline" '
        'href="https://www.cisa.gov/cyber-hygiene-services">https://www.cisa.gov/cyber-hygiene-services</a></div>',
    },
    "results_part2": {
        "sha256": "9748d38d43e6645e068bcdfad460ef9c923fe4e98646b65f6a8debd8004456c7",
        "text": "Your next scan is scheduled for <next_scan_date>.\n"
        "\n"
        "If you have questions, please email at "
        "vulnerability@cisa.dhs.gov.\n"
        "\n"
        "Regards,\n"
        "\n"
        "<assignee_name>\n"
        "Web Application Scanning (WAS)\n"
        "Cybersecurity and Infrastructure Security Agency (CISA)\n"
        "Email: reports@cyber.dhs.gov\n"
        "<cisa_logo>",
        "html": "<div>Your next scan is scheduled for "
        "<strong>&lt;next_scan_date&gt;</strong>.<br><br>If you "
        "have questions, please email at "
        "vulnerability@cisa.dhs.gov.<br><br>Regards,<br><br><strong>&lt;assignee_name&gt;</strong><br>Web "
        "Application Scanning (WAS)<br>Cybersecurity and "
        "Infrastructure Security Agency (CISA)<br>Email: <a "
        'style="color:#467886;text-decoration:underline" '
        'href="mailto:reports@cyber.dhs.gov">reports@cyber.dhs.gov</a></div>\n'
        "<div>&lt;cisa_logo&gt;</div>",
    },
    "targets_removed": {
        "sha256": "728c6729e2450c4302e2e74d534c4bd39df0f9156a50fcdca37a859bfe16008d",
        "text": "As of <last_scan_date>, the <num_removed_webapps> "
        "target(s) listed below were inaccessible by our scanners "
        "two consecutive times, and have been removed from your "
        "scan:\n"
        "\n"
        "<list_removed_webapps>\n"
        "\n"
        "Please provide an updated list of targets to "
        "vulnerability@cisa.dhs.gov. Once we receive an updated "
        "list of targets, they will be scanned as part of your "
        "next regularly scheduled scan.",
        "html": "<div>As of <strong>&lt;last_scan_date&gt;</strong>, the "
        "<strong>&lt;num_removed_webapps&gt;</strong> target(s) "
        "listed below were inaccessible by our scanners two "
        "consecutive times, and have been removed from your "
        "scan:</div>\n"
        "<div><br></div>\n"
        "<div>&lt;list_removed_webapps&gt;</div>\n"
        "<div><br></div>\n"
        "<div>Please provide an updated list of targets to "
        "vulnerability@cisa.dhs.gov. Once we receive an updated "
        "list of targets, they will be scanned as part of your "
        "next regularly scheduled scan.</div>",
    },
}

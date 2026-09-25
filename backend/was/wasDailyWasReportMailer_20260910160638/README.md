# WAS Report Mailer Email Templates

This directory documents the exported historical Power Automate flow named
`dailywas - Report Mailer`. The original export may be reviewed locally under
`Microsoft.Flow/flows/`, but it is intentionally excluded from source control
because it contains tenant, connection, chat, SharePoint, and user identifiers.
The active WAS Python mailer does not execute the exported flow or read email
content from `definition.json`.

The current customer email implementation uses the approved Outlook `.msg`
templates supplied with the WAS project. The approved wording was separated
into reusable sections so that each customer receives only the information
that applies to the current report outcome.

## Current implementation

The relevant runtime files are outside this export directory:

- `../src/was_mailer/customer_email_templates.py` contains the reusable,
  approved text sections derived from the supplied Outlook templates.
- `../src/was_mailer/message.py` selects and combines those sections and builds
  the plain-text and HTML alternatives.
- `../src/was_mailer/email_reports.py` obtains the report-run data, customer POC,
  recipients, and attachment, then sends the composed MIME message through SES.
- `../src/was_reports/resources/assets/CISA_logo_email.png` is the packaged copy
  of the individual CISA logo used at the bottom of the HTML alternative. The
  original remains at `../was_report/assets/CISA_logo_email.png`.

The Python mailer is the source of truth for current production behavior. The
Power Automate JSON documents the workflow that preceded it.

## Authoritative September 21 source

The approved source is `WAS_EMAIL_templates_Newest9_21.zip`. Its component DOCX
files and flowchart supersede the earlier Outlook `.msg` examples. The archive
is not read at runtime. Exact text and formatting extracted from it are stored
in `../src/was_mailer/authoritative_email_sections.py`, together with the source
archive and component SHA-256 values. Customer wording must not be rewritten
without a newly approved source.

`customer_email_templates.py` performs only documented placeholder
substitution and section selection. It does not paraphrase the source sections.

## Composition strategy

Customer deliveries start with the source title and the exact POC line. The
mailer does not invent a `Hello` salutation when a POC is present:

```text
WAS Results for EXAMPLE

Jordan Smith,
```

If no POC is available, the placeholder fallback produces `Hello,`. An
analyst-only test copy uses a separate, clearly identified analyst message and
is not the customer template.

```text
Hello,
```

The mailer then includes sections according to the tracker template and the
data available for that report.

| Section | Included when |
| --- | --- |
| Results introduction and Attachment 7 notice | Any PDF-producing customer outcome |
| No-report notice | Template is `All NWS` or `FCEB All NWS` |
| Inaccessible-target count and list | `recent_nws` contains one or more targets |
| Common inaccessible reasons and scanner-IP link | `recent_nws` contains one or more targets, or all targets are inaccessible |
| Two-scan removal warning | A non-FCEB PDF outcome has inaccessible targets; the authoritative all-NWS source also contains this language |
| Removed-target list | Template is `Targets Removed`, and both `recent_nws` and `remove_nws` have values |
| Qualys internal-error and rescan block | A PDF-producing template when `qualys_error` has values |
| Appendix C and report FAQ instructions | A PDF report is being delivered |
| Temporary Attachment 7 vendor-maintenance notice | A PDF report is being delivered |
| Next scan date | Always; a missing value is rendered as `Not available` |
| Signature | Always |
| CISA logo | Bottom of the HTML alternative |

An empty optional value does not produce an empty heading. The complete section
is omitted. This is the composable behavior that replaces one large email body
containing every possible message.

## Tracker template outcomes

### Results

Used for a normal report with accessible applications and no special
customer-action condition.

- Subject: `<TAG> - WAS Results`
- PDF: attached
- Includes the scan-start timestamp, highlighted Attachment 7 notice, Appendix
  C instructions, questions address, next scan, assigned analyst and WAS team
  signature, and individual CISA logo.
- Inaccessible-target and Qualys-error sections are added only when their data
  is present.

### Action Required

Used when some targets were inaccessible and customer action is needed.

- Subject: `<TAG> - WAS Results - Action Required`
- PDF: attached
- Uses the complete standard `Results` email as its base.
- Adds inaccessible counts, target URLs, the source list of possible causes,
  scanner-IP link, and the non-FCEB two-scan removal warning.

### FCEB Action Required

Used when some FCEB targets were inaccessible.

- Subject: `<TAG> - WAS Results - Action Required`
- PDF: attached
- Uses the complete standard `Results` email as its base.
- Adds inaccessible counts, target URLs, possible causes, and the scanner-IP
  link. It omits the non-FCEB removal-warning component.

### Targets Removed

Used after eligible targets have been removed following consecutive
inaccessible scans.

- Subject: `<TAG> - WAS Results - Targets Removed`
- PDF: attached
- Uses the complete `Action Required` email as its base.
- Adds a separate list of targets removed from Qualys after two consecutive NWS
  scans.
- Explains how the customer can provide an updated target list to request
  additional targets for the next scheduled scan.

### All NWS

Used when all targets were inaccessible and no useful PDF report was generated.

- Subject: `<TAG> - WAS Report Not Generated - Action Required`
- PDF: not attached
- Uses the authoritative no-report component verbatim, including its
  inaccessible-target list, possible causes, scanner-IP link, and approved
  two-scan removal notice.
- Omits report-only instructions such as Appendix C and the PDF password
  reminder.

### FCEB All NWS

Used when all FCEB targets were inaccessible and no useful PDF report was
generated.

- Subject: `<TAG> - WAS Report Not Generated - Action Required`
- PDF: not attached
- Uses the same authoritative no-report component as `All NWS`. The source does
  not define a separate FCEB all-NWS paragraph, so the implementation does not
  alter that component.
- Omits all report-only instructions and does not attach a PDF.

## Example: normal results email

The following illustrates the rendered plain-text alternative. Names, tags,
dates, and URLs are examples.

```text
Subject: EXAMPLE - WAS Results

WAS Results for EXAMPLE

Jordan Smith,

Attached is a report containing the results from your most recent Web
Application Scanning (WAS) vulnerability scan that began at September 23, 2026
at 01:00 AM Eastern Time.

Important Note: Attachment 7 (Sensitive Data - Social Security and Credit Card
Numbers) will not be populated for this scan cycle due to vendor maintenance.
We apologize for any inconvenience and are happy to assist with any questions.

Additional details regarding findings, links crawled, vulnerabilities by webapp
and severity, sensitive data found, etc., can be found under Appendix C:
Attachments. To access the attachments embedded within the report, open the
report with a dedicated PDF reader, such as Adobe Acrobat, and double-click on
the paper clip icon to the left of the attachment name. A helpful list of scan
report and WAS FAQs can be found here:
https://www.cisa.gov/cyber-hygiene-services

Your next scan is scheduled for October 16, 2026.

If you have questions, please email at vulnerability@cisa.dhs.gov.

Regards,
Assigned Analyst
Web Application Scanning (WAS)
Cybersecurity and Infrastructure Security Agency (CISA)
Email: reports@cyber.dhs.gov

[Individual CISA logo appears here in the HTML version]
```

The encrypted customer PDF is attached as
`<TAG>_WAS_report_<YYYY-MM-DD>.pdf`; internal UUIDs are not exposed in its
customer-facing filename.

## Example: action-required additions

For an `Action Required` outcome, the following block is inserted after the
report introduction:

```text
2 out of 10 web applications from your scan were inaccessible by our scanner.
The inaccessible target(s) is/are:
- https://first.example.gov
- https://second.example.gov

This may be due to:
- The application(s) no longer being publicly accessible
- The application(s) have been decommissioned
- Scanner traffic being blocked (e.g., firewall or safelisting restrictions)
  - https://rules.vm.cyber.dhs.gov/was.txt

```

For `Targets Removed`, the same block is followed by the removed-target list and
the instructions for providing an updated list to request additional targets.

## Qualys internal-error block

The Qualys-error block can be added to PDF-producing `Results`, `Action
Required`, `Targets Removed`, and `FCEB Action Required` outcomes. The
authoritative all-NWS component is selected as a complete alternative and does
not receive this overlay. A URL is included only when its Qualys result is
`SCAN_INTERNAL_ERROR` or `SCAN_RESULTS_INVALID`. `PROCESSING` is not treated as
a customer-facing Qualys internal error.

```text
Please Note: Our scanners experienced an internal error causing the assessment
of the following webapp(s) not to complete. If you would like a rescan prior to
your next regularly scheduled scan date, please provide a date and time for an
ad hoc scan:
- https://error.example.gov
```

## Example: no-report email

An `All NWS` outcome does not attach a PDF and begins as follows:

```text
Subject: EXAMPLE - WAS Report Not Generated - Action Required

WAS Report for EXAMPLE could not be generated

Jordan Smith,

A Web Application Scanning (WAS) vulnerability report could not be generated
for your most recent scan on September 23, 2026 at 01:00 AM Eastern Time. This
is because ALL target(s) provided for your scan were inaccessible by our
scanners.

The inaccessible target(s) is/are:
- https://first.example.gov
- https://second.example.gov

[The authoritative possible-cause and two-scan policy paragraphs follow.]

Your next scan is scheduled for October 16, 2026.

Regards,
Assigned Analyst
Web Application Scanning (WAS)
Cybersecurity and Infrastructure Security Agency (CISA)
Email: reports@cyber.dhs.gov

[Individual CISA logo appears here in the HTML version]
```

## HTML and accessibility behavior

The same content is sent as both plain text and HTML. The HTML alternative:

- escapes all tracker and stakeholder values before rendering them;
- renders list values as semantic bullet lists;
- preserves the approved bold, italic, underline, and highlighted sections;
- includes a descriptive `WAS Results for <TAG>` heading;
- places the CISA logo after the signature and gives it `alt="CISA"`;
- references the logo by content ID so it can render inline without retrieving
  an image from an external website; and
- keeps the plain-text alternative available when a client blocks HTML or
  inline images.

The resulting MIME structure is conceptually:

```text
multipart/mixed
├── multipart/alternative
│   ├── text/plain
│   └── multipart/related
│       ├── text/html
│       └── image/png (inline, Content-ID: cisa-logo)
└── application/pdf (only for report-producing outcomes)
```

Email clients may still expose the inline image in an attachment list, but the
HTML body places it at the bottom of the message.

## Data used by the composer

The email composer receives these values from the persisted report run and its
linked tracker and stakeholder records:

| Value | Purpose |
| --- | --- |
| `stakeholder_tag` | Subject, heading, and report identity |
| `was_report_poc` | Exact POC line after the source title |
| `template` | Selects the outcome-specific sections |
| `assignee_name` | One assigned analyst shown above the WAS team signature |
| `recent_nws` | Inaccessible target list |
| `nws` | Total and inaccessible counts |
| `remove_nws` | Removed target list |
| `qualys_error` | Targets with `SCAN_INTERNAL_ERROR` or `SCAN_RESULTS_INVALID` |
| `scan_started_at` | Full Qualys scan-start instant rendered in Eastern Time as `last_scan_date` |
| `next_scheduled` | Customer-facing next scan date |
| `output_path` | PDF attachment source when a report is required |

This data-driven composition prevents irrelevant sections from appearing in a
customer email and keeps the approved wording centralized for future review.

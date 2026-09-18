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

## Supplied Outlook source templates

The approved source material was supplied for review in the local
`../WAS_email_templates/` directory:

- `CUSTOMERTAG - WAS Results.msg` supplies the normal report-delivery wording.
- `CUSTOMERTAG - WAS Results - Action Required.msg` supplies the report plus
  customer-action wording.
- `NWS - Action Required.msg` supplies the no-accessible-web-service wording.

The binary `.msg` files are intentionally excluded from source control because
they retain Outlook author metadata. The Python implementation does not parse
them at runtime. Their approved wording is represented as reviewable constants
in `customer_email_templates.py`, then selected using tracker data as described
below.

## Composition strategy

Every report email starts with a salutation. Customer deliveries use the WAS
report POC when one is configured:

```text
Hello Jordan Smith,
```

If no POC is available, or when the delivery is an analyst-only copy, the
salutation is:

```text
Hello,
```

The mailer then includes sections according to the tracker template and the
data available for that report.

| Section | Included when |
| --- | --- |
| Scanner IP allowlist notice | A PDF report is being delivered |
| Report attachment and password reminder | A PDF report is being delivered |
| No-report notice | Template is `All NWS` or `FCEB All NWS` |
| Inaccessible-target count and list | `recent_nws` contains one or more targets |
| Common inaccessible reasons | `recent_nws` contains one or more targets |
| Two-scan removal notice | Template is `All NWS` |
| FCEB retention notice | Template is `FCEB Action Required` or `FCEB All NWS` |
| Removed-target list | Template is `Targets Removed` and `remove_nws` has values |
| Additional-target request instructions | Template is `Targets Removed` and removed targets are listed |
| Qualys internal-error and rescan block | Any template when `qualys_error` has values |
| Appendix C and report FAQ instructions | A PDF report is being delivered |
| Password support notice | A PDF report is being delivered |
| Temporary sensitive-data notice | A PDF report is being delivered |
| Next scan date | `next_scheduled` is available |
| Signature | Always |
| CISA logo | Bottom of the HTML alternative |

An empty optional value does not produce an empty heading. The complete section
is omitted. This is the composable behavior that replaces one large email body
containing every possible message.

## Tracker template outcomes

### Results

Used for a normal report with accessible applications and no special
customer-action condition.

- Subject: `<TAG> WAS Results`
- PDF: attached
- Includes the allowlist, report/password, highlighted sensitive-data,
  Appendix C, password support, questions, next-scan, assigned analyst and WAS
  team signature, and individual CISA logo sections.
- Inaccessible-target and Qualys-error sections are added only when their data
  is present.

### Action Required

Used when some targets were inaccessible and customer action is needed.

- Subject: `<TAG> WAS Results - Action Required`
- PDF: attached
- Uses the complete standard `Results` email as its base.
- Adds inaccessible counts, target URLs, and an explanation of common NWS
  conditions.

### FCEB Action Required

Used when some FCEB targets were inaccessible.

- Subject: `<TAG> WAS Results - Action Required`
- PDF: attached
- Uses the complete standard `Results` email as its base.
- Adds inaccessible counts, target URLs, and common NWS reasons.
- Includes the FCEB retention notice instead of a removal warning.

### Targets Removed

Used after eligible targets have been removed following consecutive
inaccessible scans.

- Subject: `<TAG> WAS Results - Action Required`
- PDF: attached
- Uses the complete `Action Required` email as its base.
- Adds a separate list of targets removed from Qualys after two consecutive NWS
  scans.
- Explains how the customer can provide an updated target list to request
  additional targets for the next scheduled scan.

### All NWS

Used when all targets were inaccessible and no useful PDF report was generated.

- Subject: `<TAG> WAS Results - Action Required`
- PDF: not attached
- Includes the no-report notice, inaccessible target list, common reasons, and
  the approved two-scan removal notice.
- Omits report-only instructions such as Appendix C and the PDF password
  reminder.

### FCEB All NWS

Used when all FCEB targets were inaccessible and no useful PDF report was
generated.

- Subject: `<TAG> WAS Results - Action Required`
- PDF: not attached
- Includes the no-report notice, inaccessible target list, common reasons, and
  the FCEB retention notice.
- Omits the non-FCEB removal warning and all report-only instructions.

## Example: normal results email

The following illustrates the rendered plain-text alternative. Names, tags,
dates, and URLs are examples.

```text
Subject: EXAMPLE WAS Results

Hello Jordan Smith,

Please be sure to review and revise your allowlist for CISA WAS source IP's as
our scanner IP's have recently changed:
https://rules.vm.cyber.dhs.gov/was.txt

Attached is a report containing the results from your most recent Web
Application Scanning (WAS) vulnerability scan. You should use the same password
as before. If you have yet to receive a password, please let us know.

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

Please have a technical POC contact vulnerability@cisa.dhs.gov should you need
a copy of, or to update your WAS report password.

If you have any additional questions or concerns, please let us know.

Your next scan is scheduled for October 16, 2026.

Regards,
Assigned Analyst
Web Application Scanning (WAS)
Cybersecurity and Infrastructure Security Agency (CISA)
Email: reports@cyber.dhs.gov

[Individual CISA logo appears here in the HTML version]
```

The encrypted PDF is attached after the message alternatives in the MIME
message.

## Example: action-required additions

For an `Action Required` outcome, the following block is inserted after the
report introduction:

```text
Results indicate that 2 out of 10 web applications from your scan are
inaccessible by our scanner. The inaccessible target(s) is/are:
- https://first.example.gov
- https://second.example.gov

A few common reasons why the web applications are inaccessible are:
- The web applications are not publicly accessible via the internet and can
  only be reached in your internal network.
- Your firewalls are blocking our traffic. We recommend safelisting CISA CyHy
  source IP addresses.
- The target web applications may have been down for maintenance or
  experiencing connectivity issues during the time of the scan.
- The target web applications are behind a login page. Web applications that
  require authentication may either completely fail to scan or return with
  limited findings.

```

For `Targets Removed`, the same block is followed by the removed-target list and
the instructions for providing an updated list to request additional targets.

## Qualys internal-error block

The Qualys-error block is independent of the selected email template. It can be
added to `Results`, `Action Required`, `Targets Removed`, `All NWS`, or either
FCEB outcome. A URL is included only when its Qualys result is
`SCAN_INTERNAL_ERROR` or `SCAN_RESULTS_INVALID`. `PROCESSING` is not treated as
a customer-facing Qualys internal error.

```text
A Qualys internal error prevented the scan from completing for the following
web applications, so they do not have updated results in this report:
- https://error.example.gov

If you would like a rescan before your next regularly scheduled scan, please
provide a preferred date and time for an ad hoc scan.
```

## Example: no-report email

An `All NWS` outcome does not attach a PDF and begins as follows:

```text
Subject: EXAMPLE WAS Results - Action Required

Hello Jordan Smith,

Your most recent Web Application Scanning (WAS) vulnerability scan found no
accessible web services. No PDF report was generated.

Results indicate that 10 out of 10 web applications from your scan are
inaccessible by our scanner. The inaccessible target(s) is/are:
- https://first.example.gov
- https://second.example.gov

[Common reasons and the applicable removal or FCEB retention notice follow.]

If you have any additional questions or concerns, please let us know.

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
| `was_report_poc` | Named customer salutation |
| `template` | Selects the outcome-specific sections |
| `assignee_name` | One assigned analyst shown above the WAS team signature |
| `recent_nws` | Inaccessible target list |
| `nws` | Total and inaccessible counts |
| `remove_nws` | Removed target list |
| `qualys_error` | Targets with `SCAN_INTERNAL_ERROR` or `SCAN_RESULTS_INVALID` |
| `next_scheduled` | Customer-facing next scan date |
| `output_path` | PDF attachment source when a report is required |

This data-driven composition prevents irrelevant sections from appearing in a
customer email and keeps the approved wording centralized for future review.

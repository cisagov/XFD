# Manual report recovery

The daily batch does not automatically retry rows marked `MANUAL`. Use the
guarded recovery command only for explicit tracker IDs whose logs confirm one
of these resolved causes:

- `password-validation`: the historical password rule rejected a stored
  password that the current existing-password validator now accepts.
- `qualys-read-timeout`: report generation stopped on a safe Qualys read
  timeout, with no uncertain report-creation outcome.

Preview is the default and does not change data, generate reports, or send
email:

```bash
make recover-manual-reports \
  MANUAL_TRACKER_IDS="123,456" \
  RECOVERY_CAUSE="password-validation" \
  DAYS_BACK=7
```

Review every result. Applying requires the exact confirmation value and sends
successful reports to the normal customer recipients:

```bash
make recover-manual-reports \
  MANUAL_TRACKER_IDS="123,456" \
  RECOVERY_CAUSE="password-validation" \
  DAYS_BACK=7 \
  APPLY=1 \
  RECOVERY_CONFIRM=RECOVER
```

For a controlled test, override all report recipients:

```bash
make recover-manual-reports \
  MANUAL_TRACKER_IDS="123,456" \
  RECOVERY_CAUSE="password-validation" \
  DAYS_BACK=7 \
  TEST_RECIPIENTS="approved.analyst@example.gov" \
  APPLY=1 \
  RECOVERY_CONFIRM=RECOVER
```

The command rechecks each row immediately before reclaiming it. It requires a
current non-legacy execution within the requested window, an active automated
stakeholder, the exact matching historical failure note, and the existing
failed customer report run. Sent, held, active, unrelated-manual, overlapping,
and uncertain-creation records are blocked. Password recovery also requires
the current stored password to pass the existing-password validator.

Recovery preserves the original report-run row and its identity. It rotates
the generation lease, clears only the exact matching failure note, regenerates
the report, archives it, sends it, and records the structured sent state. A new
failure receives the current specific failure category.

An informational note such as `Sent 09/22/2026` is not a recovery cause. First
confirm the historical delivery outside this command, then reconcile its
structured sent date with the existing command:

```bash
make tracker-mark-sent TRACKER_ID=123 SENT_DATE=2026-09-22
```

This tracker-only command is for historical delivery performed outside the
structured report-run workflow. For a linked report run whose email status is
`held`, use `make reconcile-email-delivery REPORT_RUN_ID=<id>` so the report
run, tracker, and batch attempt are reconciled together. That command supports
held **customer** delivery only. It does not reconcile standalone delivery or
analyst summary and digest delivery.

## Unsupported recovery paths

The repository does not provide a safe automated recovery command for these
states:

- A held standalone delivery. The ordinary standalone mail command blocks the
  run even when previous failures are included.
- A held analyst-purpose report delivery, batch summary, or assignee digest
  delivery.
- An uncertain Qualys report-creation outcome.
- A partially completed Qualys web-application deletion.
- Target-removal or deletion reconciliation after the production tracker has
  recorded manual follow-up.

For held standalone or analyst email, preserve the report-run and delivery
evidence, determine the SES outcome through the approved AWS investigation
process, and escalate for a reviewed recovery decision. Do not reset delivery
rows, regenerate a report, or send a replacement message merely because the
outcome is unknown. The customer-only reconciliation command must not be used
for these delivery purposes.

Production web-application deletion can partially succeed before a later
Qualys request fails. The tracker records manual follow-up instead of blindly
replaying the deletion set. Verify the current Qualys state against the
tracker evidence and escalate the remaining work. The guarded manual-report
recovery command is not a deletion-retry command.

Do not use recovery to bypass `manual_report`, explicit operator notes,
unresolved Qualys operation failures, held delivery, or uncertain Qualys
report creation. A completed scan containing Qualys error webapps is part of
the automated reporting flow and does not use this manual-recovery command.

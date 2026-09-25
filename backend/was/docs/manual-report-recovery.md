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

Do not use recovery to bypass `manual_report`, explicit operator notes,
unresolved Qualys operation failures, held delivery, or uncertain Qualys
report creation. A completed scan containing Qualys error webapps is part of
the automated reporting flow and does not use this manual-recovery command.

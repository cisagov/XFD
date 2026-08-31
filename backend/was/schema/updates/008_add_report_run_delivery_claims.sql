ALTER TABLE was_report_runs
    ADD COLUMN IF NOT EXISTS email_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS email_claimed_at TIMESTAMPTZ;

UPDATE was_report_runs
SET email_status = CASE
        WHEN emailed_at IS NOT NULL THEN 'sent'
        WHEN email_error IS NOT NULL THEN 'failed'
        ELSE 'pending'
    END
WHERE email_status = 'pending';

CREATE UNIQUE INDEX IF NOT EXISTS was_report_runs_active_schedule_uidx
    ON was_report_runs (stakeholder_tag, scheduled_epoch)
    WHERE scheduled_epoch IS NOT NULL
      AND status IN ('running', 'completed');

CREATE INDEX IF NOT EXISTS was_report_runs_email_status_idx
    ON was_report_runs (email_status, completed_at)
    WHERE emailed_at IS NULL;

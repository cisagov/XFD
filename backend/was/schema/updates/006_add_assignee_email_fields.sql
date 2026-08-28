ALTER TABLE was_assignees
    ADD COLUMN IF NOT EXISTS email TEXT,
    ADD COLUMN IF NOT EXISTS email_enabled BOOLEAN DEFAULT TRUE;

ALTER TABLE was_daily_report_tracker
    ADD COLUMN IF NOT EXISTS assignee_emailed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS assignee_email_message_id TEXT,
    ADD COLUMN IF NOT EXISTS assignee_email_error TEXT;

CREATE INDEX IF NOT EXISTS was_daily_report_tracker_assignee_email_idx
    ON was_daily_report_tracker (assignee_id, data_pull_date, assignee_emailed_at);

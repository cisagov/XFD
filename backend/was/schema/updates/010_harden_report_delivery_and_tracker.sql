BEGIN;

ALTER TABLE was_report_runs
    ADD COLUMN IF NOT EXISTS generation_token TEXT,
    ADD COLUMN IF NOT EXISTS email_claim_token TEXT,
    ADD COLUMN IF NOT EXISTS delivery_purpose TEXT NOT NULL DEFAULT 'customer'
        CHECK (delivery_purpose IN ('customer', 'analyst'));

ALTER TABLE was_daily_report_tracker
    ADD COLUMN IF NOT EXISTS scan_execution_key TEXT,
    ADD COLUMN IF NOT EXISTS assignee_email_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (assignee_email_status IN
               ('pending', 'sending', 'sent', 'failed', 'held')),
    ADD COLUMN IF NOT EXISTS assignee_email_claim_token TEXT,
    ADD COLUMN IF NOT EXISTS assignee_email_claimed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS digest_revision BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS digest_claimed_revision BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS was_daily_report_tracker_scan_execution_uidx
    ON was_daily_report_tracker (scan_execution_key)
    WHERE scan_execution_key IS NOT NULL;

UPDATE was_daily_report_tracker
SET assignee_email_status = CASE
        WHEN assignee_emailed_at IS NOT NULL THEN 'sent'
        ELSE 'held'
    END
WHERE assignee_email_status = 'pending'
  AND (assignee_emailed_at IS NOT NULL OR assignee_email_error IS NOT NULL);

UPDATE was_report_runs
SET delivery_purpose = 'analyst'
WHERE generation_token IS NULL
  AND scheduled_epoch IS NULL
  AND (source_tracker_id IS NULL OR email_status = 'held');

UPDATE was_report_runs
SET qualys_xml_report_status = CASE
        WHEN qualys_xml_report_id IS NULL AND qualys_xml_report_status IS NULL
            THEN 'CREATE_REQUESTED'
        ELSE qualys_xml_report_status
    END,
    qualys_detail_report_status = CASE
        WHEN qualys_detail_report_id IS NULL
             AND qualys_detail_report_status IS NULL
            THEN 'CREATE_REQUESTED'
        ELSE qualys_detail_report_status
    END
WHERE generation_token IS NULL
  AND status IN ('running', 'failed');

COMMIT;

ALTER TABLE was_report_runs
    ADD COLUMN IF NOT EXISTS qualys_detail_report_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS qualys_detail_report_status VARCHAR(32),
    ADD COLUMN IF NOT EXISTS qualys_detail_last_polled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS qualys_xml_report_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS qualys_xml_report_status VARCHAR(32),
    ADD COLUMN IF NOT EXISTS qualys_xml_last_polled_at TIMESTAMPTZ;

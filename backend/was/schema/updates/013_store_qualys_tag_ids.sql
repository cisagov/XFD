ALTER TABLE was_stakeholders
    ADD COLUMN qualys_tag_id BIGINT;

ALTER TABLE was_daily_report_tracker
    ADD COLUMN tag_id BIGINT;

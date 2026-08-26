ALTER TABLE was_report_runs
    ADD COLUMN IF NOT EXISTS output_path TEXT,
    ADD COLUMN IF NOT EXISTS artifact_type VARCHAR(32);

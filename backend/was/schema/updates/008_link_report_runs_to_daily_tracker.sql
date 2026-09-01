ALTER TABLE was_report_runs
    ADD COLUMN IF NOT EXISTS source_tracker_id BIGINT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'was_report_runs_source_tracker_id_fkey'
    ) THEN
        ALTER TABLE was_report_runs
            ADD CONSTRAINT was_report_runs_source_tracker_id_fkey
            FOREIGN KEY (source_tracker_id)
            REFERENCES was_daily_report_tracker(id);
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS was_report_runs_source_tracker_id_uidx
    ON was_report_runs (source_tracker_id)
    WHERE source_tracker_id IS NOT NULL;

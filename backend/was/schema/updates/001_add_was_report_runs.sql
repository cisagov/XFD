CREATE TABLE IF NOT EXISTS was_report_runs (
    id                     BIGSERIAL PRIMARY KEY,
    stakeholder_tag        VARCHAR(128) NOT NULL REFERENCES was_stakeholders(tag),
    status                 VARCHAR(32) NOT NULL,
    scheduled_epoch        BIGINT,
    output_path            TEXT,
    artifact_type          VARCHAR(32),
    started_at             TIMESTAMPTZ DEFAULT NOW(),
    completed_at           TIMESTAMPTZ,
    error_message          TEXT,
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS was_report_runs_stakeholder_tag_idx
    ON was_report_runs (stakeholder_tag);

CREATE INDEX IF NOT EXISTS was_report_runs_status_idx
    ON was_report_runs (status);

CREATE INDEX IF NOT EXISTS was_report_runs_scheduled_epoch_idx
    ON was_report_runs (scheduled_epoch);

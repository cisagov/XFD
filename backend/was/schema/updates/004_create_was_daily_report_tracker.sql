CREATE TABLE IF NOT EXISTS was_assignees (
    id                       BIGSERIAL PRIMARY KEY,
    name                     VARCHAR(256) NOT NULL UNIQUE,
    email                    TEXT,
    active                   BOOLEAN DEFAULT TRUE,
    email_enabled            BOOLEAN DEFAULT TRUE,
    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS was_daily_report_tracker (
    id                       BIGSERIAL PRIMARY KEY,
    source_row_number        INTEGER,

    data_pull_date           DATE,
    tag                      VARCHAR(128),
    scan_name                TEXT,
    assignee_id              BIGINT REFERENCES was_assignees(id),
    assignee                 VARCHAR(256),
    status                   VARCHAR(128),
    result                   VARCHAR(128),
    report_sent_date         DATE,
    report_scan_notes        TEXT,
    scan_start_date          DATE,
    next_scan_date           DATE,
    poc                      TEXT,
    poc_email                TEXT,
    customer_notes           TEXT,
    nws                      TEXT,
    template                 VARCHAR(128),
    recent_nws               TEXT,
    remove_nws               TEXT,
    legacy_password          TEXT,
    schedule_id              BIGINT,
    qualys_error             TEXT,
    assignee_emailed_at      TIMESTAMPTZ,
    assignee_email_message_id TEXT,
    assignee_email_error     TEXT,

    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS was_daily_report_tracker_tag_idx
    ON was_daily_report_tracker (tag);

CREATE INDEX IF NOT EXISTS was_daily_report_tracker_assignee_id_idx
    ON was_daily_report_tracker (assignee_id);

CREATE INDEX IF NOT EXISTS was_daily_report_tracker_data_pull_date_idx
    ON was_daily_report_tracker (data_pull_date);

CREATE INDEX IF NOT EXISTS was_daily_report_tracker_next_scan_date_idx
    ON was_daily_report_tracker (next_scan_date);

CREATE INDEX IF NOT EXISTS was_daily_report_tracker_schedule_id_idx
    ON was_daily_report_tracker (schedule_id);

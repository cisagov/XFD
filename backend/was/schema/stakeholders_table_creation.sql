CREATE TABLE was_stakeholders (
    tag                    VARCHAR(128) PRIMARY KEY,

    customer_name          VARCHAR(512),
    comments               TEXT,
    location_notes         TEXT,

    ci_type                VARCHAR(128),
    testing_sector         VARCHAR(256),
    subtype                VARCHAR(128),

    distro_email           TEXT,
    tech_poc_email         TEXT,
    was_report_poc         TEXT,

    frequency              VARCHAR(64),

    num_web_apps           INTEGER,
    web_apps_last_updated  BIGINT,

    last_scanned           BIGINT,
    next_scheduled         BIGINT,
    onboarding_date        BIGINT,

    parent_tag             VARCHAR(128) REFERENCES was_stakeholders(tag),

    ticket                 VARCHAR(128),

    -- Updated per your request: default FALSE
    elections              BOOLEAN DEFAULT FALSE,
    fceb                   BOOLEAN DEFAULT FALSE,
    manual_report          BOOLEAN DEFAULT FALSE,
    retired                BOOLEAN DEFAULT FALSE,

    state                  VARCHAR(64),

    report_password        VARCHAR(256),

    created_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE was_report_runs (
    id                     BIGSERIAL PRIMARY KEY,
    stakeholder_tag        VARCHAR(128) NOT NULL REFERENCES was_stakeholders(tag),
    status                 VARCHAR(32) NOT NULL,
    scheduled_epoch        BIGINT,
    output_path            TEXT,
    artifact_type          VARCHAR(32),
    emailed_at             TIMESTAMPTZ,
    email_message_id       TEXT,
    email_error            TEXT,
    email_status           VARCHAR(32) NOT NULL DEFAULT 'pending',
    email_claimed_at       TIMESTAMPTZ,
    started_at             TIMESTAMPTZ DEFAULT NOW(),
    completed_at           TIMESTAMPTZ,
    error_message          TEXT,
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX was_report_runs_stakeholder_tag_idx
    ON was_report_runs (stakeholder_tag);

CREATE INDEX was_report_runs_status_idx
    ON was_report_runs (status);

CREATE INDEX was_report_runs_scheduled_epoch_idx
    ON was_report_runs (scheduled_epoch);

CREATE UNIQUE INDEX was_report_runs_active_schedule_uidx
    ON was_report_runs (stakeholder_tag, scheduled_epoch)
    WHERE scheduled_epoch IS NOT NULL
      AND status IN ('running', 'completed');

CREATE INDEX was_report_runs_email_status_idx
    ON was_report_runs (email_status, completed_at)
    WHERE emailed_at IS NULL;

CREATE TABLE was_assignees (
    id                       BIGSERIAL PRIMARY KEY,
    name                     VARCHAR(256) NOT NULL UNIQUE,
    email                    TEXT,
    active                   BOOLEAN DEFAULT TRUE,
    email_enabled            BOOLEAN DEFAULT TRUE,
    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO was_assignees (name)
VALUES
    ('Mina Salehi'),
    ('Tenesa Ellis'),
    ('Brycen Ford'),
    ('Zack Cogswell'),
    ('Justin Rothfleisch'),
    ('Oscar Saunders'),
    ('Wale Ojelabi')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE was_daily_report_tracker (
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

CREATE INDEX was_daily_report_tracker_tag_idx
    ON was_daily_report_tracker (tag);

CREATE INDEX was_daily_report_tracker_assignee_id_idx
    ON was_daily_report_tracker (assignee_id);

CREATE INDEX was_daily_report_tracker_data_pull_date_idx
    ON was_daily_report_tracker (data_pull_date);

CREATE INDEX was_daily_report_tracker_next_scan_date_idx
    ON was_daily_report_tracker (next_scan_date);

CREATE INDEX was_daily_report_tracker_schedule_id_idx
    ON was_daily_report_tracker (schedule_id);

CREATE INDEX was_daily_report_tracker_assignee_email_idx
    ON was_daily_report_tracker (
        assignee_id,
        data_pull_date,
        assignee_emailed_at
    );

CREATE TABLE was_special_cases (
    id                       BIGSERIAL PRIMARY KEY,
    value                    VARCHAR(256) NOT NULL UNIQUE,
    active                   BOOLEAN DEFAULT TRUE,
    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX was_special_cases_active_idx
    ON was_special_cases (active);

INSERT INTO was_special_cases (value)
VALUES
    ('CROSSFEED'),
    ('CBOE'),
    ('SCCCS')
ON CONFLICT (value) DO NOTHING;

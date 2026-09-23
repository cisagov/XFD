CREATE TABLE was_stakeholders (
    tag                    VARCHAR(128) PRIMARY KEY
                           CHECK (tag = BTRIM(tag)
                                  AND POSITION(' ' IN tag) = 0
                                  AND POSITION(CHR(9) IN tag) = 0
                                  AND POSITION(CHR(10) IN tag) = 0
                                  AND POSITION(CHR(13) IN tag) = 0),

    customer_name          VARCHAR(512),
    comments               TEXT,
    location_notes         TEXT,

    ci_type                VARCHAR(128) NOT NULL CHECK (BTRIM(ci_type) <> ''),
    testing_sector         VARCHAR(256) NOT NULL
                           CHECK (BTRIM(testing_sector) <> ''),
    subtype                VARCHAR(128) CHECK (
        subtype IS NULL OR BTRIM(subtype) <> ''
    ),

    distro_email           TEXT CHECK (
        POSITION(CHR(10) IN COALESCE(distro_email, '')) = 0
        AND POSITION(CHR(13) IN COALESCE(distro_email, '')) = 0
    ),
    tech_poc_email         TEXT CHECK (
        POSITION(CHR(10) IN COALESCE(tech_poc_email, '')) = 0
        AND POSITION(CHR(13) IN COALESCE(tech_poc_email, '')) = 0
    ),
    was_report_poc         TEXT,

    frequency              VARCHAR(64) NOT NULL CHECK (BTRIM(frequency) <> ''),

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

    state                  VARCHAR(64) NOT NULL CHECK (
        state IN (
            'AK', 'AL', 'AR', 'AS', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE',
            'FL', 'GA', 'GU', 'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY',
            'LA', 'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MP', 'MS', 'MT',
            'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH', 'OK',
            'OR', 'PA', 'PR', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VA',
            'VI', 'VT', 'WA', 'WI', 'WV', 'WY', 'INTERNATIONAL'
        )
    ),

    qualys_tag_id          BIGINT,

    report_password        VARCHAR(256),

    created_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE was_report_runs (
    id                     BIGSERIAL PRIMARY KEY,
    stakeholder_tag        VARCHAR(128) NOT NULL REFERENCES was_stakeholders(tag),
    status                 VARCHAR(32) NOT NULL,
    generation_token       TEXT,
    delivery_purpose       TEXT NOT NULL DEFAULT 'customer'
                           CHECK (delivery_purpose IN ('customer', 'analyst')),
    scheduled_epoch        BIGINT,
    output_path            TEXT,
    artifact_type          VARCHAR(32),
    emailed_at             TIMESTAMPTZ,
    email_message_id       TEXT,
    email_error            TEXT,
    email_status           VARCHAR(32) NOT NULL DEFAULT 'pending',
    email_claimed_at       TIMESTAMPTZ,
    email_claim_token      TEXT,
    started_at             TIMESTAMPTZ DEFAULT NOW(),
    completed_at           TIMESTAMPTZ,
    error_message          TEXT,
    qualys_detail_report_id VARCHAR(64),
    qualys_detail_report_status VARCHAR(32),
    qualys_detail_last_polled_at TIMESTAMPTZ,
    qualys_xml_report_id    VARCHAR(64),
    qualys_xml_report_status VARCHAR(32),
    qualys_xml_last_polled_at TIMESTAMPTZ,
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

CREATE TABLE was_daily_report_tracker (
    id                       BIGSERIAL PRIMARY KEY,
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
    scan_started_at          TIMESTAMPTZ,
    scan_ended_at            TIMESTAMPTZ,
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
    tag_id                   BIGINT,
    scan_execution_key       TEXT,
    qualys_error             TEXT,
    assignee_emailed_at      TIMESTAMPTZ,
    assignee_email_message_id TEXT,
    assignee_email_error     TEXT,
    assignee_email_status    TEXT NOT NULL DEFAULT 'pending'
                             CHECK (assignee_email_status IN
                                    ('pending', 'sending', 'sent', 'failed', 'held')),
    assignee_email_claim_token TEXT,
    assignee_email_claimed_at TIMESTAMPTZ,
    digest_revision          BIGINT NOT NULL DEFAULT 0,
    digest_claimed_revision  BIGINT,

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

CREATE UNIQUE INDEX was_daily_report_tracker_scan_execution_uidx
    ON was_daily_report_tracker (scan_execution_key)
    WHERE scan_execution_key IS NOT NULL;

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

ALTER TABLE was_report_runs
    ADD COLUMN source_tracker_id BIGINT
    REFERENCES was_daily_report_tracker(id);

CREATE UNIQUE INDEX was_report_runs_source_tracker_id_uidx
    ON was_report_runs (source_tracker_id)
    WHERE source_tracker_id IS NOT NULL;

CREATE TABLE was_batch_runs (
    batch_id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tracker_duration_seconds DOUBLE PRECISION,
    tracker_rows_updated BIGINT,
    tracker_error TEXT,
    tracker_summary_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (tracker_summary_status IN ('pending', 'sending', 'sent', 'held')),
    tracker_summary_message_id TEXT,
    final_summary_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (final_summary_status IN ('pending', 'sending', 'sent', 'held')),
    final_summary_message_id TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE was_batch_report_attempts (
    batch_id TEXT NOT NULL REFERENCES was_batch_runs(batch_id),
    tracker_id BIGINT NOT NULL REFERENCES was_daily_report_tracker(id),
    report_run_id BIGINT,
    duration_seconds DOUBLE PRECISION NOT NULL CHECK (duration_seconds >= 0),
    generated BOOLEAN NOT NULL,
    sent BOOLEAN NOT NULL,
    error TEXT,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (batch_id, tracker_id)
);

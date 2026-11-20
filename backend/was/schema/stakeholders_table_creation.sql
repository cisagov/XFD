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

-- Standalone targets are not enrolled stakeholders and never enter daily batches.
CREATE TABLE was_standalone_report_targets (
    id BIGSERIAL PRIMARY KEY,
    qualys_tag_id BIGINT NOT NULL UNIQUE CHECK (qualys_tag_id > 0),
    tag VARCHAR(128) NOT NULL UNIQUE CHECK (BTRIM(tag) <> '' AND tag !~ '[[:cntrl:]]'),
    report_password TEXT NOT NULL CHECK (report_password <> ''),
    delivery_email TEXT NOT NULL CHECK (BTRIM(delivery_email) <> ''
        AND POSITION(CHR(10) IN delivery_email) = 0
        AND POSITION(CHR(13) IN delivery_email) = 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE was_report_runs (
    id                     BIGSERIAL PRIMARY KEY,
    stakeholder_tag        VARCHAR(128) REFERENCES was_stakeholders(tag),
    standalone_target_id   BIGINT REFERENCES was_standalone_report_targets(id),
    status                 VARCHAR(32) NOT NULL,
    generation_token       TEXT,
    delivery_purpose       TEXT NOT NULL DEFAULT 'customer'
                           CHECK (delivery_purpose IN ('customer', 'analyst', 'standalone')),
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
    updated_at             TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT was_report_runs_target_check CHECK (
        (stakeholder_tag IS NOT NULL AND standalone_target_id IS NULL
         AND delivery_purpose IN ('customer', 'analyst')) OR
        (stakeholder_tag IS NULL AND standalone_target_id IS NOT NULL
         AND delivery_purpose = 'standalone' AND scheduled_epoch IS NULL)
    )
);

CREATE INDEX was_report_runs_stakeholder_tag_idx
    ON was_report_runs (stakeholder_tag);

CREATE UNIQUE INDEX was_report_runs_active_standalone_uidx
    ON was_report_runs (standalone_target_id)
    WHERE standalone_target_id IS NOT NULL
      AND (status = 'running' OR email_status = 'sending');

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

-- Access is denied until a CLI host UID principal has a stakeholder grant.
CREATE TABLE was_delivery_stakeholder_grants (
    principal_key VARCHAR(128) NOT NULL,
    stakeholder_tag VARCHAR(128) NOT NULL REFERENCES was_stakeholders(tag),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by_principal_key VARCHAR(128),
    PRIMARY KEY (principal_key, stakeholder_tag)
);

-- Each SES request has its own durable row; retries never replace a prior row.
CREATE TABLE was_delivery_attempts (
    id BIGSERIAL PRIMARY KEY,
    report_run_id BIGINT NOT NULL REFERENCES was_report_runs(id),
    -- Historical retry links survive expiry of an intermediate retry row.
    original_failed_attempt_id BIGINT,
    failed_recipient TEXT,
    recipient_addresses TEXT[] NOT NULL,
    recipient_redacted_at TIMESTAMPTZ,
    archived_report_s3_uri TEXT,
    archive_sha256 CHAR(64),
    requested_by_principal_key VARCHAR(128),
    idempotency_key TEXT,
    claim_token TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending', 'sending', 'accepted', 'delivered',
            'confirmed_failure', 'held', 'failed_pre_send'
        )
    ),
    ses_message_id TEXT UNIQUE,
    failure_classification VARCHAR(64),
    sanitized_diagnostic VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    confirmed_failed_at TIMESTAMPTZ,
    CONSTRAINT was_delivery_recipient_retention_check CHECK (
        cardinality(recipient_addresses) > 0 OR recipient_redacted_at IS NOT NULL
    ),
    CONSTRAINT was_delivery_retry_fields_check CHECK (
        (original_failed_attempt_id IS NULL AND failed_recipient IS NULL
         AND requested_by_principal_key IS NULL AND idempotency_key IS NULL)
        OR
        (original_failed_attempt_id IS NOT NULL AND failed_recipient IS NOT NULL
         AND requested_by_principal_key IS NOT NULL
         AND idempotency_key IS NOT NULL AND BTRIM(idempotency_key) <> ''
         AND archived_report_s3_uri IS NOT NULL)
    ),
    CONSTRAINT was_delivery_s3_uri_check CHECK (
        archived_report_s3_uri IS NULL OR archived_report_s3_uri LIKE 's3://%'
    )
);

CREATE UNIQUE INDEX was_delivery_attempts_one_retry_per_recipient_uidx
    ON was_delivery_attempts (original_failed_attempt_id, failed_recipient)
    WHERE original_failed_attempt_id IS NOT NULL
      AND status <> 'failed_pre_send';

CREATE UNIQUE INDEX was_delivery_attempts_retry_request_uidx
    ON was_delivery_attempts (original_failed_attempt_id, idempotency_key)
    WHERE original_failed_attempt_id IS NOT NULL;

CREATE UNIQUE INDEX was_delivery_attempts_initial_claim_uidx
    ON was_delivery_attempts (report_run_id, claim_token)
    WHERE original_failed_attempt_id IS NULL AND claim_token IS NOT NULL;

CREATE INDEX was_delivery_attempts_run_idx
    ON was_delivery_attempts (report_run_id, created_at DESC);

CREATE INDEX was_delivery_attempts_failure_idx
    ON was_delivery_attempts (status, created_at DESC, report_run_id)
    WHERE status IN ('confirmed_failure', 'held', 'failed_pre_send');

-- A notification may arrive before the sender persists the SES message ID.
CREATE TABLE was_ses_delivery_events (
    id BIGSERIAL PRIMARY KEY,
    sns_message_id TEXT NOT NULL UNIQUE,
    ses_message_id TEXT NOT NULL,
    -- Keep SES message deduplication and history after retry detail expires.
    delivery_attempt_id BIGINT,
    event_type VARCHAR(32) NOT NULL,
    delivery_status VARCHAR(32) NOT NULL,
    affected_recipients TEXT[] NOT NULL DEFAULT '{}',
    bounce_type VARCHAR(64),
    bounce_subtype VARCHAR(64),
    smtp_status_code VARCHAR(16),
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX was_ses_delivery_events_message_idx
    ON was_ses_delivery_events (ses_message_id, occurred_at DESC);

CREATE INDEX was_ses_delivery_events_attempt_idx
    ON was_ses_delivery_events (delivery_attempt_id, occurred_at DESC);

-- This table intentionally excludes addresses, report data, and diagnostics.
CREATE TABLE was_delivery_audit_events (
    id BIGSERIAL PRIMARY KEY,
    actor_principal_key VARCHAR(128) NOT NULL,
    action VARCHAR(40) NOT NULL CHECK (
        action IN ('list', 'detail', 'correction', 'retry_requested', 'retry_result')
    ),
    -- Preserve the historical attempt ID after a retry row expires.
    delivery_attempt_id BIGINT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

-- These established stakeholder tags must never enter automatic inaccessible-
-- application deletion.  Keep the authoritative schema self-contained so a
-- database created from this file has the same required safeguards as the
-- working WAS environments.
INSERT INTO was_special_cases (value)
VALUES
    ('CROSSFEED'),
    ('CBOE'),
    ('SCCCS')
ON CONFLICT (value) DO UPDATE SET
    active = TRUE,
    updated_at = NOW();

ALTER TABLE was_report_runs
    ADD COLUMN source_tracker_id BIGINT
    REFERENCES was_daily_report_tracker(id);

ALTER TABLE was_report_runs ADD CONSTRAINT was_report_runs_standalone_tracker_check
    CHECK (standalone_target_id IS NULL OR source_tracker_id IS NULL);

CREATE UNIQUE INDEX was_report_runs_source_tracker_id_uidx
    ON was_report_runs (source_tracker_id)
    WHERE source_tracker_id IS NOT NULL;

CREATE TABLE was_batch_runs (
    batch_id TEXT PRIMARY KEY,
    parent_batch_id TEXT,
    root_batch_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    worker_count INTEGER NOT NULL DEFAULT 1 CHECK (worker_count > 0),
    run_mode TEXT NOT NULL DEFAULT 'production' CHECK (run_mode IN ('production', 'capacity')),
    workload_label VARCHAR(200),
    outcome TEXT CHECK (outcome IN ('completed', 'failed')),
    active_duration_seconds DOUBLE PRECISION,
    tracker_duration_seconds DOUBLE PRECISION,
    tracker_rows_updated BIGINT,
    tracker_error TEXT,
    tracker_summary_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (tracker_summary_status IN ('pending', 'sending', 'sent', 'held')),
    tracker_summary_message_id TEXT,
    final_summary_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (final_summary_status IN ('pending', 'sending', 'sent', 'held')),
    final_summary_message_id TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT was_batch_runs_parent_batch_fk FOREIGN KEY (parent_batch_id)
        REFERENCES was_batch_runs(batch_id),
    CONSTRAINT was_batch_runs_root_batch_fk FOREIGN KEY (root_batch_id)
        REFERENCES was_batch_runs(batch_id),
    CONSTRAINT was_batch_runs_active_duration_check CHECK (
        active_duration_seconds >= 0
    ),
    CONSTRAINT was_batch_runs_lineage_check CHECK (
        (parent_batch_id IS NULL AND root_batch_id = batch_id)
        OR
        (parent_batch_id IS NOT NULL AND root_batch_id <> batch_id)
    )
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
    delivery_duration_seconds DOUBLE PRECISION CHECK (delivery_duration_seconds >= 0),
    artifact_type TEXT CHECK (artifact_type IN ('pdf', 'notification')),
    sent_recorded_at TIMESTAMPTZ,
    PRIMARY KEY (batch_id, tracker_id)
);

CREATE TABLE was_test_replay_batches (
    replay_id UUID PRIMARY KEY,
    recipient TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE was_test_replay_items (
    replay_id UUID NOT NULL REFERENCES was_test_replay_batches(replay_id),
    tracker_id BIGINT NOT NULL REFERENCES was_daily_report_tracker(id),
    original_run_id BIGINT REFERENCES was_report_runs(id),
    report_run_id BIGINT NOT NULL UNIQUE REFERENCES was_report_runs(id),
    action TEXT NOT NULL CONSTRAINT was_test_replay_items_action_check CHECK (
        action IN ('resend', 'manual', 'targets_removed')
    ),
    template_override TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (replay_id, tracker_id),
    CONSTRAINT was_test_replay_items_template_override_check CHECK (
        (action = 'targets_removed' AND template_override = 'Targets Removed')
        OR (action <> 'targets_removed' AND template_override IS NULL)
    )
);

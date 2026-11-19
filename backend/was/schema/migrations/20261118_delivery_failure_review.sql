-- One-time additive migration for WAS CLI delivery-failure review.
-- Review the target database against the canonical schema before applying.
-- Run with a client that stops on the first SQL error; do not rerun after success.
-- No historical email recipients or SES events are backfilled.

BEGIN;

CREATE TABLE was_delivery_stakeholder_grants (
    principal_key VARCHAR(128) NOT NULL,
    stakeholder_tag VARCHAR(128) NOT NULL REFERENCES was_stakeholders(tag),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by_principal_key VARCHAR(128),
    PRIMARY KEY (principal_key, stakeholder_tag)
);

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

COMMIT;

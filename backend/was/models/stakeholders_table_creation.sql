CREATE TABLE was_stakeholders (
    tag                    VARCHAR(128) PRIMARY KEY,

    customer_name          VARCHAR(512),
    comments               TEXT,

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

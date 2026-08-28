CREATE TABLE IF NOT EXISTS was_special_cases (
    id                       BIGSERIAL PRIMARY KEY,
    value                    VARCHAR(256) NOT NULL UNIQUE,
    active                   BOOLEAN DEFAULT TRUE,
    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS was_special_cases_active_idx
    ON was_special_cases (active);

INSERT INTO was_special_cases (value)
VALUES
    ('CROSSFEED'),
    ('CBOE'),
    ('SCCCS')
ON CONFLICT (value) DO NOTHING;

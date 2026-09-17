-- Enforce stakeholder input rules for all new and changed rows while allowing
-- legacy violations to be remediated separately. PostgreSQL CHECK constraints
-- declared NOT VALID still protect new INSERT and UPDATE operations.

ALTER TABLE was_stakeholders
    ALTER COLUMN subtype DROP NOT NULL,
    DROP CONSTRAINT IF EXISTS was_stakeholders_required_fields_nonblank_check;

ALTER TABLE was_stakeholders
    ADD CONSTRAINT was_stakeholders_required_fields_nonblank_check
    CHECK (
        ci_type IS NOT NULL
        AND BTRIM(ci_type) <> ''
        AND testing_sector IS NOT NULL
        AND BTRIM(testing_sector) <> ''
        AND (subtype IS NULL OR BTRIM(subtype) <> '')
        AND frequency IS NOT NULL
        AND BTRIM(frequency) <> ''
        AND state IS NOT NULL
        AND BTRIM(state) <> ''
    ) NOT VALID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'was_stakeholders'::regclass
          AND conname = 'was_stakeholders_tag_whitespace_check'
    ) THEN
        ALTER TABLE was_stakeholders
            ADD CONSTRAINT was_stakeholders_tag_whitespace_check
            CHECK (
                tag = BTRIM(tag)
                AND POSITION(' ' IN tag) = 0
                AND POSITION(CHR(9) IN tag) = 0
                AND POSITION(CHR(10) IN tag) = 0
                AND POSITION(CHR(13) IN tag) = 0
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'was_stakeholders'::regclass
          AND conname = 'was_stakeholders_email_line_break_check'
    ) THEN
        ALTER TABLE was_stakeholders
            ADD CONSTRAINT was_stakeholders_email_line_break_check
            CHECK (
                POSITION(CHR(10) IN COALESCE(distro_email, '')) = 0
                AND POSITION(CHR(13) IN COALESCE(distro_email, '')) = 0
                AND POSITION(CHR(10) IN COALESCE(tech_poc_email, '')) = 0
                AND POSITION(CHR(13) IN COALESCE(tech_poc_email, '')) = 0
            ) NOT VALID;
    END IF;
END
$$;

DO $$
DECLARE
    invalid_required_count BIGINT;
    invalid_tag_count BIGINT;
    invalid_email_count BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO invalid_required_count
    FROM was_stakeholders
    WHERE ci_type IS NULL OR BTRIM(ci_type) = ''
       OR testing_sector IS NULL OR BTRIM(testing_sector) = ''
       OR (subtype IS NOT NULL AND BTRIM(subtype) = '')
       OR frequency IS NULL OR BTRIM(frequency) = ''
       OR state IS NULL OR BTRIM(state) = '';

    SELECT COUNT(*)
    INTO invalid_tag_count
    FROM was_stakeholders
    WHERE tag <> BTRIM(tag)
       OR POSITION(' ' IN tag) > 0
       OR POSITION(CHR(9) IN tag) > 0
       OR POSITION(CHR(10) IN tag) > 0
       OR POSITION(CHR(13) IN tag) > 0;

    SELECT COUNT(*)
    INTO invalid_email_count
    FROM was_stakeholders
    WHERE POSITION(CHR(10) IN COALESCE(distro_email, '')) > 0
       OR POSITION(CHR(13) IN COALESCE(distro_email, '')) > 0
       OR POSITION(CHR(10) IN COALESCE(tech_poc_email, '')) > 0
       OR POSITION(CHR(13) IN COALESCE(tech_poc_email, '')) > 0;

    IF invalid_required_count = 0 THEN
        ALTER TABLE was_stakeholders
            VALIDATE CONSTRAINT was_stakeholders_required_fields_nonblank_check;
        ALTER TABLE was_stakeholders
            ALTER COLUMN ci_type SET NOT NULL,
            ALTER COLUMN testing_sector SET NOT NULL,
            ALTER COLUMN frequency SET NOT NULL,
            ALTER COLUMN state SET NOT NULL;
    ELSE
        RAISE NOTICE
            'Required-field constraint is active for new changes but remains unvalidated: % legacy row(s) require remediation.',
            invalid_required_count;
    END IF;

    IF invalid_tag_count = 0 THEN
        ALTER TABLE was_stakeholders
            VALIDATE CONSTRAINT was_stakeholders_tag_whitespace_check;
    ELSE
        RAISE NOTICE
            'Tag constraint is active for new changes but remains unvalidated: % legacy row(s) require remediation.',
            invalid_tag_count;
    END IF;

    IF invalid_email_count = 0 THEN
        ALTER TABLE was_stakeholders
            VALIDATE CONSTRAINT was_stakeholders_email_line_break_check;
    ELSE
        RAISE NOTICE
            'Email constraint is active for new changes but remains unvalidated: % legacy row(s) require remediation.',
            invalid_email_count;
    END IF;
END
$$;

DO $$
DECLARE
    invalid_count BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO invalid_count
    FROM was_stakeholders
    WHERE tag <> BTRIM(tag)
       OR POSITION(' ' IN tag) > 0
       OR POSITION(CHR(9) IN tag) > 0
       OR POSITION(CHR(10) IN tag) > 0
       OR POSITION(CHR(13) IN tag) > 0
       OR ci_type IS NULL OR BTRIM(ci_type) = ''
       OR testing_sector IS NULL OR BTRIM(testing_sector) = ''
       OR subtype IS NULL OR BTRIM(subtype) = ''
       OR frequency IS NULL OR BTRIM(frequency) = ''
       OR state IS NULL OR BTRIM(state) = ''
       OR POSITION(CHR(10) IN COALESCE(distro_email, '')) > 0
       OR POSITION(CHR(13) IN COALESCE(distro_email, '')) > 0
       OR POSITION(CHR(10) IN COALESCE(tech_poc_email, '')) > 0
       OR POSITION(CHR(13) IN COALESCE(tech_poc_email, '')) > 0;

    IF invalid_count > 0 THEN
        RAISE EXCEPTION
            'Cannot harden was_stakeholders: % invalid row(s) require remediation.',
            invalid_count;
    END IF;
END
$$;

ALTER TABLE was_stakeholders
    ALTER COLUMN ci_type SET NOT NULL,
    ALTER COLUMN testing_sector SET NOT NULL,
    ALTER COLUMN subtype SET NOT NULL,
    ALTER COLUMN frequency SET NOT NULL,
    ALTER COLUMN state SET NOT NULL;

ALTER TABLE was_stakeholders
    ADD CONSTRAINT was_stakeholders_required_fields_nonblank_check
    CHECK (
        BTRIM(ci_type) <> ''
        AND BTRIM(testing_sector) <> ''
        AND BTRIM(subtype) <> ''
        AND BTRIM(frequency) <> ''
        AND BTRIM(state) <> ''
    ),
    ADD CONSTRAINT was_stakeholders_tag_whitespace_check
    CHECK (
        tag = BTRIM(tag)
        AND POSITION(' ' IN tag) = 0
        AND POSITION(CHR(9) IN tag) = 0
        AND POSITION(CHR(10) IN tag) = 0
        AND POSITION(CHR(13) IN tag) = 0
    ),
    ADD CONSTRAINT was_stakeholders_email_line_break_check
    CHECK (
        POSITION(CHR(10) IN COALESCE(distro_email, '')) = 0
        AND POSITION(CHR(13) IN COALESCE(distro_email, '')) = 0
        AND POSITION(CHR(10) IN COALESCE(tech_poc_email, '')) = 0
        AND POSITION(CHR(13) IN COALESCE(tech_poc_email, '')) = 0
    );

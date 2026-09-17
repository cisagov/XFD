ALTER TABLE was_stakeholders
    DROP CONSTRAINT IF EXISTS was_stakeholders_state_check;

ALTER TABLE was_stakeholders
    ADD CONSTRAINT was_stakeholders_state_check
    CHECK (
        state IS NULL OR state IN (
            'AK', 'AL', 'AR', 'AS', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE',
            'FL', 'GA', 'GU', 'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY',
            'LA', 'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MP', 'MS', 'MT',
            'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH', 'OK',
            'OR', 'PA', 'PR', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VA',
            'VI', 'VT', 'WA', 'WI', 'WV', 'WY', 'INTERNATIONAL'
        )
    ) NOT VALID;

DO $$
DECLARE
    invalid_state_count BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO invalid_state_count
    FROM was_stakeholders
    WHERE state IS NOT NULL
      AND state NOT IN (
          'AK', 'AL', 'AR', 'AS', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE',
          'FL', 'GA', 'GU', 'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY',
          'LA', 'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MP', 'MS', 'MT',
          'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH', 'OK',
          'OR', 'PA', 'PR', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VA',
          'VI', 'VT', 'WA', 'WI', 'WV', 'WY', 'INTERNATIONAL'
      );

    IF invalid_state_count = 0 THEN
        ALTER TABLE was_stakeholders
            VALIDATE CONSTRAINT was_stakeholders_state_check;
    ELSE
        RAISE NOTICE
            'State constraint is active for new changes but remains unvalidated: % legacy row(s) use unsupported values.',
            invalid_state_count;
    END IF;
END
$$;

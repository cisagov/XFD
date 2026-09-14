DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'was_stakeholders_state_check'
          AND conrelid = 'was_stakeholders'::regclass
    ) THEN
        ALTER TABLE was_stakeholders
        ADD CONSTRAINT was_stakeholders_state_check
        CHECK (
            state IS NULL OR state IN (
                'AK', 'AL', 'AR', 'AS', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE',
                'FL', 'GA', 'GU', 'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY',
                'LA', 'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MP', 'MS', 'MT',
                'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH', 'OK',
                'OR', 'PA', 'PR', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VA',
                'VI', 'VT', 'WA', 'WI', 'WV', 'WY'
            )
        );
    END IF;
END
$$;

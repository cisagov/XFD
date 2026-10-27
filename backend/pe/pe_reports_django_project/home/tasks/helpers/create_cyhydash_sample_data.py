"""Create sample CyHy Dash DB data for local development."""

# Third-Party Libraries
from django.db import connections, transaction


def populate_cyhydash_sample_data():
    """Populate the cve table with sample data."""
    with transaction.atomic(using="cyhy_dash_db"):
        with connections["cyhy_dash_db"].cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cve (
                    id UUID NOT NULL,
                    name TEXT NULL,
                    publishedAt TIMESTAMPTZ NULL,
                    modifiedAt TIMESTAMPTZ NULL,
                    status TEXT NULL,
                    description TEXT NULL,

                    cvssV2Source TEXT NULL,
                    cvssV2Type TEXT NULL,
                    cvssV2Version TEXT NULL,
                    cvssV2VectorString TEXT NULL,
                    cvssV2BaseScore DOUBLE PRECISION NULL,
                    cvssV2BaseSeverity TEXT NULL,
                    cvssV2ExploitabilityScore DOUBLE PRECISION NULL,
                    cvssV2ImpactScore DOUBLE PRECISION NULL,

                    cvssV3Source TEXT NULL,
                    cvssV3Type TEXT NULL,
                    cvssV3Version TEXT NULL,
                    cvssV3VectorString TEXT NULL,
                    cvssV3BaseScore DOUBLE PRECISION NULL,
                    cvssV3BaseSeverity TEXT NULL,
                    cvssV3ExploitabilityScore DOUBLE PRECISION NULL,
                    cvssV3ImpactScore DOUBLE PRECISION NULL,

                    cvssV4Source TEXT NULL,
                    cvssV4Type TEXT NULL,
                    cvssV4Version TEXT NULL,
                    cvssV4VectorString TEXT NULL,
                    cvssV4BaseScore DOUBLE PRECISION NULL,
                    cvssV4BaseSeverity TEXT NULL,
                    cvssV4ExploitabilityScore DOUBLE PRECISION NULL,
                    cvssV4ImpactScore DOUBLE PRECISION NULL,

                    weaknesses TEXT[] NULL,
                    "references" TEXT[] NULL,

                    CONSTRAINT cve_pkey PRIMARY KEY (id),
                    CONSTRAINT cve_name_key UNIQUE (name)
                );
                """
            )

            cursor.execute(
                """
                INSERT INTO cve (
                    id,
                    name,
                    publishedAt,
                    modifiedAt,
                    status,
                    description,
                    cvssV3Source,
                    cvssV3Type,
                    cvssV3Version,
                    cvssV3VectorString,
                    cvssV3BaseScore,
                    cvssV3BaseSeverity,
                    cvssV3ExploitabilityScore,
                    cvssV3ImpactScore,
                    weaknesses,
                    "references"
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT (id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    publishedAt = EXCLUDED.publishedAt,
                    modifiedAt = EXCLUDED.modifiedAt,
                    status = EXCLUDED.status,
                    description = EXCLUDED.description,
                    cvssV3Source = EXCLUDED.cvssV3Source,
                    cvssV3Type = EXCLUDED.cvssV3Type,
                    cvssV3Version = EXCLUDED.cvssV3Version,
                    cvssV3VectorString = EXCLUDED.cvssV3VectorString,
                    cvssV3BaseScore = EXCLUDED.cvssV3BaseScore,
                    cvssV3BaseSeverity = EXCLUDED.cvssV3BaseSeverity,
                    cvssV3ExploitabilityScore = EXCLUDED.cvssV3ExploitabilityScore,
                    cvssV3ImpactScore = EXCLUDED.cvssV3ImpactScore,
                    weaknesses = EXCLUDED.weaknesses,
                    "references" = EXCLUDED."references";
                """,
                (
                    "11111111-1111-1111-1111-111111111111",
                    "CVE-2026-0001",
                    "2026-01-01T12:00:00Z",
                    "2026-01-02T12:00:00Z",
                    "Analyzed",
                    "A manually created sample vulnerability.",
                    "nvd@nist.gov",
                    "Primary",
                    "3.1",
                    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                    9.8,
                    "CRITICAL",
                    3.9,
                    5.9,
                    ["CWE-79"],
                    ["https://example.gov/cve/CVE-2026-0001"],
                ),
            )

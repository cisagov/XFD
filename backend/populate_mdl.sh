#!/bin/bash
set -e

docker exec -i db psql -U crossfeed -d crossfeed_mini_datalake << EOF
\i /tmp/location.sql
\i /tmp/organization.sql
\i /tmp/cidr.sql
\i /tmp/cidr_orgs.sql

UPDATE cidr_orgs
SET last_seen = CURRENT_DATE - INTERVAL '1 day';

UPDATE organization
SET region_id = 1
WHERE region_id IS NULL;

UPDATE organization
SET ip_blocks = '{}'::text[];

UPDATE organization
SET root_domains = '{}'::text[];

INSERT INTO data_source (
    data_source_uid,
    name,
    description,
    last_run
) VALUES (
    '78703098-981d-11ec-a101-02589a36c9d7',
    'Test',
    'Test data source',
    '2024-01-01'
);


INSERT INTO sub_domains (
    sub_domain_uid,
    sub_domain,
    root_domain_id,
    is_root_domain,
    data_source_uid,
    dns_record_uid,
    status,
    first_seen,
    last_seen,
    created_at,
    updated_at,
    current,
    identified,
    ip_address,
    synced_at,
    from_root_domain,
    enumerate_subs,
    subdomain_source,
    organization_uid,
    ip_only,
    reverse_name,
    screenshot,
    country,
    asn,
    cloud_hosted,
    ssl,
    censys_certificates_results,
    trustymail_results
)
VALUES (
    gen_random_uuid(),                -- sub_domain_uid
    'usagm.gov',                          -- sub_domain
    NULL,                             -- root_domain_id
    TRUE,                            -- is_root_domain
    '78703098-981d-11ec-a101-02589a36c9d7',  -- data_source_uid
    NULL,                             -- dns_record_uid
    TRUE,                         -- status (or adjust to match enum/values)
    CURRENT_DATE,                     -- first_seen
    CURRENT_DATE,                     -- last_seen
    CURRENT_TIMESTAMP,                -- created_at
    CURRENT_TIMESTAMP,                -- updated_at
    TRUE,                             -- current
    TRUE,                             -- identified
    NULL,                             -- ip_address
    NULL,                             -- synced_at
    NULL,                             -- from_root_domain
    TRUE,                            -- enumerate_subs
    'manual',                         -- subdomain_source
    (
        SELECT id
        FROM organization
        WHERE acronym = 'USAGM'
        LIMIT 1
    ),                                -- organization_uid
    FALSE,                            -- ip_only
    'gov.usagm',                             -- reverse_name
    NULL,                             -- screenshot
    NULL,                             -- country
    NULL,                             -- asn
    FALSE,                            -- cloud_hosted
    '{}',                            -- ssl
    '{}',                             -- censys_certificates_results
    '{}'                       -- trustymail_results
),
(
    gen_random_uuid(),                -- sub_domain_uid
    'cisa.gov',                          -- sub_domain
    NULL,                             -- root_domain_id
    TRUE,                            -- is_root_domain
    '78703098-981d-11ec-a101-02589a36c9d7',  -- data_source_uid
    NULL,                             -- dns_record_uid
    TRUE,                         -- status (or adjust to match enum/values)
    CURRENT_DATE,                     -- first_seen
    CURRENT_DATE,                     -- last_seen
    CURRENT_TIMESTAMP,                -- created_at
    CURRENT_TIMESTAMP,                -- updated_at
    TRUE,                             -- current
    TRUE,                             -- identified
    NULL,                             -- ip_address
    NULL,                             -- synced_at
    NULL,                             -- from_root_domain
    TRUE,                            -- enumerate_subs
    'manual',                         -- subdomain_source
    (
        SELECT id
        FROM organization
        WHERE acronym = 'DHS_CISA'
        LIMIT 1
    ),                                -- organization_uid
    FALSE,                            -- ip_only
    'gov.cisa',                             -- reverse_name
    NULL,                             -- screenshot
    NULL,                             -- country
    NULL,                             -- asn
    FALSE,                            -- cloud_hosted
    '{}',                            -- ssl
    '{}',                             -- censys_certificates_results
    '{}'
);
EOF

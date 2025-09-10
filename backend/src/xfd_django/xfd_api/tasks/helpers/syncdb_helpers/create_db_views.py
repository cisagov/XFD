"""Create views helper."""
# Standard Python Libraries
import logging

# Third-Party Libraries
from django.db import connections

# If changes are made to materialized view make sure to update version number
VW_SERVICE_VERSION = "20250823"
MAT_VW_COMBINED_VULNS_VERSION = "20250823"
DOMAIN_MAT_VIEW_VERSION = "20250823"
DOMAIN_SEARCH_MAT_VIEW_VERSION = "20250909"

LOGGER = logging.getLogger(__name__)


def create_vuln_normal_views(database):
    """Create vuln normal views."""
    with connections[database].cursor() as cursor:
        LOGGER.info("Creating normal views...")
        cursor.execute(
            """
            DROP VIEW IF EXISTS vw_ticket_vulns CASCADE;
        """
        )

        cursor.execute(
            """
            DROP VIEW IF EXISTS vw_shodan_vulns CASCADE;
        """
        )

        cursor.execute(
            """
            DROP VIEW IF EXISTS vw_credential_breaches CASCADE;
        """
        )
        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_ticket_vulns AS
            WITH latest_ticket_event AS (
                SELECT DISTINCT ON (ticket_id) *
                FROM ticket_event
                ORDER BY ticket_id, event_timestamp DESC, id DESC
            ),
            latest_ip_sub AS (
                SELECT DISTINCT ON (ip_id) ip_id, sub_domain_id
                FROM ips_subs
                ORDER BY ip_id, sub_domain_id
            )
            SELECT DISTINCT ON (t.id)
                'vuln_scanning_tickets' AS scan_source,
                t.id AS vuln_id,
                t.opened_timestamp::timestamp AS created_at,
                t.updated_timestamp::timestamp AS updated_at,
                COALESCE(t.closed_timestamp::timestamp, t.updated_timestamp::timestamp) AS last_seen,
                t.cve_string AS cve,
                t.vuln_name AS title,
                vs.cpe AS product,
                t.ip_string AS domain_string,
                COALESCE(sub_link.sub_domain_id, t.ip_id) AS domain_id,
                t.port_protocol AS protocol,
                t.vuln_port::text AS port,
                t.cvss_base_score,
                CASE
                    WHEN t.cvss_severity = 0 THEN 'N/A'
                    WHEN t.cvss_severity = 1 THEN 'Low'
                    WHEN t.cvss_severity = 2 THEN 'Medium'
                    WHEN t.cvss_severity = 3 THEN 'High'
                    WHEN t.cvss_severity = 4 THEN 'Critical'
                    ELSE 'N/A'
                END AS severity,
                t.organization_id,
                CASE WHEN t.is_open THEN 'open' ELSE 'closed' END AS state,
                t.vuln_source AS data_source,
                COALESCE(vs.description, te.reason, 'N/A') AS description,
                t.false_positive::bool AS false_positive,
                t.is_kev::bool AS is_kev,
                t.is_kev_ransomware::bool AS is_kev_ransomware,
                t.service_name AS service_string,
                t.is_risky::bool AS is_risky_service,
                t.operating_system AS os,
                NULL AS cwe,
                vs.cpe AS cpe,
                NULL AS references,
                'unconfirmed' AS substate,
                NULL AS needs_population,
                NULL AS actions,
                NULL AS structured_data,
                NULL AS kev_results,
                -- Additional fields
                t.ip_string,
                vs.cvss_vector,
                t.cvss_severity AS severity_int,
                vs.plugin_id,
                vs.solution,
                vs.synopsis,
                vs.plugin_output AS results
            FROM ticket t
            LEFT JOIN latest_ticket_event te ON te.ticket_id = t.id
            LEFT JOIN vuln_scan vs ON vs.id = te.vuln_scan_id
            LEFT JOIN latest_ip_sub sub_link ON sub_link.ip_id = t.ip_id;
            """
        )

        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_shodan_vulns AS
            -- Query for ShodanVulns
            SELECT DISTINCT ON (sv.shodan_vuln_uid)
                'shodan_vulnerability' as scan_source,
                sv.shodan_vuln_uid::text as vuln_id,
                sv."created_at"::timestamp as created_at,
                sv."timestamp"::timestamp as updated_at,
                sv."timestamp"::timestamp as last_seen,
                sv.cve as cve,
                sv.name as title,
                array_to_string(sv.cpe, ', ') as product,
                sv.ip_string as domain,
                COALESCE(sub_link.sub_domain_id, sv.ip_uid) AS domain_id,
                sv.protocol as protocol,
                sv.port as port,
                sv.cvss as cvss_base_score,
                COALESCE(sv.severity, 'N/A') as severity,
                sv.organization_uid as organization_id,
                'open' as state,
                'Shodan' as data_source,
                COALESCE(sv.summary, sv.mitigation, 'N/A') as description,
                null::bool as false_positive,
                null::bool as is_kev,
                null::bool as is_kev_ransomware,
                null as service_string,
                null::bool as is_risky_service,
                null as os, --t.os as os --Not seeing this in the ticket
                null as cwe,
                array_to_string(sv.cpe, ', ') as cpe,
                null as references,
                'unconfirmed' as substate,
                null as needs_population,
                null as actions,
                null as structured_data,
                null as kev_results,
                --Additional Data requested
                sv.ip_string,
                null AS cvss_vector,
                null::int AS severity_int,
                null as plugin_id,
                null AS solution,
                null AS synopsis,
                null AS results
            FROM shodan_vulns as sv
            LEFT JOIN LATERAL (
                SELECT sub_domain_id
                FROM ips_subs ipsubs
                WHERE ipsubs.ip_id = sv.ip_uid
                ORDER BY sub_domain_id -- or ORDER BY created_at if that column exists
                LIMIT 1
            ) AS sub_link ON TRUE
        """
        )

        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_credential_breaches AS
            SELECT DISTINCT ON (vuln_id)
                scan_source,
                vuln_id,
                created_at,
                updated_at,
                last_seen,
                cve,
                title,
                product,
                domain,
                domain_id,
                protocol,
                port,
                cvss_base_score,
                severity,
                organization_id,
                state,
                data_source,
                description,
                null::bool as false_positive,
                null::bool as is_kev,
                null::bool as is_kev_ransomware,
                null as service_string,
                null::bool as is_risky_service,
                null as os, --t.os as os --Not seeing this in the ticket
                null as cwe,
                null as cpe,
                null as references,
                'unconfirmed' as substate,
                null as needs_population,
                null as actions,
                null as structured_data,
                null as kev_results,
                --Additional Data requested
                null AS ip_string,
                null AS cvss_vector,
                null::int AS severity_int,
                null as plugin_id,
                null AS solution,
                null AS synopsis,
                null AS results
                FROM (
                SELECT
                    ce.credential_exposures_uid::text AS vuln_id,
                    'credential_breach' AS scan_source,
                    cb.breach_date AS created_at,
                    cb.modified_date AS updated_at,
                    cb.modified_date AS last_seen,
                    NULL AS cve,
                    cb.breach_name AS title,
                    NULL AS product,
                    COALESCE(sd.from_root_domain, sd.sub_domain) AS domain,
                    COALESCE(sd.root_domain_id, sd.sub_domain_uid) AS domain_id,
                    'SMTP,IMAP,POP3' AS protocol,
                    NULL AS port,
                    NULL::float AS cvss_base_score,
                    'N/A' AS severity,
                    ce.organization_id,
                    'open' AS state,
                    ds.name AS data_source,
                    cb.description,
                    ROW_NUMBER() OVER (
                        PARTITION BY cb.credential_breaches_uid, ce.sub_domain_id
                        ORDER BY ce.credential_exposures_uid
                    ) AS row_num
                FROM credential_breaches cb
                JOIN credential_exposures ce ON cb.credential_breaches_uid = ce.credential_breach_id
                JOIN sub_domains sd ON ce.sub_domain_id = sd.sub_domain_uid
                JOIN data_source ds ON ds.data_source_uid = cb.data_source_uid
            ) t
            WHERE row_num = 1;
        """
        )
        LOGGER.info("Normal views created.")


def create_vuln_materialized_views(database):
    """Create vuln materialized views."""
    create_vuln_normal_views("mini_data_lake")
    with connections[database].cursor() as cursor:
        LOGGER.info("Creating materialized views...")

        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mat_vw_combined_vulns;")

        # Example materialized view
        cursor.execute(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mat_vw_combined_vulns AS
            SELECT * from vw_ticket_vulns
            union all
            SELECT * from vw_shodan_vulns
            union all
            SELECT * from vw_credential_breaches
        """
        )

        # Create unique index required for CONCURRENTLY
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_uid
            ON mat_vw_combined_vulns (vuln_id)
        """
        )

        cursor.execute(
            "COMMENT ON MATERIALIZED VIEW mat_vw_combined_vulns IS 'version:{}';".format(
                MAT_VW_COMBINED_VULNS_VERSION
            )
        )

        # Additional optimal indexes based on search patterns
        LOGGER.info("Creating indexes on mat_vw_combined_vulns...")

        # Make sure pg_trgm extension is enabled (safe if run multiple times)
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

        # B-Tree indexes (exact matches, range filters)
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_domain_id
        ON mat_vw_combined_vulns (domain_id);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_organization_id
        ON mat_vw_combined_vulns (organization_id);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_severity
        ON mat_vw_combined_vulns (severity);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_state
        ON mat_vw_combined_vulns (state);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_substate
        ON mat_vw_combined_vulns (substate);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_is_kev
        ON mat_vw_combined_vulns (is_kev);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_created_at
        ON mat_vw_combined_vulns (created_at);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_scan_source
        ON mat_vw_combined_vulns (scan_source);
        """
        )

        # GIN + pg_trgm indexes (for partial matches)
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_title_trgm
        ON mat_vw_combined_vulns
        USING gin (title gin_trgm_ops);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_domain_string_trgm
        ON mat_vw_combined_vulns
        USING gin (domain_string gin_trgm_ops);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_ip_string_trgm
        ON mat_vw_combined_vulns
        USING gin (ip_string gin_trgm_ops);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_cpe_trgm
        ON mat_vw_combined_vulns
        USING gin (cpe gin_trgm_ops);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_os_trgm
        ON mat_vw_combined_vulns
        USING gin (os gin_trgm_ops);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_cve_trgm
        ON mat_vw_combined_vulns
        USING gin (cve gin_trgm_ops);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_cwe_trgm
        ON mat_vw_combined_vulns
        USING gin (cwe gin_trgm_ops);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_port_trgm
        ON mat_vw_combined_vulns
        USING gin (port gin_trgm_ops);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_service_string_trgm
        ON mat_vw_combined_vulns
        USING gin (service_string gin_trgm_ops);
        """
        )

        LOGGER.info("Indexes created on mat_vw_combined_vulns.")

        LOGGER.info("Materialized views created.")


def create_domain_materialized_view(database):
    """Create mat_vw_domain view."""
    with connections[database].cursor() as cursor:
        LOGGER.info("Creating domain view...")
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mat_vw_domain;")

        # Example materialized view
        cursor.execute(
            """
            CREATE MATERIALIZED VIEW mat_vw_domain AS

            -- Subdomains (with or without linked IP)
            SELECT
                sub.sub_domain_uid AS id,
                sub.created_at,
                sub.updated_at,
                sub.synced_at,
                COALESCE(string_agg(DISTINCT host(ip.ip), ', '), NULL) AS ip,
                sub.from_root_domain,
                sub.subdomain_source,
                sub.ip_only,
                sub.reverse_name,
                sub.sub_domain AS name,
                sub.screenshot,
                sub.country,
                sub.asn,
                sub.cloud_hosted,
                ip.from_cidr,
                sub.ssl,
                sub.censys_certificates_results,
                sub.trustymail_results,
                NULL AS discovered_by_id,
                sub.organization_uid AS organization_id,
                'subdomain' as source

            FROM
                sub_domains sub
            LEFT JOIN
                ips_subs link ON sub.sub_domain_uid = link.sub_domain_id
            LEFT JOIN
                ip ON ip.id = link.ip_id
            GROUP BY
                sub.sub_domain_uid, sub.created_at, sub.updated_at, sub.synced_at,
                sub.from_root_domain, sub.subdomain_source, sub.ip_only,
                sub.reverse_name, sub.sub_domain, sub.screenshot, sub.country,
                sub.asn, sub.cloud_hosted, sub.ssl,
                sub.censys_certificates_results, sub.trustymail_results,
                sub.organization_uid, ip.from_cidr


            UNION ALL

            -- IPs with no linked subdomain
            SELECT
                ip.id,
                ip.created_timestamp AS created_at,
                ip.updated_timestamp AS updated_at,
                ip.synced_at AS synced_at,
                host(ip.ip) AS ip,
                NULL AS from_root_domain,
                NULL AS subdomain_source,
                TRUE AS ip_only,
                NULL AS reverse_name,
                host(ip.ip) AS name,
                NULL AS screenshot,
                NULL AS country,
                NULL AS asn,
                NULL AS cloud_hosted,
                ip.from_cidr,
                NULL AS ssl,
                NULL AS censys_certificates_results,
                NULL AS trustymail_results,
                NULL AS discovered_by_id,
                ip.organization_id,
                'ip' as source

            FROM
                ip
            WHERE
                ip.id NOT IN (SELECT ip_id FROM ips_subs);
        """
        )
        # Add unique index to allow REFRESH CONCURRENTLY
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_mat_vw_domain_id ON mat_vw_domain (id);
            """
        )

        # Add version comment
        cursor.execute(
            "COMMENT ON MATERIALIZED VIEW mat_vw_domain IS 'version:{}';".format(
                DOMAIN_MAT_VIEW_VERSION
            )
        )

        LOGGER.info("Domain materialized view created.")

        LOGGER.info("Creating indexes on mat_vw_domain...")
        cursor.execute(
            "CREATE INDEX idx_vw_domain_organization_id ON mat_vw_domain (organization_id);"
        )
        cursor.execute("CREATE INDEX idx_vw_domain_name ON mat_vw_domain (name);")
        cursor.execute(
            "CREATE INDEX idx_vw_domain_reverse_name ON mat_vw_domain (reverse_name);"
        )
        cursor.execute("CREATE INDEX idx_vw_domain_ip ON mat_vw_domain (ip);")
        cursor.execute("CREATE INDEX idx_vw_domain_source ON mat_vw_domain (source);")
        cursor.execute(
            "CREATE INDEX idx_vw_domain_created_at ON mat_vw_domain (created_at);"
        )
        cursor.execute(
            "CREATE INDEX idx_vw_domain_updated_at ON mat_vw_domain (updated_at);"
        )
        cursor.execute(
            "CREATE INDEX CONCURRENTLY idx_vw_domain_org_id_id ON mat_vw_domain (organization_id, id);"
        )

        LOGGER.info("Domain Indexes created.")


def create_service_mat_view(database):
    """Create or replace the unified 'service' view (starting with Shodan data)."""
    with connections[database].cursor() as cursor:
        LOGGER.info("Creating 'service' view from ShodanAssets...")
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mat_vw_service CASCADE;")
        cursor.execute("DROP VIEW IF EXISTS vw_shodan_service CASCADE;")
        cursor.execute("DROP VIEW IF EXISTS vw_portscan_service CASCADE;")

        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_shodan_service AS
            WITH latest_ip_sub AS (
                SELECT DISTINCT ON (ip_id) ip_id, sub_domain_id
                FROM ips_subs
                ORDER BY ip_id, sub_domain_id
            )
            SELECT
                s.shodan_asset_uid::text AS id,
                s.created_at AS "created_at",
                s.timestamp AS "updated_at",
                'shodan' AS "service_source",
                s.port,
                COALESCE(s.product, s.server) AS service,
                s.server AS banner,
                jsonb_build_array(
                jsonb_build_object(
                        'name', COALESCE(s.product, s.server),
                        'cpe', NULL,
                        'tags', COALESCE(s.tags, '[]'::jsonb),
                        'vendor',
                            CASE
                                WHEN s.product ILIKE 'apache%' THEN 'apache'
                                WHEN s.product ILIKE 'microsoft%' THEN 'microsoft'
                                WHEN s.product ILIKE 'nginx%' THEN 'nginx'
                                WHEN s.product ILIKE 'jquery%' THEN 'jquery'
                                ELSE split_part(lower(s.product), ' ', 1)
                            END
                    )
                ) AS products,
                NULL::jsonb AS "censys_metadata",
                NULL::jsonb AS "censys_ipv4_results",
                NULL::jsonb AS "intrigue_ident_results",
                NULL::jsonb AS "shodan_results",
                NULL::jsonb AS "wappalyzer_results",
                s.timestamp AS "last_seen",
                s.ip_string AS "ip_string",
                COALESCE(sub_link.sub_domain_id,s.ip_uid) AS domain_id,
                NULL::uuid AS discovered_by_id
            FROM shodan_assets s
            LEFT JOIN latest_ip_sub sub_link ON sub_link.ip_id = s.ip_uid
            WHERE s.port IS NOT NULL AND
            (s.product IS NOT NULL OR s.server IS NOT NULL);
        """
        )

        LOGGER.info("Creating 'service' view from PortScans...")

        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_portscan_service AS
            WITH latest_ip_sub AS (
                SELECT DISTINCT ON (ip_id) ip_id, sub_domain_id
                FROM ips_subs
                ORDER BY ip_id, sub_domain_id
            )
            SELECT
                ps.id AS id,
                ps.time_scanned AS created_at,
                ps.time_scanned AS updated_at,
                'portscan' AS service_source,
                ps.port,
                ps.service_name AS service,
                ps.service_product AS banner,
                jsonb_build_array(
                    jsonb_build_object(
                        'name', ps.service_name,
                        'cpe', ps.service_cpe,
                        'tags', '[]'::jsonb,
                        'vendor',
                            CASE
                                WHEN ps.service_name ILIKE 'apache%' THEN 'apache'
                                WHEN ps.service_name ILIKE 'microsoft%' THEN 'microsoft'
                                WHEN ps.service_name ILIKE 'nginx%' THEN 'nginx'
                                WHEN ps.service_name ILIKE 'jquery%' THEN 'jquery'
                                ELSE split_part(lower(ps.service_name), ' ', 1)
                            END
                    )
                ) AS products,
                NULL::jsonb AS censys_metadata,
                NULL::jsonb AS censys_ipv4_results,
                NULL::jsonb AS intrigue_ident_results,
                NULL::jsonb AS shodan_results,
                NULL::jsonb AS wappalyzer_results,
                ps.time_scanned AS last_seen,
                ps.ip_string AS ip_string,
                COALESCE(sub_link.sub_domain_id, ps.ip_id) AS domain_id,
                NULL::uuid AS discovered_by_id
            FROM port_scan ps
            LEFT JOIN latest_ip_sub sub_link ON sub_link.ip_id = ps.ip_id
            WHERE ps.latest = TRUE
            AND ps.port IS NOT NULL
            AND ps.service_name IS NOT NULL;
        """
        )

        LOGGER.info("Creating materialized 'mat_vw_service' from union...")
        cursor.execute(
            """
            CREATE MATERIALIZED VIEW mat_vw_service AS
            SELECT * FROM vw_shodan_service
            UNION ALL
            SELECT * FROM vw_portscan_service;
            """
        )
        cursor.execute(
            "COMMENT ON MATERIALIZED VIEW mat_vw_service IS 'version:{}';".format(
                VW_SERVICE_VERSION
            )
        )
        LOGGER.info("Service materialized view created.")

        LOGGER.info("Creating unique indexes for service view...")

        cursor.execute(
            """
        CREATE UNIQUE INDEX idx_vw_service_id ON mat_vw_service (id);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_vw_service_domain_id ON mat_vw_service (domain_id);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_vw_service_port ON mat_vw_service (port);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_vw_service_service_source ON mat_vw_service (service_source);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_vw_service_updated_at ON mat_vw_service (updated_at);
        """
        )

        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_vw_service_last_seen ON mat_vw_service (last_seen);
        """
        )

        LOGGER.info("Materialized view 'mat_vw_service' created.")


def create_domain_search_mat_view(database):
    """Create mat_vw_domain_search view."""
    with connections[database].cursor() as cursor:
        LOGGER.info("Creating domain details materialized view...")
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mat_vw_domain_search;")

        # Create materialized view
        cursor.execute(
            """
            CREATE MATERIALIZED VIEW mat_vw_domain_search AS
            WITH
            -- Normalize services once; avoid JSON in hot path
            svc AS (
                SELECT
                    s.domain_id,
                    s.id AS service_id,
                    s.port,
                    COALESCE(s.service, (s.products->0->>'name')) AS service_name,
                    s.last_seen
                FROM mat_vw_service s
            ),

            -- Distinct services per domain (for count)
            svc_counts AS (
                SELECT domain_id, COUNT(*) AS services_count
                FROM (SELECT DISTINCT domain_id, service_id FROM svc) t
                GROUP BY domain_id
            ),

            -- Top-3 ports per domain by recency
            port_rank AS (
                SELECT
                    domain_id,
                    port,
                    MAX(last_seen) AS last_seen,
                    ROW_NUMBER() OVER (
                        PARTITION BY domain_id
                        ORDER BY MAX(last_seen) DESC
                    ) AS rn
                FROM svc
                GROUP BY domain_id, port
            ),
            ports_preview AS (
                SELECT
                    domain_id,
                    STRING_AGG(port::text, ', ' ORDER BY last_seen DESC) AS ports_preview
                FROM port_rank
                WHERE rn <= 3
                GROUP BY domain_id
            ),

            -- Top-3 service names per domain by recency
            svcname_rank AS (
                SELECT
                    domain_id,
                    service_name,
                    MAX(last_seen) AS last_seen,
                    ROW_NUMBER() OVER (
                        PARTITION BY domain_id
                        ORDER BY MAX(last_seen) DESC
                    ) AS rn
                FROM svc
                GROUP BY domain_id, service_name
            ),
            services_preview AS (
                SELECT
                    domain_id,
                    STRING_AGG(service_name, ', ' ORDER BY last_seen DESC) AS services_preview
                FROM svcname_rank
                WHERE rn <= 3
                GROUP BY domain_id
            ),

            -- Vuln counts per domain (already distinct by vuln_id)
            vuln_counts AS (
                SELECT
                    domain_id,
                    NULLIF(COUNT(DISTINCT vuln_id), 0) AS vulnerabilities_count
                FROM mat_vw_combined_vulns
                GROUP BY domain_id
            )

            SELECT
                d.id AS domain_id,
                d.name,
                d.ip,
                d.organization_id,
                o.name AS organization_name,
                d.source,
                d.country,
                d.cloud_hosted,
                d.reverse_name,
                d.created_at,
                d.updated_at,
                p.ports_preview,
                sp.services_preview,
                sc.services_count,
                vc.vulnerabilities_count
            FROM mat_vw_domain d
            LEFT JOIN organization o ON o.id = d.organization_id
            LEFT JOIN svc_counts       sc ON sc.domain_id = d.id
            LEFT JOIN vuln_counts      vc ON vc.domain_id = d.id
            LEFT JOIN ports_preview     p ON p.domain_id = d.id
            LEFT JOIN services_preview sp ON sp.domain_id = d.id
            """
        )

        # Add unique index for CONCURRENTLY refresh
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_mat_vw_domain_search_id
            ON mat_vw_domain_search(domain_id);
            """
        )

        # Add useful indexes for filtering and ordering
        LOGGER.info("Creating indexes on mat_vw_domain_search...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mat_vw_domain_search_org_id_id
            ON mat_vw_domain_search (organization_id, domain_id);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mat_vw_domain_search_name
            ON mat_vw_domain_search (name);
            """
        )

        # Add version comment for tracking
        cursor.execute(
            """
            COMMENT ON MATERIALIZED VIEW mat_vw_domain_search
            IS 'version:{}';
            """.format(
                DOMAIN_SEARCH_MAT_VIEW_VERSION
            )
        )

        LOGGER.info("Domain details materialized view created.")

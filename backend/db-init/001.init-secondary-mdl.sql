-- -------------------------------------------------------------
-- TablePlus 6.3.2(586)
--
-- https://tableplus.com/
--
-- Database: crossfeed_mini_datalake_secondary
-- Generation Time: 2025-03-26 09:31:26.4190
-- -------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles
        WHERE rolname = 'crossfeed'
    ) THEN
        CREATE ROLE crossfeed WITH LOGIN PASSWORD 'password';  -- Replace 'changeme' with a secure password
    END IF;
END
$$;

CREATE DATABASE crossfeed_mini_datalake_secondary
    OWNER crossfeed;

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.


\c crossfeed_mini_datalake_secondary

-- Table Definition
CREATE TABLE "public"."alembic_version" (
    "version_num" varchar(32) NOT NULL,
    PRIMARY KEY ("version_num")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."alias" (
    "alias_uid" uuid NOT NULL,
    "organization_uid" uuid NOT NULL,
    "alias" text NOT NULL,
    PRIMARY KEY ("alias_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."api_key" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "last_used" timestamptz,
    "hashed_key" text NOT NULL,
    "last_four" text NOT NULL,
    "user_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."asset_headers" (
    "_id" uuid NOT NULL,
    "organization_uid" uuid NOT NULL,
    "sub_url" text NOT NULL,
    "tech_detected" text NOT NULL,
    "interesting_header" text NOT NULL,
    "ssl2" text,
    "tls1" text,
    "certificate" text,
    "scanned" bool,
    "ssl_scanned" bool,
    PRIMARY KEY ("_id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cidr" (
    "id" uuid NOT NULL,
    "created_date" timestamptz NOT NULL,
    "network" inet,
    "start_ip" inet,
    "end_ip" inet,
    "retired" bool,
    "updated_at" timestamptz NOT NULL,
    "insert_alert" text,
    "data_source_uid" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cidr_orgs" (
    "cidr_orgs_id" uuid NOT NULL,
    "cidr_id" uuid NOT NULL,
    "organization_id" uuid NOT NULL,
    "first_seen" date,
    "last_seen" date,
    "current" bool,
    PRIMARY KEY ("cidr_orgs_id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cpe" (
    "id" uuid NOT NULL,
    "name" varchar(255) NOT NULL,
    "version" varchar(255) NOT NULL,
    "vendor" varchar(255) NOT NULL,
    "last_seen_at" timestamptz NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cpe_product_mdl" (
    "cpe_product_uid" uuid NOT NULL,
    "cpe_product_name" text,
    "version_number" text,
    "cpe_vender_uid" uuid NOT NULL,
    PRIMARY KEY ("cpe_product_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cpe_product_mdl_cves" (
    "id" int8 NOT NULL,
    "cpeproduct_id" uuid NOT NULL,
    "cve_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cpe_vender" (
    "cpe_vender_uid" uuid NOT NULL,
    "vender_name" text,
    PRIMARY KEY ("cpe_vender_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."credential_breaches" (
    "credential_breaches_uid" uuid NOT NULL,
    "breach_name" text NOT NULL,
    "description" text,
    "exposed_cred_count" int8,
    "breach_date" date,
    "added_date" timestamptz,
    "modified_date" timestamptz,
    "data_classes" _text,
    "password_included" bool,
    "is_verified" bool,
    "is_fabricated" bool,
    "is_sensitive" bool,
    "is_retired" bool,
    "is_spam_list" bool,
    "data_source_uid" uuid,
    PRIMARY KEY ("credential_breaches_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."credential_exposures" (
    "credential_exposures_uid" uuid NOT NULL,
    "email" text NOT NULL,
    "organization_uid" uuid NOT NULL,
    "root_domain" text,
    "sub_domain_string" text,
    "sub_domain_id" uuid NOT NULL,
    "breach_name" text,
    "modified_date" timestamptz,
    "credential_breaches_uid" uuid NOT NULL,
    "data_source_uid" uuid,
    "name" text,
    "login_id" text,
    "phone" text,
    "password" text,
    "hash_type" text,
    "intelx_system_id" text,
    PRIMARY KEY ("credential_exposures_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cve" (
    "id" uuid NOT NULL,
    "name" varchar(255),
    "published_at" timestamptz,
    "modified_at" timestamptz,
    "status" varchar(255),
    "description" text,
    "cvss_v2_source" varchar(255),
    "cvss_v2_type" varchar(255),
    "cvss_v2_version" varchar(255),
    "cvss_v2_vector_string" varchar(255),
    "cvss_v2_base_score" varchar(255),
    "cvss_v2_base_severity" varchar(255),
    "cvss_v2_exploitability_score" varchar(255),
    "cvss_v2_impact_score" varchar(255),
    "cvss_v3_source" varchar(255),
    "cvss_v3_type" varchar(255),
    "cvss_v3_version" varchar(255),
    "cvss_v3_vector_string" varchar(255),
    "cvss_v3_base_score" varchar(255),
    "cvss_v3_base_severity" varchar(255),
    "cvss_v3_exploitability_score" varchar(255),
    "cvss_v3_impact_score" varchar(255),
    "cvss_v4_source" varchar(255),
    "cvss_v4_type" varchar(255),
    "cvss_v4_version" varchar(255),
    "cvss_v4_vector_string" varchar(255),
    "cvss_v4_base_score" varchar(255),
    "cvss_v4_base_severity" varchar(255),
    "cvss_v4_exploitability_score" varchar(255),
    "cvss_v4_impact_score" varchar(255),
    "weaknesses" text,
    "references" text,
    "dve_score" numeric(1000,1000),
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cve_cpes" (
    "id" int8 NOT NULL,
    "cve_id" uuid NOT NULL,
    "cpe_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cyhy_contacts" (
    "_id" uuid NOT NULL,
    "org_id" text NOT NULL,
    "organization_uid" uuid NOT NULL,
    "org_name" text NOT NULL,
    "phone" text,
    "contact_type" text NOT NULL,
    "email" text,
    "name" text,
    "date_pulled" date,
    PRIMARY KEY ("_id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cyhy_db_assets" (
    "_id" uuid NOT NULL,
    "org_id" text,
    "organization_uid" uuid NOT NULL,
    "org_name" text,
    "contact" text,
    "network" inet,
    "type" text,
    "first_seen" date,
    "last_seen" date,
    "currently_in_cyhy" bool,
    PRIMARY KEY ("_id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."cyhy_kevs" (
    "cyhy_kevs_uid" uuid NOT NULL,
    "kev" varchar(255),
    "first_seen" date,
    "last_seen" date,
    PRIMARY KEY ("cyhy_kevs_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."data_source" (
    "data_source_uid" uuid NOT NULL,
    "name" text NOT NULL,
    "description" text NOT NULL,
    "last_run" date NOT NULL,
    PRIMARY KEY ("data_source_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."dns_records" (
    "dns_record_uid" uuid NOT NULL,
    "domain_name" text,
    "domain_type" text,
    "created_date" timestamptz,
    "updated_date" timestamptz,
    "expiration_date" timestamptz,
    "name_servers" text,
    "whois_server" text,
    "registrar_name" text,
    "status" text,
    "clean_text" text,
    "raw_text" text,
    "registrant_name" text,
    "registrant_organization" text,
    "registrant_street" text,
    "registrant_city" text,
    "registrant_state" text,
    "registrant_post_code" text,
    "registrant_country" text,
    "registrant_email" text,
    "registrant_phone" text,
    "registrant_phone_ext" text,
    "registrant_fax" text,
    "registrant_fax_ext" text,
    "registrant_raw_text" text,
    "administrative_name" text,
    "administrative_organization" text,
    "administrative_street" text,
    "administrative_city" text,
    "administrative_state" text,
    "administrative_post_code" text,
    "administrative_country" text,
    "administrative_email" text,
    "administrative_phone" text,
    "administrative_phone_ext" text,
    "administrative_fax" text,
    "administrative_fax_ext" text,
    "administrative_raw_text" text,
    "technical_name" text,
    "technical_organization" text,
    "technical_street" text,
    "technical_city" text,
    "technical_state" text,
    "technical_post_code" text,
    "technical_country" text,
    "technical_email" text,
    "technical_phone" text,
    "technical_phone_ext" text,
    "technical_fax" text,
    "technical_fax_ext" text,
    "technical_raw_text" text,
    "billing_name" text,
    "billing_organization" text,
    "billing_street" text,
    "billing_city" text,
    "billing_state" text,
    "billing_post_code" text,
    "billing_country" text,
    "billing_email" text,
    "billing_phone" text,
    "billing_phone_ext" text,
    "billing_fax" text,
    "billing_fax_ext" text,
    "billing_raw_text" text,
    "zone_name" text,
    "zone_organization" text,
    "zone_street" text,
    "zone_city" text,
    "zone_state" text,
    "zone_post_code" text,
    "zone_country" text,
    "zone_email" text,
    "zone_phone" text,
    "zone_phone_ext" text,
    "zone_fax" text,
    "zone_fax_ext" text,
    "zone_raw_text" text,
    PRIMARY KEY ("dns_record_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."domain_alerts" (
    "domain_alert_uid" uuid NOT NULL,
    "sub_domain_uid" uuid NOT NULL,
    "data_source_uid" uuid NOT NULL,
    "organization_uid" uuid NOT NULL,
    "alert_type" text,
    "message" text,
    "previous_value" text,
    "new_value" text,
    "date" date,
    PRIMARY KEY ("domain_alert_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."domain_permutations" (
    "suspected_domain_uid" uuid NOT NULL,
    "organization_uid" uuid NOT NULL,
    "domain_permutation" text,
    "ipv4" text,
    "ipv6" text,
    "mail_server" text,
    "name_server" text,
    "fuzzer" text,
    "date_observed" date,
    "ssdeep_score" text,
    "malicious" bool,
    "blocklist_attack_count" int4,
    "blocklist_report_count" int4,
    "data_source_uid" uuid NOT NULL,
    "sub_domain_uid" uuid,
    "dshield_record_count" int4,
    "dshield_attack_count" int4,
    "date_active" date,
    PRIMARY KEY ("suspected_domain_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."dotgov_domains" (
    "dotgov_uid" uuid NOT NULL,
    "domain_name" text NOT NULL,
    "domain_type" text,
    "agency" text,
    "organization" text,
    "city" text,
    "state" text,
    "security_contact_email" text,
    PRIMARY KEY ("dotgov_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."executives" (
    "executives_uid" uuid NOT NULL,
    "organization" uuid NOT NULL,
    "executives" text NOT NULL,
    PRIMARY KEY ("executives_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."host" (
    "id" varchar(255) NOT NULL,
    "ip_string" varchar(255),
    "ip_id" text,
    "updated_timestamp" timestamptz,
    "latest_netscan_1_timestamp" timestamptz,
    "latest_netscan_2_timestamp" timestamptz,
    "latest_vulnscan_timestamp" timestamptz,
    "latest_portscan_timestamp" timestamptz,
    "latest_scan_completion_timestamp" timestamptz,
    "location_longitude" numeric(10,6),
    "location_latitude" numeric(10,6),
    "priority" int4,
    "next_scan_timestamp" timestamptz,
    "rand" numeric(10,6),
    "curr_stage" varchar(255),
    "host_live" bool,
    "host_live_reason" varchar(255),
    "status" varchar(255),
    "organization_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."ip" (
    "ip_hash" text NOT NULL,
    "organization_id" uuid NOT NULL,
    "created_timestamp" timestamptz NOT NULL,
    "updated_timestamp" timestamptz,
    "last_seen_timestamp" timestamptz,
    "ip" inet,
    "live" bool,
    "false_positive" bool,
    "retired" bool,
    "last_reverse_lookup" timestamptz,
    "from_cidr" bool,
    "has_shodan_results" bool,
    "origin_cidr" uuid,
    "current" bool,
    PRIMARY KEY ("ip_hash")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."ips_subs" (
    "ips_subs_uid" uuid NOT NULL,
    "ip_hash" text NOT NULL,
    "sub_domain_uid" uuid NOT NULL,
    "first_seen" date,
    "last_seen" date,
    "current" bool,
    PRIMARY KEY ("ips_subs_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."location" (
    "id" uuid NOT NULL,
    "name" varchar(255),
    "country_abrv" varchar(255),
    "country" varchar(255),
    "county" varchar(255),
    "county_fips" varchar(255),
    "gnis_id" varchar(255),
    "state_abrv" varchar(255),
    "state_fips" varchar(255),
    "state" varchar(255),
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."mentions" (
    "mentions_uid" uuid NOT NULL,
    "category" text,
    "collection_date" text,
    "content" text,
    "creator" text,
    "date" date,
    "sixgill_mention_id" text,
    "post_id" text,
    "lang" text,
    "rep_grade" text,
    "site" text,
    "site_grade" text,
    "title" text,
    "type" text,
    "url" text,
    "comments_count" text,
    "sub_category" text,
    "tags" text,
    "organization_uid" uuid NOT NULL,
    "data_source_uid" uuid NOT NULL,
    "title_translated" text,
    "content_translated" text,
    "detected_lang" text,
    PRIMARY KEY ("mentions_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."notification" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "start_datetime" timestamptz,
    "end_datetime" timestamptz,
    "maintenance_type" varchar(255),
    "status" varchar(255),
    "updated_by" varchar(255),
    "message" text,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."org_id_map" (
    "id" int8 NOT NULL,
    "cyhy_id" text,
    "pe_org_id" text,
    "merge_orgs" bool,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."org_type" (
    "org_type_uid" uuid NOT NULL,
    "org_type" text,
    PRIMARY KEY ("org_type_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."organization" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "acronym" varchar(255),
    "retired" bool,
    "name" varchar(255) NOT NULL,
    "root_domains" _text,
    "ip_blocks" text NOT NULL,
    "is_passive" bool NOT NULL,
    "pending_domains" _text,
    "date_pe_first_reported" timestamptz,
    "country" text,
    "country_name" text,
    "state" varchar(255),
    "region_id" varchar(255),
    "state_fips" int4,
    "state_name" varchar(255),
    "county" text,
    "county_fips" int4,
    "type" varchar(255),
    "pe_report_on" bool,
    "pe_premium" bool,
    "pe_demo" bool,
    "agency_type" text,
    "is_parent" bool,
    "pe_run_scans" bool,
    "stakeholder" bool,
    "election" bool,
    "was_stakeholder" bool,
    "vs_stakeholder" bool,
    "pe_stakeholder" bool,
    "receives_cyhy_report" bool,
    "receives_bod_report" bool,
    "receives_cybex_report" bool,
    "init_stage" varchar(255),
    "scheduler" varchar(255),
    "enrolled_in_vs_timestamp" timestamptz NOT NULL,
    "period_start_vs_timestamp" timestamptz NOT NULL,
    "report_types" jsonb,
    "scan_types" jsonb,
    "scan_windows" jsonb,
    "scan_limits" jsonb,
    "password" text,
    "cyhy_period_start" date,
    "location_id" uuid,
    "parent_id" uuid,
    "created_by_id" uuid,
    "org_type_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."organization_tag" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "name" varchar(255) NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."organization_tag_organization" (
    "id" int8 NOT NULL,
    "organizationtag_id" uuid NOT NULL,
    "organization_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."pe_report_summary_stats" (
    "report_uid" uuid NOT NULL,
    "organization_uid" uuid NOT NULL,
    "start_date" date NOT NULL,
    "end_date" date,
    "ip_count" int4,
    "root_count" int4,
    "sub_count" int4,
    "ports_count" int4,
    "creds_count" int4,
    "breach_count" int4,
    "cred_password_count" int4,
    "domain_alert_count" int4,
    "suspected_domain_count" int4,
    "insecure_port_count" int4,
    "verified_vuln_count" int4,
    "suspected_vuln_count" int4,
    "suspected_vuln_addrs_count" int4,
    "threat_actor_count" int4,
    "dark_web_alerts_count" int4,
    "dark_web_mentions_count" int4,
    "dark_web_executive_alerts_count" int4,
    "dark_web_asset_alerts_count" int4,
    "pe_number_score" text,
    "pe_letter_grade" text,
    "pe_percent_score" numeric(1000,1000),
    "cidr_count" int4,
    "port_protocol_count" int4,
    "software_count" int4,
    "foreign_ips_count" int4,
    PRIMARY KEY ("report_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."pe_team_members" (
    "team_member_uid" uuid NOT NULL,
    "team_member_fname" text NOT NULL,
    "team_member_lname" text NOT NULL,
    "team_member_email" text NOT NULL,
    "team_member_ghID" text NOT NULL,
    "team_member_phone" text,
    "team_member_role" text,
    "team_member_notes" text,
    PRIMARY KEY ("team_member_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."pe_users" (
    "id" uuid NOT NULL,
    "email" varchar(64),
    "username" varchar(64),
    "admin" int4,
    "role" int4,
    "password_hash" varchar(128),
    "api_key" varchar(128),
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."port_scan" (
    "id" varchar(255) NOT NULL,
    "ip_string" varchar(255),
    "ip_id" text,
    "latest" bool NOT NULL,
    "port" int4,
    "protocol" varchar(255),
    "reason" varchar(255),
    "service" jsonb NOT NULL,
    "service_name" varchar(255),
    "service_confidence" int4,
    "service_method" varchar(255),
    "source" varchar(255),
    "state" varchar(255),
    "time_scanned" timestamptz,
    "organization_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."pshtt_results" (
    "pshtt_results_uid" uuid NOT NULL,
    "organization_uid" uuid NOT NULL,
    "data_source_uid" uuid NOT NULL,
    "sub_domain" text NOT NULL,
    "date_scanned" date,
    "base_domain" text,
    "base_domain_hsts_preloaded" bool,
    "canonical_url" text,
    "defaults_to_https" bool,
    "domain" text,
    "domain_enforces_https" bool,
    "domain_supports_https" bool,
    "domain_uses_strong_hsts" bool,
    "downgrades_https" bool,
    "htss" bool,
    "hsts_entire_domain" bool,
    "hsts_header" text,
    "hsts_max_age" numeric(1000,1000),
    "hsts_preload_pending" bool,
    "hsts_preload_ready" bool,
    "hsts_preloaded" bool,
    "https_bad_chain" bool,
    "https_bad_hostname" bool,
    "https_cert_chain_length" int4,
    "https_client_auth_required" bool,
    "https_custom_truststore_trusted" bool,
    "https_expired_cert" bool,
    "https_full_connection" bool,
    "https_live" bool,
    "https_probably_missing_intermediate_cert" bool,
    "https_publicly_trusted" bool,
    "https_self_signed_cert" bool,
    "https_leaf_cert_expiration_date" date,
    "https_leaf_cert_issuer" text,
    "https_leaf_cert_subject" text,
    "https_root_cert_issuer" text,
    "ip" inet,
    "live" bool,
    "notes" text,
    "redirect" bool,
    "redirect_to" text,
    "server_header" text,
    "server_version" text,
    "strictly_forces_https" bool,
    "unknown_error" bool,
    "valid_https" bool,
    "ep_http_headers" text,
    "ep_http_server_header" text,
    "ep_http_server_version" text,
    "ep_https_headers" text,
    "ep_https_hsts_header" text,
    "ep_https_server_header" text,
    "ep_https_server_version" text,
    "ep_httpswww_headers" text,
    "ep_httpswww_hsts_header" text,
    "ep_httpswww_server_header" text,
    "ep_httpswww_server_version" text,
    "ep_httpwww_headers" text,
    "ep_httpwww_server_header" text,
    "ep_httpwww_server_version" text,
    PRIMARY KEY ("pshtt_results_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."query-result-cache" (
    "id" uuid NOT NULL,
    "identifier" varchar(255),
    "time" int8 NOT NULL,
    "duration" int4 NOT NULL,
    "query" text NOT NULL,
    "result" text NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."role" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "role" varchar(255) NOT NULL,
    "approved" bool NOT NULL,
    "created_by_id" uuid,
    "approved_by_id" uuid,
    "user_id" uuid,
    "organization_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."saved_search" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "name" varchar(255) NOT NULL,
    "search_term" varchar(255) NOT NULL,
    "sort_direction" varchar(255) NOT NULL,
    "sort_field" varchar(255) NOT NULL,
    "count" int4 NOT NULL,
    "filters" jsonb NOT NULL,
    "search_path" varchar(255) NOT NULL,
    "created_by_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."scan" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "name" varchar(255) NOT NULL,
    "arguments" jsonb NOT NULL,
    "frequency" int4 NOT NULL,
    "last_run" timestamptz,
    "is_granular" bool NOT NULL,
    "is_user_modifiable" bool,
    "is_single_scan" bool NOT NULL,
    "manual_run_pending" bool NOT NULL,
    "created_by" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."scan_organization_tags" (
    "id" int8 NOT NULL,
    "scan_id" uuid NOT NULL,
    "organizationtag_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."scan_organizations" (
    "id" int8 NOT NULL,
    "scan_id" uuid NOT NULL,
    "organization_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."scan_task" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "status" text NOT NULL,
    "type" text NOT NULL,
    "fargate_task_arn" text,
    "input" text,
    "output" text,
    "requested_at" timestamptz,
    "started_at" timestamptz,
    "finished_at" timestamptz,
    "queued_at" timestamptz,
    "scan_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."scan_task_organizations" (
    "id" int8 NOT NULL,
    "scantask_id" uuid NOT NULL,
    "organization_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."sector" (
    "id" uuid NOT NULL,
    "name" varchar(255),
    "acronym" varchar(255),
    "retired" bool,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."sector_organizations" (
    "id" int8 NOT NULL,
    "sector_id" uuid NOT NULL,
    "organization_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."service" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "service_source" text,
    "port" int4 NOT NULL,
    "service" text,
    "last_seen" timestamptz,
    "banner" text,
    "products" jsonb NOT NULL,
    "censys_metadata" jsonb NOT NULL,
    "censys_ipv4_results" jsonb NOT NULL,
    "intrigue_ident_results" jsonb NOT NULL,
    "shodan_results" jsonb NOT NULL,
    "wappalyzer_results" jsonb NOT NULL,
    "domain_id" uuid,
    "discovered_by_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."shodan_assets" (
    "shodan_asset_uid" uuid NOT NULL,
    "organization_uid" uuid,
    "organization_name" text,
    "ip" text,
    "port" int4,
    "protocol" text,
    "timestamp" timestamptz,
    "product" text,
    "server" text,
    "tags" jsonb,
    "domains" jsonb,
    "hostnames" jsonb,
    "isp" text,
    "asn" int4,
    "data_source_uid" uuid,
    "country_code" text,
    "location" text,
    PRIMARY KEY ("shodan_asset_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."shodan_vulns" (
    "shodan_vuln_uid" uuid NOT NULL,
    "organization_uid" uuid NOT NULL,
    "organization_name" text,
    "ip" text,
    "port" text,
    "protocol" text,
    "timestamp" timestamptz,
    "cve" text,
    "severity" text,
    "cvss" numeric(1000,1000),
    "summary" text,
    "product" text,
    "attack_vector" text,
    "av_description" text,
    "attack_complexity" text,
    "ac_description" text,
    "confidentiality_impact" text,
    "ci_description" text,
    "integrity_impact" text,
    "ii_description" text,
    "availability_impact" text,
    "ai_description" text,
    "tags" _text,
    "domains" _text,
    "hostnames" _text,
    "isp" text,
    "asn" int4,
    "data_source_uid" uuid,
    "type" text,
    "name" text,
    "potential_vulns" _text,
    "mitigation" text,
    "server" text,
    "is_verified" bool,
    "banner" text,
    "version" text,
    "cpe" _text,
    "sub_domain_id" uuid NOT NULL,
    "service_id" uuid NOT NULL,
    PRIMARY KEY ("shodan_vuln_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."sixgill_alerts" (
    "alerts_uid" uuid NOT NULL,
    "alert_name" text,
    "content" text,
    "date" date,
    "sixgill_id" text,
    "read" text,
    "severity" text,
    "site" text,
    "threat_level" text,
    "threats" text,
    "title" text,
    "user_id" text,
    "category" text,
    "lang" text,
    "organization_uid" uuid NOT NULL,
    "data_source_uid" uuid NOT NULL,
    "content_snip" text,
    "asset_mentioned" text,
    "asset_type" text,
    PRIMARY KEY ("alerts_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."sub_domains" (
    "sub_domain_uid" uuid NOT NULL,
    "sub_domain" text NOT NULL,
    "root_domain_id" uuid,
    "is_root_domain" bool,
    "data_source_uid" uuid NOT NULL,
    "dns_record_uid" uuid,
    "status" bool,
    "first_seen" date,
    "last_seen" date,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "current" bool,
    "identified" bool,
    "ip_address" text,
    "synced_at" timestamptz,
    "from_root_domain" text,
    "enumerate_subs" bool,
    "subdomain_source" text,
    "organization_uid" uuid NOT NULL,
    "ip_only" bool NOT NULL,
    "reverse_name" varchar(512) NOT NULL,
    "screenshot" varchar(512),
    "country" varchar(255),
    "asn" varchar(255),
    "cloud_hosted" bool NOT NULL,
    "ssl" jsonb,
    "censys_certificates_results" jsonb NOT NULL,
    "trustymail_results" jsonb NOT NULL,
    PRIMARY KEY ("sub_domain_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."ticket" (
    "id" varchar(255) NOT NULL,
    "cve_string" varchar(255),
    "cve_id" uuid,
    "cvss_base_score" numeric(5,2),
    "cvss_version" varchar(255),
    "vuln_name" varchar(255),
    "cvss_score_source" varchar(255),
    "cvss_severity" numeric(5,2),
    "vpr_score" numeric(5,2),
    "false_positive" bool,
    "ip_string" varchar(255),
    "ip_id" text,
    "updated_timestamp" timestamptz,
    "location_longitude" numeric(9,6),
    "location_latitude" numeric(9,6),
    "found_in_latest_host_scan" bool,
    "organization_id" uuid,
    "vuln_port" int4,
    "port_protocol" varchar(255),
    "snapshots_bool" bool,
    "vuln_source" varchar(255),
    "vuln_source_id" int4,
    "closed_timestamp" timestamptz,
    "opened_timestamp" timestamptz,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."ticket_event" (
    "id" uuid NOT NULL,
    "reference" varchar(255),
    "vuln_scan_id" varchar(255),
    "action" varchar(255),
    "reason" varchar(255),
    "event_timestamp" timestamptz,
    "delta" jsonb NOT NULL,
    "ticket_id" varchar(255),
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."top_cves" (
    "top_cves_uid" uuid NOT NULL,
    "cve_id" text,
    "dynamic_rating" text,
    "nvd_base_score" text,
    "date" date,
    "summary" text,
    "data_source_uid" uuid NOT NULL,
    PRIMARY KEY ("top_cves_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."topic_totals" (
    "count_uuid" uuid NOT NULL,
    "organization_uid" uuid NOT NULL,
    "content_count" int4 NOT NULL,
    "count_date" text,
    PRIMARY KEY ("count_uuid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."unique_software" (
    "_id" uuid NOT NULL,
    "software_name" text NOT NULL,
    PRIMARY KEY ("_id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."user" (
    "id" uuid NOT NULL,
    "cognito_id" varchar(255),
    "login_gov_id" varchar(255),
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "first_name" varchar(255) NOT NULL,
    "last_name" varchar(255) NOT NULL,
    "full_name" varchar(255) NOT NULL,
    "email" varchar(255) NOT NULL,
    "invite_pending" bool NOT NULL,
    "login_blocked_by_maintenance" bool NOT NULL,
    "date_accepted_terms" timestamptz,
    "accepted_terms_version" text,
    "last_logged_in" timestamptz,
    "user_type" text NOT NULL,
    "region_id" varchar(255),
    "state" varchar(255),
    "okta_id" varchar(255),
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."vuln_scan" (
    "id" varchar(255) NOT NULL,
    "cert_id" varchar(255),
    "cpe" varchar(255),
    "cve_string" varchar(255),
    "cve_id" uuid,
    "cvss_base_score" varchar(255),
    "cvss_temporal_score" varchar(255),
    "cvss_temporal_vector" varchar(255),
    "cvss_vector" varchar(255),
    "description" varchar(255),
    "exploit_available" varchar(255),
    "exploitability_ease" varchar(255),
    "ip_string" varchar(255),
    "ip_id" text,
    "latest" bool NOT NULL,
    "owner" varchar(255),
    "osvdb_id" varchar(255),
    "organization_id" uuid,
    "patch_publication_timestamp" timestamptz,
    "cisa_known_exploited" timestamptz,
    "port" int4,
    "port_protocol" varchar(255),
    "risk_factor" varchar(255),
    "script_version" varchar(255),
    "see_also" varchar(255),
    "service" varchar(255),
    "severity" int4,
    "solution" varchar(255),
    "source" varchar(255),
    "synopsis" varchar(255),
    "vuln_detection_timestamp" timestamptz,
    "vuln_publication_timestamp" timestamptz,
    "xref" varchar(255),
    "cwe" varchar(255),
    "bid" varchar(255),
    "exploited_by_malware" bool NOT NULL,
    "thorough_tests" bool NOT NULL,
    "cvss_score_rationale" varchar(255),
    "cvss_score_source" varchar(255),
    "cvss3_base_score" numeric(5,2),
    "cvss3_vector" varchar(255),
    "cvss3_temporal_vector" varchar(255),
    "cvss3_temporal_score" numeric(5,2),
    "asset_inventory" bool NOT NULL,
    "plugin_id" varchar(255),
    "plugin_modification_date" timestamptz,
    "plugin_publication_date" timestamptz,
    "plugin_name" varchar(255),
    "plugin_type" varchar(255),
    "plugin_family" varchar(255),
    "f_name" varchar(255),
    "cisco_bug_id" varchar(255),
    "cisco_sa" varchar(255),
    "plugin_output" text,
    "other_findings" jsonb NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."vulnerability" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "last_seen" timestamptz,
    "title" text NOT NULL,
    "cve" text,
    "cwe" text,
    "cpe" text,
    "description" text NOT NULL,
    "references" jsonb NOT NULL,
    "cvss" numeric(100,5),
    "severity" text,
    "needs_population" bool NOT NULL,
    "state" text NOT NULL,
    "substate" text NOT NULL,
    "source" text NOT NULL,
    "notes" text NOT NULL,
    "actions" jsonb NOT NULL,
    "structured_data" jsonb NOT NULL,
    "is_kev" bool,
    "kev_results" jsonb,
    "domain_id" uuid,
    "service_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."was_findings" (
    "finding_uid" uuid NOT NULL,
    "finding_type" text,
    "webapp_id" int4,
    "was_org_id" text,
    "owasp_category" text,
    "severity" text,
    "times_detected" int4,
    "base_score" float8,
    "temporal_score" float8,
    "fstatus" text,
    "last_detected" date,
    "first_detected" date,
    "is_remediated" bool,
    "potential" bool,
    "webapp_url" text,
    "webapp_name" text,
    "name" text,
    "cvss_v3_attack_vector" text,
    "cwe_list" _int4,
    "wasc_list" jsonb,
    "last_tested" date,
    "fixed_date" date,
    "is_ignored" bool,
    "url" text,
    "qid" int4,
    "response" text,
    "sub_domain_id" uuid NOT NULL,
    "service_id" uuid NOT NULL,
    PRIMARY KEY ("finding_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."was_history" (
    "id" int8 NOT NULL,
    "was_org_id" text,
    "date_scanned" date NOT NULL,
    "vuln_cnt" int4,
    "vuln_webapp_cnt" int4,
    "web_app_cnt" int4,
    "high_rem_time" int4,
    "crit_rem_time" int4,
    "crit_vuln_cnt" int4,
    "high_vuln_cnt" int4,
    "report_period" date,
    "high_rem_cnt" int4,
    "crit_rem_cnt" int4,
    "total_potential" int4,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."was_map" (
    "was_org_id" text NOT NULL,
    "pe_org_id" uuid,
    "report_on" bool,
    "last_scanned" date,
    PRIMARY KEY ("was_org_id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."was_report" (
    "id" int8 NOT NULL,
    "org_name" text,
    "date_pulled" timestamptz,
    "last_scan_date" timestamptz,
    "security_risk" text,
    "total_info" int4,
    "num_apps" int4,
    "risk_color" text,
    "sensitive_count" int4,
    "sensitive_color" text,
    "max_days_open_urgent" int4,
    "max_days_open_critical" int4,
    "urgent_color" text,
    "critical_color" text,
    "org_was_acronym" text,
    "name_len" text,
    "vuln_csv_dict" jsonb,
    "ssn_cc_dict" jsonb,
    "app_overview_csv_dict" jsonb,
    "details_csv" jsonb,
    "info_csv" jsonb,
    "links_crawled" jsonb,
    "links_rejected" jsonb,
    "emails_found" jsonb,
    "owasp_count_dict" jsonb,
    "group_count_dict" jsonb,
    "fixed" int4,
    "total" int4,
    "vulns_monthly_dict" jsonb,
    "path_disc" int4,
    "info_disc" int4,
    "cross_site" int4,
    "burp" int4,
    "sql_inj" int4,
    "bugcrowd" int4,
    "reopened" int4,
    "reopened_color" text,
    "new_vulns" int4,
    "new_vulns_color" text,
    "tot_vulns" int4,
    "tot_vulns_color" text,
    "lev1" int4,
    "lev2" int4,
    "lev3" int4,
    "lev4" int4,
    "lev5" int4,
    "severities" _int4,
    "ages" _int4,
    "pdf_obj" bytea,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."was_tracker_customer_data" (
    "customer_id" uuid NOT NULL,
    "tag" text NOT NULL,
    "customer_name" text NOT NULL,
    "testing_sector" text NOT NULL,
    "ci_type" text NOT NULL,
    "jira_ticket" text NOT NULL,
    "ticket" text NOT NULL,
    "next_scheduled" text NOT NULL,
    "last_scanned" text NOT NULL,
    "frequency" text NOT NULL,
    "comments_notes" text NOT NULL,
    "was_report_poc" text NOT NULL,
    "was_report_email" text NOT NULL,
    "onboarding_date" text NOT NULL,
    "no_of_web_apps" int4 NOT NULL,
    "no_web_apps_last_updated" text,
    "elections" bool NOT NULL,
    "fceb" bool NOT NULL,
    "special_report" bool NOT NULL,
    "report_password" text NOT NULL,
    "child_tags" text NOT NULL,
    PRIMARY KEY ("customer_id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."web_assets" (
    "asset_uid" uuid NOT NULL,
    "asset_type" text NOT NULL,
    "asset" text NOT NULL,
    "ip_type" text,
    "verified" bool,
    "organization_uid" uuid NOT NULL,
    "asset_origin" text,
    "report_on" bool,
    "last_scanned" timestamptz,
    "report_status_reason" text,
    "data_source_uid" uuid NOT NULL,
    PRIMARY KEY ("asset_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."webpage" (
    "id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "synced_at" timestamptz,
    "last_seen" timestamptz,
    "s3_key" text,
    "url" text NOT NULL,
    "status" numeric(100,5) NOT NULL,
    "response_size" numeric(100,5),
    "headers" jsonb NOT NULL,
    "domain_id" uuid,
    "discovered_by_id" uuid,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."weekly_statuses_mdl" (
    "weekly_status_uid" uuid NOT NULL,
    "user_status" text NOT NULL,
    "key_accomplishments" text,
    "ongoing_task" text NOT NULL,
    "upcoming_task" text NOT NULL,
    "obstacles" text,
    "non_standard_meeting" text,
    "deliverables" text,
    "pto" text,
    "week_ending" date NOT NULL,
    "notes" text,
    "statusComplete" int4,
    PRIMARY KEY ("weekly_status_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_alerts_mdl" (
    "xpanse_alert_uid" uuid NOT NULL,
    "time_pulled_from_xpanse" timestamptz,
    "alert_id" text NOT NULL,
    "detection_timestamp" timestamptz,
    "alert_name" text,
    "description" text,
    "host_name" text,
    "sub_domain_id" uuid NOT NULL,
    "service_id" uuid NOT NULL,
    "alert_action" text,
    "action_pretty" text,
    "action_country" _text,
    "action_remote_port" _int4,
    "starred" bool,
    "external_id" text,
    "related_external_id" text,
    "alert_occurrence" int4,
    "severity" text,
    "matching_status" text,
    "local_insert_ts" timestamptz,
    "last_modified_ts" timestamptz,
    "case_id" int4,
    "event_timestamp" _timestamptz,
    "alert_type" text,
    "resolution_status" text,
    "resolution_comment" text,
    "tags" _text,
    "last_observed" timestamptz,
    "country_codes" _text,
    "cloud_providers" _text,
    "ipv4_addresses" _text,
    "domain_names" _text,
    "service_ids" _text,
    "website_ids" _text,
    "asset_ids" _text,
    "certificate" jsonb,
    "port_protocol" text,
    "attack_surface_rule_name" text,
    "remediation_guidance" text,
    "asset_identifiers" jsonb,
    PRIMARY KEY ("xpanse_alert_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_alerts_mdl_assets" (
    "id" int8 NOT NULL,
    "xpansealerts_id" uuid NOT NULL,
    "xpanseassetsmdl_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_alerts_mdl_business_units" (
    "id" int8 NOT NULL,
    "xpansealerts_id" uuid NOT NULL,
    "xpansebusinessunits_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_alerts_mdl_services" (
    "id" int8 NOT NULL,
    "xpansealerts_id" uuid NOT NULL,
    "xpanseservicesmdl_id" uuid NOT NULL,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_assets_mdl" (
    "xpanse_asset_uid" uuid NOT NULL,
    "asm_id" text NOT NULL,
    "asset_name" text,
    "asset_type" text,
    "last_observed" timestamptz,
    "first_observed" timestamptz,
    "externally_detected_providers" _text,
    "created" timestamptz,
    "ips" _text,
    "active_external_services_types" _text,
    "domain" text,
    "certificate_issuer" text,
    "certificate_algorithm" text,
    "certificate_classifications" _text,
    "resolves" bool,
    "top_level_asset_mapper_domain" text,
    "domain_asset_type" jsonb,
    "is_paid_level_domain" bool,
    "domain_details" jsonb,
    "dns_zone" text,
    "latest_sampled_ip" int4,
    "recent_ips" jsonb,
    "external_services" jsonb,
    "externally_inferred_vulnerability_score" numeric(5,2),
    "externally_inferred_cves" _text,
    "explainers" _text,
    "tags" _text,
    PRIMARY KEY ("xpanse_asset_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_business_units" (
    "xpanse_business_unit_uid" uuid NOT NULL,
    "entity_name" text,
    "cyhy_db_name" varchar(255),
    "state" text,
    "county" text,
    "city" text,
    "sector" text,
    "entity_type" text,
    "region" text,
    "rating" int4,
    PRIMARY KEY ("xpanse_business_unit_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_cve_services_mdl" (
    "id" int8 NOT NULL,
    "xpanse_inferred_cve_id" uuid NOT NULL,
    "xpanse_service_id" uuid NOT NULL,
    "inferred_cve_match_type" text,
    "product" text,
    "confidence" text,
    "vendor" text,
    "version_number" text,
    "activity_status" text,
    "first_observed" timestamptz,
    "last_observed" timestamptz,
    PRIMARY KEY ("id")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_cves_mdl" (
    "xpanse_cve_uid" uuid NOT NULL,
    "cve_id" text,
    "cvss_score_v2" numeric(5,2),
    "cve_severity_v2" text,
    "cvss_score_v3" numeric(5,2),
    "cve_severity_v3" text,
    PRIMARY KEY ("xpanse_cve_uid")
);

-- This script only contains the table creation statements and does not fully represent the table in the database. Do not use it as a backup.

-- Table Definition
CREATE TABLE "public"."xpanse_services_mdl" (
    "xpanse_service_uid" uuid NOT NULL,
    "service_id" text,
    "service_name" text,
    "service_type" text,
    "ip_address" _text,
    "domain" _text,
    "externally_detected_providers" _text,
    "is_active" text,
    "first_observed" timestamptz,
    "last_observed" timestamptz,
    "port" int4,
    "protocol" text,
    "active_classifications" _text,
    "inactive_classifications" _text,
    "discovery_type" text,
    "externally_inferred_vulnerability_score" numeric(5,2),
    "externally_inferred_cves" _text,
    "service_key" text,
    "service_key_type" text,
    PRIMARY KEY ("xpanse_service_uid")
);



-- Indices
CREATE INDEX alembic_version_version_num_2efbf876_like ON public.alembic_version USING btree (version_num varchar_pattern_ops);
ALTER TABLE "public"."alias" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX alias_alias_key ON public.alias USING btree (alias);
CREATE INDEX alias_organization_uid_bcc2cdb9 ON public.alias USING btree (organization_uid);
CREATE INDEX alias_alias_e67d6c6e_like ON public.alias USING btree (alias text_pattern_ops);
ALTER TABLE "public"."api_key" ADD FOREIGN KEY ("user_id") REFERENCES "public"."user"("id");


-- Indices
CREATE INDEX api_key_user_id_2b8305f7 ON public.api_key USING btree (user_id);
ALTER TABLE "public"."asset_headers" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX asset_headers_organization_uid_sub_url_8d9a71c3_uniq ON public.asset_headers USING btree (organization_uid, sub_url);
CREATE INDEX asset_headers_organization_uid_150c5556 ON public.asset_headers USING btree (organization_uid);
ALTER TABLE "public"."cidr" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX cidr_network_key ON public.cidr USING btree (network);
CREATE INDEX cidr_data_source_uid_e814595d ON public.cidr USING btree (data_source_uid);
CREATE INDEX cidr_network_83f1f4_idx ON public.cidr USING btree (network);
ALTER TABLE "public"."cidr_orgs" ADD FOREIGN KEY ("cidr_id") REFERENCES "public"."cidr"("id");
ALTER TABLE "public"."cidr_orgs" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX cidr_orgs_cidr_id_organization_id_1d58c707_uniq ON public.cidr_orgs USING btree (cidr_id, organization_id);
CREATE INDEX cidr_orgs_cidr_id_69dd8b05 ON public.cidr_orgs USING btree (cidr_id);
CREATE INDEX cidr_orgs_organization_id_b39415b6 ON public.cidr_orgs USING btree (organization_id);


-- Indices
CREATE UNIQUE INDEX cpe_name_version_vendor_a54bda44_uniq ON public.cpe USING btree (name, version, vendor);
ALTER TABLE "public"."cpe_product_mdl" ADD FOREIGN KEY ("cpe_vender_uid") REFERENCES "public"."cpe_vender"("cpe_vender_uid");


-- Indices
CREATE UNIQUE INDEX cpe_product_mdl_cpe_product_name_version_number_f8bf94e4_uniq ON public.cpe_product_mdl USING btree (cpe_product_name, version_number);
CREATE INDEX cpe_product_mdl_cpe_vender_uid_5449d117 ON public.cpe_product_mdl USING btree (cpe_vender_uid);
ALTER TABLE "public"."cpe_product_mdl_cves" ADD FOREIGN KEY ("cpeproduct_id") REFERENCES "public"."cpe_product_mdl"("cpe_product_uid");
ALTER TABLE "public"."cpe_product_mdl_cves" ADD FOREIGN KEY ("cve_id") REFERENCES "public"."cve"("id");


-- Indices
CREATE UNIQUE INDEX cpe_product_mdl_cves_cpeproduct_id_cve_id_521ae991_uniq ON public.cpe_product_mdl_cves USING btree (cpeproduct_id, cve_id);
CREATE INDEX cpe_product_mdl_cves_cpeproduct_id_6f13cbdc ON public.cpe_product_mdl_cves USING btree (cpeproduct_id);
CREATE INDEX cpe_product_mdl_cves_cve_id_04b27219 ON public.cpe_product_mdl_cves USING btree (cve_id);


-- Indices
CREATE UNIQUE INDEX cpe_vender_vender_name_key ON public.cpe_vender USING btree (vender_name);
CREATE INDEX cpe_vender_vender_name_b222af88_like ON public.cpe_vender USING btree (vender_name text_pattern_ops);
ALTER TABLE "public"."credential_breaches" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX credential_breaches_breach_name_key ON public.credential_breaches USING btree (breach_name);
CREATE INDEX credential_breaches_breach_name_abddd57e_like ON public.credential_breaches USING btree (breach_name text_pattern_ops);
CREATE INDEX credential_breaches_data_source_uid_04e85c76 ON public.credential_breaches USING btree (data_source_uid);
ALTER TABLE "public"."credential_exposures" ADD FOREIGN KEY ("sub_domain_id") REFERENCES "public"."sub_domains"("sub_domain_uid");
ALTER TABLE "public"."credential_exposures" ADD FOREIGN KEY ("credential_breaches_uid") REFERENCES "public"."credential_breaches"("credential_breaches_uid");
ALTER TABLE "public"."credential_exposures" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."credential_exposures" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX credential_exposures_breach_name_email_33cf2058_uniq ON public.credential_exposures USING btree (breach_name, email);
CREATE INDEX credential_exposures_organization_uid_12543cf9 ON public.credential_exposures USING btree (organization_uid);
CREATE INDEX credential_exposures_sub_domain_id_dbef3ddc ON public.credential_exposures USING btree (sub_domain_id);
CREATE INDEX credential_exposures_credential_breaches_uid_3b485b9f ON public.credential_exposures USING btree (credential_breaches_uid);
CREATE INDEX credential_exposures_data_source_uid_8fde1968 ON public.credential_exposures USING btree (data_source_uid);


-- Indices
CREATE UNIQUE INDEX cve_name_key ON public.cve USING btree (name);
CREATE INDEX cve_name_80440c84_like ON public.cve USING btree (name varchar_pattern_ops);
ALTER TABLE "public"."cve_cpes" ADD FOREIGN KEY ("cpe_id") REFERENCES "public"."cpe"("id");
ALTER TABLE "public"."cve_cpes" ADD FOREIGN KEY ("cve_id") REFERENCES "public"."cve"("id");


-- Indices
CREATE UNIQUE INDEX cve_cpes_cve_id_cpe_id_9833ab3e_uniq ON public.cve_cpes USING btree (cve_id, cpe_id);
CREATE INDEX cve_cpes_cve_id_bd26db06 ON public.cve_cpes USING btree (cve_id);
CREATE INDEX cve_cpes_cpe_id_4f94803a ON public.cve_cpes USING btree (cpe_id);
ALTER TABLE "public"."cyhy_contacts" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX cyhy_contacts_org_id_contact_type_email_name_92b85c52_uniq ON public.cyhy_contacts USING btree (org_id, contact_type, email, name);
CREATE INDEX cyhy_contacts_organization_uid_fb9c5353 ON public.cyhy_contacts USING btree (organization_uid);
ALTER TABLE "public"."cyhy_db_assets" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX cyhy_db_assets_org_id_network_4642b081_uniq ON public.cyhy_db_assets USING btree (org_id, network);
CREATE INDEX cyhy_db_assets_organization_uid_b2101a79 ON public.cyhy_db_assets USING btree (organization_uid);
ALTER TABLE "public"."domain_alerts" ADD FOREIGN KEY ("sub_domain_uid") REFERENCES "public"."sub_domains"("sub_domain_uid");
ALTER TABLE "public"."domain_alerts" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX domain_alerts_alert_type_sub_domain_ui_cfa006d2_uniq ON public.domain_alerts USING btree (alert_type, sub_domain_uid, date, new_value);
CREATE INDEX domain_alerts_sub_domain_uid_dbf29a19 ON public.domain_alerts USING btree (sub_domain_uid);
CREATE INDEX domain_alerts_data_source_uid_a82a17ac ON public.domain_alerts USING btree (data_source_uid);
ALTER TABLE "public"."domain_permutations" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."domain_permutations" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");
ALTER TABLE "public"."domain_permutations" ADD FOREIGN KEY ("sub_domain_uid") REFERENCES "public"."sub_domains"("sub_domain_uid");


-- Indices
CREATE UNIQUE INDEX domain_permutations_domain_permutation_organ_15048e3e_uniq ON public.domain_permutations USING btree (domain_permutation, organization_uid);
CREATE INDEX domain_permutations_organization_uid_fdfc372d ON public.domain_permutations USING btree (organization_uid);
CREATE INDEX domain_permutations_data_source_uid_da400900 ON public.domain_permutations USING btree (data_source_uid);
CREATE INDEX domain_permutations_sub_domain_uid_a236d3ba ON public.domain_permutations USING btree (sub_domain_uid);


-- Indices
CREATE UNIQUE INDEX dotgov_domains_domain_name_key ON public.dotgov_domains USING btree (domain_name);
CREATE INDEX dotgov_domains_domain_name_3e4b1316_like ON public.dotgov_domains USING btree (domain_name text_pattern_ops);
ALTER TABLE "public"."executives" ADD FOREIGN KEY ("organization") REFERENCES "public"."organization"("id");


-- Indices
CREATE INDEX executives_organization_b9920fa6 ON public.executives USING btree (organization);
ALTER TABLE "public"."host" ADD FOREIGN KEY ("ip_id") REFERENCES "public"."ip"("ip_hash");
ALTER TABLE "public"."host" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");


-- Indices
CREATE INDEX host_id_916e03f4_like ON public.host USING btree (id varchar_pattern_ops);
CREATE INDEX host_ip_id_ef54cba9 ON public.host USING btree (ip_id);
CREATE INDEX host_ip_id_ef54cba9_like ON public.host USING btree (ip_id text_pattern_ops);
CREATE INDEX host_organization_id_fbf51ac7 ON public.host USING btree (organization_id);
CREATE INDEX host_ip_stri_b105ae_idx ON public.host USING btree (ip_string);
ALTER TABLE "public"."ip" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."ip" ADD FOREIGN KEY ("origin_cidr") REFERENCES "public"."cidr"("id");


-- Indices
CREATE UNIQUE INDEX ip_ip_organization_id_61503db1_uniq ON public.ip USING btree (ip, organization_id);
CREATE INDEX ip_ip_hash_6a25c4fc_like ON public.ip USING btree (ip_hash text_pattern_ops);
CREATE INDEX ip_organization_id_241abc40 ON public.ip USING btree (organization_id);
CREATE INDEX ip_origin_cidr_f9b724e9 ON public.ip USING btree (origin_cidr);
CREATE INDEX ip_ip_d6689a_idx ON public.ip USING btree (ip, organization_id);
ALTER TABLE "public"."ips_subs" ADD FOREIGN KEY ("sub_domain_uid") REFERENCES "public"."sub_domains"("sub_domain_uid");
ALTER TABLE "public"."ips_subs" ADD FOREIGN KEY ("ip_hash") REFERENCES "public"."ip"("ip_hash");


-- Indices
CREATE UNIQUE INDEX ips_subs_ip_hash_sub_domain_uid_5775d88c_uniq ON public.ips_subs USING btree (ip_hash, sub_domain_uid);
CREATE INDEX ips_subs_ip_hash_acc23007 ON public.ips_subs USING btree (ip_hash);
CREATE INDEX ips_subs_ip_hash_acc23007_like ON public.ips_subs USING btree (ip_hash text_pattern_ops);
CREATE INDEX ips_subs_sub_domain_uid_a72948be ON public.ips_subs USING btree (sub_domain_uid);


-- Indices
CREATE UNIQUE INDEX location_gnis_id_key ON public.location USING btree (gnis_id);
CREATE INDEX location_gnis_id_f0601589_like ON public.location USING btree (gnis_id varchar_pattern_ops);
CREATE INDEX location_gnis_id_845f5b_idx ON public.location USING btree (gnis_id);
ALTER TABLE "public"."mentions" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");
ALTER TABLE "public"."mentions" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX mentions_sixgill_mention_id_key ON public.mentions USING btree (sixgill_mention_id);
CREATE INDEX mentions_sixgill_mention_id_fad7df53_like ON public.mentions USING btree (sixgill_mention_id text_pattern_ops);
CREATE INDEX mentions_organization_uid_b7fececb ON public.mentions USING btree (organization_uid);
CREATE INDEX mentions_data_source_uid_5c5f8bf8 ON public.mentions USING btree (data_source_uid);


-- Indices
CREATE UNIQUE INDEX org_id_map_cyhy_id_pe_org_id_b580d6d5_uniq ON public.org_id_map USING btree (cyhy_id, pe_org_id);
ALTER TABLE "public"."organization" ADD FOREIGN KEY ("parent_id") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."organization" ADD FOREIGN KEY ("created_by_id") REFERENCES "public"."user"("id");
ALTER TABLE "public"."organization" ADD FOREIGN KEY ("org_type_id") REFERENCES "public"."org_type"("org_type_uid");
ALTER TABLE "public"."organization" ADD FOREIGN KEY ("location_id") REFERENCES "public"."location"("id");


-- Indices
CREATE UNIQUE INDEX organization_acronym_key ON public.organization USING btree (acronym);
CREATE INDEX organization_acronym_97d5f7cb_like ON public.organization USING btree (acronym varchar_pattern_ops);
CREATE INDEX organization_location_id_067f8a89 ON public.organization USING btree (location_id);
CREATE INDEX organization_parent_id_981c8191 ON public.organization USING btree (parent_id);
CREATE INDEX organization_created_by_id_35551e36 ON public.organization USING btree (created_by_id);
CREATE INDEX organization_org_type_id_9d510ee1 ON public.organization USING btree (org_type_id);


-- Indices
CREATE UNIQUE INDEX organization_tag_name_key ON public.organization_tag USING btree (name);
CREATE INDEX organization_tag_name_7322d41a_like ON public.organization_tag USING btree (name varchar_pattern_ops);
ALTER TABLE "public"."organization_tag_organization" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."organization_tag_organization" ADD FOREIGN KEY ("organizationtag_id") REFERENCES "public"."organization_tag"("id");


-- Indices
CREATE UNIQUE INDEX organization_tag_organiz_organizationtag_id_organ_80ba4ec6_uniq ON public.organization_tag_organization USING btree (organizationtag_id, organization_id);
CREATE INDEX organization_tag_organization_organizationtag_id_2a848187 ON public.organization_tag_organization USING btree (organizationtag_id);
CREATE INDEX organization_tag_organization_organization_id_dcb828c9 ON public.organization_tag_organization USING btree (organization_id);
ALTER TABLE "public"."pe_report_summary_stats" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX pe_report_summary_stats_organization_uid_start_d_66dd3af0_uniq ON public.pe_report_summary_stats USING btree (organization_uid, start_date);
CREATE INDEX pe_report_summary_stats_organization_uid_7704a098 ON public.pe_report_summary_stats USING btree (organization_uid);


-- Indices
CREATE UNIQUE INDEX pe_users_email_key ON public.pe_users USING btree (email);
CREATE UNIQUE INDEX pe_users_username_key ON public.pe_users USING btree (username);
CREATE UNIQUE INDEX pe_users_api_key_key ON public.pe_users USING btree (api_key);
CREATE INDEX pe_users_email_6df55e0f_like ON public.pe_users USING btree (email varchar_pattern_ops);
CREATE INDEX pe_users_username_f4890452_like ON public.pe_users USING btree (username varchar_pattern_ops);
CREATE INDEX pe_users_api_key_82aa3c4a_like ON public.pe_users USING btree (api_key varchar_pattern_ops);
ALTER TABLE "public"."port_scan" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."port_scan" ADD FOREIGN KEY ("ip_id") REFERENCES "public"."ip"("ip_hash");


-- Indices
CREATE INDEX port_scan_id_8962dfc6_like ON public.port_scan USING btree (id varchar_pattern_ops);
CREATE INDEX port_scan_ip_id_5ac3d203 ON public.port_scan USING btree (ip_id);
CREATE INDEX port_scan_ip_id_5ac3d203_like ON public.port_scan USING btree (ip_id text_pattern_ops);
CREATE INDEX port_scan_organization_id_7a457e61 ON public.port_scan USING btree (organization_id);
ALTER TABLE "public"."pshtt_results" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."pshtt_results" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX pshtt_results_organization_uid_sub_domain_81ce555c_uniq ON public.pshtt_results USING btree (organization_uid, sub_domain);
CREATE INDEX pshtt_results_organization_uid_58ebe095 ON public.pshtt_results USING btree (organization_uid);
CREATE INDEX pshtt_results_data_source_uid_59849107 ON public.pshtt_results USING btree (data_source_uid);
ALTER TABLE "public"."role" ADD FOREIGN KEY ("user_id") REFERENCES "public"."user"("id");
ALTER TABLE "public"."role" ADD FOREIGN KEY ("created_by_id") REFERENCES "public"."user"("id");
ALTER TABLE "public"."role" ADD FOREIGN KEY ("approved_by_id") REFERENCES "public"."user"("id");
ALTER TABLE "public"."role" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX role_user_id_organization_id_3c3ad6d7_uniq ON public.role USING btree (user_id, organization_id);
CREATE INDEX role_created_by_id_bffd5752 ON public.role USING btree (created_by_id);
CREATE INDEX role_approved_by_id_27a41bea ON public.role USING btree (approved_by_id);
CREATE INDEX role_user_id_8cace677 ON public.role USING btree (user_id);
CREATE INDEX role_organization_id_d00f912a ON public.role USING btree (organization_id);
ALTER TABLE "public"."saved_search" ADD FOREIGN KEY ("created_by_id") REFERENCES "public"."user"("id");


-- Indices
CREATE INDEX saved_search_created_by_id_f29cf571 ON public.saved_search USING btree (created_by_id);
ALTER TABLE "public"."scan" ADD FOREIGN KEY ("created_by") REFERENCES "public"."user"("id");


-- Indices
CREATE INDEX scan_created_by_e45cf6fe ON public.scan USING btree (created_by);
ALTER TABLE "public"."scan_organization_tags" ADD FOREIGN KEY ("scan_id") REFERENCES "public"."scan"("id");
ALTER TABLE "public"."scan_organization_tags" ADD FOREIGN KEY ("organizationtag_id") REFERENCES "public"."organization_tag"("id");


-- Indices
CREATE UNIQUE INDEX scan_organization_tags_scan_id_organizationtag_id_593ecf52_uniq ON public.scan_organization_tags USING btree (scan_id, organizationtag_id);
CREATE INDEX scan_organization_tags_scan_id_6cc5e82b ON public.scan_organization_tags USING btree (scan_id);
CREATE INDEX scan_organization_tags_organizationtag_id_1beaa19c ON public.scan_organization_tags USING btree (organizationtag_id);
ALTER TABLE "public"."scan_organizations" ADD FOREIGN KEY ("scan_id") REFERENCES "public"."scan"("id");
ALTER TABLE "public"."scan_organizations" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX scan_organizations_scan_id_organization_id_fed32cfc_uniq ON public.scan_organizations USING btree (scan_id, organization_id);
CREATE INDEX scan_organizations_scan_id_f6f0b182 ON public.scan_organizations USING btree (scan_id);
CREATE INDEX scan_organizations_organization_id_2e852548 ON public.scan_organizations USING btree (organization_id);
ALTER TABLE "public"."scan_task" ADD FOREIGN KEY ("scan_id") REFERENCES "public"."scan"("id");


-- Indices
CREATE INDEX scan_task_scan_id_be503edb ON public.scan_task USING btree (scan_id);
ALTER TABLE "public"."scan_task_organizations" ADD FOREIGN KEY ("scantask_id") REFERENCES "public"."scan_task"("id");
ALTER TABLE "public"."scan_task_organizations" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX scan_task_organizations_scantask_id_organization_4eb2f5da_uniq ON public.scan_task_organizations USING btree (scantask_id, organization_id);
CREATE INDEX scan_task_organizations_scantask_id_419be1f3 ON public.scan_task_organizations USING btree (scantask_id);
CREATE INDEX scan_task_organizations_organization_id_c23384d4 ON public.scan_task_organizations USING btree (organization_id);


-- Indices
CREATE UNIQUE INDEX sector_acronym_key ON public.sector USING btree (acronym);
CREATE INDEX sector_acronym_34564b0a_like ON public.sector USING btree (acronym varchar_pattern_ops);
CREATE INDEX sector_acronym_fd7c14_idx ON public.sector USING btree (acronym);
ALTER TABLE "public"."sector_organizations" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."sector_organizations" ADD FOREIGN KEY ("sector_id") REFERENCES "public"."sector"("id");


-- Indices
CREATE UNIQUE INDEX sector_organizations_sector_id_organization_id_c9a51e0f_uniq ON public.sector_organizations USING btree (sector_id, organization_id);
CREATE INDEX sector_organizations_sector_id_dc248e70 ON public.sector_organizations USING btree (sector_id);
CREATE INDEX sector_organizations_organization_id_a28a5990 ON public.sector_organizations USING btree (organization_id);
ALTER TABLE "public"."service" ADD FOREIGN KEY ("discovered_by_id") REFERENCES "public"."scan"("id");
ALTER TABLE "public"."service" ADD FOREIGN KEY ("domain_id") REFERENCES "public"."sub_domains"("sub_domain_uid");


-- Indices
CREATE UNIQUE INDEX service_port_domain_id_e8df5226_uniq ON public.service USING btree (port, domain_id);
CREATE INDEX service_domain_id_ed507973 ON public.service USING btree (domain_id);
CREATE INDEX service_discovered_by_id_5b0c28e9 ON public.service USING btree (discovered_by_id);
ALTER TABLE "public"."shodan_assets" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."shodan_assets" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX shodan_assets_organization_uid_ip_port_89ec08ba_uniq ON public.shodan_assets USING btree (organization_uid, ip, port, protocol, "timestamp");
CREATE INDEX shodan_assets_organization_uid_76cda450 ON public.shodan_assets USING btree (organization_uid);
CREATE INDEX shodan_assets_data_source_uid_acd993ab ON public.shodan_assets USING btree (data_source_uid);
ALTER TABLE "public"."shodan_vulns" ADD FOREIGN KEY ("service_id") REFERENCES "public"."service"("id");
ALTER TABLE "public"."shodan_vulns" ADD FOREIGN KEY ("sub_domain_id") REFERENCES "public"."sub_domains"("sub_domain_uid");
ALTER TABLE "public"."shodan_vulns" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");
ALTER TABLE "public"."shodan_vulns" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");


-- Indices
CREATE UNIQUE INDEX shodan_vulns_organization_uid_ip_port_f9b33bbc_uniq ON public.shodan_vulns USING btree (organization_uid, ip, port, protocol, "timestamp");
CREATE INDEX shodan_vulns_organization_uid_b2be941d ON public.shodan_vulns USING btree (organization_uid);
CREATE INDEX shodan_vulns_data_source_uid_866c5b81 ON public.shodan_vulns USING btree (data_source_uid);
CREATE INDEX shodan_vulns_sub_domain_id_c5bd32eb ON public.shodan_vulns USING btree (sub_domain_id);
CREATE INDEX shodan_vulns_service_id_1c0e4791 ON public.shodan_vulns USING btree (service_id);
ALTER TABLE "public"."sixgill_alerts" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."sixgill_alerts" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX sixgill_alerts_sixgill_id_key ON public.sixgill_alerts USING btree (sixgill_id);
CREATE INDEX sixgill_alerts_sixgill_id_413b716f_like ON public.sixgill_alerts USING btree (sixgill_id text_pattern_ops);
CREATE INDEX sixgill_alerts_organization_uid_69a4a171 ON public.sixgill_alerts USING btree (organization_uid);
CREATE INDEX sixgill_alerts_data_source_uid_be876b69 ON public.sixgill_alerts USING btree (data_source_uid);
ALTER TABLE "public"."sub_domains" ADD FOREIGN KEY ("dns_record_uid") REFERENCES "public"."dns_records"("dns_record_uid");
ALTER TABLE "public"."sub_domains" ADD FOREIGN KEY ("root_domain_id") REFERENCES "public"."sub_domains"("sub_domain_uid");
ALTER TABLE "public"."sub_domains" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."sub_domains" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX sub_domains_sub_domain_organization_uid_b833160e_uniq ON public.sub_domains USING btree (sub_domain, organization_uid);
CREATE INDEX sub_domains_root_domain_id_a1b1be2c ON public.sub_domains USING btree (root_domain_id);
CREATE INDEX sub_domains_data_source_uid_6fd21634 ON public.sub_domains USING btree (data_source_uid);
CREATE INDEX sub_domains_dns_record_uid_1e70b745 ON public.sub_domains USING btree (dns_record_uid);
CREATE INDEX sub_domains_organization_uid_abe259f1 ON public.sub_domains USING btree (organization_uid);
ALTER TABLE "public"."ticket" ADD FOREIGN KEY ("ip_id") REFERENCES "public"."ip"("ip_hash");
ALTER TABLE "public"."ticket" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."ticket" ADD FOREIGN KEY ("cve_id") REFERENCES "public"."cve"("id");


-- Indices
CREATE UNIQUE INDEX ticket_id_1f17c5d6_uniq ON public.ticket USING btree (id);
CREATE INDEX ticket_id_1f17c5d6_like ON public.ticket USING btree (id varchar_pattern_ops);
CREATE INDEX ticket_cve_id_cd0dbbf5 ON public.ticket USING btree (cve_id);
CREATE INDEX ticket_ip_id_3aa822df ON public.ticket USING btree (ip_id);
CREATE INDEX ticket_ip_id_3aa822df_like ON public.ticket USING btree (ip_id text_pattern_ops);
CREATE INDEX ticket_organization_id_3759c8ee ON public.ticket USING btree (organization_id);
ALTER TABLE "public"."ticket_event" ADD FOREIGN KEY ("vuln_scan_id") REFERENCES "public"."vuln_scan"("id");
ALTER TABLE "public"."ticket_event" ADD FOREIGN KEY ("ticket_id") REFERENCES "public"."ticket"("id");


-- Indices
CREATE UNIQUE INDEX ticket_event_event_timestamp_ticket_id_action_d1d6974d_uniq ON public.ticket_event USING btree (event_timestamp, ticket_id, action);
CREATE INDEX ticket_event_vuln_scan_id_7f408339 ON public.ticket_event USING btree (vuln_scan_id);
CREATE INDEX ticket_event_vuln_scan_id_7f408339_like ON public.ticket_event USING btree (vuln_scan_id varchar_pattern_ops);
CREATE INDEX ticket_event_ticket_id_0244b672 ON public.ticket_event USING btree (ticket_id);
CREATE INDEX ticket_event_ticket_id_0244b672_like ON public.ticket_event USING btree (ticket_id varchar_pattern_ops);
ALTER TABLE "public"."top_cves" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX top_cves_cve_id_date_7fa6a474_uniq ON public.top_cves USING btree (cve_id, date);
CREATE INDEX top_cves_data_source_uid_753ec315 ON public.top_cves USING btree (data_source_uid);


-- Indices
CREATE UNIQUE INDEX user_cognito_id_key ON public."user" USING btree (cognito_id);
CREATE UNIQUE INDEX user_login_gov_id_key ON public."user" USING btree (login_gov_id);
CREATE UNIQUE INDEX user_email_key ON public."user" USING btree (email);
CREATE UNIQUE INDEX user_okta_id_key ON public."user" USING btree (okta_id);
CREATE INDEX user_cognito_id_ce85a480_like ON public."user" USING btree (cognito_id varchar_pattern_ops);
CREATE INDEX user_login_gov_id_2dc4e9fb_like ON public."user" USING btree (login_gov_id varchar_pattern_ops);
CREATE INDEX user_email_54dc62b2_like ON public."user" USING btree (email varchar_pattern_ops);
CREATE INDEX user_okta_id_144466d2_like ON public."user" USING btree (okta_id varchar_pattern_ops);
ALTER TABLE "public"."vuln_scan" ADD FOREIGN KEY ("cve_id") REFERENCES "public"."cve"("id");
ALTER TABLE "public"."vuln_scan" ADD FOREIGN KEY ("ip_id") REFERENCES "public"."ip"("ip_hash");
ALTER TABLE "public"."vuln_scan" ADD FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id");


-- Indices
CREATE INDEX vuln_scan_id_b81c7bc7_like ON public.vuln_scan USING btree (id varchar_pattern_ops);
CREATE INDEX vuln_scan_cve_id_4896d862 ON public.vuln_scan USING btree (cve_id);
CREATE INDEX vuln_scan_ip_id_e258bfca ON public.vuln_scan USING btree (ip_id);
CREATE INDEX vuln_scan_ip_id_e258bfca_like ON public.vuln_scan USING btree (ip_id text_pattern_ops);
CREATE INDEX vuln_scan_organization_id_7462dba8 ON public.vuln_scan USING btree (organization_id);
ALTER TABLE "public"."vulnerability" ADD FOREIGN KEY ("service_id") REFERENCES "public"."service"("id");
ALTER TABLE "public"."vulnerability" ADD FOREIGN KEY ("domain_id") REFERENCES "public"."sub_domains"("sub_domain_uid");


-- Indices
CREATE UNIQUE INDEX vulnerability_domain_id_title_9d86fe67_uniq ON public.vulnerability USING btree (domain_id, title);
CREATE INDEX vulnerability_domain_id_396cdcf6 ON public.vulnerability USING btree (domain_id);
CREATE INDEX vulnerability_service_id_6cb061d7 ON public.vulnerability USING btree (service_id);
ALTER TABLE "public"."was_findings" ADD FOREIGN KEY ("service_id") REFERENCES "public"."service"("id");
ALTER TABLE "public"."was_findings" ADD FOREIGN KEY ("sub_domain_id") REFERENCES "public"."sub_domains"("sub_domain_uid");


-- Indices
CREATE INDEX was_findings_sub_domain_id_767ad314 ON public.was_findings USING btree (sub_domain_id);
CREATE INDEX was_findings_service_id_ce7e7f14 ON public.was_findings USING btree (service_id);


-- Indices
CREATE UNIQUE INDEX was_history_was_org_id_date_scanned_8cf982b2_uniq ON public.was_history USING btree (was_org_id, date_scanned);


-- Indices
CREATE INDEX was_map_was_org_id_be6a736e_like ON public.was_map USING btree (was_org_id text_pattern_ops);


-- Indices
CREATE UNIQUE INDEX was_report_last_scan_date_org_was_acronym_5e5468bb_uniq ON public.was_report USING btree (last_scan_date, org_was_acronym);
ALTER TABLE "public"."web_assets" ADD FOREIGN KEY ("organization_uid") REFERENCES "public"."organization"("id");
ALTER TABLE "public"."web_assets" ADD FOREIGN KEY ("data_source_uid") REFERENCES "public"."data_source"("data_source_uid");


-- Indices
CREATE UNIQUE INDEX web_assets_asset_organization_uid_ed3b9b8a_uniq ON public.web_assets USING btree (asset, organization_uid);
CREATE INDEX web_assets_organization_uid_5893b6b0 ON public.web_assets USING btree (organization_uid);
CREATE INDEX web_assets_data_source_uid_716854de ON public.web_assets USING btree (data_source_uid);
ALTER TABLE "public"."webpage" ADD FOREIGN KEY ("domain_id") REFERENCES "public"."sub_domains"("sub_domain_uid");
ALTER TABLE "public"."webpage" ADD FOREIGN KEY ("discovered_by_id") REFERENCES "public"."scan"("id");


-- Indices
CREATE UNIQUE INDEX webpage_url_domain_id_81a87e5f_uniq ON public.webpage USING btree (url, domain_id);
CREATE INDEX webpage_domain_id_59407f86 ON public.webpage USING btree (domain_id);
CREATE INDEX webpage_discovered_by_id_d7969e8a ON public.webpage USING btree (discovered_by_id);
ALTER TABLE "public"."xpanse_alerts_mdl" ADD FOREIGN KEY ("sub_domain_id") REFERENCES "public"."sub_domains"("sub_domain_uid");
ALTER TABLE "public"."xpanse_alerts_mdl" ADD FOREIGN KEY ("service_id") REFERENCES "public"."service"("id");


-- Indices
CREATE UNIQUE INDEX xpanse_alerts_mdl_alert_id_key ON public.xpanse_alerts_mdl USING btree (alert_id);
CREATE INDEX xpanse_alerts_mdl_alert_id_7b6bc051_like ON public.xpanse_alerts_mdl USING btree (alert_id text_pattern_ops);
CREATE INDEX xpanse_alerts_mdl_sub_domain_id_9788fe05 ON public.xpanse_alerts_mdl USING btree (sub_domain_id);
CREATE INDEX xpanse_alerts_mdl_service_id_c15e6842 ON public.xpanse_alerts_mdl USING btree (service_id);
ALTER TABLE "public"."xpanse_alerts_mdl_assets" ADD FOREIGN KEY ("xpansealerts_id") REFERENCES "public"."xpanse_alerts_mdl"("xpanse_alert_uid");
ALTER TABLE "public"."xpanse_alerts_mdl_assets" ADD FOREIGN KEY ("xpanseassetsmdl_id") REFERENCES "public"."xpanse_assets_mdl"("xpanse_asset_uid");


-- Indices
CREATE UNIQUE INDEX xpanse_alerts_mdl_assets_xpansealerts_id_xpanseas_b0e56dc1_uniq ON public.xpanse_alerts_mdl_assets USING btree (xpansealerts_id, xpanseassetsmdl_id);
CREATE INDEX xpanse_alerts_mdl_assets_xpansealerts_id_b8d2b7f7 ON public.xpanse_alerts_mdl_assets USING btree (xpansealerts_id);
CREATE INDEX xpanse_alerts_mdl_assets_xpanseassetsmdl_id_551795c3 ON public.xpanse_alerts_mdl_assets USING btree (xpanseassetsmdl_id);
ALTER TABLE "public"."xpanse_alerts_mdl_business_units" ADD FOREIGN KEY ("xpansealerts_id") REFERENCES "public"."xpanse_alerts_mdl"("xpanse_alert_uid");
ALTER TABLE "public"."xpanse_alerts_mdl_business_units" ADD FOREIGN KEY ("xpansebusinessunits_id") REFERENCES "public"."xpanse_business_units"("xpanse_business_unit_uid");


-- Indices
CREATE UNIQUE INDEX xpanse_alerts_mdl_busine_xpansealerts_id_xpansebu_8d3090a9_uniq ON public.xpanse_alerts_mdl_business_units USING btree (xpansealerts_id, xpansebusinessunits_id);
CREATE INDEX xpanse_alerts_mdl_business_units_xpansealerts_id_c7cdac35 ON public.xpanse_alerts_mdl_business_units USING btree (xpansealerts_id);
CREATE INDEX xpanse_alerts_mdl_business_xpansebusinessunits_id_90fd8627 ON public.xpanse_alerts_mdl_business_units USING btree (xpansebusinessunits_id);
ALTER TABLE "public"."xpanse_alerts_mdl_services" ADD FOREIGN KEY ("xpansealerts_id") REFERENCES "public"."xpanse_alerts_mdl"("xpanse_alert_uid");
ALTER TABLE "public"."xpanse_alerts_mdl_services" ADD FOREIGN KEY ("xpanseservicesmdl_id") REFERENCES "public"."xpanse_services_mdl"("xpanse_service_uid");


-- Indices
CREATE UNIQUE INDEX xpanse_alerts_mdl_servic_xpansealerts_id_xpansese_03c93d63_uniq ON public.xpanse_alerts_mdl_services USING btree (xpansealerts_id, xpanseservicesmdl_id);
CREATE INDEX xpanse_alerts_mdl_services_xpansealerts_id_65bfcebc ON public.xpanse_alerts_mdl_services USING btree (xpansealerts_id);
CREATE INDEX xpanse_alerts_mdl_services_xpanseservicesmdl_id_0da6657e ON public.xpanse_alerts_mdl_services USING btree (xpanseservicesmdl_id);


-- Indices
CREATE UNIQUE INDEX xpanse_assets_mdl_asm_id_key ON public.xpanse_assets_mdl USING btree (asm_id);
CREATE INDEX xpanse_assets_mdl_asm_id_f3e3f4d1_like ON public.xpanse_assets_mdl USING btree (asm_id text_pattern_ops);
ALTER TABLE "public"."xpanse_business_units" ADD FOREIGN KEY ("cyhy_db_name") REFERENCES "public"."organization"("acronym");


-- Indices
CREATE UNIQUE INDEX xpanse_business_units_entity_name_key ON public.xpanse_business_units USING btree (entity_name);
CREATE INDEX xpanse_business_units_entity_name_91b35a02_like ON public.xpanse_business_units USING btree (entity_name text_pattern_ops);
CREATE INDEX xpanse_business_units_cyhy_db_name_76db20e6 ON public.xpanse_business_units USING btree (cyhy_db_name);
CREATE INDEX xpanse_business_units_cyhy_db_name_76db20e6_like ON public.xpanse_business_units USING btree (cyhy_db_name varchar_pattern_ops);
ALTER TABLE "public"."xpanse_cve_services_mdl" ADD FOREIGN KEY ("xpanse_service_id") REFERENCES "public"."xpanse_services_mdl"("xpanse_service_uid");
ALTER TABLE "public"."xpanse_cve_services_mdl" ADD FOREIGN KEY ("xpanse_inferred_cve_id") REFERENCES "public"."xpanse_cves_mdl"("xpanse_cve_uid");


-- Indices
CREATE UNIQUE INDEX xpanse_cve_services_mdl_xpanse_inferred_cve_id_x_99a754b9_uniq ON public.xpanse_cve_services_mdl USING btree (xpanse_inferred_cve_id, xpanse_service_id);
CREATE INDEX xpanse_cve_services_mdl_xpanse_inferred_cve_id_dcd2d4fe ON public.xpanse_cve_services_mdl USING btree (xpanse_inferred_cve_id);
CREATE INDEX xpanse_cve_services_mdl_xpanse_service_id_fafe4f16 ON public.xpanse_cve_services_mdl USING btree (xpanse_service_id);


-- Indices
CREATE UNIQUE INDEX xpanse_cves_mdl_cve_id_key ON public.xpanse_cves_mdl USING btree (cve_id);
CREATE INDEX xpanse_cves_mdl_cve_id_afd3dc4b_like ON public.xpanse_cves_mdl USING btree (cve_id text_pattern_ops);


-- Indices
CREATE UNIQUE INDEX xpanse_services_mdl_service_id_key ON public.xpanse_services_mdl USING btree (service_id);
CREATE INDEX xpanse_services_mdl_service_id_12ceccc0_like ON public.xpanse_services_mdl USING btree (service_id text_pattern_ops);

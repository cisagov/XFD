--
-- PostgreSQL database dump
-- 07/28/2026
--
-- DROP SCHEMA public;

CREATE SCHEMA public AUTHORIZATION crossfeed;

COMMENT ON SCHEMA public IS 'standard public schema';

-- DROP SEQUENCE public.auth_group_id_seq;

CREATE SEQUENCE public.auth_group_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.auth_group_permissions_id_seq;

CREATE SEQUENCE public.auth_group_permissions_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.auth_permission_id_seq;

CREATE SEQUENCE public.auth_permission_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.auth_user_groups_id_seq;

CREATE SEQUENCE public.auth_user_groups_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.auth_user_id_seq;

CREATE SEQUENCE public.auth_user_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.auth_user_user_permissions_id_seq;

CREATE SEQUENCE public.auth_user_user_permissions_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.cpe_product_cves_id_seq;

CREATE SEQUENCE public.cpe_product_cves_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public."dataAPI_apiuser_id_seq";

CREATE SEQUENCE public."dataAPI_apiuser_id_seq"
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.django_admin_log_id_seq;

CREATE SEQUENCE public.django_admin_log_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.django_celery_beat_clockedschedule_id_seq;

CREATE SEQUENCE public.django_celery_beat_clockedschedule_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.django_celery_beat_crontabschedule_id_seq;

CREATE SEQUENCE public.django_celery_beat_crontabschedule_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.django_celery_beat_intervalschedule_id_seq;

CREATE SEQUENCE public.django_celery_beat_intervalschedule_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.django_celery_beat_periodictask_id_seq;

CREATE SEQUENCE public.django_celery_beat_periodictask_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.django_celery_beat_solarschedule_id_seq;

CREATE SEQUENCE public.django_celery_beat_solarschedule_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.django_content_type_id_seq;

CREATE SEQUENCE public.django_content_type_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.django_migrations_id_seq;

CREATE SEQUENCE public.django_migrations_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.was_report_id_seq;

CREATE SEQUENCE public.was_report_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.xpanse_alerts_assets_id_seq;

CREATE SEQUENCE public.xpanse_alerts_assets_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.xpanse_alerts_business_units_id_seq;

CREATE SEQUENCE public.xpanse_alerts_business_units_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.xpanse_alerts_services_id_seq;

CREATE SEQUENCE public.xpanse_alerts_services_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.xpanse_cve_services_id_seq;

CREATE SEQUENCE public.xpanse_cve_services_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;-- public."Users" definition

-- Drop table

-- DROP TABLE public."Users";

CREATE TABLE public."Users" (
	id uuid NOT NULL,
	email varchar(64) NULL,
	username varchar(64) NULL,
	"admin" int4 NULL,
	"role" int4 NULL,
	password_hash varchar(128) NULL,
	api_key varchar(128) NULL,
	CONSTRAINT "Users_api_key_key" UNIQUE (api_key),
	CONSTRAINT "Users_pkey" PRIMARY KEY (id)
);
CREATE UNIQUE INDEX "ix_Users_email" ON public."Users" USING btree (email);
CREATE UNIQUE INDEX "ix_Users_username" ON public."Users" USING btree (username);


-- public.alembic_version definition

-- Drop table

-- DROP TABLE public.alembic_version;

CREATE TABLE public.alembic_version (
	version_num varchar(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);


-- public.asset_headers definition

-- Drop table

-- DROP TABLE public.asset_headers;

CREATE TABLE public.asset_headers (
	"_id" uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	sub_url text NOT NULL,
	tech_detected _text NOT NULL,
	interesting_header _text NOT NULL,
	ssl2 _text NULL,
	tls1 _text NULL,
	certificate json NULL,
	scanned bool NULL,
	ssl_scanned bool NULL,
	CONSTRAINT asset_headers_organizations_uid_sub_url_key UNIQUE (organizations_uid, sub_url),
	CONSTRAINT asset_headers_pkey PRIMARY KEY (_id)
);


-- public.auth_group definition

-- Drop table

-- DROP TABLE public.auth_group;

CREATE TABLE public.auth_group (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"name" varchar(150) NOT NULL,
	CONSTRAINT auth_group_name_key UNIQUE (name),
	CONSTRAINT auth_group_pkey PRIMARY KEY (id)
);
CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


-- public.auth_user definition

-- Drop table

-- DROP TABLE public.auth_user;

CREATE TABLE public.auth_user (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"password" varchar(128) NOT NULL,
	last_login timestamptz NULL,
	is_superuser bool NOT NULL,
	username varchar(150) NOT NULL,
	first_name varchar(150) NOT NULL,
	last_name varchar(150) NOT NULL,
	email varchar(254) NOT NULL,
	is_staff bool NOT NULL,
	is_active bool NOT NULL,
	date_joined timestamptz NOT NULL,
	CONSTRAINT auth_user_pkey PRIMARY KEY (id),
	CONSTRAINT auth_user_username_key UNIQUE (username)
);
CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


-- public.blocklist definition

-- Drop table

-- DROP TABLE public.blocklist;

CREATE TABLE public.blocklist (
	blocklist_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	ip inet NOT NULL,
	created_at timestamp NULL,
	updated_at timestamp NULL,
	malicious bool DEFAULT false NULL,
	attacks int8 NULL,
	reports int8 NULL,
	CONSTRAINT blocklist_pkey PRIMARY KEY (blocklist_uid)
);


-- public.cpe_vender definition

-- Drop table

-- DROP TABLE public.cpe_vender;

CREATE TABLE public.cpe_vender (
	cpe_vender_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	vender_name text NULL,
	CONSTRAINT cpe_vender_pkey PRIMARY KEY (cpe_vender_uid),
	CONSTRAINT vender_name_key UNIQUE (vender_name)
);


-- public.cve_info definition

-- Drop table

-- DROP TABLE public.cve_info;

CREATE TABLE public.cve_info (
	cve_uuid uuid DEFAULT uuid_generate_v1() NOT NULL,
	cve_name text NULL,
	cvss_2_0 numeric NULL,
	cvss_2_0_severity text NULL,
	cvss_2_0_vector text NULL,
	cvss_3_0 numeric NULL,
	cvss_3_0_severity text NULL,
	cvss_3_0_vector text NULL,
	dve_score numeric NULL,
	CONSTRAINT cve_info_pkey PRIMARY KEY (cve_uuid),
	CONSTRAINT cve_name_key UNIQUE (cve_name)
);
COMMENT ON TABLE public.cve_info IS 'Table that holds all known CVEs and their associated CVSS 2.0/3.0/DVE info';


-- public.cves definition

-- Drop table

-- DROP TABLE public.cves;

CREATE TABLE public.cves (
	cve_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	cve_name text NULL,
	published_date timestamp NULL,
	last_modified_date timestamp NULL,
	vuln_status text NULL,
	description text NULL,
	cvss_v2_source text NULL,
	cvss_v2_type text NULL,
	cvss_v2_version text NULL,
	cvss_v2_vector_string text NULL,
	cvss_v2_base_score numeric NULL,
	cvss_v2_base_severity text NULL,
	cvss_v2_exploitability_score numeric NULL,
	cvss_v2_impact_score numeric NULL,
	cvss_v3_source text NULL,
	cvss_v3_type text NULL,
	cvss_v3_version text NULL,
	cvss_v3_vector_string text NULL,
	cvss_v3_base_score numeric NULL,
	cvss_v3_base_severity text NULL,
	cvss_v3_exploitability_score numeric NULL,
	cvss_v3_impact_score numeric NULL,
	cvss_v4_source text NULL,
	cvss_v4_type text NULL,
	cvss_v4_version text NULL,
	cvss_v4_vector_string text NULL,
	cvss_v4_base_score numeric NULL,
	cvss_v4_base_severity text NULL,
	cvss_v4_exploitability_score numeric NULL,
	cvss_v4_impact_score numeric NULL,
	weaknesses _text NULL,
	reference_urls _text NULL,
	cpe_list _text NULL,
	CONSTRAINT cve_pkey PRIMARY KEY (cve_uid),
	CONSTRAINT unique_cve_name UNIQUE (cve_name)
);


-- public.cyhy_contacts definition

-- Drop table

-- DROP TABLE public.cyhy_contacts;

CREATE TABLE public.cyhy_contacts (
	"_id" uuid DEFAULT uuid_generate_v1() NOT NULL,
	org_id text NOT NULL,
	org_name text NOT NULL,
	phone text NULL,
	contact_type text NOT NULL,
	email text NULL,
	"name" text NULL,
	date_pulled date NULL,
	CONSTRAINT cyhy_contacts_org_id_contact_type_email_name_key UNIQUE (org_id, contact_type, email, name),
	CONSTRAINT cyhy_contacts_pkey PRIMARY KEY (_id)
);


-- public.cyhy_db_assets definition

-- Drop table

-- DROP TABLE public.cyhy_db_assets;

CREATE TABLE public.cyhy_db_assets (
	"_id" uuid DEFAULT uuid_generate_v1() NOT NULL,
	org_id text NULL,
	org_name text NULL,
	contact text NULL,
	network inet NULL,
	"type" text NULL,
	first_seen date NULL,
	last_seen date NULL,
	currently_in_cyhy bool NULL,
	CONSTRAINT cyhy_db_assets_pkey PRIMARY KEY (_id),
	CONSTRAINT cyhy_db_assets_unique_constraint UNIQUE (org_id, network)
);


-- public.cyhy_kevs definition

-- Drop table

-- DROP TABLE public.cyhy_kevs;

CREATE TABLE public.cyhy_kevs (
	cyhy_kevs_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	kev text NULL,
	first_seen date NULL,
	last_seen date NULL,
	CONSTRAINT cyhy_kevd_uid_pkey PRIMARY KEY (cyhy_kevs_uid),
	CONSTRAINT unique_cyhy_kevs UNIQUE (kev)
);


-- public.data_source definition

-- Drop table

-- DROP TABLE public.data_source;

CREATE TABLE public.data_source (
	data_source_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	"name" text NOT NULL,
	description text NOT NULL,
	last_run date NOT NULL,
	CONSTRAINT data_source_pkey PRIMARY KEY (data_source_uid)
);


-- public.django_celery_beat_clockedschedule definition

-- Drop table

-- DROP TABLE public.django_celery_beat_clockedschedule;

CREATE TABLE public.django_celery_beat_clockedschedule (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	clocked_time timestamptz NOT NULL,
	CONSTRAINT django_celery_beat_clockedschedule_pkey PRIMARY KEY (id)
);


-- public.django_celery_beat_crontabschedule definition

-- Drop table

-- DROP TABLE public.django_celery_beat_crontabschedule;

CREATE TABLE public.django_celery_beat_crontabschedule (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"minute" varchar(240) NOT NULL,
	"hour" varchar(96) NOT NULL,
	day_of_week varchar(64) NOT NULL,
	day_of_month varchar(124) NOT NULL,
	month_of_year varchar(64) NOT NULL,
	timezone varchar(63) NOT NULL,
	CONSTRAINT django_celery_beat_crontabschedule_pkey PRIMARY KEY (id)
);


-- public.django_celery_beat_intervalschedule definition

-- Drop table

-- DROP TABLE public.django_celery_beat_intervalschedule;

CREATE TABLE public.django_celery_beat_intervalschedule (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"every" int4 NOT NULL,
	"period" varchar(24) NOT NULL,
	CONSTRAINT django_celery_beat_intervalschedule_pkey PRIMARY KEY (id)
);


-- public.django_celery_beat_periodictasks definition

-- Drop table

-- DROP TABLE public.django_celery_beat_periodictasks;

CREATE TABLE public.django_celery_beat_periodictasks (
	ident int2 NOT NULL,
	last_update timestamptz NOT NULL,
	CONSTRAINT django_celery_beat_periodictasks_pkey PRIMARY KEY (ident)
);


-- public.django_celery_beat_solarschedule definition

-- Drop table

-- DROP TABLE public.django_celery_beat_solarschedule;

CREATE TABLE public.django_celery_beat_solarschedule (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"event" varchar(24) NOT NULL,
	latitude numeric(9, 6) NOT NULL,
	longitude numeric(9, 6) NOT NULL,
	CONSTRAINT django_celery_beat_solar_event_latitude_longitude_ba64999a_uniq UNIQUE (event, latitude, longitude),
	CONSTRAINT django_celery_beat_solarschedule_pkey PRIMARY KEY (id)
);


-- public.django_content_type definition

-- Drop table

-- DROP TABLE public.django_content_type;

CREATE TABLE public.django_content_type (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	app_label varchar(100) NOT NULL,
	model varchar(100) NOT NULL,
	CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model),
	CONSTRAINT django_content_type_pkey PRIMARY KEY (id)
);


-- public.django_migrations definition

-- Drop table

-- DROP TABLE public.django_migrations;

CREATE TABLE public.django_migrations (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	app varchar(255) NOT NULL,
	"name" varchar(255) NOT NULL,
	applied timestamptz NOT NULL,
	CONSTRAINT django_migrations_pkey PRIMARY KEY (id)
);


-- public.django_session definition

-- Drop table

-- DROP TABLE public.django_session;

CREATE TABLE public.django_session (
	session_key varchar(40) NOT NULL,
	session_data text NOT NULL,
	expire_date timestamptz NOT NULL,
	CONSTRAINT django_session_pkey PRIMARY KEY (session_key)
);
CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);
CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


-- public.dns_records definition

-- Drop table

-- DROP TABLE public.dns_records;

CREATE TABLE public.dns_records (
	dns_record_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	domain_name text NULL,
	domain_type text NULL,
	created_date timestamp NULL,
	updated_date timestamp NULL,
	expiration_date timestamp NULL,
	name_servers _text NULL,
	whois_server text NULL,
	registrar_name text NULL,
	status text NULL,
	clean_text text NULL,
	raw_text text NULL,
	registrant_name text NULL,
	registrant_organization text NULL,
	registrant_street text NULL,
	registrant_city text NULL,
	registrant_state text NULL,
	registrant_post_code text NULL,
	registrant_country text NULL,
	registrant_email text NULL,
	registrant_phone text NULL,
	registrant_phone_ext text NULL,
	registrant_fax text NULL,
	registrant_fax_ext text NULL,
	registrant_raw_text text NULL,
	administrative_name text NULL,
	administrative_organization text NULL,
	administrative_street text NULL,
	administrative_city text NULL,
	administrative_state text NULL,
	administrative_post_code text NULL,
	administrative_country text NULL,
	administrative_email text NULL,
	administrative_phone text NULL,
	administrative_phone_ext text NULL,
	administrative_fax text NULL,
	administrative_fax_ext text NULL,
	administrative_raw_text text NULL,
	technical_name text NULL,
	technical_organization text NULL,
	technical_street text NULL,
	technical_city text NULL,
	technical_state text NULL,
	technical_post_code text NULL,
	technical_country text NULL,
	technical_email text NULL,
	technical_phone text NULL,
	technical_phone_ext text NULL,
	technical_fax text NULL,
	technical_fax_ext text NULL,
	technical_raw_text text NULL,
	billing_name text NULL,
	billing_organization text NULL,
	billing_street text NULL,
	billing_city text NULL,
	billing_state text NULL,
	billing_post_code text NULL,
	billing_country text NULL,
	billing_email text NULL,
	billing_phone text NULL,
	billing_phone_ext text NULL,
	billing_fax text NULL,
	billing_fax_ext text NULL,
	billing_raw_text text NULL,
	zone_name text NULL,
	zone_organization text NULL,
	zone_street text NULL,
	zone_city text NULL,
	zone_state text NULL,
	zone_post_code text NULL,
	zone_country text NULL,
	zone_email text NULL,
	zone_phone text NULL,
	zone_phone_ext text NULL,
	zone_fax text NULL,
	zone_fax_ext text NULL,
	zone_raw_text text NULL,
	CONSTRAINT dns_records_pkey PRIMARY KEY (dns_record_uid)
);


-- public.dnsmonitor_domain_map definition

-- Drop table

-- DROP TABLE public.dnsmonitor_domain_map;

CREATE TABLE public.dnsmonitor_domain_map (
	dnsmonitor_domain_map_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	"domain" text NOT NULL,
	organization text NOT NULL,
	"date" date NOT NULL,
	CONSTRAINT dnsmonitor_domain_map_pkey PRIMARY KEY (dnsmonitor_domain_map_uid)
);
COMMENT ON TABLE public.dnsmonitor_domain_map IS 'Mapping domains to organizations for dnsmonitor script';


-- public.dotgov_domains definition

-- Drop table

-- DROP TABLE public.dotgov_domains;

CREATE TABLE public.dotgov_domains (
	dotgov_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	domain_name text NOT NULL,
	domain_type text NULL,
	agency text NULL,
	organization text NULL,
	city text NULL,
	state text NULL,
	security_contact_email text NULL,
	CONSTRAINT dotgov_uid_pkey PRIMARY KEY (dotgov_uid),
	CONSTRAINT unique_domain UNIQUE (domain_name)
);


-- public.flare_event_types definition

-- Drop table

-- DROP TABLE public.flare_event_types;

CREATE TABLE public.flare_event_types (
	flare_event_type_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	event_type text NOT NULL,
	definition text NOT NULL,
	used_in_report bool NOT NULL,
	CONSTRAINT flare_event_types_pkey PRIMARY KEY (flare_event_type_uid),
	CONSTRAINT flare_event_types_unique UNIQUE (event_type)
);


-- public.org_id_map definition

-- Drop table

-- DROP TABLE public.org_id_map;

CREATE TABLE public.org_id_map (
	cyhy_id text NULL,
	pe_org_id text NULL,
	merge_orgs bool DEFAULT false NULL,
	CONSTRAINT unique_id_map_unique UNIQUE (cyhy_id, pe_org_id)
);


-- public.org_type definition

-- Drop table

-- DROP TABLE public.org_type;

CREATE TABLE public.org_type (
	org_type_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	org_type text NULL,
	CONSTRAINT org_type_pkey PRIMARY KEY (org_type_uid)
);


-- public.pshtt_results definition

-- Drop table

-- DROP TABLE public.pshtt_results;

CREATE TABLE public.pshtt_results (
	pshtt_results_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	sub_domain_uid uuid NOT NULL,
	data_source_uid uuid NOT NULL,
	sub_domain text NOT NULL,
	date_scanned date NULL,
	base_domain text NULL,
	base_domain_hsts_preloaded bool NULL,
	canonical_url text NULL,
	defaults_to_https bool NULL,
	"domain" text NULL,
	domain_enforces_https bool NULL,
	domain_supports_https bool NULL,
	domain_uses_strong_hsts bool NULL,
	downgrades_https bool NULL,
	htss bool NULL,
	hsts_entire_domain bool NULL,
	hsts_header text NULL,
	hsts_max_age numeric NULL,
	hsts_preload_pending bool NULL,
	hsts_preload_ready bool NULL,
	hsts_preloaded bool NULL,
	https_bad_chain bool NULL,
	https_bad_hostname bool NULL,
	https_cert_chain_length int4 NULL,
	https_client_auth_required bool NULL,
	https_custom_truststore_trusted bool NULL,
	https_expired_cert bool NULL,
	https_full_connection bool NULL,
	https_live bool NULL,
	https_probably_missing_intermediate_cert bool NULL,
	https_publicly_trusted bool NULL,
	https_self_signed_cert bool NULL,
	https_leaf_cert_expiration_date date NULL,
	https_leaf_cert_issuer text NULL,
	https_leaf_cert_subject text NULL,
	https_root_cert_issuer text NULL,
	ip inet NULL,
	live bool NULL,
	notes text NULL,
	redirect bool NULL,
	redirect_to text NULL,
	server_header text NULL,
	server_version text NULL,
	strictly_forces_https bool NULL,
	unknown_error bool NULL,
	valid_https bool NULL,
	ep_http_headers text NULL,
	ep_http_server_header text NULL,
	ep_http_server_version text NULL,
	ep_https_headers text NULL,
	ep_https_hsts_header text NULL,
	ep_https_server_header text NULL,
	ep_https_server_version text NULL,
	ep_httpswww_headers text NULL,
	ep_httpswww_hsts_header text NULL,
	ep_httpswww_server_header text NULL,
	ep_httpswww_server_version text NULL,
	ep_httpwww_headers text NULL,
	ep_httpwww_server_header text NULL,
	ep_httpwww_server_version text NULL,
	CONSTRAINT pshtt_results_organizations_uid_sub_domain_uid_key UNIQUE (organizations_uid, sub_domain_uid)
);


-- public.sectors definition

-- Drop table

-- DROP TABLE public.sectors;

CREATE TABLE public.sectors (
	sector_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	id text NOT NULL,
	acronym text NULL,
	"name" text NULL,
	email text NULL,
	contact_name text NULL,
	retired bool DEFAULT false NULL,
	first_seen date NULL,
	last_seen date NULL,
	run_scorecards bool NULL,
	"password" text NULL,
	parent_sector_uid uuid NULL,
	CONSTRAINT sectors_pkey PRIMARY KEY (sector_uid),
	CONSTRAINT unique_id UNIQUE (id)
);


-- public.team_members definition

-- Drop table

-- DROP TABLE public.team_members;

CREATE TABLE public.team_members (
	team_member_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	team_member_fname text NOT NULL,
	team_member_lname text NOT NULL,
	team_member_email text NOT NULL,
	"team_member_ghID" text NOT NULL,
	team_member_phone text NULL,
	team_member_role text NULL,
	team_member_notes text NULL,
	CONSTRAINT team_members_pkey PRIMARY KEY (team_member_uid)
);


-- public.top_cves_shodan definition

-- Drop table

-- DROP TABLE public.top_cves_shodan;

CREATE TABLE public.top_cves_shodan (
	top_cves_shodan_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	cve_id text NOT NULL,
	epss_score numeric NULL,
	nvd_base_score text NULL,
	collection_date date NOT NULL,
	summary text NULL,
	data_source_uid uuid NOT NULL,
	CONSTRAINT cve_id_collect_date_uniq UNIQUE (cve_id, collection_date),
	CONSTRAINT top_cves_shodan_pkey PRIMARY KEY (top_cves_shodan_uid)
);
COMMENT ON TABLE public.top_cves_shodan IS 'Top 10 CVEs ranked by EPSS score among all distinct CVEs detected by Shodan during a report period';


-- public.topic_totals definition

-- Drop table

-- DROP TABLE public.topic_totals;

CREATE TABLE public.topic_totals (
	cound_uuid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	content_count int4 NOT NULL,
	count_date text DEFAULT to_char(CURRENT_DATE::timestamp with time zone, 'YYYY-MM-DD'::text) NULL,
	CONSTRAINT topic_totals_pk PRIMARY KEY (cound_uuid)
);


-- public.tz_cidrs definition

-- Drop table

-- DROP TABLE public.tz_cidrs;

CREATE TABLE public.tz_cidrs (
	tz_cidrs_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cidr text NOT NULL,
	attested bool NOT NULL,
	last_observed date NOT NULL,
	"current" bool NOT NULL,
	data_source_uids _uuid NOT NULL,
	CONSTRAINT org_uid_cidr_unique UNIQUE (organizations_uid, cidr),
	CONSTRAINT tz_cidrs_pkey PRIMARY KEY (tz_cidrs_uid)
);


-- public.tz_ips definition

-- Drop table

-- DROP TABLE public.tz_ips;

CREATE TABLE public.tz_ips (
	tz_ips_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	ip_address text NOT NULL,
	tz_cidrs_uid uuid NULL,
	attested bool NOT NULL,
	last_observed date NOT NULL,
	"current" bool NOT NULL,
	data_source_uids _uuid NOT NULL,
	CONSTRAINT org_uid_ip_unique UNIQUE (organizations_uid, ip_address),
	CONSTRAINT tz_ips_pkey PRIMARY KEY (tz_ips_uid)
);


-- public.tz_root_domains definition

-- Drop table

-- DROP TABLE public.tz_root_domains;

CREATE TABLE public.tz_root_domains (
	tz_root_domains_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	root_domain text NOT NULL,
	ip_address text NULL,
	attested bool NOT NULL,
	last_observed date NOT NULL,
	"current" bool NOT NULL,
	data_source_uids _uuid NOT NULL,
	CONSTRAINT org_uid_root_unique UNIQUE (organizations_uid, root_domain),
	CONSTRAINT tz_root_domains_pkey PRIMARY KEY (tz_root_domains_uid)
);
COMMENT ON TABLE public.tz_root_domains IS 'root domains table for the Tier 0 project';


-- public.tz_shodan_assets definition

-- Drop table

-- DROP TABLE public.tz_shodan_assets;

CREATE TABLE public.tz_shodan_assets (
	tz_shodan_assets_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	ip text NULL,
	port text NULL,
	protocol text NULL,
	product text NULL,
	"server" text NULL,
	domains _text NULL,
	hostnames _text NULL,
	isp text NULL,
	asn text NULL,
	country_code text NULL,
	"location" text NULL,
	tags _text NULL,
	"timestamp" timestamp NOT NULL,
	last_observed date NOT NULL,
	data_source_uid uuid NOT NULL,
	CONSTRAINT org_ip_port_protocol_obsv_unique UNIQUE (organizations_uid, ip, port, protocol, last_observed),
	CONSTRAINT tz_shodan_assets_pkey PRIMARY KEY (tz_shodan_assets_uid)
);


-- public.tz_shodan_vulns definition

-- Drop table

-- DROP TABLE public.tz_shodan_vulns;

CREATE TABLE public.tz_shodan_vulns (
	tz_shodan_vulns_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	is_verified bool NOT NULL,
	"type" text NULL,
	potential_vulns _text NULL,
	cve text NULL,
	cvss_score numeric NULL,
	cvss_severity text NULL,
	summary text NULL,
	mitigation text NULL,
	ip text NULL,
	port text NULL,
	protocol text NULL,
	product text NULL,
	"version" text NULL,
	cpe _text NULL,
	"server" text NULL,
	banner text NULL,
	domains _text NULL,
	hostnames _text NULL,
	isp text NULL,
	asn text NULL,
	tags _text NULL,
	"timestamp" timestamp NOT NULL,
	last_observed date NOT NULL,
	data_source_uid uuid NOT NULL,
	CONSTRAINT org_vuln_ip_port_protocol_obsv_unique UNIQUE (organizations_uid, potential_vulns, cve, ip, port, protocol, last_observed),
	CONSTRAINT tz_shodan_vulns_pkey PRIMARY KEY (tz_shodan_vulns_uid)
);


-- public.tz_sub_domains definition

-- Drop table

-- DROP TABLE public.tz_sub_domains;

CREATE TABLE public.tz_sub_domains (
	tz_sub_domains_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	tz_root_domains_uid uuid NOT NULL,
	sub_domain text NOT NULL,
	ip_address text NULL,
	last_observed date NOT NULL,
	"current" bool NOT NULL,
	data_source_uids _uuid NOT NULL,
	CONSTRAINT root_uid_sub_unique UNIQUE (tz_root_domains_uid, sub_domain),
	CONSTRAINT tz_sub_domains_pkey PRIMARY KEY (tz_sub_domains_uid)
);


-- public.unique_software definition

-- Drop table

-- DROP TABLE public.unique_software;

CREATE TABLE public.unique_software (
	"_id" uuid DEFAULT uuid_generate_v1() NOT NULL,
	software_name text NOT NULL,
	CONSTRAINT unique_software_pkey PRIMARY KEY (_id)
);


-- public.was_findings definition

-- Drop table

-- DROP TABLE public.was_findings;

CREATE TABLE public.was_findings (
	finding_uid uuid NOT NULL,
	finding_type varchar NULL,
	webapp_id int4 NULL,
	was_org_id text NULL,
	owasp_category varchar NULL,
	severity varchar NULL,
	times_detected int4 NULL,
	base_score float8 NULL,
	temporal_score float8 NULL,
	fstatus varchar NULL,
	last_detected date NULL,
	first_detected date NULL,
	is_remediated bool NULL,
	potential bool NULL,
	webapp_url text NULL,
	webapp_name text NULL,
	"name" text NULL,
	cvss_v3_attack_vector text NULL,
	cwe_list _int4 NULL,
	wasc_list jsonb NULL,
	last_tested date NULL,
	fixed_date date NULL,
	is_ignored bool NULL,
	url text NULL,
	qid int4 NULL,
	response text NULL,
	CONSTRAINT was_findings_pkey PRIMARY KEY (finding_uid)
);


-- public.was_history definition

-- Drop table

-- DROP TABLE public.was_history;

CREATE TABLE public.was_history (
	was_org_id text NOT NULL,
	date_scanned date NOT NULL,
	vuln_cnt int4 NULL,
	vuln_webapp_cnt int4 NULL,
	web_app_cnt int4 NULL,
	high_rem_time int4 NULL,
	crit_rem_time int4 NULL,
	crit_vuln_cnt int4 NULL,
	high_vuln_cnt int4 NULL,
	report_period date NULL,
	high_rem_cnt int4 NULL,
	crit_rem_cnt int4 NULL,
	total_potential int4 NULL,
	CONSTRAINT was_history_pkey PRIMARY KEY (was_org_id, date_scanned)
);


-- public.was_report definition

-- Drop table

-- DROP TABLE public.was_report;

CREATE TABLE public.was_report (
	id serial4 NOT NULL,
	org_name text NULL,
	date_pulled timestamp NULL,
	last_scan_date timestamp NULL,
	security_risk text NULL,
	total_info int4 NULL,
	num_apps int4 NULL,
	risk_color text NULL,
	sensitive_count int4 NULL,
	sensitive_color text NULL,
	max_days_open_urgent int4 NULL,
	max_days_open_critical int4 NULL,
	urgent_color text NULL,
	critical_color text NULL,
	org_was_acronym text NULL,
	name_len text NULL,
	vuln_csv_dict jsonb DEFAULT '{}'::jsonb NULL,
	ssn_cc_dict jsonb DEFAULT '{}'::jsonb NULL,
	app_overview_csv_dict jsonb DEFAULT '{}'::jsonb NULL,
	details_csv jsonb DEFAULT '[]'::jsonb NULL,
	info_csv jsonb DEFAULT '[]'::jsonb NULL,
	links_crawled jsonb DEFAULT '[]'::jsonb NULL,
	links_rejected jsonb DEFAULT '[]'::jsonb NULL,
	emails_found jsonb DEFAULT '[]'::jsonb NULL,
	path_disc int4 NULL,
	info_disc int4 NULL,
	cross_site int4 NULL,
	burp int4 NULL,
	sql_inj int4 NULL,
	bugcrowd int4 NULL,
	reopened int4 NULL,
	reopened_color text NULL,
	new_vulns int4 NULL,
	new_vulns_color text NULL,
	tot_vulns int4 NULL,
	tot_vulns_color text NULL,
	lev1 int4 NULL,
	lev2 int4 NULL,
	lev3 int4 NULL,
	lev4 int4 NULL,
	lev5 int4 NULL,
	severities _int4 NULL,
	ages _int4 NULL,
	pdf_obj bytea NULL,
	owasp_count_dict jsonb DEFAULT '{}'::jsonb NULL,
	group_count_dict jsonb DEFAULT '{}'::jsonb NULL,
	fixed int4 NULL,
	total int4 NULL,
	vulns_monthly_dict jsonb DEFAULT '{}'::jsonb NULL,
	CONSTRAINT was_report_pkey PRIMARY KEY (id)
);


-- public.was_summary definition

-- Drop table

-- DROP TABLE public.was_summary;

CREATE TABLE public.was_summary (
	customer_id uuid NULL,
	was_org_id text NULL,
	webapp_count int4 NULL,
	active_vuln_count int4 NULL,
	webapp_with_vulns_count int4 NULL,
	last_updated date NULL,
	CONSTRAINT was_summary_was_org_id_key UNIQUE (was_org_id)
);


-- public.was_tracker_customerdata definition

-- Drop table

-- DROP TABLE public.was_tracker_customerdata;

CREATE TABLE public.was_tracker_customerdata (
	customer_id uuid DEFAULT uuid_generate_v1() NOT NULL,
	tag text NOT NULL,
	customer_name text NOT NULL,
	testing_sector text NOT NULL,
	ci_type text NOT NULL,
	jira_ticket text NULL,
	ticket text NOT NULL,
	next_scheduled text NOT NULL,
	last_scanned text NOT NULL,
	frequency text NOT NULL,
	comments_notes text NOT NULL,
	was_report_poc text NOT NULL,
	was_report_email text NOT NULL,
	onboarding_date text NOT NULL,
	no_of_web_apps int4 NOT NULL,
	no_web_apps_last_updated text NULL,
	elections bool NULL,
	fceb bool NULL,
	special_report bool NULL,
	report_password text NULL,
	child_tags text NULL,
	CONSTRAINT was_tracker_customerdata_pk PRIMARY KEY (customer_id)
);


-- public.weekly_statuses definition

-- Drop table

-- DROP TABLE public.weekly_statuses;

CREATE TABLE public.weekly_statuses (
	weekly_status_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	user_status text NOT NULL,
	key_accomplishments text NULL,
	ongoing_task text NOT NULL,
	upcoming_task text NOT NULL,
	obstacles text NULL,
	non_standard_meeting text NULL,
	deliverables text NULL,
	pto text NULL,
	week_ending date NOT NULL,
	notes text NULL,
	"statusComplete" int4 NULL,
	CONSTRAINT weekly_statuses_pkey PRIMARY KEY (weekly_status_uid)
);

-- Table Triggers

create trigger set_status_completed_and_week_ending_trigger before
insert
    on
    public.weekly_statuses for each row execute function set_status_completed_and_week_ending();


-- public.xpanse_alerts definition

-- Drop table

-- DROP TABLE public.xpanse_alerts;

CREATE TABLE public.xpanse_alerts (
	xpanse_alert_uid uuid NOT NULL,
	time_pulled_from_xpanse timestamptz NULL,
	alert_id text NOT NULL,
	detection_timestamp timestamptz NULL,
	alert_name text NULL,
	description text NULL,
	host_name text NULL,
	alert_action text NULL,
	action_pretty text NULL,
	action_country _text NULL,
	action_remote_port _int4 NULL,
	starred bool NULL,
	external_id text NULL,
	related_external_id text NULL,
	alert_occurrence int4 NULL,
	severity text NULL,
	matching_status text NULL,
	local_insert_ts timestamptz NULL,
	last_modified_ts timestamptz NULL,
	case_id int4 NULL,
	event_timestamp _timestamptz NULL,
	alert_type text NULL,
	resolution_status text NULL,
	resolution_comment text NULL,
	tags _text NULL,
	last_observed timestamptz NULL,
	country_codes _text NULL,
	cloud_providers _text NULL,
	ipv4_addresses _text NULL,
	domain_names _text NULL,
	service_ids _text NULL,
	website_ids _text NULL,
	asset_ids _text NULL,
	certificate jsonb NULL,
	port_protocol text NULL,
	attack_surface_rule_name text NULL,
	remediation_guidance text NULL,
	asset_identifiers jsonb NULL,
	CONSTRAINT xpanse_alerts_alert_id_key UNIQUE (alert_id),
	CONSTRAINT xpanse_alerts_pkey PRIMARY KEY (xpanse_alert_uid)
);
CREATE INDEX xpanse_alerts_alert_id_3566eec7_like ON public.xpanse_alerts USING btree (alert_id text_pattern_ops);


-- public.xpanse_assets definition

-- Drop table

-- DROP TABLE public.xpanse_assets;

CREATE TABLE public.xpanse_assets (
	xpanse_asset_uid uuid NOT NULL,
	asm_id text NOT NULL,
	asset_name text NULL,
	asset_type text NULL,
	last_observed timestamptz NULL,
	first_observed timestamptz NULL,
	externally_detected_providers _text NULL,
	created timestamptz NULL,
	ips _text NULL,
	active_external_services_types _text NULL,
	"domain" text NULL,
	certificate_issuer text NULL,
	certificate_algorithm text NULL,
	certificate_classifications _text NULL,
	resolves bool NULL,
	top_level_asset_mapper_domain text NULL,
	domain_asset_type jsonb NULL,
	is_paid_level_domain bool NULL,
	domain_details jsonb NULL,
	dns_zone text NULL,
	latest_sampled_ip int4 NULL,
	recent_ips jsonb NULL,
	external_services jsonb NULL,
	externally_inferred_vulnerability_score numeric(5, 2) NULL,
	externally_inferred_cves _text NULL,
	explainers _text NULL,
	tags _text NULL,
	CONSTRAINT xpanse_assets_asm_id_key UNIQUE (asm_id),
	CONSTRAINT xpanse_assets_pkey PRIMARY KEY (xpanse_asset_uid)
);
CREATE INDEX xpanse_assets_asm_id_545e3cab_like ON public.xpanse_assets USING btree (asm_id text_pattern_ops);


-- public.xpanse_cves definition

-- Drop table

-- DROP TABLE public.xpanse_cves;

CREATE TABLE public.xpanse_cves (
	xpanse_cve_uid uuid NOT NULL,
	cve_id text NULL,
	cvss_score_v2 numeric(5, 2) NULL,
	cve_severity_v2 text NULL,
	cvss_score_v3 numeric(5, 2) NULL,
	cve_severity_v3 text NULL,
	CONSTRAINT xpanse_cves_cve_id_key UNIQUE (cve_id),
	CONSTRAINT xpanse_cves_pkey PRIMARY KEY (xpanse_cve_uid)
);
CREATE INDEX xpanse_cves_cve_id_3d6e0b3d_like ON public.xpanse_cves USING btree (cve_id text_pattern_ops);


-- public.xpanse_services definition

-- Drop table

-- DROP TABLE public.xpanse_services;

CREATE TABLE public.xpanse_services (
	xpanse_service_uid uuid NOT NULL,
	service_id text NULL,
	service_name text NULL,
	service_type text NULL,
	ip_address _text NULL,
	"domain" _text NULL,
	externally_detected_providers _text NULL,
	is_active text NULL,
	first_observed timestamptz NULL,
	last_observed timestamptz NULL,
	port int4 NULL,
	protocol text NULL,
	active_classifications _text NULL,
	inactive_classifications _text NULL,
	discovery_type text NULL,
	externally_inferred_vulnerability_score numeric(5, 2) NULL,
	externally_inferred_cves _text NULL,
	service_key text NULL,
	service_key_type text NULL,
	CONSTRAINT xpanse_services_pkey PRIMARY KEY (xpanse_service_uid),
	CONSTRAINT xpanse_services_service_id_key UNIQUE (service_id)
);
CREATE INDEX xpanse_services_service_id_db370a84_like ON public.xpanse_services USING btree (service_id text_pattern_ops);


-- public.auth_permission definition

-- Drop table

-- DROP TABLE public.auth_permission;

CREATE TABLE public.auth_permission (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"name" varchar(255) NOT NULL,
	content_type_id int4 NOT NULL,
	codename varchar(100) NOT NULL,
	CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename),
	CONSTRAINT auth_permission_pkey PRIMARY KEY (id),
	CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


-- public.auth_user_groups definition

-- Drop table

-- DROP TABLE public.auth_user_groups;

CREATE TABLE public.auth_user_groups (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	user_id int4 NOT NULL,
	group_id int4 NOT NULL,
	CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id),
	CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id),
	CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);
CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


-- public.auth_user_user_permissions definition

-- Drop table

-- DROP TABLE public.auth_user_user_permissions;

CREATE TABLE public.auth_user_user_permissions (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	user_id int4 NOT NULL,
	permission_id int4 NOT NULL,
	CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id),
	CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id),
	CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);
CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


-- public.cpe_product definition

-- Drop table

-- DROP TABLE public.cpe_product;

CREATE TABLE public.cpe_product (
	cpe_product_uid uuid NOT NULL,
	cpe_product_name text NULL,
	version_number text NULL,
	cpe_vender_uid uuid NOT NULL,
	CONSTRAINT cpe_product_cpe_product_name_version_number_79faa8ba_uniq UNIQUE (cpe_product_name, version_number),
	CONSTRAINT cpe_product_pkey PRIMARY KEY (cpe_product_uid),
	CONSTRAINT cpe_product_cpe_vender_uid_245bdeee_fk_cpe_vende FOREIGN KEY (cpe_vender_uid) REFERENCES public.cpe_vender(cpe_vender_uid) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX cpe_product_cpe_vender_uid_245bdeee ON public.cpe_product USING btree (cpe_vender_uid);


-- public.cpe_product_cves definition

-- Drop table

-- DROP TABLE public.cpe_product_cves;

CREATE TABLE public.cpe_product_cves (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	cpeproduct_id uuid NOT NULL,
	cves_id uuid NOT NULL,
	CONSTRAINT cpe_product_cves_cpeproduct_id_cves_id_ccffe4de_uniq UNIQUE (cpeproduct_id, cves_id),
	CONSTRAINT cpe_product_cves_pkey PRIMARY KEY (id),
	CONSTRAINT cpe_product_cves_cpeproduct_id_71138136_fk_cpe_produ FOREIGN KEY (cpeproduct_id) REFERENCES public.cpe_product(cpe_product_uid) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT cpe_product_cves_cves_id_e0654851_fk_cves_cve_uid FOREIGN KEY (cves_id) REFERENCES public.cves(cve_uid) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX cpe_product_cves_cpeproduct_id_71138136 ON public.cpe_product_cves USING btree (cpeproduct_id);
CREATE INDEX cpe_product_cves_cves_id_e0654851 ON public.cpe_product_cves USING btree (cves_id);


-- public.credential_breaches definition

-- Drop table

-- DROP TABLE public.credential_breaches;

CREATE TABLE public.credential_breaches (
	credential_breaches_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	breach_name text NOT NULL,
	description text NULL,
	exposed_cred_count int8 NULL,
	breach_date date NULL,
	added_date timestamp NULL,
	modified_date timestamp NULL,
	data_classes _text NULL,
	password_included bool NULL,
	is_verified bool NULL,
	is_fabricated bool NULL,
	is_sensitive bool NULL,
	is_retired bool NULL,
	is_spam_list bool NULL,
	data_source_uid uuid NOT NULL,
	CONSTRAINT hibp_breaches_breach_name_key UNIQUE (breach_name),
	CONSTRAINT hibp_breaches_pkey PRIMARY KEY (credential_breaches_uid),
	CONSTRAINT credential_breaches_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid)
);


-- public."dataAPI_apiuser" definition

-- Drop table

-- DROP TABLE public."dataAPI_apiuser";

CREATE TABLE public."dataAPI_apiuser" (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"apiKey" varchar(200) NULL,
	user_id int4 NOT NULL,
	refresh_token varchar(200) NULL,
	CONSTRAINT "dataAPI_apiuser_pkey" PRIMARY KEY (id),
	CONSTRAINT "dataAPI_apiuser_user_id_key" UNIQUE (user_id),
	CONSTRAINT "dataAPI_apiuser_user_id_9b9cb3a6_fk_auth_user_id" FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED
);


-- public.django_admin_log definition

-- Drop table

-- DROP TABLE public.django_admin_log;

CREATE TABLE public.django_admin_log (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	action_time timestamptz NOT NULL,
	object_id text NULL,
	object_repr varchar(200) NOT NULL,
	action_flag int2 NOT NULL,
	change_message text NOT NULL,
	content_type_id int4 NULL,
	user_id int4 NOT NULL,
	CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0)),
	CONSTRAINT django_admin_log_pkey PRIMARY KEY (id),
	CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);
CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


-- public.django_celery_beat_periodictask definition

-- Drop table

-- DROP TABLE public.django_celery_beat_periodictask;

CREATE TABLE public.django_celery_beat_periodictask (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"name" varchar(200) NOT NULL,
	task varchar(200) NOT NULL,
	args text NOT NULL,
	kwargs text NOT NULL,
	queue varchar(200) NULL,
	exchange varchar(200) NULL,
	routing_key varchar(200) NULL,
	expires timestamptz NULL,
	enabled bool NOT NULL,
	last_run_at timestamptz NULL,
	total_run_count int4 NOT NULL,
	date_changed timestamptz NOT NULL,
	description text NOT NULL,
	crontab_id int4 NULL,
	interval_id int4 NULL,
	solar_id int4 NULL,
	one_off bool NOT NULL,
	start_time timestamptz NULL,
	priority int4 NULL,
	headers text NOT NULL,
	clocked_id int4 NULL,
	expire_seconds int4 NULL,
	CONSTRAINT django_celery_beat_periodictask_expire_seconds_check CHECK ((expire_seconds >= 0)),
	CONSTRAINT django_celery_beat_periodictask_name_key UNIQUE (name),
	CONSTRAINT django_celery_beat_periodictask_pkey PRIMARY KEY (id),
	CONSTRAINT django_celery_beat_periodictask_priority_check CHECK ((priority >= 0)),
	CONSTRAINT django_celery_beat_periodictask_total_run_count_check CHECK ((total_run_count >= 0)),
	CONSTRAINT django_celery_beat_p_clocked_id_47a69f82_fk_django_ce FOREIGN KEY (clocked_id) REFERENCES public.django_celery_beat_clockedschedule(id) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT django_celery_beat_p_crontab_id_d3cba168_fk_django_ce FOREIGN KEY (crontab_id) REFERENCES public.django_celery_beat_crontabschedule(id) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT django_celery_beat_p_interval_id_a8ca27da_fk_django_ce FOREIGN KEY (interval_id) REFERENCES public.django_celery_beat_intervalschedule(id) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT django_celery_beat_p_solar_id_a87ce72c_fk_django_ce FOREIGN KEY (solar_id) REFERENCES public.django_celery_beat_solarschedule(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX django_celery_beat_periodictask_clocked_id_47a69f82 ON public.django_celery_beat_periodictask USING btree (clocked_id);
CREATE INDEX django_celery_beat_periodictask_crontab_id_d3cba168 ON public.django_celery_beat_periodictask USING btree (crontab_id);
CREATE INDEX django_celery_beat_periodictask_interval_id_a8ca27da ON public.django_celery_beat_periodictask USING btree (interval_id);
CREATE INDEX django_celery_beat_periodictask_name_265a36b7_like ON public.django_celery_beat_periodictask USING btree (name varchar_pattern_ops);
CREATE INDEX django_celery_beat_periodictask_solar_id_a87ce72c ON public.django_celery_beat_periodictask USING btree (solar_id);


-- public.mentions definition

-- Drop table

-- DROP TABLE public.mentions;

CREATE TABLE public.mentions (
	mentions_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	category text NULL,
	collection_date text NULL,
	"content" text NULL,
	creator text NULL,
	"date" date NULL,
	sixgill_mention_id text NULL,
	post_id text NULL,
	lang text NULL,
	rep_grade text NULL,
	site text NULL,
	site_grade text NULL,
	title text NULL,
	"type" text NULL,
	url text NULL,
	comments_count text NULL,
	sub_category text NULL,
	tags text NULL,
	organizations_uid uuid NOT NULL,
	data_source_uid uuid NOT NULL,
	title_translated text NULL,
	content_translated text NULL,
	detected_lang text NULL,
	CONSTRAINT mentions_pkey PRIMARY KEY (mentions_uid),
	CONSTRAINT mentions_sixgill_mention_id_key UNIQUE (sixgill_mention_id),
	CONSTRAINT mentions_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid)
);


-- public.organizations definition

-- Drop table

-- DROP TABLE public.organizations;

CREATE TABLE public.organizations (
	organizations_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	"name" text NOT NULL,
	cyhy_db_name text NULL,
	org_type_uid uuid NULL,
	report_on bool DEFAULT false NULL,
	"password" text NULL,
	date_first_reported timestamp NULL,
	parent_org_uid uuid NULL,
	premium_report bool NULL,
	agency_type text NULL,
	demo bool DEFAULT false NULL,
	scorecard bool DEFAULT false NULL,
	fceb bool DEFAULT false NULL,
	receives_cyhy_report bool DEFAULT false NULL,
	receives_bod_report bool DEFAULT false NULL,
	receives_cybex_report bool DEFAULT false NULL,
	run_scans bool DEFAULT false NULL,
	is_parent bool DEFAULT false NULL,
	ignore_roll_up bool DEFAULT false NULL,
	retired bool DEFAULT false NULL,
	cyhy_period_start timestamp NULL,
	fceb_child bool DEFAULT false NULL,
	election bool DEFAULT false NULL,
	scorecard_child bool DEFAULT false NULL,
	location_name text NULL,
	county text NULL,
	county_fips numeric NULL,
	state_abbreviation text NULL,
	state_fips numeric NULL,
	state_name text NULL,
	country text NULL,
	country_name text NULL,
	exec_url text NULL,
	CONSTRAINT organizations_pkey PRIMARY KEY (organizations_uid),
	CONSTRAINT unique_cyhy_db_name UNIQUE (cyhy_db_name),
	CONSTRAINT organizations_org_type_uid_fkey FOREIGN KEY (org_type_uid) REFERENCES public.org_type(org_type_uid),
	CONSTRAINT parent_child_fkey FOREIGN KEY (parent_org_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.report_summary_stats definition

-- Drop table

-- DROP TABLE public.report_summary_stats;

CREATE TABLE public.report_summary_stats (
	report_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	start_date date NOT NULL,
	end_date date NULL,
	ip_count int4 NULL,
	root_count int4 NULL,
	sub_count int4 NULL,
	ports_count int4 NULL,
	creds_count int4 NULL,
	breach_count int4 NULL,
	cred_password_count int4 NULL,
	domain_alert_count int4 NULL,
	suspected_domain_count int4 NULL,
	insecure_port_count int4 NULL,
	verified_vuln_count int4 NULL,
	suspected_vuln_count int4 NULL,
	suspected_vuln_addrs_count int4 NULL,
	threat_actor_count int4 NULL,
	dark_web_alerts_count int4 NULL,
	dark_web_mentions_count int4 NULL,
	dark_web_executive_alerts_count int4 NULL,
	dark_web_asset_alerts_count int4 NULL,
	pe_number_score text NULL,
	pe_letter_grade text NULL,
	pe_percent_score numeric NULL,
	cidr_count int4 NULL,
	port_protocol_count int4 NULL,
	software_count int4 NULL,
	foreign_ips_count int4 NULL,
	CONSTRAINT report_summary_stats_pkey PRIMARY KEY (report_uid),
	CONSTRAINT unique_report UNIQUE (organizations_uid, start_date),
	CONSTRAINT report_summary_stats_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.root_domains definition

-- Drop table

-- DROP TABLE public.root_domains;

CREATE TABLE public.root_domains (
	root_domain_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	root_domain text NOT NULL,
	ip_address text NULL,
	data_source_uid uuid NOT NULL,
	enumerate_subs bool DEFAULT true NULL,
	CONSTRAINT root_domains_pkey PRIMARY KEY (root_domain_uid),
	CONSTRAINT root_domains_root_domain_organizations_uid_key UNIQUE (root_domain, organizations_uid),
	CONSTRAINT root_domains_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT root_domains_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.scorecard_summary_stats definition

-- Drop table

-- DROP TABLE public.scorecard_summary_stats;

CREATE TABLE public.scorecard_summary_stats (
	scorecard_summary_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	start_date date NOT NULL,
	end_date date NULL,
	score text NULL,
	discovery_score float8 NULL,
	profiling_score float8 NULL,
	identification_score float8 NULL,
	tracking_score float8 NULL,
	ips_self_reported int4 NULL,
	ips_discovered int4 NULL,
	ips_monitored int4 NULL,
	domains_self_reported int4 NULL,
	domains_discovered int4 NULL,
	domains_monitored int4 NULL,
	web_apps_self_reported int4 NULL,
	web_apps_discovered int4 NULL,
	web_apps_monitored int4 NULL,
	certs_self_reported int4 NULL,
	certs_discovered int4 NULL,
	certs_monitored int4 NULL,
	total_ports int4 NULL,
	risky_ports int4 NULL,
	protocols int4 NULL,
	insecure_protocols int4 NULL,
	total_services int4 NULL,
	unsupported_software int4 NULL,
	ext_host_kev int4 NULL,
	ext_host_vuln_critical int4 NULL,
	ext_host_vuln_high int4 NULL,
	web_apps_kev int4 NULL,
	web_apps_vuln_critical int4 NULL,
	web_apps_vuln_high int4 NULL,
	total_kev int4 NULL,
	total_vuln_critical int4 NULL,
	total_vuln_high int4 NULL,
	org_avg_days_remediate_kev int4 NULL,
	org_avg_days_remediate_critical int4 NULL,
	org_avg_days_remediate_high int4 NULL,
	sect_avg_days_remediate_kev int4 NULL,
	sect_avg_days_remediate_critical int4 NULL,
	sect_avg_days_remediate_high int4 NULL,
	bod_22_01 bool NULL,
	bod_19_02_critical bool NULL,
	bod_19_02_high bool NULL,
	org_web_avg_days_remediate_critical int4 NULL,
	org_web_avg_days_remediate_high int4 NULL,
	sect_web_avg_days_remediate_critical int4 NULL,
	sect_web_avg_days_remediate_high int4 NULL,
	email_compliance_pct float8 NULL,
	https_compliance_pct float8 NULL,
	sector_name text NULL,
	CONSTRAINT scorecard_summary_stats_pkey PRIMARY KEY (scorecard_summary_uid),
	CONSTRAINT unique_scorecard UNIQUE (organizations_uid, start_date, sector_name),
	CONSTRAINT scorecard_summary_stats_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.sectors_orgs definition

-- Drop table

-- DROP TABLE public.sectors_orgs;

CREATE TABLE public.sectors_orgs (
	sector_org_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	sector_uid uuid NOT NULL,
	organizations_uid uuid NOT NULL,
	first_seen date NULL,
	last_seen date NULL,
	CONSTRAINT sectors_orgs_pkey PRIMARY KEY (sector_org_uid),
	CONSTRAINT unique_sector_org UNIQUE (sector_uid, organizations_uid),
	CONSTRAINT sectors_orgs_orgs_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid) ON DELETE CASCADE,
	CONSTRAINT sectors_orgs_sector_uid_fkey FOREIGN KEY (sector_uid) REFERENCES public.sectors(sector_uid) ON DELETE CASCADE
);


-- public.shodan_assets definition

-- Drop table

-- DROP TABLE public.shodan_assets;

CREATE TABLE public.shodan_assets (
	shodan_asset_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	organization text NULL,
	ip text NULL,
	port int4 NULL,
	protocol text NULL,
	"timestamp" timestamp NULL,
	product text NULL,
	"server" text NULL,
	tags _text NULL,
	domains _text NULL,
	hostnames _text NULL,
	isn text NULL,
	asn int4 NULL,
	data_source_uid uuid NOT NULL,
	country_code text NULL,
	"location" text NULL,
	CONSTRAINT shodan_assets_organizations_uid_ip_port_protocol_timestamp_key UNIQUE (organizations_uid, ip, port, protocol, "timestamp"),
	CONSTRAINT shodan_assets_pkey PRIMARY KEY (shodan_asset_uid),
	CONSTRAINT shodan_assets_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT shodan_assets_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.shodan_vulns definition

-- Drop table

-- DROP TABLE public.shodan_vulns;

CREATE TABLE public.shodan_vulns (
	shodan_vuln_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	organization text NULL,
	ip text NULL,
	port text NULL,
	protocol text NULL,
	"timestamp" timestamp NULL,
	cve text NULL,
	severity text NULL,
	cvss numeric NULL,
	summary text NULL,
	product text NULL,
	attack_vector text NULL,
	av_description text NULL,
	attack_complexity text NULL,
	ac_description text NULL,
	confidentiality_impact text NULL,
	ci_description text NULL,
	integrity_impact text NULL,
	ii_description text NULL,
	availability_impact text NULL,
	ai_description text NULL,
	tags _text NULL,
	domains _text NULL,
	hostnames _text NULL,
	isn text NULL,
	asn int4 NULL,
	data_source_uid uuid NOT NULL,
	"type" text NULL,
	"name" text NULL,
	potential_vulns _text NULL,
	mitigation text NULL,
	"server" text NULL,
	is_verified bool DEFAULT true NULL,
	banner text NULL,
	"version" text NULL,
	cpe _text NULL,
	CONSTRAINT shodan_verified_vulns_organizations_uid_ip_port_protocol_ti_key UNIQUE (organizations_uid, ip, port, protocol, "timestamp"),
	CONSTRAINT shodan_verified_vulns_pkey PRIMARY KEY (shodan_vuln_uid),
	CONSTRAINT shodan_verified_vulns_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT shodan_verified_vulns_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.sub_domains definition

-- Drop table

-- DROP TABLE public.sub_domains;

CREATE TABLE public.sub_domains (
	sub_domain_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	sub_domain text NOT NULL,
	root_domain_uid uuid NOT NULL,
	data_source_uid uuid NOT NULL,
	dns_record_uid uuid NULL,
	status bool DEFAULT false NULL,
	first_seen date NULL,
	last_seen date NULL,
	"current" bool NULL,
	identified bool DEFAULT false NULL,
	CONSTRAINT sub_domains_pkey PRIMARY KEY (sub_domain_uid),
	CONSTRAINT sub_domains_un UNIQUE (sub_domain, root_domain_uid),
	CONSTRAINT sub_domains_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT sub_domains_dns_records_uid_fkey FOREIGN KEY (dns_record_uid) REFERENCES public.dns_records(dns_record_uid),
	CONSTRAINT sub_domains_root_domain_uid_fkey FOREIGN KEY (root_domain_uid) REFERENCES public.root_domains(root_domain_uid),
	CONSTRAINT sub_domains_sub_domain_root_domain_uid_key FOREIGN KEY (root_domain_uid) REFERENCES public.root_domains(root_domain_uid)
);


-- public.top_cves definition

-- Drop table

-- DROP TABLE public.top_cves;

CREATE TABLE public.top_cves (
	top_cves_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	cve_id text NULL,
	dynamic_rating text NULL,
	nvd_base_score text NULL,
	"date" date NULL,
	summary text NULL,
	data_source_uid uuid NOT NULL,
	CONSTRAINT top_cves_cve_id_date_key UNIQUE (cve_id, date),
	CONSTRAINT top_cves_pkey PRIMARY KEY (top_cves_uid),
	CONSTRAINT top_cves_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid)
);


-- public.was_map definition

-- Drop table

-- DROP TABLE public.was_map;

CREATE TABLE public.was_map (
	was_org_id text NOT NULL,
	pe_org_id uuid NULL,
	report_on bool NULL,
	last_scanned date NULL,
	CONSTRAINT was_map_pkey PRIMARY KEY (was_org_id),
	CONSTRAINT pe_org_id_fk FOREIGN KEY (pe_org_id) REFERENCES public.organizations(organizations_uid)
);


-- public.web_assets definition

-- Drop table

-- DROP TABLE public.web_assets;

CREATE TABLE public.web_assets (
	asset_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	asset_type text NOT NULL,
	asset text NOT NULL,
	ip_type text NULL,
	verified bool NULL,
	organizations_uid uuid NOT NULL,
	asset_origin text NULL,
	report_on bool DEFAULT true NULL,
	last_scanned timestamp NULL,
	report_status_reason text NULL,
	data_source_uid uuid NOT NULL,
	CONSTRAINT web_assets_asset_organizations_uid_key UNIQUE (asset, organizations_uid),
	CONSTRAINT web_assets_pkey PRIMARY KEY (asset_uid),
	CONSTRAINT web_assets_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT web_assets_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.xpanse_alerts_assets definition

-- Drop table

-- DROP TABLE public.xpanse_alerts_assets;

CREATE TABLE public.xpanse_alerts_assets (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	xpansealerts_id uuid NOT NULL,
	xpanseassets_id uuid NOT NULL,
	CONSTRAINT xpanse_alerts_assets_pkey PRIMARY KEY (id),
	CONSTRAINT xpanse_alerts_assets_xpansealerts_id_xpanseas_ff643833_uniq UNIQUE (xpansealerts_id, xpanseassets_id),
	CONSTRAINT xpanse_alerts_assets_xpansealerts_id_b676d836_fk_xpanse_al FOREIGN KEY (xpansealerts_id) REFERENCES public.xpanse_alerts(xpanse_alert_uid) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT xpanse_alerts_assets_xpanseassets_id_fb3ecbe2_fk_xpanse_as FOREIGN KEY (xpanseassets_id) REFERENCES public.xpanse_assets(xpanse_asset_uid) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX xpanse_alerts_assets_xpansealerts_id_b676d836 ON public.xpanse_alerts_assets USING btree (xpansealerts_id);
CREATE INDEX xpanse_alerts_assets_xpanseassets_id_fb3ecbe2 ON public.xpanse_alerts_assets USING btree (xpanseassets_id);


-- public.xpanse_alerts_services definition

-- Drop table

-- DROP TABLE public.xpanse_alerts_services;

CREATE TABLE public.xpanse_alerts_services (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	xpansealerts_id uuid NOT NULL,
	xpanseservices_id uuid NOT NULL,
	CONSTRAINT xpanse_alerts_services_pkey PRIMARY KEY (id),
	CONSTRAINT xpanse_alerts_services_xpansealerts_id_xpansese_e854e30a_uniq UNIQUE (xpansealerts_id, xpanseservices_id),
	CONSTRAINT xpanse_alerts_servic_xpansealerts_id_8cf2e46d_fk_xpanse_al FOREIGN KEY (xpansealerts_id) REFERENCES public.xpanse_alerts(xpanse_alert_uid) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT xpanse_alerts_servic_xpanseservices_id_113b499d_fk_xpanse_se FOREIGN KEY (xpanseservices_id) REFERENCES public.xpanse_services(xpanse_service_uid) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX xpanse_alerts_services_xpansealerts_id_8cf2e46d ON public.xpanse_alerts_services USING btree (xpansealerts_id);
CREATE INDEX xpanse_alerts_services_xpanseservices_id_113b499d ON public.xpanse_alerts_services USING btree (xpanseservices_id);


-- public.xpanse_business_units definition

-- Drop table

-- DROP TABLE public.xpanse_business_units;

CREATE TABLE public.xpanse_business_units (
	xpanse_business_unit_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	entity_name text NULL,
	state text NULL,
	county text NULL,
	city text NULL,
	sector text NULL,
	entity_type text NULL,
	region text NULL,
	rating int4 NULL,
	cyhy_db_name varchar(255) NULL,
	CONSTRAINT unique_xpanse_business_unit UNIQUE (entity_name),
	CONSTRAINT xpanse_business_units_pkey PRIMARY KEY (xpanse_business_unit_uid),
	CONSTRAINT xpanse_business_units_cyhy_db_name_fkey FOREIGN KEY (cyhy_db_name) REFERENCES public.organizations(cyhy_db_name)
);


-- public.xpanse_cve_services definition

-- Drop table

-- DROP TABLE public.xpanse_cve_services;

CREATE TABLE public.xpanse_cve_services (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	inferred_cve_match_type text NULL,
	product text NULL,
	confidence text NULL,
	vendor text NULL,
	version_number text NULL,
	activity_status text NULL,
	first_observed timestamptz NULL,
	last_observed timestamptz NULL,
	xpanse_inferred_cve_id uuid NOT NULL,
	xpanse_service_id uuid NOT NULL,
	CONSTRAINT xpanse_cve_services_pkey PRIMARY KEY (id),
	CONSTRAINT xpanse_cve_services_xpanse_inferred_cve_id_x_fd68e42a_uniq UNIQUE (xpanse_inferred_cve_id, xpanse_service_id),
	CONSTRAINT xpanse_cve_services_xpanse_inferred_cve__8065a32d_fk_xpanse_cv FOREIGN KEY (xpanse_inferred_cve_id) REFERENCES public.xpanse_cves(xpanse_cve_uid) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT xpanse_cve_services_xpanse_service_id_fe4d7182_fk_xpanse_se FOREIGN KEY (xpanse_service_id) REFERENCES public.xpanse_services(xpanse_service_uid) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX xpanse_cve_services_xpanse_inferred_cve_id_8065a32d ON public.xpanse_cve_services USING btree (xpanse_inferred_cve_id);
CREATE INDEX xpanse_cve_services_xpanse_service_id_fe4d7182 ON public.xpanse_cve_services USING btree (xpanse_service_id);


-- public.alerts definition

-- Drop table

-- DROP TABLE public.alerts;

CREATE TABLE public.alerts (
	alerts_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	alert_name text NULL,
	"content" text NULL,
	"date" date NULL,
	sixgill_id text NULL,
	"read" text NULL,
	severity text NULL,
	site text NULL,
	threat_level text NULL,
	threats text NULL,
	title text NULL,
	user_id text NULL,
	category text NULL,
	lang text NULL,
	organizations_uid uuid NOT NULL,
	data_source_uid uuid NOT NULL,
	content_snip text NULL,
	asset_mentioned text NULL,
	asset_type text NULL,
	CONSTRAINT alerts_pkey PRIMARY KEY (alerts_uid),
	CONSTRAINT alerts_sixgill_id_key UNIQUE (sixgill_id),
	CONSTRAINT alerts_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT alerts_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.alias definition

-- Drop table

-- DROP TABLE public.alias;

CREATE TABLE public.alias (
	alias_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	alias text NOT NULL,
	CONSTRAINT alias_alias_key UNIQUE (alias),
	CONSTRAINT alias_pkey PRIMARY KEY (alias_uid),
	CONSTRAINT alias_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.auth_group_permissions definition

-- Drop table

-- DROP TABLE public.auth_group_permissions;

CREATE TABLE public.auth_group_permissions (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	group_id int4 NOT NULL,
	permission_id int4 NOT NULL,
	CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id),
	CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id),
	CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);
CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


-- public.cidrs definition

-- Drop table

-- DROP TABLE public.cidrs;

CREATE TABLE public.cidrs (
	cidr_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	network cidr NOT NULL,
	organizations_uid uuid NULL,
	data_source_uid uuid NULL,
	insert_alert text NULL,
	first_seen date NULL,
	last_seen date NULL,
	"current" bool NULL,
	CONSTRAINT cidrs_uid_pkey PRIMARY KEY (cidr_uid),
	CONSTRAINT unique_org_cidr UNIQUE (organizations_uid, network),
	CONSTRAINT cidrs_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT cidrs_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.credential_exposures definition

-- Drop table

-- DROP TABLE public.credential_exposures;

CREATE TABLE public.credential_exposures (
	credential_exposures_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	email text NOT NULL,
	organizations_uid uuid NOT NULL,
	root_domain text NULL,
	sub_domain text NULL,
	breach_name text NULL,
	modified_date timestamp NULL,
	credential_breaches_uid uuid NOT NULL,
	data_source_uid uuid NOT NULL,
	"name" text NULL,
	login_id text NULL,
	phone text NULL,
	"password" text NULL,
	hash_type text NULL,
	intelx_system_id text NULL,
	login_url text NULL,
	CONSTRAINT credential_exposure_unique_constraint UNIQUE (breach_name, email,organizations_uid),
	CONSTRAINT hibp_exposed_credentials_pkey PRIMARY KEY (credential_exposures_uid),
	CONSTRAINT credential_exposures_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT hibp_exposed_credentials_breach_id_fkey FOREIGN KEY (credential_breaches_uid) REFERENCES public.credential_breaches(credential_breaches_uid),
	CONSTRAINT hibp_exposed_credentials_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_certs definition

-- Drop table

-- DROP TABLE public.cyhy_certs;

CREATE TABLE public.cyhy_certs (
	cyhy_certs_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	cyhy_id text NULL,
	serial text NULL,
	issuer text NULL,
	not_before timestamp NULL,
	not_after timestamp NULL,
	sct_or_not_before timestamp NULL,
	sct_exists bool NULL,
	pem text NULL,
	subjects text NULL,
	trimmed_subjects text NULL,
	sub_domain_uid uuid NULL,
	organizations_uid uuid NOT NULL,
	first_seen date NULL,
	last_seen date NULL,
	CONSTRAINT cyhy_certs_uid_pkey PRIMARY KEY (cyhy_certs_uid),
	CONSTRAINT unique_cyhy_cert UNIQUE (cyhy_id, organizations_uid, sub_domain_uid),
	CONSTRAINT cyhy_certs_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid),
	CONSTRAINT cyhy_domains_sub_domain_uid_fkey FOREIGN KEY (sub_domain_uid) REFERENCES public.sub_domains(sub_domain_uid)
);


-- public.cyhy_domains definition

-- Drop table

-- DROP TABLE public.cyhy_domains;

CREATE TABLE public.cyhy_domains (
	cyhy_domains_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	"domain" text NULL,
	agency_id text NULL,
	agency_name text NULL,
	cyhy_stakeholder bool NULL,
	scan_date timestamp NULL,
	first_seen date NULL,
	last_seen date NULL,
	CONSTRAINT cyhy_domains_uid_pkey PRIMARY KEY (cyhy_domains_uid),
	CONSTRAINT unique_cyhy_domain UNIQUE (domain),
	CONSTRAINT cyhy_domains_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_https_scan definition

-- Drop table

-- DROP TABLE public.cyhy_https_scan;

CREATE TABLE public.cyhy_https_scan (
	cyhy_https_scan_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cyhy_id text NULL,
	cyhy_latest bool NULL,
	domain_supports_https bool NULL,
	domain_enforces_https bool NULL,
	domain_uses_strong_hsts bool NULL,
	live bool NULL,
	scan_date timestamp NULL,
	hsts_base_domain_preloaded bool NULL,
	"domain" text NULL,
	base_domain text NULL,
	is_base_domain bool NULL,
	first_seen date NULL,
	last_seen date NULL,
	https_full_connection bool NULL,
	https_client_auth_required bool NULL,
	CONSTRAINT cyhy_https_scan_uid_pkey PRIMARY KEY (cyhy_https_scan_uid),
	CONSTRAINT unique_cyhy_https_scan UNIQUE (cyhy_id),
	CONSTRAINT cyhy_https_scan_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_port_scans definition

-- Drop table

-- DROP TABLE public.cyhy_port_scans;

CREATE TABLE public.cyhy_port_scans (
	cyhy_port_scans_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cyhy_id text NULL,
	cyhy_time timestamp NULL,
	service_name text NULL,
	port text NULL,
	product text NULL,
	cpe text NULL,
	first_seen date NULL,
	last_seen date NULL,
	ip text NULL,
	state text NULL,
	agency_type text NULL,
	CONSTRAINT cyhy_port_scans_uid_pkey PRIMARY KEY (cyhy_port_scans_uid),
	CONSTRAINT unique_cyhy_port_scans UNIQUE (cyhy_id),
	CONSTRAINT cyhy_port_scans_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_port_scans_new definition

-- Drop table

-- DROP TABLE public.cyhy_port_scans_new;

CREATE TABLE public.cyhy_port_scans_new (
	cyhy_port_scans_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cyhy_id text NULL,
	cyhy_time timestamp NULL,
	service_name text NULL,
	port text NULL,
	product text NULL,
	cpe text NULL,
	first_seen date NULL,
	last_seen date NULL,
	ip text NULL,
	state text NULL,
	agency_type text NULL,
	report_period timestamp NULL,
	CONSTRAINT cyhy_port_scans_new_uid_pkey PRIMARY KEY (cyhy_port_scans_uid),
	CONSTRAINT new_unique_cyhy_port_scans UNIQUE (ip, port, service_name, report_period),
	CONSTRAINT cyhy_port_scans_new_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_snapshots definition

-- Drop table

-- DROP TABLE public.cyhy_snapshots;

CREATE TABLE public.cyhy_snapshots (
	cyhy_snapshots_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cyhy_id text NULL,
	cyhy_last_change timestamp NULL,
	host_count int4 NULL,
	vulnerable_host_count int4 NULL,
	first_seen date NULL,
	last_seen date NULL,
	CONSTRAINT cyhy_snapshots_uid_pkey PRIMARY KEY (cyhy_snapshots_uid),
	CONSTRAINT unique_cyhy_snapshot UNIQUE (cyhy_id),
	CONSTRAINT cyhy_snapshot_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_sslyze definition

-- Drop table

-- DROP TABLE public.cyhy_sslyze;

CREATE TABLE public.cyhy_sslyze (
	cyhy_sslyze_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cyhy_id text NULL,
	cyhy_latest bool NULL,
	scanned_port text NULL,
	"domain" text NULL,
	base_domain text NULL,
	is_base_domain bool NULL,
	scanned_hostname text NULL,
	sslv2 bool NULL,
	scan_date timestamp NULL,
	sslv3 bool NULL,
	any_3des bool NULL,
	any_rc4 bool NULL,
	first_seen date NULL,
	last_seen date NULL,
	is_symantec_cert bool NULL,
	CONSTRAINT cyhy_sslyze_uid_pkey PRIMARY KEY (cyhy_sslyze_uid),
	CONSTRAINT unique_sslyze UNIQUE (cyhy_id),
	CONSTRAINT cyhy_sslyze_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_tickets definition

-- Drop table

-- DROP TABLE public.cyhy_tickets;

CREATE TABLE public.cyhy_tickets (
	cyhy_tickets_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cyhy_id text NULL,
	false_positive bool NULL,
	time_opened timestamp NULL,
	time_closed timestamp NULL,
	cvss_base_score float8 NULL,
	cve text NULL,
	first_seen date NULL,
	last_seen date NULL,
	"source" text NULL,
	ip text NULL,
	CONSTRAINT cyhy_ticket_uid_pkey PRIMARY KEY (cyhy_tickets_uid),
	CONSTRAINT unique_cyhy_ticket UNIQUE (cyhy_id),
	CONSTRAINT cyhy_ticket_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_trustymail definition

-- Drop table

-- DROP TABLE public.cyhy_trustymail;

CREATE TABLE public.cyhy_trustymail (
	cyhy_trustymail_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cyhy_id text NULL,
	cyhy_latest bool NULL,
	base_domain text NULL,
	is_base_domain bool NULL,
	"domain" text NULL,
	dmarc_record bool NULL,
	valid_spf bool NULL,
	scan_date timestamp NULL,
	live bool NULL,
	spf_record bool NULL,
	valid_dmarc bool NULL,
	valid_dmarc_base_domain bool NULL,
	dmarc_policy text NULL,
	dmarc_policy_percentage text NULL,
	aggregate_report_uris text NULL,
	domain_supports_smtp bool NULL,
	first_seen date NULL,
	last_seen date NULL,
	dmarc_subdomain_policy text NULL,
	domain_supports_starttls bool NULL,
	CONSTRAINT cyhy_trustymail_uid_pkey PRIMARY KEY (cyhy_trustymail_uid),
	CONSTRAINT unique_trustymail UNIQUE (cyhy_id),
	CONSTRAINT cyhy_trustymail_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.cyhy_vuln_scans definition

-- Drop table

-- DROP TABLE public.cyhy_vuln_scans;

CREATE TABLE public.cyhy_vuln_scans (
	cyhy_vuln_scans_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	cyhy_id text NULL,
	cyhy_time timestamp NULL,
	plugin_name text NULL,
	cvss_base_score float8 NULL,
	cve text NULL,
	first_seen date NULL,
	last_seen date NULL,
	ip text NULL,
	CONSTRAINT cyhy_vuln_scans_uid_pkey PRIMARY KEY (cyhy_vuln_scans_uid),
	CONSTRAINT unique_cyhy_vuln_scans UNIQUE (cyhy_id),
	CONSTRAINT cyhy_vulns_scans_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.domain_alerts definition

-- Drop table

-- DROP TABLE public.domain_alerts;

CREATE TABLE public.domain_alerts (
	domain_alert_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	sub_domain_uid uuid NOT NULL,
	data_source_uid uuid NOT NULL,
	organizations_uid uuid NOT NULL,
	alert_type text NULL,
	message text NULL,
	previous_value text NULL,
	new_value text NULL,
	"date" date NULL,
	CONSTRAINT domain_alerts_alert_type_sub_domain_uid_date_new_value_key UNIQUE (alert_type, sub_domain_uid, date, new_value),
	CONSTRAINT domain_alerts_pkey PRIMARY KEY (domain_alert_uid),
	CONSTRAINT domain_alerts_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT domain_alerts_sub_domain_uid_fkey FOREIGN KEY (sub_domain_uid) REFERENCES public.sub_domains(sub_domain_uid)
);


-- public.domain_permutations definition

-- Drop table

-- DROP TABLE public.domain_permutations;

CREATE TABLE public.domain_permutations (
	suspected_domain_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	domain_permutation text NULL,
	ipv4 text NULL,
	ipv6 text NULL,
	mail_server text NULL,
	name_server text NULL,
	fuzzer text NULL,
	date_observed date NULL,
	ssdeep_score text NULL,
	malicious bool NULL,
	blocklist_attack_count int4 NULL,
	blocklist_report_count int4 NULL,
	data_source_uid uuid NOT NULL,
	sub_domain_uid uuid NULL,
	dshield_record_count int4 NULL,
	dshield_attack_count int4 NULL,
	date_active date NULL,
	CONSTRAINT domain_permutations_domain_permutation_organizations_uid_key UNIQUE (domain_permutation, organizations_uid),
	CONSTRAINT dnstwist_domain_masq_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid),
	CONSTRAINT domain_permutations_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT domain_permutations_sub_domain_uid_fkey FOREIGN KEY (sub_domain_uid) REFERENCES public.sub_domains(sub_domain_uid)
);


-- public.executives definition

-- Drop table

-- DROP TABLE public.executives;

CREATE TABLE public.executives (
	executives_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	prefix text NULL,
	first_name text NOT NULL,
	middle_initial text NULL,
	last_name text NOT NULL,
	suffix text NULL,
	last_modified date NOT NULL,
	sixgill_id text NULL,
	CONSTRAINT executives_pkey PRIMARY KEY (executives_uid),
	CONSTRAINT executives_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);


-- public.flare_events definition

-- Drop table

-- DROP TABLE public.flare_events;

CREATE TABLE public.flare_events (
	flare_events_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	flare_uid text NOT NULL,
	event_type text NOT NULL,
	event_date date NOT NULL,
	collection_date date NOT NULL,
	title text NULL,
	"content" text NULL,
	content_hash text NULL,
	actor text NULL,
	category text NULL,
	"source" text NULL,
	url text NULL,
	risk_scores text NULL,
	related_identifiers _text NULL,
	data_source_uid uuid NOT NULL,
	severity text NOT NULL,
	related_identifiers_txt _text NULL,
	CONSTRAINT flare_events_pkey PRIMARY KEY (flare_events_uid),
	CONSTRAINT org_uid_flare_uid_uniq UNIQUE (organizations_uid, flare_uid),
	CONSTRAINT flare_events_data_source_fk FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid),
	CONSTRAINT flare_events_flare_event_types_fk FOREIGN KEY (event_type) REFERENCES public.flare_event_types(event_type),
	CONSTRAINT flare_events_organizations_fk FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid)
);
COMMENT ON TABLE public.flare_events IS 'Table to hold all event data from Flare';


-- public.ips definition

-- Drop table

-- DROP TABLE public.ips;

CREATE TABLE public.ips (
	ip_hash text NOT NULL,
	ip inet NOT NULL,
	origin_cidr uuid NULL,
	shodan_results bool NULL,
	live bool NULL,
	date_last_live timestamp NULL,
	last_reverse_lookup timestamp NULL,
	first_seen date NULL,
	last_seen date NULL,
	"current" bool NULL,
	from_cidr varchar DEFAULT false NOT NULL,
	organizations_uid uuid NULL,
	CONSTRAINT ip_unique UNIQUE (ip),
	CONSTRAINT ips_pkey PRIMARY KEY (ip_hash),
	CONSTRAINT fk_org_uid FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid),
	CONSTRAINT ip_origin_cidr_uid_fkey FOREIGN KEY (origin_cidr) REFERENCES public.cidrs(cidr_uid)
);
CREATE INDEX idx_ips_origin_cidr ON public.ips USING btree (origin_cidr);


-- public.ips_subs definition

-- Drop table

-- DROP TABLE public.ips_subs;

CREATE TABLE public.ips_subs (
	ips_subs_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	ip_hash text NOT NULL,
	sub_domain_uid uuid NOT NULL,
	first_seen date NULL,
	last_seen date NULL,
	"current" bool NULL,
	CONSTRAINT ips_subs_pkey PRIMARY KEY (ips_subs_uid),
	CONSTRAINT unique_ips_subs_unique UNIQUE (ip_hash, sub_domain_uid),
	CONSTRAINT ip_subs_ip_hash_fkey FOREIGN KEY (ip_hash) REFERENCES public.ips(ip_hash) ON DELETE CASCADE,
	CONSTRAINT ips_subs_sub_domain_uid_fkey FOREIGN KEY (sub_domain_uid) REFERENCES public.sub_domains(sub_domain_uid) ON DELETE CASCADE
);


-- public.old_shodan_insecure_protocols_unverified_vulns definition

-- Drop table

-- DROP TABLE public.old_shodan_insecure_protocols_unverified_vulns;

CREATE TABLE public.old_shodan_insecure_protocols_unverified_vulns (
	insecure_product_uid uuid DEFAULT uuid_generate_v1() NOT NULL,
	organizations_uid uuid NOT NULL,
	organization text NULL,
	ip text NULL,
	port int4 NULL,
	protocol text NULL,
	"type" text NULL,
	"name" text NULL,
	potential_vulns _text NULL,
	mitigation text NULL,
	"timestamp" timestamp NULL,
	product text NULL,
	"server" text NULL,
	tags _text NULL,
	domains _text NULL,
	hostnames _text NULL,
	isn text NULL,
	asn int4 NULL,
	data_source_uid uuid NOT NULL,
	CONSTRAINT shodan_insecure_protocols_unv_organizations_uid_ip_port_pro_key UNIQUE (organizations_uid, ip, port, protocol, "timestamp"),
	CONSTRAINT shodan_insecure_protocols_unverified_vulns_pkey PRIMARY KEY (insecure_product_uid),
	CONSTRAINT shodan_insecure_protocols_unverified_vul_organizations_uid_fkey FOREIGN KEY (organizations_uid) REFERENCES public.organizations(organizations_uid),
	CONSTRAINT shodan_insecure_protocols_unverified_vulns_data_source_uid_fkey FOREIGN KEY (data_source_uid) REFERENCES public.data_source(data_source_uid)
);


-- public.xpanse_alerts_business_units definition

-- Drop table

-- DROP TABLE public.xpanse_alerts_business_units;

CREATE TABLE public.xpanse_alerts_business_units (
	id int8 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	xpansealerts_id uuid NOT NULL,
	xpansebusinessunits_id uuid NOT NULL,
	CONSTRAINT xpanse_alerts_business_u_xpansealerts_id_xpansebu_66a44281_uniq UNIQUE (xpansealerts_id, xpansebusinessunits_id),
	CONSTRAINT xpanse_alerts_business_units_pkey PRIMARY KEY (id),
	CONSTRAINT xpanse_alerts_busine_xpansealerts_id_d0609f44_fk_xpanse_al FOREIGN KEY (xpansealerts_id) REFERENCES public.xpanse_alerts(xpanse_alert_uid) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT xpanse_alerts_busine_xpansebusinessunits__5a0fd6d4_fk_xpanse_bu FOREIGN KEY (xpansebusinessunits_id) REFERENCES public.xpanse_business_units(xpanse_business_unit_uid) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX xpanse_alerts_business_units_xpansealerts_id_d0609f44 ON public.xpanse_alerts_business_units USING btree (xpansealerts_id);
CREATE INDEX xpanse_alerts_business_units_xpansebusinessunits_id_5a0fd6d4 ON public.xpanse_alerts_business_units USING btree (xpansebusinessunits_id);


-- public.mat_vw_breachcomp source

CREATE MATERIALIZED VIEW public.mat_vw_breachcomp
TABLESPACE pg_default
AS SELECT creds.credential_exposures_uid,
    creds.email,
    creds.breach_name,
    creds.organizations_uid,
    creds.root_domain,
    creds.sub_domain,
    creds.hash_type,
    creds.name,
    creds.login_id,
    creds.password,
    creds.phone,
    creds.data_source_uid,
    b.description,
    b.breach_date,
    b.added_date,
    timezone('UTC'::text, b.modified_date::date::timestamp with time zone) AS modified_date,
    b.data_classes,
    b.password_included,
    b.is_verified,
    b.is_fabricated,
    b.is_sensitive,
    b.is_retired,
    b.is_spam_list
   FROM credential_exposures creds
     JOIN credential_breaches b ON creds.credential_breaches_uid = b.credential_breaches_uid
  WHERE timezone('UTC'::text, b.modified_date::date::timestamp with time zone) >= (CURRENT_DATE - '30 days'::interval)
WITH DATA;


-- public.mat_vw_breachcomp_breachdetails source

CREATE MATERIALIZED VIEW public.mat_vw_breachcomp_breachdetails
TABLESPACE pg_default
AS SELECT organizations_uid,
    breach_name,
    date(modified_date) AS mod_date,
    description,
    breach_date,
    password_included,
    count(email) AS number_of_creds
   FROM vw_breachcomp vb
  GROUP BY organizations_uid, breach_name, (date(modified_date)), description, breach_date, password_included
  ORDER BY (date(modified_date)) DESC
WITH DATA;


-- public.mat_vw_breachcomp_credsbydate source

CREATE MATERIALIZED VIEW public.mat_vw_breachcomp_credsbydate
TABLESPACE pg_default
AS SELECT organizations_uid,
    date(modified_date) AS mod_date,
    sum(
        CASE password_included
            WHEN false THEN 1
            ELSE 0
        END) AS no_password,
    sum(
        CASE password_included
            WHEN true THEN 1
            ELSE 0
        END) AS password_included
   FROM vw_breachcomp
  GROUP BY organizations_uid, (date(modified_date))
  ORDER BY (date(modified_date)) DESC
WITH DATA;


-- public.mat_vw_cyhy_port_counts source

CREATE MATERIALIZED VIEW public.mat_vw_cyhy_port_counts
TABLESPACE pg_default
AS SELECT report_period,
    organizations_uid,
    cyhy_db_name,
    fceb,
    fceb_child,
    count(*) AS ports,
    sum(
        CASE
            WHEN (service_name = ANY (ARRAY['rdp'::text, 'telnet'::text, 'ftp'::text, 'rpc'::text, 'smb'::text, 'sql'::text, 'ldap'::text, 'irc'::text, 'netbios'::text, 'kerberos'::text])) AND state = 'open'::text THEN 1
            ELSE 0
        END) AS risky_ports
   FROM ( SELECT o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
            o.fceb_child,
            cps.report_period,
            cps.port,
            cps.ip,
            cps.service_name,
            cps.state
           FROM cyhy_port_scans_new cps
             JOIN organizations o ON o.organizations_uid = cps.organizations_uid) p_i
  GROUP BY report_period, organizations_uid, fceb, fceb_child, cyhy_db_name
WITH DATA;


-- public.mat_vw_cyhy_protocol_counts source

CREATE MATERIALIZED VIEW public.mat_vw_cyhy_protocol_counts
TABLESPACE pg_default
AS SELECT report_period,
    organizations_uid,
    cyhy_db_name,
    fceb,
    fceb_child,
    count(*) AS protocols
   FROM ( SELECT DISTINCT o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
            o.fceb_child,
            cps.report_period,
            cps.port,
            cps.service_name
           FROM cyhy_port_scans_new cps
             JOIN organizations o ON o.organizations_uid = cps.organizations_uid) p_i
  GROUP BY report_period, organizations_uid, cyhy_db_name, fceb, fceb_child
WITH DATA;


-- public.mat_vw_cyhy_risky_protocol_counts source

CREATE MATERIALIZED VIEW public.mat_vw_cyhy_risky_protocol_counts
TABLESPACE pg_default
AS SELECT report_period,
    organizations_uid,
    cyhy_db_name,
    fceb,
    fceb_child,
    sum(
        CASE
            WHEN (service_name = ANY (ARRAY['rdp'::text, 'telnet'::text, 'ftp'::text, 'rpc'::text, 'smb'::text, 'sql'::text, 'ldap'::text, 'irc'::text, 'netbios'::text, 'kerberos'::text])) AND state = 'open'::text THEN 1
            ELSE 0
        END) AS risky_protocols
   FROM ( SELECT DISTINCT o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
            o.fceb_child,
            cps.report_period,
            cps.port,
            cps.service_name,
            cps.state
           FROM cyhy_port_scans_new cps
             JOIN organizations o ON o.organizations_uid = cps.organizations_uid) p_i
  GROUP BY report_period, organizations_uid, cyhy_db_name, fceb, fceb_child
WITH DATA;


-- public.mat_vw_cyhy_services_counts source

CREATE MATERIALIZED VIEW public.mat_vw_cyhy_services_counts
TABLESPACE pg_default
AS SELECT report_period,
    organizations_uid,
    cyhy_db_name,
    fceb,
    fceb_child,
    sum(
        CASE
            WHEN service_name = ANY (ARRAY['http'::text, 'https'::text, 'http-proxy'::text]) THEN 1
            ELSE 0
        END) AS services
   FROM ( SELECT DISTINCT o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
            o.fceb_child,
            cps.report_period,
            cps.port,
            cps.service_name
           FROM cyhy_port_scans_new cps
             JOIN organizations o ON o.organizations_uid = cps.organizations_uid) p_i
  GROUP BY report_period, organizations_uid, cyhy_db_name, fceb, fceb_child
WITH DATA;


-- public.mat_vw_fceb_total_ips source

CREATE MATERIALIZED VIEW public.mat_vw_fceb_total_ips
TABLESPACE pg_default
AS SELECT fceb_orgs.organizations_uid,
    fceb_orgs.cyhy_db_name,
    COALESCE(count(all_ips.ip), 0::bigint) AS total_ips,
    COALESCE(count(
        CASE
            WHEN all_ips.origin_cidr IS NULL AND all_ips.ip IS NOT NULL THEN 1
            ELSE NULL::integer
        END), 0::bigint) AS ip_discovered,
    COALESCE(count(
        CASE
            WHEN all_ips.origin_cidr IS NOT NULL THEN 1
            ELSE NULL::integer
        END), 0::bigint) AS cidr_reported
   FROM ( SELECT organizations.organizations_uid,
            organizations.cyhy_db_name
           FROM organizations
          WHERE (organizations.fceb = true OR organizations.fceb_child = true) AND organizations.retired IS FALSE) fceb_orgs
     LEFT JOIN ( SELECT cidrs_table.organizations_uid,
            ips_table.ip,
            ips_table.origin_cidr
           FROM ips ips_table
             JOIN cidrs cidrs_table ON ips_table.origin_cidr = cidrs_table.cidr_uid
          WHERE ips_table.current IS TRUE
        UNION
         SELECT rd.organizations_uid,
            i.ip,
            i.origin_cidr
           FROM root_domains rd
             JOIN sub_domains sd ON rd.root_domain_uid = sd.root_domain_uid
             JOIN ips_subs si ON sd.sub_domain_uid = si.sub_domain_uid
             JOIN ips i ON si.ip_hash = i.ip_hash
          WHERE sd.current IS TRUE) all_ips ON fceb_orgs.organizations_uid = all_ips.organizations_uid
  GROUP BY fceb_orgs.organizations_uid, fceb_orgs.cyhy_db_name
  ORDER BY (COALESCE(count(all_ips.ip), 0::bigint))
WITH DATA;


-- public.mat_vw_orgs_all_ips source

CREATE MATERIALIZED VIEW public.mat_vw_orgs_all_ips
TABLESPACE pg_default
AS SELECT reported_orgs.organizations_uid,
    reported_orgs.cyhy_db_name,
    array_agg(all_ips.ip) AS ip_addresses
   FROM ( SELECT organizations.organizations_uid,
            organizations.cyhy_db_name
           FROM organizations
          WHERE organizations.report_on = true) reported_orgs
     LEFT JOIN ( SELECT cidrs_table.organizations_uid,
            ips_table.ip
           FROM ips ips_table
             JOIN cidrs cidrs_table ON ips_table.origin_cidr = cidrs_table.cidr_uid
        UNION
         SELECT rd.organizations_uid,
            i.ip
           FROM root_domains rd
             JOIN sub_domains sd ON rd.root_domain_uid = sd.root_domain_uid
             JOIN ips_subs si ON sd.sub_domain_uid = si.sub_domain_uid
             JOIN ips i ON si.ip_hash = i.ip_hash) all_ips ON reported_orgs.organizations_uid = all_ips.organizations_uid
  GROUP BY reported_orgs.organizations_uid, reported_orgs.cyhy_db_name
  ORDER BY reported_orgs.organizations_uid, reported_orgs.cyhy_db_name
WITH DATA;


-- public.mat_vw_orgs_attacksurface source

CREATE MATERIALIZED VIEW public.mat_vw_orgs_attacksurface
TABLESPACE pg_default
AS SELECT domains_view.organizations_uid,
    domains_view.cyhy_db_name,
    ports_view.num_ports,
    domains_view.num_root_domain,
    domains_view.num_sub_domain,
    ips_view.num_ips,
    cidrs_view.count AS num_cidrs,
    port_prot_view.port_protocol AS num_ports_protocols,
    soft_view.num_software,
    for_ips_view.num_foreign_ips
   FROM vw_orgs_total_domains domains_view
     JOIN vw_orgs_total_ips ips_view ON domains_view.organizations_uid = ips_view.organizations_uid
     JOIN vw_orgs_total_ports ports_view ON ips_view.organizations_uid = ports_view.organizations_uid
     JOIN vw_orgs_total_cidrs cidrs_view ON cidrs_view.organizations_uid = ips_view.organizations_uid
     JOIN vw_orgs_total_ports_protocols port_prot_view ON port_prot_view.organizations_uid = ports_view.organizations_uid
     JOIN vw_orgs_total_software soft_view ON soft_view.organizations_uid = port_prot_view.organizations_uid
     JOIN vw_orgs_total_foreign_ips for_ips_view ON for_ips_view.organizations_uid = soft_view.organizations_uid
  ORDER BY ips_view.num_ips, domains_view.num_sub_domain, domains_view.num_root_domain, ports_view.num_ports
WITH DATA;


-- public.outdated_vw_breach_complete source

CREATE OR REPLACE VIEW public.outdated_vw_breach_complete
AS SELECT creds.credential_exposures_uid AS hibp_exposed_credentials_uid,
    creds.email,
    creds.breach_name,
    creds.organizations_uid,
    creds.root_domain,
    creds.sub_domain,
    b.description,
    b.breach_date,
    b.added_date,
    b.modified_date,
    b.data_classes,
    b.password_included,
    b.is_verified,
    b.is_fabricated,
    b.is_sensitive,
    b.is_retired,
    b.is_spam_list
   FROM credential_exposures creds
     JOIN credential_breaches b ON creds.credential_breaches_uid = b.credential_breaches_uid;


-- public.vw_breachcomp source

CREATE OR REPLACE VIEW public.vw_breachcomp
AS SELECT creds.credential_exposures_uid,
    creds.email,
    creds.breach_name,
    creds.organizations_uid,
    creds.root_domain,
    creds.sub_domain,
    creds.hash_type,
    creds.name,
    creds.login_id,
    creds.password,
    creds.phone,
    creds.data_source_uid,
    b.description,
    b.breach_date,
    b.added_date,
    timezone('UTC'::text, b.modified_date::date::timestamp with time zone) AS modified_date,
    b.data_classes,
    b.password_included,
    b.is_verified,
    b.is_fabricated,
    b.is_sensitive,
    b.is_retired,
    b.is_spam_list
   FROM credential_exposures creds
     JOIN credential_breaches b ON creds.credential_breaches_uid = b.credential_breaches_uid
  WHERE creds.data_source_uid = ANY (ARRAY['fa4e7454-8baa-11ed-b121-02c6a3fe975b'::uuid, '744fb0ec-981d-11ec-a0ff-02589a36c9d7'::uuid]);


-- public.vw_breachcomp_breachdetails source

CREATE OR REPLACE VIEW public.vw_breachcomp_breachdetails
AS SELECT organizations_uid,
    breach_name,
    date(modified_date) AS mod_date,
    description,
    breach_date,
    password_included,
    count(email) AS number_of_creds
   FROM vw_breachcomp vb
  GROUP BY organizations_uid, breach_name, (date(modified_date)), description, breach_date, password_included
  ORDER BY (date(modified_date)) DESC;


-- public.vw_breachcomp_credsbydate source

CREATE OR REPLACE VIEW public.vw_breachcomp_credsbydate
AS SELECT organizations_uid,
    date(modified_date) AS mod_date,
    sum(
        CASE password_included
            WHEN false THEN 1
            ELSE 0
        END) AS no_password,
    sum(
        CASE password_included
            WHEN true THEN 1
            ELSE 0
        END) AS password_included
   FROM vw_breachcomp
  GROUP BY organizations_uid, (date(modified_date))
  ORDER BY (date(modified_date)) DESC;


-- public.vw_cidrs source

CREATE OR REPLACE VIEW public.vw_cidrs
AS SELECT cidr_uid,
    network,
    organizations_uid,
    data_source_uid,
    insert_alert
   FROM cidrs;


-- public.vw_cyhy_port_counts source

CREATE OR REPLACE VIEW public.vw_cyhy_port_counts
AS SELECT report_period,
    organizations_uid,
    cyhy_db_name,
    fceb,
    fceb_child,
    count(*) AS ports,
    sum(
        CASE
            WHEN (service_name = ANY (ARRAY['rdp'::text, 'telnet'::text, 'ftp'::text, 'rpc'::text, 'smb'::text, 'sql'::text, 'ldap'::text, 'irc'::text, 'netbios'::text, 'kerberos'::text])) AND state = 'open'::text THEN 1
            ELSE 0
        END) AS risky_ports
   FROM ( SELECT o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
            o.fceb_child,
            cps.report_period,
            cps.port,
            cps.ip,
            cps.service_name,
            cps.state
           FROM cyhy_port_scans_new cps
             JOIN organizations o ON o.organizations_uid = cps.organizations_uid) p_i
  GROUP BY report_period, organizations_uid, fceb, fceb_child, cyhy_db_name;


-- public.vw_cyhy_protocol_counts source

CREATE OR REPLACE VIEW public.vw_cyhy_protocol_counts
AS SELECT report_period,
    organizations_uid,
    cyhy_db_name,
    fceb,
    fceb_child,
    count(*) AS protocols
   FROM ( SELECT DISTINCT o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
            o.fceb_child,
            cps.report_period,
            cps.port,
            cps.service_name
           FROM cyhy_port_scans_new cps
             JOIN organizations o ON o.organizations_uid = cps.organizations_uid) p_i
  GROUP BY report_period, organizations_uid, cyhy_db_name, fceb, fceb_child;


-- public.vw_cyhy_risky_protocol_counts source

CREATE OR REPLACE VIEW public.vw_cyhy_risky_protocol_counts
AS SELECT report_period,
    organizations_uid,
    cyhy_db_name,
    fceb,
    fceb_child,
    sum(
        CASE
            WHEN (service_name = ANY (ARRAY['rdp'::text, 'telnet'::text, 'ftp'::text, 'rpc'::text, 'smb'::text, 'sql'::text, 'ldap'::text, 'irc'::text, 'netbios'::text, 'kerberos'::text])) AND state = 'open'::text THEN 1
            ELSE 0
        END) AS risky_protocols
   FROM ( SELECT DISTINCT o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
            o.fceb_child,
            cps.report_period,
            cps.port,
            cps.service_name,
            cps.state
           FROM cyhy_port_scans_new cps
             JOIN organizations o ON o.organizations_uid = cps.organizations_uid) p_i
  GROUP BY report_period, organizations_uid, cyhy_db_name, fceb, fceb_child;


-- public.vw_cyhy_services_counts source

CREATE OR REPLACE VIEW public.vw_cyhy_services_counts
AS SELECT report_period,
    organizations_uid,
    cyhy_db_name,
    fceb,
    fceb_child,
    sum(
        CASE
            WHEN service_name = ANY (ARRAY['http'::text, 'https'::text, 'http-proxy'::text]) THEN 1
            ELSE 0
        END) AS services
   FROM ( SELECT DISTINCT o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
            o.fceb_child,
            cps.report_period,
            cps.port,
            cps.service_name
           FROM cyhy_port_scans_new cps
             JOIN organizations o ON o.organizations_uid = cps.organizations_uid) p_i
  GROUP BY report_period, organizations_uid, cyhy_db_name, fceb, fceb_child;


-- public.vw_darkweb_assetalerts source

CREATE OR REPLACE VIEW public.vw_darkweb_assetalerts
AS SELECT organizations_uid,
    max(date) AS date,
    site AS "Site",
    title AS "Title",
    count(*) AS "Events"
   FROM alerts a
  WHERE alert_name !~~ '%executive%'::text AND site IS NOT NULL AND site <> 'NaN'::text
  GROUP BY site, title, organizations_uid
  ORDER BY (count(*)) DESC;


-- public.vw_darkweb_execalerts source

CREATE OR REPLACE VIEW public.vw_darkweb_execalerts
AS SELECT organizations_uid,
    max(date) AS date,
    site AS "Site",
    title AS "Title",
    count(*) AS "Events"
   FROM alerts a
  WHERE alert_name ~~ '%executive%'::text AND site IS NOT NULL AND site <> 'NaN'::text
  GROUP BY site, title, organizations_uid
  ORDER BY (count(*)) DESC;


-- public.vw_darkweb_inviteonlymarkets source

CREATE OR REPLACE VIEW public.vw_darkweb_inviteonlymarkets
AS SELECT organizations_uid,
    date,
    site AS "Site"
   FROM alerts a
  WHERE site ~~ 'market%'::text AND site IS NOT NULL AND site <> 'NaN'::text AND site <> ''::text;


-- public.vw_darkweb_mentionsbydate source

CREATE OR REPLACE VIEW public.vw_darkweb_mentionsbydate
AS SELECT organizations_uid,
    date,
    count(*) AS "Count"
   FROM mentions m
  GROUP BY organizations_uid, date
  ORDER BY date DESC;


-- public.vw_darkweb_mostactposts source

CREATE OR REPLACE VIEW public.vw_darkweb_mostactposts
AS SELECT organizations_uid,
    date,
    title AS "Title",
        CASE
            WHEN comments_count = 'NaN'::text THEN 1
            WHEN comments_count = '0.0'::text THEN 1
            WHEN comments_count IS NULL THEN 1
            WHEN comments_count = ''::text THEN 1
            ELSE comments_count::numeric::integer
        END AS "Comments Count"
   FROM mentions m
  WHERE site ~~ 'forum%'::text OR site ~~ 'market%'::text
  ORDER BY (
        CASE
            WHEN comments_count = 'NaN'::text THEN 1
            WHEN comments_count = '0.0'::text THEN 1
            WHEN comments_count IS NULL THEN 1
            WHEN comments_count = ''::text THEN 1
            ELSE comments_count::numeric::integer
        END) DESC;


-- public.vw_darkweb_potentialthreats source

CREATE OR REPLACE VIEW public.vw_darkweb_potentialthreats
AS SELECT organizations_uid,
    date,
    site AS "Site",
    btrim(threats, '{}'::text) AS "Threats"
   FROM alerts a
  WHERE site IS NOT NULL AND site <> 'NaN'::text AND site <> ''::text;


-- public.vw_darkweb_sites source

CREATE OR REPLACE VIEW public.vw_darkweb_sites
AS SELECT organizations_uid,
    date,
    site AS "Site"
   FROM mentions m;


-- public.vw_darkweb_socmedia_mostactposts source

CREATE OR REPLACE VIEW public.vw_darkweb_socmedia_mostactposts
AS SELECT organizations_uid,
    date,
    title AS "Title",
        CASE
            WHEN comments_count = 'NaN'::text THEN 1
            WHEN comments_count = '0.0'::text THEN 1
            WHEN comments_count = ''::text THEN 1
            ELSE comments_count::numeric::integer
        END AS "Comments Count"
   FROM mentions m
  WHERE site !~~ 'forum%'::text AND site !~~ 'market%'::text
  ORDER BY (
        CASE
            WHEN comments_count = 'NaN'::text THEN 1
            WHEN comments_count = '0.0'::text THEN 1
            WHEN comments_count = ''::text THEN 1
            ELSE comments_count::numeric::integer
        END) DESC;


-- public.vw_darkweb_threatactors source

CREATE OR REPLACE VIEW public.vw_darkweb_threatactors
AS SELECT organizations_uid,
    date,
    creator AS "Creator",
    round(rep_grade::numeric, 3) AS "Grade"
   FROM mentions m
  ORDER BY (round(rep_grade::numeric, 3)) DESC;


-- public.vw_darkweb_topcves source

CREATE OR REPLACE VIEW public.vw_darkweb_topcves
AS SELECT top_cves_uid,
    cve_id,
    dynamic_rating,
    nvd_base_score,
    date,
    summary,
    data_source_uid
   FROM top_cves tc
  ORDER BY date DESC
 LIMIT 10;


-- public.vw_domain_counts source

CREATE OR REPLACE VIEW public.vw_domain_counts
AS SELECT o.organizations_uid,
    o.cyhy_db_name,
    o.fceb,
    o.fceb_child,
    COALESCE(cnts.identified, 0::bigint) AS identified,
    COALESCE(cnts.unidentified, 0::bigint) AS unidentified
   FROM organizations o
     LEFT JOIN ( SELECT rd.organizations_uid,
            sum(
                CASE sd.identified
                    WHEN true THEN 1
                    ELSE 0
                END) AS identified,
            sum(
                CASE sd.identified
                    WHEN false THEN 1
                    ELSE 0
                END) AS unidentified
           FROM root_domains rd
             JOIN sub_domains sd ON sd.root_domain_uid = rd.root_domain_uid
          GROUP BY rd.organizations_uid) cnts ON o.organizations_uid = cnts.organizations_uid;


-- public.vw_dscore_pe_domain source

CREATE OR REPLACE VIEW public.vw_dscore_pe_domain
AS SELECT organizations_uid,
    parent_org_uid,
    count(sub_domain) FILTER (WHERE identified = false) AS num_ident_domain,
    count(sub_domain) AS num_monitor_domain
   FROM ( SELECT orgs.organizations_uid,
            orgs.parent_org_uid,
            all_domains.sub_domain,
            all_domains.identified
           FROM ( SELECT organizations.organizations_uid,
                    organizations.parent_org_uid
                   FROM organizations) orgs
             LEFT JOIN ( SELECT root_domains.organizations_uid,
                    sub_domains.sub_domain,
                    sub_domains.identified
                   FROM root_domains
                     JOIN sub_domains ON root_domains.root_domain_uid = sub_domains.root_domain_uid) all_domains ON orgs.organizations_uid = all_domains.organizations_uid) domain_data
  GROUP BY organizations_uid, parent_org_uid;

COMMENT ON VIEW public.vw_dscore_pe_domain IS 'Retrieves all the PE domain data needed to calculate the discovery score';


-- public.vw_dscore_pe_ip source

CREATE OR REPLACE VIEW public.vw_dscore_pe_ip
AS SELECT organizations_uid,
    parent_org_uid,
    COALESCE(count(ip) FILTER (WHERE origin_cidr IS NOT NULL), 0::bigint) AS num_ident_ip,
    COALESCE(count(ip), 0::bigint) AS num_monitor_ip
   FROM ( SELECT organizations.organizations_uid,
            organizations.parent_org_uid,
            ips.ip,
            ips.origin_cidr
           FROM organizations
             LEFT JOIN ips ON organizations.organizations_uid = ips.organizations_uid) ip_data
  GROUP BY organizations_uid, parent_org_uid;

COMMENT ON VIEW public.vw_dscore_pe_ip IS 'Retrieves all the PE IP data needed to calculate the discovery score';


-- public.vw_dscore_vs_cert source

CREATE OR REPLACE VIEW public.vw_dscore_vs_cert
AS SELECT organizations_uid,
    parent_org_uid,
    sum(num_ident_cert) AS num_ident_cert,
    sum(num_monitor_cert) AS num_monitor_cert
   FROM ( SELECT organizations.organizations_uid,
            organizations.parent_org_uid,
            0 AS num_ident_cert,
            0 AS num_monitor_cert
           FROM organizations) cert_data
  GROUP BY organizations_uid, parent_org_uid;

COMMENT ON VIEW public.vw_dscore_vs_cert IS 'Retrieves all VS certificate data needed for the calculation of the I-Score, currently not pulling any real data until VS fixes their certificate scan script';


-- public.vw_dscore_vs_mail source

CREATE OR REPLACE VIEW public.vw_dscore_vs_mail
AS SELECT organizations_uid,
    parent_org_uid,
    COALESCE(sum(domain_counter) FILTER (WHERE valid_dmarc_base_domain = true OR valid_dmarc = true), 0::bigint) AS num_valid_dmarc,
    COALESCE(sum(domain_counter) FILTER (WHERE valid_spf = true), 0::bigint) AS num_valid_spf,
    COALESCE(sum(domain_counter) FILTER (WHERE valid_dmarc_base_domain = true OR valid_dmarc = true OR valid_spf = true), 0::bigint) AS num_valid_dmarc_or_spf,
    sum(domain_counter) AS total_mail_domains
   FROM ( SELECT orgs.organizations_uid,
            orgs.parent_org_uid,
            mail.domain,
            mail.valid_dmarc_base_domain,
            mail.valid_dmarc,
            mail.valid_spf,
            mail.domain_counter
           FROM ( SELECT organizations.organizations_uid,
                    organizations.parent_org_uid
                   FROM organizations) orgs
             LEFT JOIN ( SELECT cyhy_trustymail.cyhy_trustymail_uid,
                    cyhy_trustymail.organizations_uid,
                    cyhy_trustymail.cyhy_id,
                    cyhy_trustymail.cyhy_latest,
                    cyhy_trustymail.base_domain,
                    cyhy_trustymail.is_base_domain,
                    cyhy_trustymail.domain,
                    cyhy_trustymail.dmarc_record,
                    cyhy_trustymail.valid_spf,
                    cyhy_trustymail.scan_date,
                    cyhy_trustymail.live,
                    cyhy_trustymail.spf_record,
                    cyhy_trustymail.valid_dmarc,
                    cyhy_trustymail.valid_dmarc_base_domain,
                    cyhy_trustymail.dmarc_policy,
                    cyhy_trustymail.dmarc_policy_percentage,
                    cyhy_trustymail.aggregate_report_uris,
                    cyhy_trustymail.domain_supports_smtp,
                    cyhy_trustymail.first_seen,
                    cyhy_trustymail.last_seen,
                    cyhy_trustymail.dmarc_subdomain_policy,
                    cyhy_trustymail.domain_supports_starttls,
                    1 AS domain_counter
                   FROM cyhy_trustymail
                  WHERE cyhy_trustymail.cyhy_latest = true) mail ON orgs.organizations_uid = mail.organizations_uid) mail_data
  GROUP BY organizations_uid, parent_org_uid;

COMMENT ON VIEW public.vw_dscore_vs_mail IS 'Retrieves all the VS mail data needed to calculate the discovery score';


-- public.vw_dscore_was_webapp source

CREATE OR REPLACE VIEW public.vw_dscore_was_webapp
AS SELECT organizations_uid,
    parent_org_uid,
    sum(num_ident_webapp) AS num_ident_webapp,
    sum(num_monitor_webapp) AS num_monitor_webapp
   FROM ( SELECT orgs.organizations_uid,
            orgs.parent_org_uid,
            COALESCE(webapps.num_ident_webapp, 0) AS num_ident_webapp,
            COALESCE(webapps.num_monitor_webapp, 0) AS num_monitor_webapp
           FROM ( SELECT organizations.organizations_uid,
                    organizations.parent_org_uid,
                    organizations.cyhy_db_name
                   FROM organizations) orgs
             LEFT JOIN ( SELECT was_summary.was_org_id,
                    was_summary.webapp_count AS num_ident_webapp,
                    was_summary.webapp_count AS num_monitor_webapp
                   FROM was_summary) webapps ON orgs.cyhy_db_name = webapps.was_org_id) webapp_data
  GROUP BY organizations_uid, parent_org_uid;

COMMENT ON VIEW public.vw_dscore_was_webapp IS 'Retrieves all the WAS webapp data needed to calculate the discovery score. Currently just using number of webapps as both identified/monitored for now.';


-- public.vw_fceb_time_to_remediate source

CREATE OR REPLACE VIEW public.vw_fceb_time_to_remediate
AS SELECT month_seen,
    year_seen,
    organizations_uid,
    cyhy_db_name,
    avg(
        CASE
            WHEN is_kev THEN remediation_time
            ELSE NULL::interval
        END) AS kev_ttr,
    sum(
        CASE
            WHEN is_kev THEN 1
            ELSE 0
        END) AS kev_count,
    avg(
        CASE
            WHEN is_critical THEN remediation_time
            ELSE NULL::interval
        END) AS critical_ttr,
    sum(
        CASE
            WHEN is_critical THEN 1
            ELSE 0
        END) AS critical_count,
    avg(
        CASE
            WHEN is_high THEN remediation_time
            ELSE NULL::interval
        END) AS high_ttr,
    sum(
        CASE
            WHEN is_high THEN 1
            ELSE 0
        END) AS high_count
   FROM ( SELECT date_part('month'::text, ct.time_closed) AS month_seen,
            date_part('year'::text, ct.time_closed) AS year_seen,
            o.organizations_uid,
            o.cyhy_db_name,
            o.fceb,
                CASE
                    WHEN ct.cvss_base_score >= 7::double precision AND ct.cvss_base_score < 9::double precision THEN true
                    ELSE false
                END AS is_high,
                CASE
                    WHEN ct.cvss_base_score >= 9::double precision AND ct.cvss_base_score <= 10::double precision THEN true
                    ELSE false
                END AS is_critical,
                CASE
                    WHEN (ct.cve IN ( SELECT cyhy_kevs.kev
                       FROM cyhy_kevs)) THEN true
                    ELSE false
                END AS is_kev,
            ct.time_closed - ct.time_opened AS remediation_time
           FROM cyhy_tickets ct
             JOIN organizations o ON o.organizations_uid = ct.organizations_uid
          WHERE (o.fceb = true OR o.fceb_child = true) AND o.retired IS FALSE AND ct.false_positive IS FALSE AND ct.time_closed IS NOT NULL) summary
  GROUP BY month_seen, year_seen, organizations_uid, cyhy_db_name;


-- public.vw_fceb_total_ips source

CREATE OR REPLACE VIEW public.vw_fceb_total_ips
AS SELECT fceb_orgs.organizations_uid,
    fceb_orgs.cyhy_db_name,
    COALESCE(count(all_ips.ip), 0::bigint) AS total_ips,
    COALESCE(count(
        CASE
            WHEN all_ips.origin_cidr IS NULL AND all_ips.ip IS NOT NULL THEN 1
            ELSE NULL::integer
        END), 0::bigint) AS ip_discovered,
    COALESCE(count(
        CASE
            WHEN all_ips.origin_cidr IS NOT NULL THEN 1
            ELSE NULL::integer
        END), 0::bigint) AS cidr_reported
   FROM ( SELECT organizations.organizations_uid,
            organizations.cyhy_db_name
           FROM organizations
          WHERE (organizations.fceb = true OR organizations.fceb_child = true) AND organizations.retired IS FALSE) fceb_orgs
     LEFT JOIN ( SELECT cidrs_table.organizations_uid,
            ips_table.ip,
            ips_table.origin_cidr
           FROM ips ips_table
             JOIN cidrs cidrs_table ON ips_table.origin_cidr = cidrs_table.cidr_uid
          WHERE ips_table.current IS TRUE
        UNION
         SELECT rd.organizations_uid,
            i.ip,
            i.origin_cidr
           FROM root_domains rd
             JOIN sub_domains sd ON rd.root_domain_uid = sd.root_domain_uid
             JOIN ips_subs si ON sd.sub_domain_uid = si.sub_domain_uid
             JOIN ips i ON si.ip_hash = i.ip_hash
          WHERE i.current IS TRUE) all_ips ON fceb_orgs.organizations_uid = all_ips.organizations_uid
  GROUP BY fceb_orgs.organizations_uid, fceb_orgs.cyhy_db_name
  ORDER BY (COALESCE(count(all_ips.ip), 0::bigint));


-- public.vw_flare_breachcomp source

CREATE OR REPLACE VIEW public.vw_flare_breachcomp
AS SELECT creds.credential_exposures_uid,
    creds.email,
    creds.breach_name,
    creds.organizations_uid,
    creds.root_domain,
    creds.sub_domain,
    creds.hash_type,
    creds.name,
    creds.login_id,
    creds.password,
    creds.phone,
    creds.data_source_uid,
    b.description,
    b.breach_date,
    b.added_date,
    creds.modified_date,
    b.data_classes,
    b.password_included,
    b.is_verified,
    b.is_fabricated,
    b.is_sensitive,
    b.is_retired,
    b.is_spam_list,
    creds.login_url
   FROM credential_exposures creds
     JOIN credential_breaches b ON creds.credential_breaches_uid = b.credential_breaches_uid
  WHERE creds.data_source_uid = '751a4ff4-ac0c-11ef-8c7d-02527bfc647f'::uuid;


-- public.vw_flare_breachcomp_breachdetails source

CREATE OR REPLACE VIEW public.vw_flare_breachcomp_breachdetails
AS SELECT organizations_uid,
    breach_name,
    date(modified_date) AS mod_date,
    description,
    breach_date,
    password_included,
    count(email) AS number_of_creds
   FROM vw_flare_breachcomp vb
  GROUP BY organizations_uid, breach_name, (date(modified_date)), description, breach_date, password_included
  ORDER BY (date(modified_date)) DESC;


-- public.vw_flare_breachcomp_credsbydate source

CREATE OR REPLACE VIEW public.vw_flare_breachcomp_credsbydate
AS SELECT organizations_uid,
    date(modified_date) AS mod_date,
    sum(
        CASE password_included
            WHEN false THEN 1
            ELSE 0
        END) AS no_password,
    sum(
        CASE password_included
            WHEN true THEN 1
            ELSE 0
        END) AS password_included
   FROM vw_flare_breachcomp
  GROUP BY organizations_uid, (date(modified_date))
  ORDER BY (date(modified_date)) DESC;


-- public.vw_ips_cidr_org_info source

CREATE OR REPLACE VIEW public.vw_ips_cidr_org_info
AS SELECT i.ip_hash,
    i.ip,
    i.origin_cidr,
    ct.network,
    o.organizations_uid
   FROM ips i
     JOIN cidrs ct ON ct.cidr_uid = i.origin_cidr
     JOIN organizations o ON o.organizations_uid = ct.organizations_uid;

COMMENT ON VIEW public.vw_ips_cidr_org_info IS 'View containing ip data joined with data from the cidrs and organizations tables';


-- public.vw_ips_sub_root_org_info source

CREATE OR REPLACE VIEW public.vw_ips_sub_root_org_info
AS SELECT i.ip_hash,
    i.ip,
    i.origin_cidr,
    o.organizations_uid,
    i.current AS i_current,
    sd.current AS sd_current
   FROM ips i
     JOIN ips_subs is2 ON i.ip_hash = is2.ip_hash
     JOIN sub_domains sd ON sd.sub_domain_uid = is2.sub_domain_uid
     JOIN root_domains rd ON rd.root_domain_uid = sd.root_domain_uid
     JOIN organizations o ON o.organizations_uid = rd.organizations_uid;

COMMENT ON VIEW public.vw_ips_sub_root_org_info IS 'View containing ip data joined with data from sub_domains, root_domains, and organizations tables';


-- public.vw_iscore_orgs_ip_counts source

CREATE OR REPLACE VIEW public.vw_iscore_orgs_ip_counts
AS SELECT fceb_list.organizations_uid,
    fceb_list.cyhy_db_name,
    COALESCE(agg_ips.num_ips, '-1'::integer::bigint) AS ip_count
   FROM ( SELECT organizations.organizations_uid,
            organizations.cyhy_db_name
           FROM organizations
          WHERE organizations.fceb = true AND organizations.retired = false) fceb_list
     LEFT JOIN ( SELECT fceb_ips.organizations_uid,
            COALESCE(count(fceb_ips.ip), 0::bigint) AS num_ips
           FROM ( SELECT COALESCE(fceb.parent_org_uid, fceb.organizations_uid) AS organizations_uid,
                    all_ips.ip
                   FROM ( SELECT organizations.organizations_uid,
                            organizations.parent_org_uid
                           FROM organizations
                          WHERE (organizations.fceb = true OR organizations.fceb_child = true) AND organizations.retired = false) fceb
                     LEFT JOIN ( SELECT cidrs_table.organizations_uid,
                            ips_table.ip
                           FROM ips ips_table
                             JOIN cidrs cidrs_table ON ips_table.origin_cidr = cidrs_table.cidr_uid
                        UNION
                         SELECT rd.organizations_uid,
                            i.ip
                           FROM root_domains rd
                             JOIN sub_domains sd ON rd.root_domain_uid = sd.root_domain_uid
                             JOIN ips_subs si ON sd.sub_domain_uid = si.sub_domain_uid
                             JOIN ips i ON si.ip_hash = i.ip_hash) all_ips ON fceb.organizations_uid = all_ips.organizations_uid) fceb_ips
          GROUP BY fceb_ips.organizations_uid) agg_ips ON fceb_list.organizations_uid = agg_ips.organizations_uid
  ORDER BY agg_ips.num_ips;

COMMENT ON VIEW public.vw_iscore_orgs_ip_counts IS 'Retrieve list of all stakeholders PE reports on and the  total numbrt of IPs associated with each one.';


-- public.vw_iscore_pe_breach source

CREATE OR REPLACE VIEW public.vw_iscore_pe_breach
AS SELECT orgs.organizations_uid,
    orgs.parent_org_uid,
    COALESCE(breach_data.date, '0001-01-01'::date) AS date,
    COALESCE(breach_data.breach_count, 0) AS breach_count
   FROM ( SELECT organizations.organizations_uid,
            organizations.parent_org_uid
           FROM organizations) orgs
     LEFT JOIN ( SELECT DISTINCT vw_breachcomp.organizations_uid,
            vw_breachcomp.breach_name,
            date(vw_breachcomp.modified_date) AS date,
            1 AS breach_count
           FROM vw_breachcomp) breach_data ON orgs.organizations_uid = breach_data.organizations_uid;

COMMENT ON VIEW public.vw_iscore_pe_breach IS 'Retrieve all relevant PE breach data needed for the calculation of the I-Score';


-- public.vw_iscore_pe_cred source

CREATE OR REPLACE VIEW public.vw_iscore_pe_cred
AS SELECT orgs.organizations_uid,
    orgs.parent_org_uid,
    COALESCE(cred_data.date, '0001-01-01'::date) AS date,
    COALESCE(cred_data.password_creds, 0::bigint) AS password_creds,
    COALESCE(cred_data.total_creds, 0::bigint) AS total_creds
   FROM ( SELECT organizations.organizations_uid,
            organizations.parent_org_uid
           FROM organizations) orgs
     LEFT JOIN ( SELECT vw_breachcomp_credsbydate.organizations_uid,
            vw_breachcomp_credsbydate.password_included AS password_creds,
            vw_breachcomp_credsbydate.no_password + vw_breachcomp_credsbydate.password_included AS total_creds,
            vw_breachcomp_credsbydate.mod_date AS date
           FROM vw_breachcomp_credsbydate) cred_data ON orgs.organizations_uid = cred_data.organizations_uid;

COMMENT ON VIEW public.vw_iscore_pe_cred IS 'Retrieve all relevant PE credential data needed for the calculation of the I-Score';


-- public.vw_iscore_pe_darkweb source

CREATE OR REPLACE VIEW public.vw_iscore_pe_darkweb
AS SELECT organizations_uid,
    parent_org_uid,
    alert_type,
    date,
    "Count"
   FROM ( SELECT orgs.organizations_uid,
            orgs.parent_org_uid,
            'MENTION'::text AS alert_type,
            COALESCE(vw_darkweb_mentionsbydate.date, '0001-01-01'::date) AS date,
            COALESCE(vw_darkweb_mentionsbydate."Count", 0::bigint) AS "Count"
           FROM ( SELECT organizations.organizations_uid,
                    organizations.parent_org_uid
                   FROM organizations) orgs
             LEFT JOIN vw_darkweb_mentionsbydate ON orgs.organizations_uid = vw_darkweb_mentionsbydate.organizations_uid
        UNION ALL
         SELECT orgs.organizations_uid,
            orgs.parent_org_uid,
            'POTENTIAL_THREAT'::text AS alert_type,
            COALESCE(threats.date, '0001-01-01'::date) AS date,
            COALESCE(threats."Count", 0) AS "Count"
           FROM ( SELECT organizations.organizations_uid,
                    organizations.parent_org_uid
                   FROM organizations) orgs
             LEFT JOIN ( SELECT vw_darkweb_potentialthreats.organizations_uid,
                    vw_darkweb_potentialthreats.date,
                    1 AS "Count"
                   FROM vw_darkweb_potentialthreats) threats ON orgs.organizations_uid = threats.organizations_uid
        UNION ALL
         SELECT orgs.organizations_uid,
            orgs.parent_org_uid,
            'INVITE_ONLY'::text AS alert_type,
            COALESCE(invites.date, '0001-01-01'::date) AS date,
            COALESCE(invites."Count", 0) AS "Count"
           FROM ( SELECT organizations.organizations_uid,
                    organizations.parent_org_uid
                   FROM organizations) orgs
             LEFT JOIN ( SELECT vw_darkweb_inviteonlymarkets.organizations_uid,
                    vw_darkweb_inviteonlymarkets.date,
                    1 AS "Count"
                   FROM vw_darkweb_inviteonlymarkets) invites ON orgs.organizations_uid = invites.organizations_uid
        UNION ALL
         SELECT orgs.organizations_uid,
            orgs.parent_org_uid,
            'ASSET'::text AS alert_type,
            COALESCE(assets.date, '0001-01-01'::date) AS date,
            COALESCE(assets."Count", 0) AS "Count"
           FROM ( SELECT organizations.organizations_uid,
                    organizations.parent_org_uid
                   FROM organizations) orgs
             LEFT JOIN ( SELECT vw_darkweb_assetalerts.organizations_uid,
                    vw_darkweb_assetalerts.date,
                    1 AS "Count"
                   FROM vw_darkweb_assetalerts) assets ON orgs.organizations_uid = assets.organizations_uid) dw_data;

COMMENT ON VIEW public.vw_iscore_pe_darkweb IS 'Retrieve all relevant PE dark web data needed for the calculation of the I-Score';


-- public.vw_iscore_pe_protocol source

CREATE OR REPLACE VIEW public.vw_iscore_pe_protocol
AS SELECT orgs.organizations_uid,
    orgs.parent_org_uid,
    protocol_data.port,
    protocol_data.ip,
    protocol_data.protocol,
    protocol_data.protocol_type,
    protocol_data.date
   FROM ( SELECT organizations.organizations_uid,
            organizations.parent_org_uid
           FROM organizations) orgs
     JOIN ( SELECT vw_shodanvulns_suspected.organizations_uid,
            vw_shodanvulns_suspected.port,
            vw_shodanvulns_suspected.ip,
            vw_shodanvulns_suspected.protocol,
            'Unencrypted'::text AS protocol_type,
            vw_shodanvulns_suspected."timestamp"::date AS date
           FROM vw_shodanvulns_suspected
          WHERE vw_shodanvulns_suspected.type = 'Insecure Protocol'::text
        UNION
         SELECT vw_shodanvulns_suspected.organizations_uid,
            vw_shodanvulns_suspected.port,
            vw_shodanvulns_suspected.ip,
            vw_shodanvulns_suspected.protocol,
            'Encrypted'::text AS protocol_type,
            vw_shodanvulns_suspected."timestamp"::date AS date
           FROM vw_shodanvulns_suspected
          WHERE NOT (vw_shodanvulns_suspected.protocol IN ( SELECT DISTINCT vw_shodanvulns_suspected_1.protocol
                   FROM vw_shodanvulns_suspected vw_shodanvulns_suspected_1
                  WHERE vw_shodanvulns_suspected_1.type = 'Insecure Protocol'::text))) protocol_data ON orgs.organizations_uid = protocol_data.organizations_uid;

COMMENT ON VIEW public.vw_iscore_pe_protocol IS 'Retrieve all relevant PE protocol data for the calculation of the I-Score';


-- public.vw_iscore_pe_vuln source

CREATE OR REPLACE VIEW public.vw_iscore_pe_vuln
AS SELECT orgs.organizations_uid,
    orgs.parent_org_uid,
    all_vulns.date,
    all_vulns.cve AS cve_name,
    all_vulns.cvss_score
   FROM ( SELECT organizations.organizations_uid,
            organizations.parent_org_uid
           FROM organizations) orgs
     LEFT JOIN ( SELECT all_cves.organizations_uid,
            all_cves.date,
            all_cves.cve,
            COALESCE(cve_info.cvss_3_0, cve_info.cvss_2_0) AS cvss_score
           FROM ( SELECT DISTINCT vw_shodanvulns_suspected.organizations_uid,
                    date(vw_shodanvulns_suspected."timestamp") AS date,
                    unnest(vw_shodanvulns_suspected.potential_vulns) AS cve
                   FROM vw_shodanvulns_suspected
                  WHERE vw_shodanvulns_suspected.type <> 'Insecure Protocol'::text
                UNION
                 SELECT DISTINCT vw_shodanvulns_verified.organizations_uid,
                    vw_shodanvulns_verified."timestamp" AS date,
                    vw_shodanvulns_verified.cve
                   FROM vw_shodanvulns_verified) all_cves
             JOIN cve_info ON all_cves.cve = cve_info.cve_name) all_vulns ON orgs.organizations_uid = all_vulns.organizations_uid;

COMMENT ON VIEW public.vw_iscore_pe_vuln IS 'Retrieve all relevant PE vulnerability data needed for the calculation of the I-Score';


-- public.vw_iscore_vs_vuln source

CREATE OR REPLACE VIEW public.vw_iscore_vs_vuln
AS SELECT orgs.organizations_uid,
    orgs.parent_org_uid,
    vs_vulns.cve_name,
    vs_vulns.cvss_score
   FROM ( SELECT organizations.organizations_uid,
            organizations.parent_org_uid
           FROM organizations) orgs
     LEFT JOIN ( SELECT cyhy_tickets.organizations_uid,
            cyhy_tickets.cve AS cve_name,
            cyhy_tickets.cvss_base_score AS cvss_score
           FROM cyhy_tickets
          WHERE cyhy_tickets.false_positive = false AND cyhy_tickets.time_closed IS NULL) vs_vulns ON orgs.organizations_uid = vs_vulns.organizations_uid;

COMMENT ON VIEW public.vw_iscore_vs_vuln IS 'Retrieve all VS vulnerability data needed for the calculation of the I-Score';


-- public.vw_iscore_vs_vuln_prev source

CREATE OR REPLACE VIEW public.vw_iscore_vs_vuln_prev
AS SELECT orgs.organizations_uid,
    orgs.parent_org_uid,
    vs_vulns.cve_name,
    vs_vulns.cvss_score,
    vs_vulns.time_closed
   FROM ( SELECT organizations.organizations_uid,
            organizations.parent_org_uid
           FROM organizations) orgs
     LEFT JOIN ( SELECT cyhy_tickets.organizations_uid,
            cyhy_tickets.cve AS cve_name,
            cyhy_tickets.cvss_base_score AS cvss_score,
            cyhy_tickets.time_closed
           FROM cyhy_tickets
          WHERE cyhy_tickets.false_positive = false AND cyhy_tickets.time_closed IS NOT NULL) vs_vulns ON orgs.organizations_uid = vs_vulns.organizations_uid;

COMMENT ON VIEW public.vw_iscore_vs_vuln_prev IS 'Retrieve all historical (previous period) VS vuln info for the calculation of the I-Score. Filter results for time_closed within previous report period.';


-- public.vw_iscore_was_vuln source

CREATE OR REPLACE VIEW public.vw_iscore_was_vuln
AS SELECT orgs.organizations_uid,
    orgs.parent_org_uid,
    was_vulns.date,
    was_vulns.cve_name,
    was_vulns.cvss_score,
    was_vulns.owasp_category
   FROM ( SELECT organizations.organizations_uid,
            organizations.cyhy_db_name,
            organizations.parent_org_uid
           FROM organizations) orgs
     LEFT JOIN ( SELECT was_findings.was_org_id AS org_id,
            was_findings.last_detected AS date,
            ''::text AS cve_name,
            was_findings.base_score AS cvss_score,
            was_findings.owasp_category
           FROM was_findings
          WHERE was_findings.finding_type::text = 'VULNERABILITY'::text AND (was_findings.fstatus::text = ANY (ARRAY['NEW'::character varying::text, 'ACTIVE'::character varying::text, 'REOPENED'::character varying::text]))) was_vulns ON orgs.cyhy_db_name = was_vulns.org_id;

COMMENT ON VIEW public.vw_iscore_was_vuln IS 'Retrieve all relevant WAS vulnerability data needed for the calculation of the I-Score';


-- public.vw_iscore_was_vuln_prev source

CREATE OR REPLACE VIEW public.vw_iscore_was_vuln_prev
AS SELECT orgs.organizations_uid,
    orgs.parent_org_uid,
    was_vulns_prev.vuln_cnt AS was_total_vulns_prev,
    was_vulns_prev.date
   FROM ( SELECT organizations.organizations_uid,
            organizations.cyhy_db_name,
            organizations.parent_org_uid
           FROM organizations) orgs
     LEFT JOIN ( SELECT was_history.was_org_id AS org_id,
            was_history.vuln_cnt,
            was_history.date_scanned AS date
           FROM was_history) was_vulns_prev ON orgs.cyhy_db_name = was_vulns_prev.org_id;

COMMENT ON VIEW public.vw_iscore_was_vuln_prev IS 'Retrieve historical (previous report period) WAS vuln data for I-Score calculation. Filter results by previous report period range.';


-- public.vw_orgs_all_ips source

CREATE OR REPLACE VIEW public.vw_orgs_all_ips
AS SELECT reported_orgs.organizations_uid,
    reported_orgs.cyhy_db_name,
    array_agg(all_ips.ip) AS ip_addresses
   FROM ( SELECT organizations.organizations_uid,
            organizations.cyhy_db_name
           FROM organizations
          WHERE organizations.report_on = true) reported_orgs
     LEFT JOIN ( SELECT cidrs_table.organizations_uid,
            ips_table.ip
           FROM ips ips_table
             JOIN cidrs cidrs_table ON ips_table.origin_cidr = cidrs_table.cidr_uid
        UNION
         SELECT rd.organizations_uid,
            i.ip
           FROM root_domains rd
             JOIN sub_domains sd ON rd.root_domain_uid = sd.root_domain_uid
             JOIN ips_subs si ON sd.sub_domain_uid = si.sub_domain_uid
             JOIN ips i ON si.ip_hash = i.ip_hash) all_ips ON reported_orgs.organizations_uid = all_ips.organizations_uid
  GROUP BY reported_orgs.organizations_uid, reported_orgs.cyhy_db_name
  ORDER BY reported_orgs.organizations_uid, reported_orgs.cyhy_db_name;


-- public.vw_orgs_attacksurface source

CREATE OR REPLACE VIEW public.vw_orgs_attacksurface
AS SELECT domains_view.organizations_uid,
    domains_view.cyhy_db_name,
    ports_view.num_ports,
    domains_view.num_root_domain,
    domains_view.num_sub_domain,
    ips_view.num_ips,
    cidrs_view.count AS num_cidrs,
    port_prot_view.port_protocol AS num_ports_protocols,
    soft_view.num_software,
    for_ips_view.num_foreign_ips
   FROM vw_orgs_total_domains domains_view
     JOIN vw_orgs_total_ips ips_view ON domains_view.organizations_uid = ips_view.organizations_uid
     JOIN vw_orgs_total_ports ports_view ON ips_view.organizations_uid = ports_view.organizations_uid
     JOIN vw_orgs_total_cidrs cidrs_view ON cidrs_view.organizations_uid = ips_view.organizations_uid
     JOIN vw_orgs_total_ports_protocols port_prot_view ON port_prot_view.organizations_uid = ports_view.organizations_uid
     JOIN vw_orgs_total_software soft_view ON soft_view.organizations_uid = port_prot_view.organizations_uid
     JOIN vw_orgs_total_foreign_ips for_ips_view ON for_ips_view.organizations_uid = soft_view.organizations_uid
  ORDER BY ips_view.num_ips, domains_view.num_sub_domain, domains_view.num_root_domain, ports_view.num_ports;


-- public.vw_orgs_contact_info source

CREATE OR REPLACE VIEW public.vw_orgs_contact_info
AS SELECT organizations.organizations_uid,
    organizations.cyhy_db_name,
    organizations.name AS agency_name,
    cyhy_contacts.contact_type,
    cyhy_contacts.name AS contact_name,
    cyhy_contacts.email,
    replace(cyhy_contacts.phone, '.'::text, '-'::text) AS phone,
    cyhy_contacts.date_pulled
   FROM organizations
     JOIN cyhy_contacts ON organizations.cyhy_db_name = cyhy_contacts.org_id
  ORDER BY organizations.cyhy_db_name, cyhy_contacts.contact_type;

COMMENT ON VIEW public.vw_orgs_contact_info IS 'Gets the contact info for all PE organizations';


-- public.vw_orgs_total_cidrs source

CREATE OR REPLACE VIEW public.vw_orgs_total_cidrs
AS SELECT reported_orgs.organizations_uid,
    COALESCE(cidr_counts.count, 0::bigint) AS count
   FROM ( SELECT organizations.organizations_uid
           FROM organizations) reported_orgs
     LEFT JOIN ( SELECT c.organizations_uid,
            count(c.network) AS count
           FROM cidrs c
          WHERE c.current
          GROUP BY c.organizations_uid) cidr_counts ON reported_orgs.organizations_uid = cidr_counts.organizations_uid;


-- public.vw_orgs_total_domains source

CREATE OR REPLACE VIEW public.vw_orgs_total_domains
AS SELECT root_table.organizations_uid,
    root_table.cyhy_db_name,
    root_table.num_root_domain,
    sub_table.num_sub_domain
   FROM ( SELECT reported_orgs.organizations_uid,
            reported_orgs.cyhy_db_name,
            COALESCE(root_counts.num_root_domain, 0::bigint) AS num_root_domain
           FROM ( SELECT organizations.organizations_uid,
                    organizations.cyhy_db_name
                   FROM organizations) reported_orgs
             LEFT JOIN ( SELECT root_table_1.organizations_uid,
                    count(DISTINCT root_table_1.root_domain) AS num_root_domain
                   FROM root_domains root_table_1
                  WHERE root_table_1.enumerate_subs IS TRUE
                  GROUP BY root_table_1.organizations_uid) root_counts ON reported_orgs.organizations_uid = root_counts.organizations_uid) root_table
     JOIN ( SELECT reported_orgs.organizations_uid,
            reported_orgs.cyhy_db_name,
            COALESCE(sub_counts.num_sub_domain, 0::bigint) AS num_sub_domain
           FROM ( SELECT organizations.organizations_uid,
                    organizations.cyhy_db_name
                   FROM organizations) reported_orgs
             LEFT JOIN ( SELECT root_table_1.organizations_uid,
                    count(DISTINCT sub_table_1.sub_domain) AS num_sub_domain
                   FROM sub_domains sub_table_1
                     JOIN root_domains root_table_1 ON sub_table_1.root_domain_uid = root_table_1.root_domain_uid
                  WHERE sub_table_1.current = true
                  GROUP BY root_table_1.organizations_uid) sub_counts ON reported_orgs.organizations_uid = sub_counts.organizations_uid) sub_table ON root_table.organizations_uid = sub_table.organizations_uid
  ORDER BY sub_table.num_sub_domain, root_table.num_root_domain;

COMMENT ON VIEW public.vw_orgs_total_domains IS 'Gets the total number of root and sub domains for all orgs.';


-- public.vw_orgs_total_foreign_ips source

CREATE OR REPLACE VIEW public.vw_orgs_total_foreign_ips
AS SELECT reported_orgs.organizations_uid,
    COALESCE(foreign_ips.num_foreign_ips, 0::bigint) AS num_foreign_ips
   FROM ( SELECT organizations.organizations_uid
           FROM organizations) reported_orgs
     LEFT JOIN ( SELECT sa.organizations_uid,
            count(
                CASE
                    WHEN sa.country_code <> 'US'::text AND sa.country_code IS NOT NULL THEN 1
                    ELSE NULL::integer
                END) AS num_foreign_ips
           FROM shodan_assets sa
          GROUP BY sa.organizations_uid) foreign_ips ON reported_orgs.organizations_uid = foreign_ips.organizations_uid;


-- public.vw_orgs_total_ips source

CREATE OR REPLACE VIEW public.vw_orgs_total_ips
AS SELECT ci.organizations_uid,
    ci.cyhy_db_name,
    ci.parent_org_uid,
    COALESCE(ci.cidr_ip_count, 0::double precision) AS cidr_ips,
    COALESCE(li.lone_count, 0::bigint) AS identified_ips,
    COALESCE(ci.cidr_ip_count, 0::double precision) + COALESCE(li.lone_count, 0::bigint)::double precision AS num_ips,
    ci.cidr_count
   FROM ( SELECT o.organizations_uid,
            o.cyhy_db_name,
            o.parent_org_uid,
            sum(ic.ip_count) AS cidr_ip_count,
            count(ic.network) AS cidr_count
           FROM organizations o
             LEFT JOIN ( SELECT c.organizations_uid,
                    masklen(c.network::inet) AS masklen,
                    c.network,
                        CASE
                            WHEN family(c.network::inet) = 4 THEN
                            CASE
                                WHEN masklen(c.network::inet) < 31 THEN (2::double precision ^ (32 - (( SELECT masklen(c.network::inet) AS masklen)))::double precision) - 2::double precision
                                WHEN masklen(c.network::inet) = 31 THEN 2::double precision
                                WHEN masklen(c.network::inet) = 32 THEN 1::double precision
                                ELSE NULL::double precision
                            END
                            WHEN family(c.network::inet) = 6 THEN
                            CASE
                                WHEN masklen(c.network::inet) < 127 THEN (2::double precision ^ (128 - (( SELECT masklen(c.network::inet) AS masklen)))::double precision) - 2::double precision
                                WHEN masklen(c.network::inet) = 127 THEN 2::double precision
                                WHEN masklen(c.network::inet) = 128 THEN 1::double precision
                                ELSE NULL::double precision
                            END
                            ELSE NULL::double precision
                        END AS ip_count
                   FROM cidrs c
                  WHERE c.current) ic ON ic.organizations_uid = o.organizations_uid
          GROUP BY o.organizations_uid, o.cyhy_db_name) ci
     LEFT JOIN ( SELECT lone_ips.organizations_uid,
            count(lone_ips.ip) AS lone_count
           FROM ( SELECT DISTINCT rd.organizations_uid,
                    i.ip
                   FROM ips i
                     JOIN ips_subs si ON si.ip_hash = i.ip_hash
                     JOIN sub_domains sd ON sd.sub_domain_uid = si.sub_domain_uid
                     JOIN root_domains rd ON rd.root_domain_uid = sd.root_domain_uid
                  WHERE sd.current AND i.current AND i.origin_cidr IS NULL) lone_ips
          GROUP BY lone_ips.organizations_uid) li ON li.organizations_uid = ci.organizations_uid;


-- public.vw_orgs_total_ports source

CREATE OR REPLACE VIEW public.vw_orgs_total_ports
AS SELECT reported_orgs.organizations_uid,
    reported_orgs.cyhy_db_name,
    COALESCE(count(all_ports.port), 0::bigint) AS num_ports
   FROM ( SELECT organizations.organizations_uid,
            organizations.cyhy_db_name
           FROM organizations) reported_orgs
     LEFT JOIN ( SELECT DISTINCT assets.organizations_uid,
            assets.ip,
            assets.port
           FROM shodan_assets assets
        UNION
         SELECT DISTINCT vulns.organizations_uid,
            vulns.ip,
            vulns.port::integer AS port
           FROM shodan_vulns vulns
        UNION
         SELECT DISTINCT unverif_vulns.organizations_uid,
            unverif_vulns.ip,
            unverif_vulns.port
           FROM old_shodan_insecure_protocols_unverified_vulns unverif_vulns) all_ports ON reported_orgs.organizations_uid = all_ports.organizations_uid
  GROUP BY reported_orgs.organizations_uid, reported_orgs.cyhy_db_name
  ORDER BY (COALESCE(count(all_ports.port), 0::bigint));

COMMENT ON VIEW public.vw_orgs_total_ports IS 'Gets the total number of unique ports for every organization P&E reports on';


-- public.vw_orgs_total_ports_protocols source

CREATE OR REPLACE VIEW public.vw_orgs_total_ports_protocols
AS SELECT reported_orgs.organizations_uid,
    COALESCE(protocols.port_protocol, 0::bigint) AS port_protocol
   FROM ( SELECT organizations.organizations_uid
           FROM organizations) reported_orgs
     LEFT JOIN ( SELECT t.organizations_uid,
            count(*) AS port_protocol
           FROM ( SELECT DISTINCT sa.port,
                    sa.protocol,
                    sa.organizations_uid
                   FROM shodan_assets sa) t
          GROUP BY t.organizations_uid) protocols ON reported_orgs.organizations_uid = protocols.organizations_uid;


-- public.vw_orgs_total_software source

CREATE OR REPLACE VIEW public.vw_orgs_total_software
AS SELECT reported_orgs.organizations_uid,
    COALESCE(software.num_software, 0::bigint) AS num_software
   FROM ( SELECT organizations.organizations_uid
           FROM organizations) reported_orgs
     LEFT JOIN ( SELECT t.organizations_uid,
            count(*) AS num_software
           FROM ( SELECT DISTINCT sa.product,
                    sa.organizations_uid
                   FROM shodan_assets sa
                  WHERE sa.product IS NOT NULL) t
          GROUP BY t.organizations_uid) software ON reported_orgs.organizations_uid = software.organizations_uid;


-- public.vw_pescore_check_new_cve source

CREATE OR REPLACE VIEW public.vw_pescore_check_new_cve
AS SELECT current_cves.cve_name
   FROM ( SELECT unverif_vulns.cve_name
           FROM organizations o
             JOIN ( SELECT DISTINCT vss.organizations_uid,
                    unnest(vss.potential_vulns) AS cve_name
                   FROM vw_shodanvulns_suspected vss
                  WHERE vss.type <> 'Insecure Protocol'::text) unverif_vulns ON o.organizations_uid = unverif_vulns.organizations_uid
          WHERE o.report_on = true
        UNION
         SELECT verif_vulns.cve_name
           FROM organizations o
             JOIN ( SELECT DISTINCT shodan_vulns.organizations_uid,
                    shodan_vulns.cve AS cve_name
                   FROM shodan_vulns
                  WHERE shodan_vulns.is_verified = true) verif_vulns ON o.organizations_uid = verif_vulns.organizations_uid
          WHERE o.report_on = true) current_cves
     LEFT JOIN cve_info ON current_cves.cve_name = cve_info.cve_name
  WHERE cve_info.cve_name IS NULL;

COMMENT ON VIEW public.vw_pescore_check_new_cve IS 'View to get any new CVEs that aren''t yet in the cve_info table';


-- public.vw_pshtt_domains_to_run source

CREATE OR REPLACE VIEW public.vw_pshtt_domains_to_run
AS SELECT sd.sub_domain_uid,
    sd.sub_domain,
    o.organizations_uid,
    o.name
   FROM sub_domains sd
     JOIN root_domains rd ON rd.root_domain_uid = sd.root_domain_uid
     JOIN organizations o ON o.organizations_uid = rd.organizations_uid
     LEFT JOIN ( SELECT pr_1.sub_domain_uid
           FROM pshtt_results pr_1
          WHERE pr_1.date_scanned > (CURRENT_DATE - '15 days'::interval)) pr ON pr.sub_domain_uid = sd.sub_domain_uid
  WHERE sd.current = true AND pr.sub_domain_uid IS NULL;


-- public.vw_scorecard_orgs source

CREATE OR REPLACE VIEW public.vw_scorecard_orgs
AS WITH RECURSIVE org_queries AS (
         WITH RECURSIVE sector_queries AS (
                 SELECT s.sector_uid,
                    s.id,
                    s.acronym,
                    s.name,
                    s.email,
                    s.contact_name,
                    s.retired,
                    s.first_seen,
                    s.last_seen,
                    s.run_scorecards,
                    s.password,
                    s.parent_sector_uid
                   FROM sectors s
                  WHERE s.run_scorecards = true
                UNION ALL
                 SELECT e.sector_uid,
                    e.id,
                    e.acronym,
                    e.name,
                    e.email,
                    e.contact_name,
                    e.retired,
                    e.first_seen,
                    e.last_seen,
                    e.run_scorecards,
                    e.password,
                    e.parent_sector_uid
                   FROM sectors e
                     JOIN sector_queries c ON e.parent_sector_uid = c.sector_uid
                )
         SELECT o.organizations_uid,
            o.cyhy_db_name,
            cq.id AS sector_id,
            o.parent_org_uid,
            o.retired,
            o.receives_cyhy_report,
            o.is_parent,
            o.fceb,
            o.fceb_child,
            o.name,
            o.cyhy_period_start
           FROM sector_queries cq
             JOIN sectors_orgs so ON so.sector_uid = cq.sector_uid
             JOIN organizations o ON o.organizations_uid = so.organizations_uid
        UNION ALL
         SELECT co.organizations_uid,
            co.cyhy_db_name,
            oq_1.sector_id,
            co.parent_org_uid,
            co.retired,
            co.receives_cyhy_report,
            co.is_parent,
            co.fceb,
            co.fceb_child,
            co.name,
            co.cyhy_period_start
           FROM organizations co
             JOIN org_queries oq_1 ON oq_1.organizations_uid = co.parent_org_uid
        )
 SELECT DISTINCT organizations_uid,
    cyhy_db_name,
    sector_id,
    parent_org_uid,
    retired,
    receives_cyhy_report,
    is_parent,
    fceb,
    fceb_child,
    name,
    cyhy_period_start
   FROM org_queries oq
  WHERE retired <> true;


-- public.vw_scorecard_top_orgs source

CREATE OR REPLACE VIEW public.vw_scorecard_top_orgs
AS WITH RECURSIVE sector_queries AS (
         SELECT s.sector_uid,
            s.id,
            s.acronym,
            s.name,
            s.email,
            s.contact_name,
            s.retired,
            s.first_seen,
            s.last_seen,
            s.run_scorecards,
            s.password,
            s.parent_sector_uid
           FROM sectors s
          WHERE s.run_scorecards = true
        UNION ALL
         SELECT e.sector_uid,
            e.id,
            e.acronym,
            e.name,
            e.email,
            e.contact_name,
            e.retired,
            e.first_seen,
            e.last_seen,
            e.run_scorecards,
            e.password,
            e.parent_sector_uid
           FROM sectors e
             JOIN sector_queries c ON e.parent_sector_uid = c.sector_uid
        )
 SELECT o.organizations_uid,
    o.cyhy_db_name,
    cq.id AS sector_id,
    o.parent_org_uid,
    o.retired,
    o.receives_cyhy_report,
    o.is_parent,
    o.fceb,
    o.fceb_child,
    o.name,
    o.cyhy_period_start
   FROM sector_queries cq
     JOIN sectors_orgs so ON so.sector_uid = cq.sector_uid
     JOIN organizations o ON o.organizations_uid = so.organizations_uid;


-- public.vw_sector_orgs source

CREATE OR REPLACE VIEW public.vw_sector_orgs
AS WITH RECURSIVE org_queries AS (
         WITH RECURSIVE sector_queries AS (
                 SELECT s.sector_uid,
                    s.id,
                    s.acronym,
                    s.name,
                    s.email,
                    s.contact_name,
                    s.retired,
                    s.first_seen,
                    s.last_seen,
                    s.run_scorecards,
                    s.password,
                    s.parent_sector_uid
                   FROM sectors s
                UNION ALL
                 SELECT e.sector_uid,
                    e.id,
                    e.acronym,
                    e.name,
                    e.email,
                    e.contact_name,
                    e.retired,
                    e.first_seen,
                    e.last_seen,
                    e.run_scorecards,
                    e.password,
                    e.parent_sector_uid
                   FROM sectors e
                     JOIN sector_queries c ON e.parent_sector_uid = c.sector_uid
                )
         SELECT o.organizations_uid,
            o.cyhy_db_name,
            cq.id AS sector_id,
            cq.run_scorecards,
            true AS top_level_org,
            o.parent_org_uid,
            o.report_on,
            o.retired,
            o.demo,
            o.receives_cyhy_report,
            o.is_parent,
            o.fceb,
            o.fceb_child,
            o.name,
            o.cyhy_period_start
           FROM sector_queries cq
             JOIN sectors_orgs so ON so.sector_uid = cq.sector_uid
             JOIN organizations o ON o.organizations_uid = so.organizations_uid
        UNION ALL
         SELECT co.organizations_uid,
            co.cyhy_db_name,
            oq_1.sector_id,
            oq_1.run_scorecards,
            false AS top_level_org,
            co.parent_org_uid,
            co.report_on,
            co.retired,
            co.demo,
            co.receives_cyhy_report,
            co.is_parent,
            co.fceb,
            co.fceb_child,
            co.name,
            co.cyhy_period_start
           FROM organizations co
             JOIN org_queries oq_1 ON oq_1.organizations_uid = co.parent_org_uid
        )
 SELECT DISTINCT organizations_uid,
    cyhy_db_name,
    name,
    sector_id,
    run_scorecards,
    top_level_org,
    parent_org_uid,
    report_on,
    retired,
    demo,
    receives_cyhy_report,
    is_parent,
    fceb,
    fceb_child,
    cyhy_period_start
   FROM org_queries oq
  WHERE retired <> true;


-- public.vw_sector_time_to_remediate source

CREATE OR REPLACE VIEW public.vw_sector_time_to_remediate
AS SELECT month_seen,
    year_seen,
    sector_id,
    organizations_uid,
    cyhy_db_name,
    avg(
        CASE
            WHEN is_kev THEN remediation_time
            ELSE NULL::interval
        END) AS kev_ttr,
    sum(
        CASE
            WHEN is_kev THEN 1
            ELSE 0
        END) AS kev_count,
    avg(
        CASE
            WHEN is_critical THEN remediation_time
            ELSE NULL::interval
        END) AS critical_ttr,
    sum(
        CASE
            WHEN is_critical THEN 1
            ELSE 0
        END) AS critical_count,
    avg(
        CASE
            WHEN is_high THEN remediation_time
            ELSE NULL::interval
        END) AS high_ttr,
    sum(
        CASE
            WHEN is_high THEN 1
            ELSE 0
        END) AS high_count
   FROM ( SELECT date_part('month'::text, ct.time_closed) AS month_seen,
            date_part('year'::text, ct.time_closed) AS year_seen,
            o.organizations_uid,
            o.cyhy_db_name,
            vso.sector_id,
            o.fceb,
                CASE
                    WHEN ct.cvss_base_score >= 7::double precision AND ct.cvss_base_score < 9::double precision THEN true
                    ELSE false
                END AS is_high,
                CASE
                    WHEN ct.cvss_base_score >= 9::double precision AND ct.cvss_base_score <= 10::double precision THEN true
                    ELSE false
                END AS is_critical,
                CASE
                    WHEN (ct.cve IN ( SELECT cyhy_kevs.kev
                       FROM cyhy_kevs)) THEN true
                    ELSE false
                END AS is_kev,
            ct.time_closed - ct.time_opened AS remediation_time
           FROM cyhy_tickets ct
             JOIN organizations o ON o.organizations_uid = ct.organizations_uid
             JOIN vw_scorecard_orgs vso ON o.organizations_uid = vso.organizations_uid
          WHERE o.retired IS FALSE AND ct.false_positive IS FALSE AND ct.time_closed IS NOT NULL) summary
  GROUP BY month_seen, year_seen, sector_id, organizations_uid, cyhy_db_name;


-- public.vw_shodanvulns_suspected source

CREATE OR REPLACE VIEW public.vw_shodanvulns_suspected
AS SELECT svv.organizations_uid,
    svv.organization,
    svv.ip,
    svv.port,
    svv.protocol,
    svv.type,
    svv.name,
    svv.potential_vulns,
    svv.mitigation,
    svv."timestamp",
    svv.product,
    svv.server,
    svv.tags,
    svv.domains,
    svv.hostnames,
    svv.isn,
    svv.asn,
    ds.name AS data_source
   FROM shodan_vulns svv
     JOIN data_source ds ON ds.data_source_uid = svv.data_source_uid
  WHERE svv.is_verified = false;


-- public.vw_shodanvulns_verified source

CREATE OR REPLACE VIEW public.vw_shodanvulns_verified
AS SELECT svv.organizations_uid,
    svv.organization,
    svv.ip,
    svv.port,
    svv.protocol,
    svv."timestamp",
    svv.cve,
    svv.severity,
    svv.cvss,
    svv.summary,
    svv.product,
    svv.attack_vector,
    svv.av_description,
    svv.attack_complexity,
    svv.ac_description,
    svv.confidentiality_impact,
    svv.ci_description,
    svv.integrity_impact,
    svv.ii_description,
    svv.availability_impact,
    svv.ai_description,
    svv.tags,
    svv.domains,
    svv.hostnames,
    svv.isn,
    svv.asn,
    ds.name AS data_source,
    svv.banner,
    svv.version,
    svv.cpe
   FROM shodan_vulns svv
     JOIN data_source ds ON ds.data_source_uid = svv.data_source_uid
  WHERE svv.is_verified = true;



-- DROP FUNCTION public.armor(bytea);

CREATE OR REPLACE FUNCTION public.armor(bytea)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_armor$function$
;

-- DROP FUNCTION public.armor(bytea, _text, _text);

CREATE OR REPLACE FUNCTION public.armor(bytea, text[], text[])
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_armor$function$
;

-- DROP FUNCTION public.crypt(text, text);

CREATE OR REPLACE FUNCTION public.crypt(text, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_crypt$function$
;

-- DROP FUNCTION public.dearmor(text);

CREATE OR REPLACE FUNCTION public.dearmor(text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_dearmor$function$
;

-- DROP FUNCTION public.decrypt(bytea, bytea, text);

CREATE OR REPLACE FUNCTION public.decrypt(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_decrypt$function$
;

-- DROP FUNCTION public.decrypt_iv(bytea, bytea, bytea, text);

CREATE OR REPLACE FUNCTION public.decrypt_iv(bytea, bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_decrypt_iv$function$
;

-- DROP FUNCTION public.digest(bytea, text);

CREATE OR REPLACE FUNCTION public.digest(bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_digest$function$
;

-- DROP FUNCTION public.digest(text, text);

CREATE OR REPLACE FUNCTION public.digest(text, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_digest$function$
;

-- DROP FUNCTION public.encrypt(bytea, bytea, text);

CREATE OR REPLACE FUNCTION public.encrypt(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_encrypt$function$
;

-- DROP FUNCTION public.encrypt_iv(bytea, bytea, bytea, text);

CREATE OR REPLACE FUNCTION public.encrypt_iv(bytea, bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_encrypt_iv$function$
;

-- DROP FUNCTION public.gen_random_bytes(int4);

CREATE OR REPLACE FUNCTION public.gen_random_bytes(integer)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_random_bytes$function$
;

-- DROP FUNCTION public.gen_random_uuid();

CREATE OR REPLACE FUNCTION public.gen_random_uuid()
 RETURNS uuid
 LANGUAGE c
 PARALLEL SAFE
AS '$libdir/pgcrypto', $function$pg_random_uuid$function$
;

-- DROP FUNCTION public.gen_salt(text);

CREATE OR REPLACE FUNCTION public.gen_salt(text)
 RETURNS text
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_gen_salt$function$
;

-- DROP FUNCTION public.gen_salt(text, int4);

CREATE OR REPLACE FUNCTION public.gen_salt(text, integer)
 RETURNS text
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_gen_salt_rounds$function$
;

-- DROP FUNCTION public.get_cred_metrics(date, date);

CREATE OR REPLACE FUNCTION public.get_cred_metrics(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, password_creds bigint, total_creds bigint, num_breaches bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		cred_metrics.organizations_uid,
		cred_metrics.password_creds,
		cred_metrics.total_creds,
		breach_metrics.num_breaches
	FROM
		(
			SELECT
				reported_orgs.organizations_uid,
				CAST(COALESCE(creds.password_included, 0) as bigint) password_creds,
				CAST(COALESCE(creds.no_password + creds.password_included, 0) as bigint) total_creds
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						vw_breachcomp_credsbydate.organizations_uid,
						SUM(no_password) as no_password,
						SUM(password_included) as password_included
					FROM
						public.vw_breachcomp_credsbydate
					WHERE
						mod_date BETWEEN start_date AND end_date
					GROUP BY
						vw_breachcomp_credsbydate.organizations_uid
				) creds
				ON reported_orgs.organizations_uid = creds.organizations_uid
		) cred_metrics
		INNER JOIN
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(breaches.num_breaches, 0) num_breaches
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						vw_breachcomp.organizations_uid,
						COUNT(DISTINCT breach_name) as num_breaches
					FROM
						public.vw_breachcomp
					WHERE
						modified_date BETWEEN start_date AND end_date
					GROUP BY
						vw_breachcomp.organizations_uid
				) breaches
				ON reported_orgs.organizations_uid = breaches.organizations_uid
		) breach_metrics
		ON
		cred_metrics.organizations_uid = breach_metrics.organizations_uid;
END; $function$
;

-- DROP FUNCTION public.get_darkweb_metrics(date, date);

CREATE OR REPLACE FUNCTION public.get_darkweb_metrics(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, num_dw_alerts bigint, num_dw_mentions bigint, num_dw_threats bigint, num_dw_invites bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		dw_alert_metrics.organizations_uid,
		dw_alert_metrics.num_dw_alerts,
		CAST(dw_mention_metrics.num_dw_mentions as bigint) AS num_dw_mentions,
		dw_threat_metrics.num_dw_threats,
		dw_invite_metrics.num_dw_invites
	FROM
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(alerts.num_dw_alerts, 0) AS num_dw_alerts
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					/* Get count of dark web alerts for the report period*/
					SELECT
						alerts.organizations_uid,
						COUNT(*) num_dw_alerts
					FROM
						public.alerts
					WHERE
						date BETWEEN start_date AND end_date
					GROUP BY
						alerts.organizations_uid
				) alerts
				ON reported_orgs.organizations_uid = alerts.organizations_uid
		) dw_alert_metrics
		INNER JOIN
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(mentions.num_dw_mentions, 0) AS num_dw_mentions
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						vw_darkweb_mentionsbydate.organizations_uid,
						SUM(public.vw_darkweb_mentionsbydate."Count") as num_dw_mentions
					FROM
						public.vw_darkweb_mentionsbydate
					WHERE
						date BETWEEN start_date AND end_date
					GROUP BY
						vw_darkweb_mentionsbydate.organizations_uid
				) mentions
				ON reported_orgs.organizations_uid = mentions.organizations_uid
		) dw_mention_metrics
		ON
		dw_alert_metrics.organizations_uid = dw_mention_metrics.organizations_uid
		INNER JOIN
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(threats.num_dw_threats, 0) AS num_dw_threats
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						vw_darkweb_potentialthreats.organizations_uid,
						COUNT(*) as num_dw_threats
					FROM
						public.vw_darkweb_potentialthreats
					WHERE
						date BETWEEN start_date AND end_date
					GROUP BY
						vw_darkweb_potentialthreats.organizations_uid
				) threats
				ON reported_orgs.organizations_uid = threats.organizations_uid
		) dw_threat_metrics
		ON
		dw_alert_metrics.organizations_uid = dw_threat_metrics.organizations_uid
		INNER JOIN
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(invites.num_dw_invites, 0) AS num_dw_invites
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						vw_darkweb_inviteonlymarkets.organizations_uid,
						COUNT(*) as num_dw_invites
					FROM
						public.vw_darkweb_inviteonlymarkets
					WHERE
						date BETWEEN start_date AND end_date
					GROUP BY
						vw_darkweb_inviteonlymarkets.organizations_uid
				) invites
				ON reported_orgs.organizations_uid = invites.organizations_uid
		) dw_invite_metrics
		ON
		dw_alert_metrics.organizations_uid = dw_invite_metrics.organizations_uid;
END; $function$
;

-- DROP FUNCTION public.get_domain_metrics(date, date);

CREATE OR REPLACE FUNCTION public.get_domain_metrics(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, num_sus_domain bigint, num_alert_domain bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		domain_sus_metrics.organizations_uid,
		domain_sus_metrics.num_sus_domain,
		domain_alert_metrics.num_alert_domain
	FROM
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(domain_sus.num_sus_domain, 0) num_sus_domain
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						domain_permutations.organizations_uid,
						COUNT(*) as num_sus_domain
					FROM
						public.domain_permutations
					WHERE
						date_active BETWEEN start_date AND end_date
						AND
						malicious = True
					GROUP BY
						domain_permutations.organizations_uid
				) domain_sus
				ON reported_orgs.organizations_uid = domain_sus.organizations_uid
		) domain_sus_metrics
		INNER JOIN
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(domain_alerts.num_alert_domain, 0) num_alert_domain
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						domain_alerts.organizations_uid,
						COUNT(*) as num_alert_domain
					FROM
						public.domain_alerts
					WHERE
						date BETWEEN start_date AND end_date
					GROUP BY
						domain_alerts.organizations_uid
				) domain_alerts
				ON reported_orgs.organizations_uid = domain_alerts.organizations_uid
		) domain_alert_metrics
		ON
		domain_sus_metrics.organizations_uid = domain_alert_metrics.organizations_uid;
END; $function$
;

-- DROP FUNCTION public.get_vuln_metrics(date, date);

CREATE OR REPLACE FUNCTION public.get_vuln_metrics(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, num_verif_vulns bigint, num_assets_unverif_vulns bigint, num_insecure_ports bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		verif_vuln_metrics.organizations_uid,
		verif_vuln_metrics.num_verif_vulns,
		assets_unverif_vuln_metrics.num_assets_unverif_vulns,
		insecure_port_metrics.num_insecure_ports
	FROM
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(verif_vulns.num_verif_vulns, 0) AS num_verif_vulns
			FROM
				(
					/* Orgs we're reporting on */
					SELECT
						organizations.organizations_uid
					FROM
						public.organizations
					WHERE
						report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						cve_ip_combos.organizations_uid,
						COUNT(*) as num_verif_vulns
					FROM
						(
							SELECT DISTINCT
								vw_shodanvulns_verified.organizations_uid,
								cve,
								ip
							FROM
								public.vw_shodanvulns_verified
							WHERE
								timestamp BETWEEN start_date AND end_date
						) cve_ip_combos
					GROUP BY
						cve_ip_combos.organizations_uid
				) verif_vulns
				ON
				reported_orgs.organizations_uid = verif_vulns.organizations_uid
		) verif_vuln_metrics
		INNER JOIN
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(assets_unverif_vulns.num_assets_unverif_vuln, 0) AS num_assets_unverif_vulns
			FROM
				(
					/* Orgs we're reporting on */
						SELECT
							organizations.organizations_uid
						FROM
							public.organizations
						WHERE
							report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						cve_ip_combos.organizations_uid,
						COUNT(*) as num_assets_unverif_vuln
					FROM
						(
							SELECT DISTINCT
								vw_shodanvulns_suspected.organizations_uid,
								potential_vulns,
								ip
							FROM
								public.vw_shodanvulns_suspected
							WHERE
								timestamp BETWEEN start_date AND end_date
								AND
								vw_shodanvulns_suspected.type != 'Insecure Protocol'
						) cve_ip_combos
					GROUP BY
						cve_ip_combos.organizations_uid
				) assets_unverif_vulns
				ON
				reported_orgs.organizations_uid = assets_unverif_vulns.organizations_uid
		) assets_unverif_vuln_metrics
		ON
		verif_vuln_metrics.organizations_uid = assets_unverif_vuln_metrics.organizations_uid
		INNER JOIN
		(
			SELECT
				reported_orgs.organizations_uid,
				COALESCE(insecure_ports.num_risky_port, 0) AS num_insecure_ports
			FROM
				(
					/* Orgs we're reporting on */
						SELECT
							organizations.organizations_uid
						FROM
							public.organizations
						WHERE
							report_on = True
				) reported_orgs
				LEFT JOIN
				(
					SELECT
						risky_ports.organizations_uid,
						COUNT(port) as num_risky_port
					FROM
						(
							SELECT DISTINCT
								vw_shodanvulns_suspected.organizations_uid,
								protocol,
								ip,
								port
							FROM
								public.vw_shodanvulns_suspected
							WHERE
								vw_shodanvulns_suspected.type = 'Insecure Protocol'
								AND
								(protocol != 'http' AND protocol != 'smtp')
								AND
								timestamp BETWEEN start_date AND end_date
						) risky_ports
					GROUP BY
						risky_ports.organizations_uid
				) insecure_ports
				ON
				reported_orgs.organizations_uid = insecure_ports.organizations_uid
		) insecure_port_metrics
		ON
		verif_vuln_metrics.organizations_uid = insecure_port_metrics.organizations_uid;
END; $function$
;

-- DROP FUNCTION public.hmac(bytea, bytea, text);

CREATE OR REPLACE FUNCTION public.hmac(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_hmac$function$
;

-- DROP FUNCTION public.hmac(text, text, text);

CREATE OR REPLACE FUNCTION public.hmac(text, text, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pg_hmac$function$
;

-- DROP FUNCTION public.insert_cidr(inet, uuid, text, date, date);

CREATE OR REPLACE FUNCTION public.insert_cidr(arg_net inet, arg_org_uid uuid, arg_data_src text, arg_first_seen date, arg_last_seen date)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
declare
    parent_uid uuid := null;
    comp_cidr_uid uuid := null;
    comp_net cidr;
    comp_uid uuid := null;
    comp_parent_uid uuid := null;
    comp_cyhy_id text := null;
    save_to_db boolean := true;
    ds_uid uuid := null;
    new_cidr_uid uuid := null;
    in_cidrs record;
    cidrs_in record;
begin
        select o.parent_org_uid into parent_uid from organizations o where o.organizations_uid = arg_org_uid;
        select ds.data_source_uid into ds_uid from data_source ds where ds.name = arg_data_src;
        -- Check if any cidrs equal the provided cidr
        select ct.cidr_uid, o.organizations_uid , ct.network, o.parent_org_uid, o."cyhy_db_name"  as parent_id from cidrs ct
        join organizations o on ct.organizations_uid = o.organizations_uid
        where ct.network = arg_net into comp_cidr_uid, comp_uid, comp_net, comp_parent_uid, comp_cyhy_id;
        if (comp_net is not null) then
            --if the already saved cidr's org is the given cidr's parent org
            if (comp_uid = parent_uid) then
                -- point given cidr to the new child org
                update cidrs set organizations_uid = arg_org_uid, last_seen = arg_last_seen
                where organizations_uid = comp_uid and network = arg_net;
                new_cidr_uid := comp_cidr_uid;
                save_to_db := false;
            --if the given cidr is the parent to the already saved cidr.
            --(the cidr exists in the db and has already been assigned to a
            --child org. We know this is true if the provided cidr's org_uid is equal
            --to the already existing cidr's parent_org_uid)
            elseif (arg_org_uid = comp_parent_uid) then
            	-- update last_seen
            	update cidrs set last_seen = arg_last_seen
            	where network = arg_net;
                raise notice 'This cidr already exists in a child organization';
                save_to_db := false;
                --return comp_cidr_uid;
            -- if the cidr already exists and the same org
            elseif (arg_org_uid = comp_uid) then
            update cidrs set last_seen = arg_last_seen
            where organizations_uid = comp_uid and network = arg_net;
            new_cidr_uid := comp_cidr_uid;
            save_to_db :=false;
            --if the orgs are not related
            else
                insert into cidrs (network, organizations_uid, insert_alert, data_source_uid, first_seen, last_seen)
                values (arg_net, arg_org_uid, 'Cidr duplicate between unrelated org. This cidr is also found in the following org. org_cyhy_id:' || comp_cyhy_id || ' org_uid: ' || comp_uid , ds_uid, arg_first_seen, arg_last_seen)
                on conflict (organizations_uid, network )
                do update set last_seen = excluded.last_seen
                returning cidr_uid into new_cidr_uid;
                save_to_db := false;
            end if;
        end if;
        -- Check if the cidr is contained in an existing cidr block
        if exists(select ct.network from cidrs ct where arg_net << ct.network) then
            for in_cidrs in select o.organizations_uid , tct.network, o.parent_org_uid, tct.cidr_uid from cidrs tct
            join organizations o on o.organizations_uid = tct.organizations_uid where arg_net << tct.network and tct."current" loop
                -- Our cidr is found in an existing cidr for the same org
                --do nothing
                if (in_cidrs.organizations_uid = arg_org_uid) then
                    raise notice 'This cidr is containeed in another cidr for the same organization';
                    save_to_db := false;
                -- Our cidr is found in an existing cidr related to our parent org
                -- add cidr
                elseif (in_cidrs.organizations_uid = parent_uid) then
                    if (new_cidr_uid is null) then
                        insert into cidrs (network, organizations_uid , data_source_uid, first_seen, last_seen)
                        values (arg_net, arg_org_uid, ds_uid, arg_first_seen, arg_last_seen)
                        on conflict (organizations_uid, network )
                        do update set last_seen = excluded.last_seen
                        returning cidr_uid into new_cidr_uid;
                        save_to_db := false;
                    end if;
                    --UPDATE IPS THAT BELONG TO THIS CIDR TO POINT HERE *******************************************
                    update ips
                    set origin_cidr = new_cidr_uid
                    where ip << arg_net
                    and origin_cidr = in_cidrs.cidr_uid;
                -- Our cidr is found in an existing cidr related to our child org
                -- don't add cidr
                elseif (arg_org_uid = in_cidrs.parent_org_uid) then
                    save_to_db := false;
                --Our cidr is found in an existing cidr unrelated to our org
                -- insert with an insert warning
                else
                    insert into cidrs (network, organizations_uid, insert_alert, data_source_uid, first_seen, last_seen)
                    values (arg_net, arg_org_uid, 'This cidr range is contained in another cidr owned by the following unrelated org. org_uid:' || in_cidrs.organizations_uid , ds_uid, arg_first_seen, arg_last_seen)
                    on conflict (organizations_uid, network)
                    DO UPDATE SET insert_alert = cidrs.insert_alert || ', ' || in_cidrs.organizations_uid,
                    last_seen = excluded.last_seen
                    returning cidr_uid into new_cidr_uid;
                    save_to_db := false;
                end if;
            end loop;
        end if;
        -- Check if any cidrs are contained within it
        if exists(select ct.network from cidrs ct where ct.network << arg_net ) then
            for cidrs_in in select cidr_uid, o.organizations_uid , tct.network, o.parent_org_uid, tct.cidr_uid from cidrs tct
            join organizations o on o.organizations_uid = tct.organizations_uid where tct.network << arg_net  loop
                -- an existing cidr is found in our cidr for the same org
                -- update existing cidr to current cidr
                if (cidrs_in.organizations_uid = arg_org_uid) then
                    if (new_cidr_uid is null) then
                        insert into cidrs (network, organizations_uid , data_source_uid, first_seen, last_seen)
                        values (arg_net, arg_org_uid, ds_uid, arg_first_seen, arg_last_seen)
                        on conflict (organizations_uid, network )
                        do update set last_seen = excluded.last_seen
                        returning cidr_uid into new_cidr_uid;
                        save_to_db := false;
                    end if;
                    --update all ips to point to this new cidr block
                    update ips
                    set origin_cidr = new_cidr_uid
                    where ip << arg_net
                    and origin_cidr = cidrs_in.cidr_uid;
                    --delete the old cidr
                    DELETE FROM cidrs
                    WHERE network = cidrs_in.network
                    and organizations_uid = arg_org_uid;
                -- an existing cidr related to our parent org is found in our cidr
                -- update existing cidr to our org and cidr
                elseif (cidrs_in.organizations_uid = parent_uid) then
                    if (new_cidr_uid is null) then
                        insert into cidrs (network, organizations_uid , data_source_uid, first_seen, last_seen)
                        values (arg_net, arg_org_uid, ds_uid, arg_first_seen, arg_last_seen)
                        on conflict (organizations_uid, network )
                        do update set last_seen = excluded.last_seen
                        returning cidr_uid into new_cidr_uid;
                        save_to_db := false;
                    end if;
                    --update all ips to point to this new cidr block
                    update ips
                    set origin_cidr = new_cidr_uid
                    where ip << arg_net
                    and origin_cidr = cidrs_in.cidr_uid;
                    --delete the old cidr
                    DELETE FROM cidrs
                    WHERE network = cidrs_in.network
                    and organizations_uid = arg_org_uid;
                -- an existing cidr is found in our cidr related to our child org
                -- add new cidr to our org
                elseif (arg_org_uid = cidrs_in.parent_org_uid) then
                    if (new_cidr_uid is null) then
                        insert into cidrs (network, organizations_uid , data_source_uid, first_seen, last_seen)
                        values (arg_net, arg_org_uid, ds_uid, arg_first_seen, arg_last_seen)
                        on conflict (organizations_uid, network )
                        do update set last_seen = excluded.last_seen
                        returning cidr_uid into new_cidr_uid;
                        save_to_db := false;
                    end if;
                    update ips
                    set origin_cidr = cidrs_in.cidr_uid
                    where ip << cidrs_in.network
                    and origin_cidr = arg_net;
                --an existing cidr unrelated to our org is found in our cidr
                -- insert with an insert warning
                else
                    insert into cidrs (network, organizations_uid, insert_alert, data_source_uid, first_seen, last_seen)
                    values (arg_net, arg_org_uid, 'another cidr owned by the following unrelated org is contained in this cidr range  . org_uid:' || cidrs_in.organizations_uid , ds_uid, arg_first_seen, arg_last_seen)
                    on conflict (organizations_uid, network)
                    DO UPDATE SET insert_alert = cidrs.insert_alert || ', ' || cidrs_in.organizations_uid,
                    last_seen = excluded.last_seen
                    returning cidr_uid into new_cidr_uid;
                    save_to_db := false;
                end if;
            end loop;
            save_to_db := false;
        end if;
        if (save_to_db = true) then
            insert into cidrs (network, organizations_uid , data_source_uid, first_seen, last_seen)
            values (arg_net, arg_org_uid, ds_uid, arg_first_seen, arg_last_seen)
            on conflict (organizations_uid, network )
            do update set last_seen = excluded.last_seen
            returning cidr_uid into new_cidr_uid;
        end if;
    return new_cidr_uid;
end;
$function$
;

-- DROP FUNCTION public.insert_sub_domain(bool, date, text, uuid, text, text, uuid);

CREATE OR REPLACE FUNCTION public.insert_sub_domain(arg_identified boolean, arg_date date, sub_d text, org_uid uuid, data_src text, root_d text DEFAULT NULL::text, root_d_uid uuid DEFAULT NULL::uuid)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
declare
	sub_id uuid;
	ds_uid uuid := null;
begin
		-- Try to fetch the subdomain
		select sub_domain_uid into sub_id from sub_domains sd
		join root_domains rd on rd.root_domain_uid = sd.root_domain_uid
		where sd.sub_domain = sub_d
		and rd.organizations_uid = org_uid;

		-- If the subdomain does not exist in the databse, create record
		if (sub_id is null) then
			-- If no root_domain_uid is provided to this function, look it up
			if (root_d_uid is null and root_d is not null) then
				begin
					select rd.root_domain_uid into root_d_uid
					from root_domains rd
					where rd.root_domain = root_d and rd.organizations_uid = org_uid;
					raise notice 'uid found: %', root_d_uid;
				end;
			else
					raise notice 'uid provided: %', root_d_uid;
			end if;

			-- Query the data_source_uid based on the provided data source name
			select ds.data_source_uid into ds_uid from data_source ds where ds.name = data_src;

			-- If no root_domain_uid provided nor found, create a new root domain and return the root_domain_uid
			if (root_d_uid is null) then
				begin
					insert into root_domains (organizations_uid, root_domain, data_source_uid, enumerate_subs)
					values (org_uid, root_d, ds_uid, false)
					on conflict (organizations_uid, root_domain) do nothing;
					-- Get newly created root domain's uid
					select rd.root_domain_uid into root_d_uid from root_domains rd where rd.root_domain = root_d;
				end;
			end if;

			-- Create sub_domain and return uid
			insert into sub_domains (sub_domain, root_domain_uid, data_source_uid, first_seen, last_seen, identified)
			values (sub_d, root_d_uid, ds_uid, arg_date, arg_date, arg_identified)
			on conflict (sub_domain, root_domain_uid)
			do update set last_seen = excluded.last_seen, identified = EXCLUDED.identified
			returning sub_domain_uid into sub_id;
			raise notice 'uid out of if: %', root_d_uid;
	 	end if;
 	return sub_id;
end;
$function$
;

-- DROP FUNCTION public.insert_sub_domain_new(bool, date, text, uuid, text, text, uuid);

CREATE OR REPLACE FUNCTION public.insert_sub_domain_new(arg_identified boolean, arg_date date, sub_d text, org_uid uuid, data_src text, root_d text DEFAULT NULL::text, root_d_uid uuid DEFAULT NULL::uuid)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
declare
	sub_id uuid;
	ds_uid uuid := null;
begin
		-- Try to fetch the subdomain's uid
		select sub_domain_uid into sub_id from sub_domains sd
		join root_domains rd on rd.root_domain_uid = sd.root_domain_uid
		where sd.sub_domain = sub_d
		and rd.organizations_uid = org_uid;

		-- If the subdomain does not exist in the databse, create subdomain record
		if (sub_id is null) then
			-- Query the data_source_uid based on the provided data source name
			select ds.data_source_uid into ds_uid from data_source ds where ds.name = data_src;

			-- Query the root domain for this subdomain
			if (root_d_uid is null and root_d is not null) then
				-- If no root_domain_uid is provided to this function, look it up in the root_domains table
				begin
					select rd.root_domain_uid into root_d_uid
					from root_domains rd
					where rd.root_domain = root_d and rd.organizations_uid = org_uid;
					raise notice 'uid found: %', root_d_uid;
				end;
			else
				-- Otherwise, use the provided root_domain_uid
					raise notice 'uid provided: %', root_d_uid;
			end if;
			-- If no root_domain_uid provided nor found, create a new root domain record and return its uid
			if (root_d_uid is null) then
				begin
					insert into root_domains (organizations_uid, root_domain, data_source_uid, enumerate_subs)
					values (org_uid, root_d, ds_uid, false)
					on conflict (organizations_uid, root_domain) do nothing;
					-- Get newly created root domain's uid
					select rd.root_domain_uid into root_d_uid from root_domains rd where rd.root_domain = root_d;
				end;
			end if;

			-- Create sub_domain and return uid
			insert into sub_domains (sub_domain, root_domain_uid, data_source_uid, first_seen, last_seen, identified)
			values (sub_d, root_d_uid, ds_uid, arg_date, arg_date, arg_identified)
			on conflict (sub_domain, root_domain_uid)
			do update set last_seen = excluded.last_seen, identified = EXCLUDED.identified
			returning sub_domain_uid into sub_id;
			raise notice 'uid out of if: %', root_d_uid;
	 	end if;
 	return sub_id;
end;$function$
;

-- DROP FUNCTION public.link_ips_and_subs(date, text, inet, uuid, text, text, uuid, text);

CREATE OR REPLACE FUNCTION public.link_ips_and_subs(arg_date date, arg_ip_hash text, arg_ip inet, arg_org_uid uuid, arg_sub_domain text, arg_data_src text, arg_root_uid uuid DEFAULT NULL::uuid, arg_root text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
declare
	sub_id uuid;
	ip_hash_return text;
	ds_uid uuid := null;
	i_s_uid uuid := null;
begin

		-- Insert ip, if it already exists then update last_seen
		insert into ips (ip_hash, ip, first_seen, last_seen, organizations_uid)
		values (arg_ip_hash, arg_ip, arg_date, arg_date, arg_org_uid)
		on conflict (ip)
		do update set
			last_seen = EXCLUDED.last_seen,
			organizations_uid = EXCLUDED.organizations_uid;



	   -- Get sub domain uid (add it if it doesn't exist)
	   -- If root is null, don't pass root domain to insert subs
	   if (arg_root is null) then
	   		select insert_sub_domain(arg_identified => true, arg_date=> arg_date, sub_d=> arg_sub_domain, org_uid => arg_org_uid, data_src => arg_data_src,root_d_uid => arg_root_uid)
	   		into sub_id;
	   -- Else, pass root domain to insert subs
	   else
	   		select insert_sub_domain(arg_identified => true, arg_date=> arg_date, sub_d=> arg_sub_domain, org_uid => arg_org_uid, data_src => arg_data_src, root_d => arg_root)
	   		into sub_id;
	   end if;


	  -- Insert into ip_subs table
	  insert into ips_subs (ip_hash, sub_domain_uid, first_seen, last_seen)
	  values (arg_ip_hash, sub_id, arg_date, arg_date)
	  on conflict(ip_hash, sub_domain_uid)
	  do update set
	  		last_seen = EXCLUDED.last_seen
	  returning ips_subs_uid into i_s_uid; -- insert both fk ids into the product_order table

	return i_s_uid;
end;
$function$
;

-- DROP FUNCTION public.pes_base_metrics(date, date);

CREATE OR REPLACE FUNCTION public.pes_base_metrics(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, cyhy_db_name text, num_breaches bigint, num_total_creds bigint, num_pass_creds bigint, num_alert_domain bigint, num_sus_domain bigint, num_insecure_ports bigint, num_verif_vulns bigint, num_assets_unverif_vulns bigint, num_dw_alerts bigint, num_dw_mentions bigint, num_dw_threats bigint, num_dw_invites bigint, num_ports bigint, num_root_domain bigint, num_sub_domain bigint, num_ips bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		cred_metrics.organizations_uid,
		attacksurface_metrics.cyhy_db_name,
		cred_metrics.num_breaches,
		cred_metrics.total_creds AS num_total_creds,
		cred_metrics.password_creds AS num_pass_creds,
		domain_metrics.num_alert_domain,
		domain_metrics.num_sus_domain,
		vuln_metrics.num_insecure_ports,
		vuln_metrics.num_verif_vulns,
		vuln_metrics.num_assets_unverif_vulns,
		darkweb_metrics.num_dw_alerts,
		darkweb_metrics.num_dw_mentions,
		darkweb_metrics.num_dw_threats,
		darkweb_metrics.num_dw_invites,
		attacksurface_metrics.num_ports,
		attacksurface_metrics.num_root_domain,
		attacksurface_metrics.num_sub_domain,
		attacksurface_metrics.num_ips
	FROM
		(
			SELECT
				*
			FROM
				get_cred_metrics(start_date, end_date)
		) cred_metrics
		INNER JOIN
		(
			SELECT
				*
			FROM
				get_domain_metrics(start_date, end_date)
		) domain_metrics
		ON
		cred_metrics.organizations_uid = domain_metrics.organizations_uid
		INNER JOIN
		(
			SELECT
				*
			FROM
				get_vuln_metrics(start_date, end_date)
		) vuln_metrics
		ON
		cred_metrics.organizations_uid = vuln_metrics.organizations_uid
		INNER JOIN
		(
			SELECT
				*
			FROM
				get_darkweb_metrics(start_date, end_date)
		) darkweb_metrics
		ON
		cred_metrics.organizations_uid = darkweb_metrics.organizations_uid
		INNER JOIN
		(
			SELECT
				*
			FROM
				public.vw_orgs_attacksurface
		) attacksurface_metrics
		ON
		cred_metrics.organizations_uid = attacksurface_metrics.organizations_uid
	ORDER BY
		attacksurface_metrics.cyhy_db_name ASC;
END; $function$
;

-- DROP FUNCTION public.pes_check_new_cve(date, date);

CREATE OR REPLACE FUNCTION public.pes_check_new_cve(start_date date, end_date date)
 RETURNS TABLE(cve_name text)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		current_cves.cve_name
	FROM
		(
			/* Select unverified CVEs */
			SELECT
				reported_orgs.organizations_uid,
				reported_orgs.cyhy_db_name,
				unverif_cve_list.unverif_cve as cve_name
			FROM
				(
					SELECT
						organizations.organizations_uid,
						organizations.cyhy_db_name
					FROM
						public.organizations
					WHERE
						organizations.report_on = True
				) reported_orgs
				INNER JOIN
				(
					SELECT DISTINCT
						vss.organizations_uid,
						UNNEST(vss.potential_vulns) as unverif_cve
					FROM
						public.vw_shodanvulns_suspected vss
					WHERE
						vss."type" != 'Insecure Protocol'
						AND
						vss.timestamp BETWEEN start_date AND end_date
				) unverif_cve_list
				ON
				reported_orgs.organizations_uid = unverif_cve_list.organizations_uid
			UNION
			/* Select verified CVEs */
			SELECT
				reported_orgs.organizations_uid,
				reported_orgs.cyhy_db_name,
				verif_cve_list.cve as cve_name
			FROM
				(
					SELECT
						organizations.organizations_uid,
						organizations.cyhy_db_name
					FROM
						public.organizations
					WHERE
						organizations.report_on = True
				) reported_orgs
				INNER JOIN
				(
					SELECT DISTINCT
						shodan_vulns.organizations_uid,
						shodan_vulns.cve
					FROM
						public.shodan_vulns
					WHERE
						shodan_vulns.timestamp BETWEEN start_date AND end_date
						AND
						shodan_vulns.is_verified = true
				) verif_cve_list
				ON
				reported_orgs.organizations_uid = verif_cve_list.organizations_uid
		) current_cves
		LEFT JOIN
		public.cve_info
		ON
		current_cves.cve_name = cve_info.cve_name
	WHERE
		cve_info.cve_name IS NULL;
END; $function$
;

-- DROP FUNCTION public.pes_cve_metrics(date, date);

CREATE OR REPLACE FUNCTION public.pes_cve_metrics(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, cyhy_db_name text, num_verif_cve bigint, num_verif_low bigint, num_verif_med bigint, num_verif_high bigint, num_verif_crit bigint, max_verif_cvss numeric, num_unverif_cve bigint, num_unverif_low bigint, num_unverif_med bigint, num_unverif_high bigint, num_unverif_crit bigint, max_unverif_cvss numeric)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		reported_orgs.organizations_uid,
		reported_orgs.cyhy_db_name,
		COALESCE(verif.num_verif_cves, 0) as num_verif_cve,
		COALESCE(verif.num_verif_low, 0) as num_verif_low,
		COALESCE(verif.num_verif_med, 0) as num_verif_med,
		COALESCE(verif.num_verif_high, 0) as num_verif_high,
		COALESCE(verif.num_verif_crit, 0) as num_verif_crit,
		COALESCE(verif.max_verif_cvss, 0) as max_verif_cvss,
		COALESCE(unverif.num_unverif_cves, 0) as num_unverif_cve,
		COALESCE(unverif.num_unverif_low, 0) as num_unverif_low,
		COALESCE(unverif.num_unverif_med, 0) as num_unverif_med,
		COALESCE(unverif.num_unverif_high, 0) as num_unverif_high,
		COALESCE(unverif.num_unverif_crit, 0) as num_unverif_crit,
		COALESCE(unverif.max_unverif_cvss, 0) as max_unverif_cvss
	FROM
		(
			SELECT
				organizations.organizations_uid,
				organizations.cyhy_db_name
			FROM
				public.organizations
			WHERE
				organizations.report_on = True
		) reported_orgs
		LEFT JOIN
		(
			/* Aggregated counts for verified CVEs */
			SELECT
				verif_cves.organizations_uid,
				verif_cves.cyhy_db_name,
				COUNT(*) as num_verif_cves,
				COUNT(*) FILTER (WHERE verif_cves.cvss_score < 4) as num_verif_low,
				COUNT(*) FILTER (WHERE verif_cves.cvss_score >= 4 AND verif_cves.cvss_score < 7) as num_verif_med,
				COUNT(*) FILTER (WHERE verif_cves.cvss_score >= 7 AND verif_cves.cvss_score < 9) as num_verif_high,
				COUNT(*) FILTER (WHERE verif_cves.cvss_score >= 9) as num_verif_crit,
				MAX(verif_cves.cvss_score) as max_verif_cvss
			FROM
				(
					SELECT
						reported_orgs.organizations_uid,
						reported_orgs.cyhy_db_name,
						verif_cve_list.cve as cve_name,
						COALESCE(cve_info.cvss_3_0, cve_info.cvss_2_0) as cvss_score,
						cve_info.dve_score
					FROM
						(
							/* Orgs that PE reports on */
							SELECT
								organizations.organizations_uid,
								organizations.cyhy_db_name
							FROM
								public.organizations
							WHERE
								organizations.report_on = True
						) reported_orgs
						INNER JOIN
						(
							/* List of verified CVEs for this report period */
							SELECT DISTINCT
								shodan_vulns.organizations_uid,
								shodan_vulns.cve,
								shodan_vulns.cvss,
								shodan_vulns.severity
							FROM
								public.shodan_vulns
							WHERE
								shodan_vulns.timestamp BETWEEN start_date AND end_date
								AND
								shodan_vulns.is_verified = true
						) verif_cve_list
						ON
						reported_orgs.organizations_uid = verif_cve_list.organizations_uid
						INNER JOIN
						/* CVE information */
						public.cve_info
						ON
						verif_cve_list.cve = cve_info.cve_name
					WHERE
						/* Filter out CVEs that don't have CVSS 2.0 nor 3.0 scores */
						NOT (cve_info.cvss_2_0 IS NULL AND cve_info.cvss_3_0 IS NULL)
					ORDER BY
						reported_orgs.cyhy_db_name
				) verif_cves
			GROUP BY
				verif_cves.organizations_uid,
				verif_cves.cyhy_db_name
		) verif
		ON
		reported_orgs.organizations_uid = verif.organizations_uid
		LEFT JOIN
		(
			/* Aggregated counts for unverified CVEs */
			SELECT
				unverif_cves.organizations_uid,
				unverif_cves.cyhy_db_name,
				COUNT(*) as num_unverif_cves,
				COUNT(*) FILTER (WHERE unverif_cves.cvss_score < 4) as num_unverif_low,
				COUNT(*) FILTER (WHERE unverif_cves.cvss_score >= 4 AND unverif_cves.cvss_score < 7) as num_unverif_med,
				COUNT(*) FILTER (WHERE unverif_cves.cvss_score >= 7 AND unverif_cves.cvss_score < 9) as num_unverif_high,
				COUNT(*) FILTER (WHERE unverif_cves.cvss_score >= 9) as num_unverif_crit,
				MAX(unverif_cves.cvss_score) as max_unverif_cvss
			FROM
				(
					SELECT
						reported_orgs.organizations_uid,
						reported_orgs.cyhy_db_name,
						unverif_cve_list.unverif_cve as cve_name,
						COALESCE(cve_info.cvss_3_0, cve_info.cvss_2_0) as cvss_score,
						cve_info.dve_score
					FROM
						(
							/* Orgs that PE reports on */
							SELECT
								organizations.organizations_uid,
								organizations.cyhy_db_name
							FROM
								public.organizations
							WHERE
								organizations.report_on = True
						) reported_orgs
						INNER JOIN
						(
							/* List of unverified CVEs for this report period */
							SELECT DISTINCT
								vss.organizations_uid,
								UNNEST(vss.potential_vulns) as unverif_cve
							FROM
								public.vw_shodanvulns_suspected vss
							WHERE
								vss."type" != 'Insecure Protocol'
								AND
								vss.timestamp BETWEEN start_date AND end_date
						) unverif_cve_list
						ON
						reported_orgs.organizations_uid = unverif_cve_list.organizations_uid
						INNER JOIN
						/* CVE information */
						public.cve_info
						ON
						unverif_cve_list.unverif_cve = cve_info.cve_name
					WHERE
						/* Filter out CVEs that don't have CVSS 2.0 nor 3.0 scores */
						NOT (cve_info.cvss_2_0 IS NULL AND cve_info.cvss_3_0 IS NULL)
					ORDER BY
						reported_orgs.cyhy_db_name
				) unverif_cves
			GROUP BY
				unverif_cves.organizations_uid,
				unverif_cves.cyhy_db_name
		) unverif
		ON
		reported_orgs.organizations_uid = unverif.organizations_uid
	ORDER BY
		reported_orgs.cyhy_db_name;
END; $function$
;

-- DROP FUNCTION public.pes_hist_data_domalert(date, date);

CREATE OR REPLACE FUNCTION public.pes_hist_data_domalert(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, cyhy_db_name text, mod_date date)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		reported_orgs.organizations_uid,
		reported_orgs.cyhy_db_name,
		domain_alerts.date as mod_date
	FROM
		(
			/* Orgs we're reporting on */
			SELECT
				organizations.organizations_uid,
				organizations.cyhy_db_name
			FROM
				public.organizations
			WHERE
				report_on = True
		) reported_orgs
		LEFT JOIN
		(
			SELECT
				domain_alerts.organizations_uid,
				domain_alerts.date
			FROM
				public.domain_alerts
			WHERE
				domain_alerts.date BETWEEN start_date AND end_date
		) domain_alerts
		ON reported_orgs.organizations_uid = domain_alerts.organizations_uid
	ORDER BY
		reported_orgs.cyhy_db_name,
		domain_alerts.date;
END; $function$
;

-- DROP FUNCTION public.pes_hist_data_dwalert(date, date);

CREATE OR REPLACE FUNCTION public.pes_hist_data_dwalert(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, cyhy_db_name text, mod_date date)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		reported_orgs.organizations_uid,
		reported_orgs.cyhy_db_name,
		alerts.date AS mod_date
	FROM
		(
			/* Orgs we're reporting on */
			SELECT
				organizations.organizations_uid,
				organizations.cyhy_db_name
			FROM
				public.organizations
			WHERE
				report_on = True
		) reported_orgs
		LEFT JOIN
		(
			/* Get count of dark web alerts for the report period*/
			SELECT
				alerts.organizations_uid,
				alerts.date
			FROM
				public.alerts
			WHERE
				alerts.date BETWEEN start_date AND end_date
		) alerts
		ON reported_orgs.organizations_uid = alerts.organizations_uid
	ORDER BY
		reported_orgs.cyhy_db_name,
		alerts.date;
END; $function$
;

-- DROP FUNCTION public.pes_hist_data_dwment(date, date);

CREATE OR REPLACE FUNCTION public.pes_hist_data_dwment(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, cyhy_db_name text, date date, num_mentions bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		reported_orgs.organizations_uid,
		reported_orgs.cyhy_db_name,
		dw_mentions.date,
		COALESCE(dw_mentions."Count", 0) as num_mentions
	FROM
		(
			SELECT
				organizations.organizations_uid,
				organizations.cyhy_db_name
			FROM
				public.organizations
			WHERE
				report_on = True
		) reported_orgs
		LEFT JOIN
		(
			SELECT
				*
			FROM
				public.vw_darkweb_mentionsbydate dwm
			WHERE
				dwm.date BETWEEN start_date AND end_date
		) dw_mentions
		ON
		reported_orgs.organizations_uid = dw_mentions.organizations_uid;
END; $function$
;

-- DROP FUNCTION public.pes_hist_data_totcred(date, date);

CREATE OR REPLACE FUNCTION public.pes_hist_data_totcred(start_date date, end_date date)
 RETURNS TABLE(organizations_uid uuid, cyhy_db_name text, mod_date date, no_password bigint, password_included bigint, total_creds bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
RETURN QUERY
	SELECT
		reported_orgs.organizations_uid,
		reported_orgs.cyhy_db_name,
		cred_dat.mod_date,
		COALESCE(cred_dat.no_password, 0) as no_password,
		COALESCE(cred_dat.password_included, 0) as password_included,
		COALESCE(cred_dat.total_creds, 0) as total_creds
	FROM
		(
			SELECT
				organizations.organizations_uid,
				organizations.cyhy_db_name
			FROM
				public.organizations
			WHERE
				report_on = True
		) reported_orgs
		LEFT JOIN
		(
			SELECT
				*,
				vw_breachcomp_credsbydate.no_password + vw_breachcomp_credsbydate.password_included as total_creds
			FROM
				public.vw_breachcomp_credsbydate
			WHERE
				vw_breachcomp_credsbydate.mod_date BETWEEN start_date AND end_date
		) cred_dat
		ON
		reported_orgs.organizations_uid = cred_dat.organizations_uid
	ORDER BY
		reported_orgs.cyhy_db_name,
		cred_dat.mod_date;
END; $function$
;

-- DROP FUNCTION public.pgp_armor_headers(in text, out text, out text);

CREATE OR REPLACE FUNCTION public.pgp_armor_headers(text, OUT key text, OUT value text)
 RETURNS SETOF record
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_armor_headers$function$
;

-- DROP FUNCTION public.pgp_key_id(bytea);

CREATE OR REPLACE FUNCTION public.pgp_key_id(bytea)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_key_id_w$function$
;

-- DROP FUNCTION public.pgp_pub_decrypt(bytea, bytea, text, text);

CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt(bytea, bytea, text, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_text$function$
;

-- DROP FUNCTION public.pgp_pub_decrypt(bytea, bytea, text);

CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt(bytea, bytea, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_text$function$
;

-- DROP FUNCTION public.pgp_pub_decrypt(bytea, bytea);

CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt(bytea, bytea)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_text$function$
;

-- DROP FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text, text);

CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_bytea$function$
;

-- DROP FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea);

CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_bytea$function$
;

-- DROP FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text);

CREATE OR REPLACE FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_decrypt_bytea$function$
;

-- DROP FUNCTION public.pgp_pub_encrypt(text, bytea, text);

CREATE OR REPLACE FUNCTION public.pgp_pub_encrypt(text, bytea, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_encrypt_text$function$
;

-- DROP FUNCTION public.pgp_pub_encrypt(text, bytea);

CREATE OR REPLACE FUNCTION public.pgp_pub_encrypt(text, bytea)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_encrypt_text$function$
;

-- DROP FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea);

CREATE OR REPLACE FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_encrypt_bytea$function$
;

-- DROP FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea, text);

CREATE OR REPLACE FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_pub_encrypt_bytea$function$
;

-- DROP FUNCTION public.pgp_sym_decrypt(bytea, text);

CREATE OR REPLACE FUNCTION public.pgp_sym_decrypt(bytea, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_decrypt_text$function$
;

-- DROP FUNCTION public.pgp_sym_decrypt(bytea, text, text);

CREATE OR REPLACE FUNCTION public.pgp_sym_decrypt(bytea, text, text)
 RETURNS text
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_decrypt_text$function$
;

-- DROP FUNCTION public.pgp_sym_decrypt_bytea(bytea, text);

CREATE OR REPLACE FUNCTION public.pgp_sym_decrypt_bytea(bytea, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_decrypt_bytea$function$
;

-- DROP FUNCTION public.pgp_sym_decrypt_bytea(bytea, text, text);

CREATE OR REPLACE FUNCTION public.pgp_sym_decrypt_bytea(bytea, text, text)
 RETURNS bytea
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_decrypt_bytea$function$
;

-- DROP FUNCTION public.pgp_sym_encrypt(text, text);

CREATE OR REPLACE FUNCTION public.pgp_sym_encrypt(text, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_encrypt_text$function$
;

-- DROP FUNCTION public.pgp_sym_encrypt(text, text, text);

CREATE OR REPLACE FUNCTION public.pgp_sym_encrypt(text, text, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_encrypt_text$function$
;

-- DROP FUNCTION public.pgp_sym_encrypt_bytea(bytea, text);

CREATE OR REPLACE FUNCTION public.pgp_sym_encrypt_bytea(bytea, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_encrypt_bytea$function$
;

-- DROP FUNCTION public.pgp_sym_encrypt_bytea(bytea, text, text);

CREATE OR REPLACE FUNCTION public.pgp_sym_encrypt_bytea(bytea, text, text)
 RETURNS bytea
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pgcrypto', $function$pgp_sym_encrypt_bytea$function$
;

-- DROP FUNCTION public.query_breach(text);

CREATE OR REPLACE FUNCTION public.query_breach(b_name text)
 RETURNS TABLE(breach_name text, description text, exposed_cred_count bigint, breach_date date, added_date timestamp without time zone, modified_date timestamp without time zone, data_classes text[], password_included boolean, is_verified boolean, data_source text)
 LANGUAGE plpgsql
AS $function$
BEGIN
   RETURN QUERY
   SELECT cb.breach_name, cb.description, cb.exposed_cred_count, cb.breach_date,
   			cb.added_date , cb.modified_date, cb.data_classes, cb.password_included ,
   			cb.is_verified , ds.name-- I added parentheses
   FROM  credential_breaches cb
   join data_source ds on ds.data_source_uid = cb.data_source_uid
   where lower(cb.breach_name) = lower(b_name);                    -- potential ambiguity
END
$function$
;

-- DROP FUNCTION public.query_emails(text, text);

CREATE OR REPLACE FUNCTION public.query_emails(b_name text, org_id text)
 RETURNS TABLE(email text, org_name text, org_cyhy_id text, data_source text, name text, login_id text, phone text, password text, hash_type text)
 LANGUAGE plpgsql
AS $function$
BEGIN
   RETURN QUERY
   SELECT c.email, o.name, o.cyhy_db_name, d.name, c.name, c.login_id, c.phone, c.password, c.hash_type -- I added parentheses
   FROM  credential_exposures c
   join organizations o on o.organizations_uid = c.organizations_uid
   join data_source d on d.data_source_uid = c.data_source_uid
    where lower(c.breach_name) = lower(b_name)
    and o.cyhy_db_name = org_id;                    -- potential ambiguity
END
$function$
;

-- DROP FUNCTION public.set_status_completed_and_week_ending();

CREATE OR REPLACE FUNCTION public.set_status_completed_and_week_ending()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW."statusComplete" := 1;
    NEW.week_ending := date_trunc('week', CURRENT_DATE) + interval '4 days';
    RETURN NEW;
END;
$function$
;

-- DROP FUNCTION public.uuid_generate_v1();

CREATE OR REPLACE FUNCTION public.uuid_generate_v1()
 RETURNS uuid
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v1$function$
;

-- DROP FUNCTION public.uuid_generate_v1mc();

CREATE OR REPLACE FUNCTION public.uuid_generate_v1mc()
 RETURNS uuid
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v1mc$function$
;

-- DROP FUNCTION public.uuid_generate_v3(uuid, text);

CREATE OR REPLACE FUNCTION public.uuid_generate_v3(namespace uuid, name text)
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v3$function$
;

-- DROP FUNCTION public.uuid_generate_v4();

CREATE OR REPLACE FUNCTION public.uuid_generate_v4()
 RETURNS uuid
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v4$function$
;

-- DROP FUNCTION public.uuid_generate_v5(uuid, text);

CREATE OR REPLACE FUNCTION public.uuid_generate_v5(namespace uuid, name text)
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_generate_v5$function$
;

-- DROP FUNCTION public.uuid_nil();

CREATE OR REPLACE FUNCTION public.uuid_nil()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_nil$function$
;

-- DROP FUNCTION public.uuid_ns_dns();

CREATE OR REPLACE FUNCTION public.uuid_ns_dns()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_ns_dns$function$
;

-- DROP FUNCTION public.uuid_ns_oid();

CREATE OR REPLACE FUNCTION public.uuid_ns_oid()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_ns_oid$function$
;

-- DROP FUNCTION public.uuid_ns_url();

CREATE OR REPLACE FUNCTION public.uuid_ns_url()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_ns_url$function$
;

-- DROP FUNCTION public.uuid_ns_x500();

CREATE OR REPLACE FUNCTION public.uuid_ns_x500()
 RETURNS uuid
 LANGUAGE c
 IMMUTABLE PARALLEL SAFE STRICT
AS '$libdir/uuid-ossp', $function$uuid_ns_x500$function$
;

-- Production-equivalent report views for local PE development.
-- Source of truth: edit this file (and local_report_view_order.txt) directly.
-- Flare views filter credential_exposures by the Flare data_source_uid.

CREATE MATERIALIZED VIEW mat_vw_breachcomp AS
 SELECT creds.credential_exposures_uid,
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
    timezone('UTC'::text, ((b.modified_date)::date)::timestamp with time zone) AS modified_date,
    b.data_classes,
    b.password_included,
    b.is_verified,
    b.is_fabricated,
    b.is_sensitive,
    b.is_retired,
    b.is_spam_list
   FROM (credential_exposures creds
     JOIN credential_breaches b ON ((creds.credential_breaches_uid = b.credential_breaches_uid)))
  WHERE (timezone('UTC'::text, ((b.modified_date)::date)::timestamp with time zone) >= (CURRENT_DATE - '30 days'::interval));


CREATE VIEW vw_breachcomp AS
 SELECT creds.credential_exposures_uid,
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
    timezone('UTC'::text, ((b.modified_date)::date)::timestamp with time zone) AS modified_date,
    b.data_classes,
    b.password_included,
    b.is_verified,
    b.is_fabricated,
    b.is_sensitive,
    b.is_retired,
    b.is_spam_list
   FROM (credential_exposures creds
     JOIN credential_breaches b ON ((creds.credential_breaches_uid = b.credential_breaches_uid)))
  WHERE creds.data_source_uid = ANY (ARRAY['fa4e7454-8baa-11ed-b121-02c6a3fe975b'::uuid, '744fb0ec-981d-11ec-a0ff-02589a36c9d7'::uuid]);


CREATE MATERIALIZED VIEW mat_vw_breachcomp_breachdetails AS
 SELECT vb.organizations_uid,
    vb.breach_name,
    date(vb.modified_date) AS mod_date,
    vb.description,
    vb.breach_date,
    vb.password_included,
    count(vb.email) AS number_of_creds
   FROM vw_breachcomp vb
  GROUP BY vb.organizations_uid, vb.breach_name, (date(vb.modified_date)), vb.description, vb.breach_date, vb.password_included
  ORDER BY (date(vb.modified_date)) DESC;


CREATE MATERIALIZED VIEW mat_vw_breachcomp_credsbydate AS
 SELECT vw_breachcomp.organizations_uid,
    date(vw_breachcomp.modified_date) AS mod_date,
    sum(
        CASE vw_breachcomp.password_included
            WHEN false THEN 1
            ELSE 0
        END) AS no_password,
    sum(
        CASE vw_breachcomp.password_included
            WHEN true THEN 1
            ELSE 0
        END) AS password_included
   FROM vw_breachcomp
  GROUP BY vw_breachcomp.organizations_uid, (date(vw_breachcomp.modified_date))
  ORDER BY (date(vw_breachcomp.modified_date)) DESC;


CREATE VIEW vw_breachcomp_breachdetails AS
 SELECT vb.organizations_uid,
    vb.breach_name,
    date(vb.modified_date) AS mod_date,
    vb.description,
    vb.breach_date,
    vb.password_included,
    count(vb.email) AS number_of_creds
   FROM vw_breachcomp vb
  GROUP BY vb.organizations_uid, vb.breach_name, (date(vb.modified_date)), vb.description, vb.breach_date, vb.password_included
  ORDER BY (date(vb.modified_date)) DESC;


CREATE VIEW vw_breachcomp_credsbydate AS
 SELECT vw_breachcomp.organizations_uid,
    date(vw_breachcomp.modified_date) AS mod_date,
    sum(
        CASE vw_breachcomp.password_included
            WHEN false THEN 1
            ELSE 0
        END) AS no_password,
    sum(
        CASE vw_breachcomp.password_included
            WHEN true THEN 1
            ELSE 0
        END) AS password_included
   FROM vw_breachcomp
  GROUP BY vw_breachcomp.organizations_uid, (date(vw_breachcomp.modified_date))
  ORDER BY (date(vw_breachcomp.modified_date)) DESC;


CREATE VIEW vw_darkweb_assetalerts AS
 SELECT a.organizations_uid,
    max(a.date) AS date,
    a.site AS "Site",
    a.title AS "Title",
    count(*) AS "Events"
   FROM alerts a
  WHERE ((a.alert_name !~~ '%executive%'::text) AND (a.site IS NOT NULL) AND (a.site <> 'NaN'::text))
  GROUP BY a.site, a.title, a.organizations_uid
  ORDER BY (count(*)) DESC;


CREATE VIEW vw_darkweb_execalerts AS
 SELECT a.organizations_uid,
    max(a.date) AS date,
    a.site AS "Site",
    a.title AS "Title",
    count(*) AS "Events"
   FROM alerts a
  WHERE ((a.alert_name ~~ '%executive%'::text) AND (a.site IS NOT NULL) AND (a.site <> 'NaN'::text))
  GROUP BY a.site, a.title, a.organizations_uid
  ORDER BY (count(*)) DESC;


CREATE VIEW vw_darkweb_inviteonlymarkets AS
 SELECT a.organizations_uid,
    a.date,
    a.site AS "Site"
   FROM alerts a
  WHERE ((a.site ~~ 'market%'::text) AND (a.site IS NOT NULL) AND (a.site <> 'NaN'::text) AND (a.site <> ''::text));


CREATE VIEW vw_darkweb_mentionsbydate AS
 SELECT m.organizations_uid,
    m.date,
    count(*) AS "Count"
   FROM mentions m
  GROUP BY m.organizations_uid, m.date
  ORDER BY m.date DESC;


CREATE VIEW vw_darkweb_mostactposts AS
 SELECT m.organizations_uid,
    m.date,
    m.title AS "Title",
        CASE
            WHEN (m.comments_count = 'NaN'::text) THEN 1
            WHEN (m.comments_count = '0.0'::text) THEN 1
            WHEN (m.comments_count IS NULL) THEN 1
            WHEN (m.comments_count = ''::text) THEN 1
            ELSE ((m.comments_count)::numeric)::integer
        END AS "Comments Count"
   FROM mentions m
  WHERE ((m.site ~~ 'forum%'::text) OR (m.site ~~ 'market%'::text))
  ORDER BY
        CASE
            WHEN (m.comments_count = 'NaN'::text) THEN 1
            WHEN (m.comments_count = '0.0'::text) THEN 1
            WHEN (m.comments_count IS NULL) THEN 1
            WHEN (m.comments_count = ''::text) THEN 1
            ELSE ((m.comments_count)::numeric)::integer
        END DESC;


CREATE VIEW vw_darkweb_potentialthreats AS
 SELECT a.organizations_uid,
    a.date,
    a.site AS "Site",
    btrim(a.threats, '{}'::text) AS "Threats"
   FROM alerts a
  WHERE ((a.site IS NOT NULL) AND (a.site <> 'NaN'::text) AND (a.site <> ''::text));


CREATE VIEW vw_darkweb_sites AS
 SELECT m.organizations_uid,
    m.date,
    m.site AS "Site"
   FROM mentions m;


CREATE VIEW vw_darkweb_socmedia_mostactposts AS
 SELECT m.organizations_uid,
    m.date,
    m.title AS "Title",
        CASE
            WHEN (m.comments_count = 'NaN'::text) THEN 1
            WHEN (m.comments_count = '0.0'::text) THEN 1
            WHEN (m.comments_count = ''::text) THEN 1
            ELSE ((m.comments_count)::numeric)::integer
        END AS "Comments Count"
   FROM mentions m
  WHERE ((m.site !~~ 'forum%'::text) AND (m.site !~~ 'market%'::text))
  ORDER BY
        CASE
            WHEN (m.comments_count = 'NaN'::text) THEN 1
            WHEN (m.comments_count = '0.0'::text) THEN 1
            WHEN (m.comments_count = ''::text) THEN 1
            ELSE ((m.comments_count)::numeric)::integer
        END DESC;


CREATE VIEW vw_darkweb_threatactors AS
 SELECT m.organizations_uid,
    m.date,
    m.creator AS "Creator",
    round((m.rep_grade)::numeric, 3) AS "Grade"
   FROM mentions m
  ORDER BY (round((m.rep_grade)::numeric, 3)) DESC;


CREATE VIEW vw_ips_sub_root_org_info AS
 SELECT i.ip_hash,
    i.ip,
    i.origin_cidr,
    o.organizations_uid,
    i.current AS i_current,
    sd.current AS sd_current
   FROM ((((ips i
     JOIN ips_subs is2 ON ((i.ip_hash = is2.ip_hash)))
     JOIN sub_domains sd ON ((sd.sub_domain_uid = is2.sub_domain_uid)))
     JOIN root_domains rd ON ((rd.root_domain_uid = sd.root_domain_uid)))
     JOIN organizations o ON ((o.organizations_uid = rd.organizations_uid)));


CREATE VIEW vw_shodanvulns_suspected AS
 SELECT svv.organizations_uid,
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
   FROM (shodan_vulns svv
     JOIN data_source ds ON ((ds.data_source_uid = svv.data_source_uid)))
  WHERE (svv.is_verified = false);


CREATE VIEW vw_shodanvulns_verified AS
 SELECT svv.organizations_uid,
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
   FROM (shodan_vulns svv
     JOIN data_source ds ON ((ds.data_source_uid = svv.data_source_uid)))
  WHERE (svv.is_verified = true);


CREATE VIEW vw_flare_breachcomp AS
 SELECT creds.credential_exposures_uid,
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


CREATE VIEW vw_flare_breachcomp_breachdetails AS
 SELECT vb.organizations_uid,
    vb.breach_name,
    date(vb.modified_date) AS mod_date,
    vb.description,
    vb.breach_date,
    vb.password_included,
    count(vb.email) AS number_of_creds
   FROM vw_flare_breachcomp vb
  GROUP BY vb.organizations_uid, vb.breach_name, (date(vb.modified_date)), vb.description, vb.breach_date, vb.password_included
  ORDER BY (date(vb.modified_date)) DESC;


CREATE VIEW vw_flare_breachcomp_credsbydate AS
 SELECT vw_flare_breachcomp.organizations_uid,
    date(vw_flare_breachcomp.modified_date) AS mod_date,
    sum(
        CASE vw_flare_breachcomp.password_included
            WHEN false THEN 1
            ELSE 0
        END) AS no_password,
    sum(
        CASE vw_flare_breachcomp.password_included
            WHEN true THEN 1
            ELSE 0
        END) AS password_included
   FROM vw_flare_breachcomp
  GROUP BY vw_flare_breachcomp.organizations_uid, (date(vw_flare_breachcomp.modified_date))
  ORDER BY (date(vw_flare_breachcomp.modified_date)) DESC;

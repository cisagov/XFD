import { BaseEntity, ViewEntity, ViewColumn } from 'typeorm';

@ViewEntity({
  name: 'vw_service_stats',
  expression: `
    SELECT o.acronym, o.id as "organizationId", s.service, COUNT(*) AS count, o."regionId" as "regionId"
    FROM service s
    INNER JOIN domain ON s."domainId" = domain.id
    join organization o on domain."organizationId" = o.id 
    WHERE s.service IS NOT NULL 
    AND (domain."isFceb" = true OR (domain."isFceb" = false AND domain."fromCidr" = true))
    GROUP BY o.acronym, o.id, s.service, "regionId"
    ORDER BY count DESC;
  `,
  materialized: true
})
export class VwServiceStats extends BaseEntity {
  @ViewColumn()
  acronym: string;

  @ViewColumn()
  organizationId: string;

  @ViewColumn()
  service: string;

  @ViewColumn()
  count: number;
}

@ViewEntity({
  name: 'vw_port_stats',
  expression: `
    SELECT o.acronym, o.id as "organizationId", s.port, COUNT(*) AS count, o."regionId" as "regionId"
    from "domain" d 
    join service s on s."domainId" = d.id 
    join organization o on d."organizationId" = o.id 
    WHERE (d."isFceb" = true OR (d."isFceb" = false AND d."fromCidr" = true))
    group by o.acronym, o.id, s.port, "regionId"
    ORDER BY count DESC;
  `,
  materialized: true
})
export class VwPortsStats extends BaseEntity {
  @ViewColumn()
  acronym: string;

  @ViewColumn()
  organizationId: string;

  @ViewColumn()
  port: string;

  @ViewColumn()
  count: number;
}

@ViewEntity({
  name: 'vw_num_vulns_stats',
  expression: `
  select acronym, "organizationId", "domainSeverity", "count", "regionId" as "regionId"
  from
  (select o.acronym, o.id as "organizationId", o."regionId" as "regionId", CONCAT(d.name, '|', v.severity) as "domainSeverity", count(*) as count, row_number() over (partition by o.acronym order by count(*) DESC) as row
  from "domain" d 
  join vulnerability v on v."domainId" = d.id 
  join organization o on d."organizationId" = o.id
  where v.state = 'open'
  and (d."isFceb" = true OR (d."isFceb" = false AND d."fromCidr" = true))
  group by  o.acronym, o.id, d.name, v.severity, "regionId"
  order by count desc) as ranked_vulns
  where "row" <= 50;
  `,
  materialized: true
})
export class VwNumVulns extends BaseEntity {
  @ViewColumn()
  acronym: string;

  @ViewColumn()
  organizationId: string;

  @ViewColumn()
  domainSeverity: string;

  @ViewColumn()
  count: number;
}

@ViewEntity({
  name: 'vw_latest_vulns_stats',
  expression: `
    select acronym, "organizationId", id, "createdAt","updatedAt", "lastSeen","title", "cve", "cwe", "cpe","description", "references","cvss","severity", "needsPopulation", "state", "substate","source", "notes","actions","structuredData","isKev","kevResults","domainId","serviceId", "regionId"
    from
    (select o.acronym, o.id as "organizationId", o."regionId" as "regionId", v.*, row_number() over (partition by o.acronym order by v."createdAt" desc) as row
    from vulnerability v 
    left join "domain" d on v."domainId" = d.id 
    join organization o on d."organizationId" = o.id
    where v.state = 'open'
    and (d."isFceb" = true OR (d."isFceb" = false AND d."fromCidr" = true))
    order by v."createdAt" desc) as ranked_vulns
    where "row" <= 50;
  `,
  materialized: true
})
export class VwLatestVulns extends BaseEntity {
  @ViewColumn()
  acronym: string;

  @ViewColumn()
  organizationId: string;

  @ViewColumn()
  id: string;

  @ViewColumn()
  createdAt: string;

  @ViewColumn()
  updatedAt: string;

  @ViewColumn()
  lastSeen: string;

  @ViewColumn()
  title: string;

  @ViewColumn()
  cve: string;

  @ViewColumn()
  cwe: string;

  @ViewColumn()
  cpe: string;

  @ViewColumn()
  description: string;

  @ViewColumn()
  references: string;

  @ViewColumn()
  cvss: string;

  @ViewColumn()
  severity: string;

  @ViewColumn()
  needsPopulation: string;

  @ViewColumn()
  state: string;

  @ViewColumn()
  substate: string;

  @ViewColumn()
  source: string;

  @ViewColumn()
  notes: string;

  @ViewColumn()
  actions: string;

  @ViewColumn()
  structuredData: string;

  @ViewColumn()
  isKev: string;

  @ViewColumn()
  kevResults: string;

  @ViewColumn()
  domainId: string;

  @ViewColumn()
  serviceId: string;
}

@ViewEntity({
  name: 'vw_most_common_vulns_stats',
  expression: `
  select acronym, "organizationId", title, description, severity, "count", "regionId"
  from
  (select o.acronym, o.id as "organizationId", o."regionId" as "regionId", v.title, v.description, v.severity, count(v.*) as "count", 
  row_number() over (partition by o.acronym order by count(*) desc, case severity  when 'Critical' then 0 when 'High' then 1 when 'Medium' then 2 when 'Low' then 3 end) as row
  from vulnerability v 
  left join "domain" d on d.id = v."domainId" 
  join organization o on d."organizationId" = o.id
  where v.state = 'open'
  and (d."isFceb" = true OR (d."isFceb" = false AND d."fromCidr" = true))
  group by o.acronym, o.id, v.title, v.description, v.severity, "regionId"
  ) as ranked_vulns
  where row <=50;
  `,
  materialized: true
})
export class VwMostCommonVulns extends BaseEntity {
  @ViewColumn()
  acronym: string;

  @ViewColumn()
  organizationId: string;

  @ViewColumn()
  title: string;

  @ViewColumn()
  description: string;

  @ViewColumn()
  severity: string;

  @ViewColumn()
  count: string;
}

@ViewEntity({
  name: 'vw_severity_stats',
  expression: `
    select o.acronym, o.id as "organizationId", v.severity, count(*) as "count", o."regionId" as "regionId"
    from vulnerability v  
    left join "domain" d on d.id = v."domainId" 
    join organization o on d."organizationId" = o.id
    where v.state = 'open'
    and (d."isFceb" = true OR (d."isFceb" = false AND d."fromCidr" = true))
    group by o.acronym, o.id, v.severity, "regionId"
    order by v.severity asc;
  `,
  materialized: true
})
export class VwSeverityStats extends BaseEntity {
  @ViewColumn()
  acronym: string;

  @ViewColumn()
  organizationId: string;

  @ViewColumn()
  severity: string;

  @ViewColumn()
  count: string;
}

@ViewEntity({
  name: 'vw_domain_stats',
  expression: `
    select o.acronym, o.id as "organizationId", count(*), o."regionId" as "regionId"
    from "domain" d 
    join organization o on d."organizationId" = o.id
    where (d."isFceb" = true OR (d."isFceb" = false AND d."fromCidr" = true))
    group by o.acronym, o.id, "regionId";
  `,
  materialized: true
})
export class VwDomainStats extends BaseEntity {
  @ViewColumn()
  acronym: string;

  @ViewColumn()
  organizationId: string;

  @ViewColumn()
  count: string;
}

@ViewEntity({
  name: 'vw_org_stats',
  expression: `
    select o.name, o.acronym, o.id as "organizationId", o.id as "orgId", count(*) as "count", o."regionId" as "regionId"
    from "domain" d 
    join organization o on d."organizationId" = o.id
    join vulnerability v on d.id = v."domainId" 
    where v.state = 'open'
    and (d."isFceb" = true OR (d."isFceb" = false AND d."fromCidr" = true))
    group by o.name, o.acronym, o.id, "regionId"
    order by "count" desc;
  `,
  materialized: true
})
export class VwOrgStats extends BaseEntity {
  @ViewColumn()
  name: string;

  @ViewColumn()
  acronym: string;

  @ViewColumn()
  organizationId: string;

  @ViewColumn()
  orgId: string;

  @ViewColumn()
  count: string;
}

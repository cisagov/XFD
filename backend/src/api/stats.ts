import { ValidateNested, IsOptional, IsObject, IsUUID } from 'class-validator';
import { Type } from 'class-transformer';
import {
  connectToDatabase,
  Vulnerability,
  VwServiceStats,
  VwPortsStats,
  VwNumVulns,
  VwLatestVulns,
  VwMostCommonVulns,
  VwSeverityStats,
  VwDomainStats,
  VwOrgStats
} from '../models';
import { validateBody, wrapHandler } from './helpers';
import { SelectQueryBuilder } from 'typeorm';
import {
  isGlobalViewAdmin,
  getOrgMemberships,
  getTagOrganizations
} from './auth';

interface Point {
  id: string;
  label: string;
  value: number;
}

interface Stats {
  domains: {
    services: Point[];
    ports: Point[];
    numVulnerabilities: Point[];
    total: number;
  };
  vulnerabilities: {
    severity: Point[];
    byOrg: Point[];
    latestVulnerabilities: Vulnerability[];
    mostCommonVulnerabilities: Vulnerability[];
  };
}

class StatsFilters {
  @IsUUID()
  @IsOptional()
  organization?: string;

  @IsUUID()
  @IsOptional()
  tag?: string;
}

class StatsSearch {
  @Type(() => StatsFilters)
  @ValidateNested()
  @IsObject()
  @IsOptional()
  filters?: StatsFilters;
}

/**
 * @swagger
 *
 * /stats:
 *  get:
 *    description: Get stats.
 *    tags:
 *    - Stats
 */
export const get = wrapHandler(async (event) => {
  await connectToDatabase();
  const search = await validateBody(StatsSearch, event.body);

  const filterQuery = async (
    qs: SelectQueryBuilder<any>
  ): Promise<SelectQueryBuilder<any>> => {
    if (!isGlobalViewAdmin(event)) {
      qs.andWhere('stat."organizationId" IN (:...orgs)', {
        orgs: getOrgMemberships(event)
      });
    }
    if (search.filters?.organization) {
      qs.andWhere('stat."organizationId" = :org', {
        org: search.filters?.organization
      });
    }
    if (search.filters?.tag) {
      qs.andWhere('stat."organizationId" IN (:...orgs)', {
        orgs: await getTagOrganizations(event, search.filters.tag)
      });
    }

    return qs.cache(15 * 60 * 1000); // 15 minutes
  };

  const performQuery = async (qs: SelectQueryBuilder<any>) => {
    qs = await filterQuery(qs);
    return (await qs.getRawMany()).map((e) => ({
      id: String(e.id),
      value: Number(e.value),
      label: String(e.id)
    })) as { id: string; value: number; label: string }[];
  };

  const MAX_RESULTS = 50;

  const services = await performQuery(
    VwServiceStats.createQueryBuilder('stat')
      .select('service as id, sum(stat.count) as value')
      .groupBy('service')
      .orderBy('value', 'DESC')
  );
  const ports = await performQuery(
    VwPortsStats.createQueryBuilder('stat')
      .select('port as id, sum(stat.count) as value')
      .groupBy('port')
      .orderBy('value', 'DESC')
  );
  const numVulnerabilities = await performQuery(
    VwNumVulns.createQueryBuilder('stat')
      .select('"domainSeverity" as id, sum(stat.count) as value')
      .groupBy('"domainSeverity"')
      .orderBy('value', 'DESC')
      .limit(MAX_RESULTS)
  );
  const latestVulnerabilities = await (
    await filterQuery(
      VwLatestVulns.createQueryBuilder('stat')
        .orderBy('stat.createdAt', 'ASC')
        .limit(MAX_RESULTS)
    )
  ).getMany();
  const mostCommonVulnerabilities = await (
    await filterQuery(
      VwMostCommonVulns.createQueryBuilder('stat')
        .select(
          'stat.title, stat.description, stat.severity, sum(stat.count) as count'
        )
        .groupBy('stat.title, stat.description, stat.severity')
        .orderBy('count', 'DESC')
        .limit(MAX_RESULTS)
    )
  ).getRawMany();
  const severity = await performQuery(
    VwSeverityStats.createQueryBuilder('stat')
      .select('stat.severity as id, sum(stat.count) as value')
      .groupBy('stat.severity')
      .orderBy('stat.severity', 'ASC')
  );
  const total = await performQuery(
    VwDomainStats.createQueryBuilder('stat').select('sum(stat.count) as value')
  );
  const byOrg = (
    await (
      await filterQuery(
        VwOrgStats.createQueryBuilder('stat')
          .select('stat.name as id, "orgId", count as value')
          .orderBy('value', 'DESC')
      )
    ).getRawMany()
  ).map((e) => ({
    id: String(e.id),
    orgId: String(e.orgId),
    value: Number(e.value),
    label: String(e.id)
  }));
  const result: Stats = {
    domains: {
      services,
      ports: ports,
      numVulnerabilities: numVulnerabilities,
      total: total[0].value
    },
    vulnerabilities: {
      severity,
      byOrg,
      latestVulnerabilities,
      mostCommonVulnerabilities
    }
  };
  return {
    statusCode: 200,
    body: JSON.stringify({
      result
    })
  };
});

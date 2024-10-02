import {
  ValidateNested,
  IsOptional,
  IsObject,
  IsUUID,
  IsArray
} from 'class-validator';
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
import { getTagOrganizations } from './auth';

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
  @IsOptional()
  @IsArray()
  // Validates each item in array as UUID
  @Type(() => IsUUID)
  organizations?: string[];

  @IsUUID()
  @IsOptional()
  tag?: string;

  @IsOptional()
  @IsArray()
  @Type(() => IsUUID)
  regions?: string[];
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
    if (
      search.filters?.organizations &&
      search.filters?.organizations.length > 0
    ) {
      console.log('adding org filter -> ?');
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: search.filters?.organizations
      });
    }
    if (search.filters?.tag) {
      qs.andWhere('stat."organizationId" IN (:...orgs)', {
        orgs: await getTagOrganizations(event, search.filters.tag)
      });
    }

    if (search.filters?.regions && search.filters.regions.length > 0) {
      qs.andWhere('"organization"."regionId" IN (:...regions)', {
        regions: search.filters.regions
      });
    }

    qs.andWhere(
      '(domain."isFceb" = true OR (domain."isFceb" = false AND domain."fromCidr" = true))'
    );

    // Handles the case where no orgs and no regions are set, and we pull stats for a region that will never exist
    if (
      search.filters?.organizations?.length === 0 &&
      search.filters?.regions?.length === 0
    ) {
      qs.andWhere('organization."regionId" IN (:...regions)', {
        regions: ['FORCEEMPTY']
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

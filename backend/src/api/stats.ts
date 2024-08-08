import {
  ValidateNested,
  IsOptional,
  IsObject,
  IsUUID,
  isUUID,
  IsArray
} from 'class-validator';
import { Type } from 'class-transformer';
import { Domain, connectToDatabase, Vulnerability, Service } from '../models';
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
    if (!isGlobalViewAdmin(event)) {
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: getOrgMemberships(event)
      });
    }
    if (
      search.filters?.organizations &&
      search.filters?.organizations.length > 0
    ) {
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: search.filters?.organizations
      });
    }
    if (search.filters?.tag) {
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: await getTagOrganizations(event, search.filters.tag)
      });
    }

    if (search.filters?.regions && search.filters.regions.length > 0) {
      qs.andWhere('"organization"."regionId" IN (:...regions)', {
        regions: search.filters.regions
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
    Service.createQueryBuilder('service')
      .innerJoinAndSelect('service.domain', 'domain')
      .innerJoin('domain.organization', 'organization')
      .where('service IS NOT NULL')
      .select('service as id, count(*) as value')
      .groupBy('service')
      .orderBy('value', 'DESC')
  );
  const ports = await performQuery(
    Domain.createQueryBuilder('domain')
      .innerJoinAndSelect('domain.services', 'services')
      .innerJoin('domain.organization', 'organization')
      .select('services.port as id, count(*) as value')
      .groupBy('services.port')
      .orderBy('value', 'DESC')
  );
  const numVulnerabilities = await performQuery(
    Domain.createQueryBuilder('domain')
      .innerJoinAndSelect('domain.vulnerabilities', 'vulnerabilities')
      .innerJoin('domain.organization', 'organization')
      .andWhere("vulnerabilities.state = 'open'")
      .select(
        "CONCAT(domain.name, '|', vulnerabilities.severity) as id, count(*) as value"
      )
      .groupBy('vulnerabilities.severity, domain.id')
      .orderBy('value', 'DESC')
      .limit(MAX_RESULTS)
  );
  const latestVulnerabilities = await (
    await filterQuery(
      Vulnerability.createQueryBuilder('vulnerability')
        .leftJoinAndSelect('vulnerability.domain', 'domain')
        .innerJoin('domain.organization', 'organization')
        .andWhere("vulnerability.state = 'open'")
        .orderBy('vulnerability.createdAt', 'ASC')
        .limit(MAX_RESULTS)
    )
  ).getMany();
  const mostCommonVulnerabilities = await (
    await filterQuery(
      Vulnerability.createQueryBuilder('vulnerability')
        .leftJoinAndSelect('vulnerability.domain', 'domain')
        .innerJoin('domain.organization', 'organization')
        .andWhere("vulnerability.state = 'open'")
        .select(
          'vulnerability.title, vulnerability.description, vulnerability.severity, count(*) as count'
        )
        .groupBy(
          'vulnerability.title, vulnerability.description, vulnerability.severity'
        )
        .orderBy('count', 'DESC')
        .limit(MAX_RESULTS)
    )
  ).getRawMany();
  const severity = await performQuery(
    Vulnerability.createQueryBuilder('vulnerability')
      .leftJoinAndSelect('vulnerability.domain', 'domain')
      .innerJoin('domain.organization', 'organization')
      .andWhere("vulnerability.state = 'open'")
      .select('vulnerability.severity as id, count(*) as value')
      .groupBy('vulnerability.severity')
      .orderBy('vulnerability.severity', 'ASC')
  );
  const total = await performQuery(
    Domain.createQueryBuilder('domain')
      .select('count(*) as value')
      .innerJoin('domain.organization', 'organization')
  );
  const byOrg = (
    await (
      await filterQuery(
        Domain.createQueryBuilder('domain')
          .innerJoinAndSelect('domain.organization', 'organization')
          .innerJoinAndSelect('domain.vulnerabilities', 'vulnerabilities')
          .andWhere("vulnerabilities.state = 'open'")
          .select(
            'organization.name as id, organization.id as "orgId", count(*) as value'
          )
          .groupBy('organization.name, organization.id')
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

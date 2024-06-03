import { ValidateNested, IsOptional, IsObject, IsUUID } from 'class-validator';
import { Type } from 'class-transformer';
import {
  Domain,
  connectToDatabase,
  Vulnerability,
  Service,
  Organization
} from '../models';
import { validateBody, wrapHandler } from './helpers';
import { SelectQueryBuilder } from 'typeorm';
import {
  isGlobalViewAdmin,
  getOrgMemberships,
  getRegionOrganizations,
  getTagOrganizations,
  isRegionalAdmin,
  isOnlyRegionalAdmin,
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
    // numVulnerabilities: Point[];
    // total: number;
  };
  vulnerabilities: {
    // severity: Point[];
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
    if (!isGlobalViewAdmin(event)) { //&& !isRegionalAdmin(event)
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: getOrgMemberships(event)
      });
    }
    // if (isOnlyRegionalAdmin(event)){
    //   qs.andWhere('domain."organizationId" IN (:...orgs)',{
    //     orgs: await getRegionOrganizations(event)
    //   })
    // }
    if (search.filters?.organization) {
      qs.andWhere('domain."organizationId" = :org', {
        org: search.filters?.organization
      });
    }
    if (search.filters?.tag) {
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: await getTagOrganizations(event, search.filters.tag)
      });
    }

    return qs.cache(15 * 60 * 1000); // 15 minutes
  };

  const MAX_RESULTS = 50;

  const performQuery = async (qs: SelectQueryBuilder<any>) => {
    qs = await filterQuery(qs);
    return (await qs.getRawMany()).map((e) => ({
      id: String(e.id),
      value: Number(e.value),
      label: String(e.id)
    })) as { id: string; value: number; label: string }[];
  };

  // Define all the queries
  const servicesQuery = Service.createQueryBuilder('service')
    .innerJoinAndSelect('service.domain', 'domain')
    .where('service IS NOT NULL')
    .select('service as id, count(*) as value')
    .groupBy('service')
    .orderBy('value', 'DESC');

  const portsQuery = Domain.createQueryBuilder('domain')
    .innerJoinAndSelect('domain.services', 'services')
    .select('services.port as id, count(*) as value')
    .groupBy('services.port')
    .orderBy('value', 'DESC');

  const latestVulnerabilitiesQuery = await (
    await filterQuery(
      Vulnerability.createQueryBuilder('vulnerability')
        .leftJoinAndSelect('vulnerability.domain', 'domain')
        .andWhere("vulnerability.state = 'open'")
        .orderBy('vulnerability.createdAt', 'ASC')
        .limit(MAX_RESULTS)
    )
  ).getMany();

  const mostCommonVulnerabilitiesQuery = await (
    await filterQuery(
      Vulnerability.createQueryBuilder('vulnerability')
        .leftJoinAndSelect('vulnerability.domain', 'domain')
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
  ).getMany();

  const byOrgQuery = Domain.createQueryBuilder('domain')
    .innerJoinAndSelect('domain.organization', 'organization')
    .innerJoinAndSelect('domain.vulnerabilities', 'vulnerabilities')
    .andWhere("vulnerabilities.state = 'open'")
    .select(
      'organization.name as id, organization.id as "orgId", count(*) as value'
    )
    .groupBy('organization.name, organization.id')
    .orderBy('value', 'DESC');

  // Execute all queries concurrently
  const [
    services,
    ports,
    latestVulnerabilities,
    mostCommonVulnerabilities,
    byOrg
  ] = await Promise.all([
    performQuery(servicesQuery),
    performQuery(portsQuery),
    latestVulnerabilitiesQuery,
    mostCommonVulnerabilitiesQuery,
    performQuery(byOrgQuery)
  ]);
  // Construct the result object
  const result: Stats = {
    domains: {
      services,
      ports
    },
    vulnerabilities: {
      latestVulnerabilities,
      mostCommonVulnerabilities,
      byOrg
    }
  };

  return {
    statusCode: 200,
    body: JSON.stringify({ result })
  };
});

/**
 * @swagger
 *
 * /summaryStats:
 *  post:
 *    description: Get stats.
 *    tags:
 *    - Stats
 */
export const getSummary = wrapHandler(async (event) => {
  await connectToDatabase();
  const search = await validateBody(StatsSearch, event.body);

  // Function to filter queries based on permissions and search filters
  const filterQuery = async (
    qs: SelectQueryBuilder<any>,
    entityType: string
  ): Promise<SelectQueryBuilder<any>> => {
    if (!isGlobalViewAdmin(event)) { //&& !isRegionalAdmin(event)
      qs.andWhere(`${entityType} IN (:...orgs)`, {
        orgs: getOrgMemberships(event)
      });
    }
    
    // if (isOnlyRegionalAdmin(event)){
    //   qs.andWhere(`${entityType}  IN (:...orgs)`,{
    //     orgs: await getRegionOrganizations(event)
    //   })
    // }
    if (search.filters?.organization) {
      qs.andWhere(`${entityType} = :org`, {
        org: search.filters.organization
      });
    }
    if (search.filters?.tag) {
      qs.andWhere(`${entityType} IN (:...orgs)`, {
        orgs: await getTagOrganizations(event, search.filters.tag)
      });
    }
    return qs.cache(15 * 60 * 1000); // Cache for 15 minutes
  };

  // Function to perform service query
  const performServiceQuery = async (qs: SelectQueryBuilder<any>) => {
    qs = await filterQuery(qs, 'domain."organizationId"');
    const results = await qs.getRawMany();
    const dictionary: { [key: string]: number } = {
      Critical: 0,
      High: 0,
      Medium: 0,
      Low: 0
    };

    results.forEach((e) => {
      dictionary[String(e.id)] = Number(e.value);
    });

    return dictionary;
  };

  // Execute severity query and organization query concurrently
  const [severity, orgResults] = await Promise.all([
    performServiceQuery(
      Vulnerability.createQueryBuilder('vulnerability')
        .leftJoinAndSelect('vulnerability.domain', 'domain')
        .andWhere("vulnerability.state = 'open'")
        .select('vulnerability.severity as id, count(*) as value')
        .groupBy('vulnerability.severity')
        .orderBy('vulnerability.severity', 'ASC')
    ),
    (
      await filterQuery(
        Organization.createQueryBuilder('organization')
          .select(
            'organization.name, organization.acronym, organization."rootDomains", organization."ipBlocks", organization."stateName", organization."regionId", count(DISTINCT roles."userId") as members'
          )
          .leftJoin('organization.userRoles', 'roles')
          .groupBy(
            'organization.name, organization.acronym, organization."rootDomains", organization."ipBlocks", organization."stateName", organization."regionId"'
          ),
        'organization.id'
      )
    ).getRawMany()
  ]);

  // Process organization results to get organization object
  let organization;
  if (orgResults.length === 1) {
    organization = orgResults[0];
    organization.rootDomainCount = organization.rootDomains.length;
  } else {
    const memberSum = orgResults.reduce(
      (sum, result) => sum + result.members,
      0
    );
    const rootSum = orgResults.reduce(
      (sum, result) => sum + result.rootDomains.length,
      0
    );
    organization = {
      name: 'Multiple Organizations Selected',
      acronym: 'MANY',
      rootDomains: [],
      ipBlocks: [],
      stateName: 'NA',
      regionId: 'NA',
      members: memberSum,
      rootDomainCount: rootSum
    };
  }

  return {
    statusCode: 200,
    body: JSON.stringify({
      severity,
      org: organization
    })
  };
});

/**
 * @swagger
 *
 * /vulnSummaryStats:
 *  post:
 *    description: Get vuln summary stats.
 *    tags:
 *    - Stats
 */
export const getVulnSummary = wrapHandler(async (event) => {
  await connectToDatabase();
  const search = await validateBody(StatsSearch, event.body);

  const filterQuery = async (
    qs: SelectQueryBuilder<any>
  ): Promise<SelectQueryBuilder<any>> => {
    if (!isGlobalViewAdmin(event)  ) { //&& !isRegionalAdmin(event)
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: getOrgMemberships(event)
      });
    }
    // if (isOnlyRegionalAdmin(event)){
    //   qs.andWhere('domain."organizationId" IN (:...orgs)',{
    //     orgs: await getRegionOrganizations(event)
    //   })
    // }
    if (search.filters?.organization) {
      qs.andWhere('domain."organizationId" = :org', {
        org: search.filters.organization
      });
    }
    if (search.filters?.tag) {
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: await getTagOrganizations(event, search.filters.tag)
      });
    }
    return qs.cache(15 * 60 * 1000); // 15 minutes
  };

  // Execute queries concurrently
  const [dnstwistResults, credBreachResult, inventoryResult] =
    await Promise.all([
      (
        await filterQuery(
          Vulnerability.createQueryBuilder('vulnerability')
            .leftJoinAndSelect('vulnerability.domain', 'domain')
            .select('count(*)')
            .andWhere("vulnerability.state = 'open'")
            .andWhere("vulnerability.cve = 'DNSTwist Suspicious Domain'")
        )
      ).getRawMany(),
      (
        await filterQuery(
          Vulnerability.createQueryBuilder('vulnerability')
            .leftJoinAndSelect('vulnerability.domain', 'domain')
            .select('count(*)')
            .andWhere("vulnerability.state = 'open'")
            .andWhere("vulnerability.cve = 'Credential Breach'")
        )
      ).getRawMany(),
      (
        await filterQuery(
          Domain.createQueryBuilder('domain')
            .leftJoinAndSelect(
              'domain.vulnerabilities',
              'vulnerabilities',
              "state = 'open'"
            )
            .select('count(Distinct domain.id)')
        )
      ).getRawMany()
    ]);

  // Extract counts from query results
  const dnstwistVulnCount = Number(dnstwistResults[0]?.count || 0);
  const credBreachCount = Number(credBreachResult[0]?.count || 0);
  const inventoryCount = Number(inventoryResult[0]?.count || 0);

  return {
    statusCode: 200,
    body: JSON.stringify({
      dnstwistVulnCount,
      credBreachCount,
      inventoryCount
    })
  };
});

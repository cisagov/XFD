import { ValidateNested, IsOptional, IsObject, IsUUID } from 'class-validator';
import { Type } from 'class-transformer';
import { Domain, connectToDatabase, Vulnerability, Service, Organization } from '../models';
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
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: getOrgMemberships(event)
      });
    }
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
      .where('service IS NOT NULL')
      .select('service as id, count(*) as value')
      .groupBy('service')
      .orderBy('value', 'DESC')
  );
  const ports = await performQuery(
    Domain.createQueryBuilder('domain')
      .innerJoinAndSelect('domain.services', 'services')
      .select('services.port as id, count(*) as value')
      .groupBy('services.port')
      .orderBy('value', 'DESC')
  );
  const numVulnerabilities = await performQuery(
    Domain.createQueryBuilder('domain')
      .innerJoinAndSelect('domain.vulnerabilities', 'vulnerabilities')
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
        .andWhere("vulnerability.state = 'open'")
        .orderBy('vulnerability.createdAt', 'ASC')
        .limit(MAX_RESULTS)
    )
  ).getMany();
  const mostCommonVulnerabilities = await (
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
  ).getRawMany();
  const severity = await performQuery(
    Vulnerability.createQueryBuilder('vulnerability')
      .leftJoinAndSelect('vulnerability.domain', 'domain')
      .andWhere("vulnerability.state = 'open'")
      .select('vulnerability.severity as id, count(*) as value')
      .groupBy('vulnerability.severity')
      .orderBy('vulnerability.severity', 'ASC')
  );
  const total = await performQuery(
    Domain.createQueryBuilder('domain').select('count(*) as value')
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

  const filterQuery = async (
    qs: SelectQueryBuilder<any>
  ): Promise<SelectQueryBuilder<any>> => {
    if (!isGlobalViewAdmin(event)) {
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: getOrgMemberships(event)
      });
    }
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

  const performServiceQuery = async (qs: SelectQueryBuilder<any>) => {
    qs = await filterQuery(qs);
    const results = await qs.getRawMany();
    console.log(results)
    const dictionary: { [key: string]: number } = {
      "Critical": 0,
      "High": 0,
      "Medium": 0,
      "Low": 0
    };
    
    results.forEach(e => {
      console.log
        dictionary[String(e.id)] = Number(e.value);
    });
    
    return dictionary;
};

  const severity = await performServiceQuery(
    Vulnerability.createQueryBuilder('vulnerability')
      .leftJoinAndSelect('vulnerability.domain', 'domain')
      .andWhere("vulnerability.state = 'open'")
      .select('vulnerability.severity as id, count(*) as value')
      .groupBy('vulnerability.severity')
      .orderBy('vulnerability.severity', 'ASC')
  );
  console.log(`The severity response is ${severity}`)
  
  const organization_query = Organization.createQueryBuilder('organization')
  .select('organization.name, organization.acronym, organization."rootDomains", organization."ipBlocks", organization."stateName", organization."regionId", count(DISTINCT roles."userId") as members')
  .leftJoin('organization.userRoles', 'roles')
  .groupBy('organization.name, organization.acronym, organization."rootDomains", organization."ipBlocks", organization."stateName", organization."regionId"')
  if (!isGlobalViewAdmin(event)) {
    organization_query.andWhere('organization.id IN (:...orgs)', {
      orgs: getOrgMemberships(event)
    });
  }
  if (search.filters?.organization) {
    organization_query.andWhere('organization.id = :org', {
      org: search.filters?.organization
    });
  }
  if (search.filters?.tag) {
    organization_query.andWhere('organization.id IN (:...orgs)', {
      orgs: await getTagOrganizations(event, search.filters.tag)
    });
  }
  const org_results = await organization_query.getRawMany();

  let org
  if (org_results.length === 1) {
    org = org_results[0];
    org.rootDomainCount = org.rootDomains.length
} else {
  let member_sum = 0;
  let root_sum = 0;
  for (const result of org_results) {
      member_sum += result.members;
      root_sum += result.rootDomains.length
  }
    org ={
      "name": "Multiple Organizations Selected",
            "acronym": "MANY",
            "rootDomains": [],
            "ipBlocks": [],
            "stateName": "NA",
            "regionId": "NA",
            "members": member_sum,
            "rootDomainCount": root_sum
    };
}
  return {
    statusCode: 200,
    body: JSON.stringify({
      severity,
      org
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
    if (!isGlobalViewAdmin(event)) {
      qs.andWhere('domain."organizationId" IN (:...orgs)', {
        orgs: getOrgMemberships(event)
      });
    }
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
  const dnstwist_query = Vulnerability.createQueryBuilder('vulnerability')
  .leftJoinAndSelect('vulnerability.domain', 'domain')
  .select("count(*)")
  .andWhere("vulnerability.state = 'open'")
  .andWhere("vulnerability.cve = 'DNSTwist Suspicious Domain'")

  const filtered_dnstwist_query = await filterQuery(dnstwist_query)
  const dnstwist_results = await filtered_dnstwist_query.getRawMany();
  let dnstwist_vuln_count
  dnstwist_vuln_count = Number(dnstwist_results[0].count);

  const cred_breach_query = Vulnerability.createQueryBuilder('vulnerability')
  .leftJoinAndSelect('vulnerability.domain', 'domain')
  .select("count(*)")
  .andWhere("vulnerability.state = 'open'")
  .andWhere("vulnerability.cve = 'Credential Breach'")

  const filtered_cred_breach_query = await filterQuery(cred_breach_query)
  const cred_breach_result = await filtered_cred_breach_query.getRawMany();
  let cred_breach_count
  cred_breach_count = Number(cred_breach_result[0].count);


  let inventory_query = Domain.createQueryBuilder('domain')
      .leftJoinAndSelect(
        'domain.vulnerabilities',
        'vulnerabilities',
        "state = 'open'"
      )
      .select("count(Distinct domain.id)")

    const filtered_inventory_query = await filterQuery(inventory_query)
    const inventory_result = await filtered_inventory_query.getRawMany();
    let inventory_count
    inventory_count = Number(inventory_result[0].count);

  return {
    statusCode: 200,
    body: JSON.stringify({
      dnstwist_vuln_count,
      cred_breach_count,
      inventory_count
    })
  };
});
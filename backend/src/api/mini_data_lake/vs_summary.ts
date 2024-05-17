import {
    IsString,
    isUUID,
    IsArray,
    IsBoolean,
    IsUUID,
    IsOptional,
    IsNotEmpty,
    IsNumber,
    IsEnum
  } from 'class-validator';
  import {
    Organization,
    connectToDatabase,
    Cidr,
    Role,
    ScanTask,
    Scan,
    User,
    OrganizationTag,
    PendingDomain,
    DL_Organization,
    connectToDatalake2,
    Ticket
  } from '../../models';
  import {
    validateBody,
    wrapHandler,
    NotFound,
    REGION_STATE_MAP,
    Unauthorized
  } from '../helpers';
  import {
    isOrgAdmin,
    isGlobalWriteAdmin,
    isRegionalAdmin,
    getOrgMemberships,
    isGlobalViewAdmin
  } from '../auth';
  import { In } from 'typeorm';
  import { plainToClass } from 'class-transformer';
  import { randomBytes } from 'crypto';
  import { promises } from 'dns';
  import { Address4, Address6 } from 'ip-address';
  
  async function get_findings(org: DL_Organization):Promise<{
    acronym: string | null ;
    assetsOwned: number;
    assetsScanned: number;
    hosts: number;
    services: number;
    vulnerabilities: number;
    vulnerableHosts: number;
  }> {
    let vuln_count;
    
  console.log(`vuln count is ${vuln_count}`)
    const findings = {
      acronym: org.acronym,
      assetsOwned: countAssets(org.cidrs),
      assetsScanned: 0,
      hosts: 0,
      services: 0,
      vulnerabilities: await countVulnerabilities(org.id),
      vulnerableHosts: 0
    }

    return findings
  }

  async function countVulnerabilities(org_id: string): Promise<number>{
    const dataLake = await connectToDatalake2();
    const ticketRepository = dataLake.getRepository(Ticket);

    const count = ticketRepository
      .createQueryBuilder('ticket')
      .where(
        'ticket.organizationId = :organizationId AND ticket."vulnSource" = :vulnSource AND ticket."falsePositive" = :falsePositive AND ticket."foundInLatestHostScan" = :foundInLatestHostScan',
        {
          organizationId: org_id,
          vulnSource: 'nessus',
          falsePositive: false,
          foundInLatestHostScan: true
        }
      )
      .getCount();
      
      return count
  }

  function countAssets(cidrs: Cidr[]): number{
    let asset_count = 0
    for (const cidr of cidrs){
      if (cidr.network !== null){
          asset_count += countAvailableIPs(cidr.network)
      }
    }
    return asset_count
  }

  function countAvailableIPs(input: string): number {
    if (input.includes(':')) {
        // IPv6 CIDR notation
        const ipAddress = new Address6(input);
        if (Address6.isValid(input)) {
            return 1; // Valid IPv6 address
        } else {
            const parts = input.split('/');
            if (parts.length === 2) {
                const prefixLength = parseInt(parts[1], 10);
                if (!isNaN(prefixLength) && prefixLength >= 0 && prefixLength <= 128) {
                    const numIPs = Math.pow(2, 128 - prefixLength);
                    return numIPs;
                }
            }
        }
    } else {
        // IPv4 CIDR notation or standalone IP address
        const parts = input.split('/');
        if (parts.length === 2) {
            // IPv4 CIDR notation
            const prefixLength = parseInt(parts[1], 10);
            if (Address4.isValid(input) && !isNaN(prefixLength) && prefixLength >= 0 && prefixLength <= 32) {
                const numIPs = Math.pow(2, 32 - prefixLength) - 2;
                return numIPs;
            }
        } else {
            // Standalone IPv4 address
            const ipAddress = new Address4(input);
            if (Address4.isValid(input)) {
                return 1; // Valid IPv4 address
            }
        }
    }

    // Invalid input
    return 0;
}


/**
 * @swagger
 *
 * /mdl/vsAssetCount:
 *  get:
 *    description: Count assets belonging to organizations.
 *    tags:
 *    - VS_assets
 */
export const assetCount = wrapHandler(async (event) => {
    console.log('list function called with event: ', event);
  
    if (!isGlobalViewAdmin(event) && getOrgMemberships(event).length === 0) {
      return {
        //TODO: Should we return a 403?
        statusCode: 200,
        body: JSON.stringify([])
      };
    }
    await connectToDatabase();
    console.log('Database connected');
  
    let where: any = { parent: null };
    if (!isGlobalViewAdmin(event)) {
      where = { id: In(getOrgMemberships(event)), parent: null };
    }
    
    const xfd_orgs = await Organization.find({
      where,
      select: ["acronym"],
      order: { acronym: 'ASC' }
    });
    const acronymList = xfd_orgs.map(entity => entity.acronym);
    let result_dict: {[key: string]: number} = {};
    const mdl_connection = await connectToDatalake2();
    for (const acronym of acronymList) {
        try{
            console.log(acronym); 
            const mdl_org = await mdl_connection.getRepository(DL_Organization).findOne({ where: { acronym }, relations: ["cidrs"] });
            if(mdl_org){
                result_dict[acronym] = 0;
            for (const cidr of mdl_org.cidrs){
                if (cidr.network !== null){
                    result_dict[acronym] += countAvailableIPs(cidr.network)
                }
            }
            }
        }
        catch{
            console.log('Failed')
        }
        
    }
  
    return {
      statusCode: 200,
      body: JSON.stringify(result_dict)
    };
  });


  /**
 * @swagger
 *
 * /mdl/mdl/vsHighLevelFindings/{acronym}:
 *  get:
 *    description: Return high level findings for the logged-in user's organization.
 *    tags:
 *    - Mini Data Lake
 */
export const findings = wrapHandler(async (event) => {
  try {
    if (!isGlobalViewAdmin(event) && getOrgMemberships(event).length === 0) {
      return {
        //TODO: Should we return a 403?
        statusCode: 200,
        body: JSON.stringify([])
      };
    }

    await connectToDatabase();
    console.log('Database connected');
  
    let where: any = { parent: null };
    if (!isGlobalViewAdmin(event)) {
      where = { id: In(getOrgMemberships(event)), parent: null };
    }
    
    const xfd_orgs = await Organization.find({
      where,
      select: ["acronym"],
      order: { acronym: 'ASC' }
    });
    const acronymList = xfd_orgs.map(entity => entity.acronym);

    const userId = event.requestContext.authorizer!.id;
    if (!userId) {
      return Unauthorized;
    }
    const acronym = event.pathParameters?.acronym;
    if (acronymList.includes(acronym)) {
      const mdl_connection = await connectToDatalake2();
      const mdl_org = await mdl_connection.getRepository(DL_Organization).findOne({ where: { acronym: acronym, retired: false }, relations: ["cidrs","children", "children.cidrs"] });
      if (mdl_org){
        const requested_org = await get_findings(mdl_org)
        const total = {
          "assetsOwned": requested_org.assetsOwned,
          "assetsScanned": requested_org.assetsScanned,
          "hosts": requested_org.hosts,
          "services": requested_org.services,
          "vulnerabilities": requested_org.vulnerabilities,
          "vulnerableHosts": requested_org.vulnerableHosts
        }
        const children: Promise<{
            acronym: string | null ;
            assetsOwned: number;
            assetsScanned: number;
            hosts: number;
            services: number;
            vulnerabilities: number;
            vulnerableHosts: number;
          }>[] = []
        mdl_org.children.forEach(child =>{
          if(child.retired){
            return
          }
          children.push(get_findings(child))
        })
        const awaited_children = await Promise.all(children);

        for (const child of awaited_children){
          total.assetsOwned += child.assetsOwned
          total.assetsScanned += child.assetsScanned
          total.hosts += child.hosts
          total.services += child.services
          total.vulnerabilities += child.vulnerabilities
          total.vulnerableHosts += child.vulnerableHosts
        }
        const return_dict = {
          "children": children,
          "organization": requested_org,
          "total": total
        };
         return {
            statusCode: 200,
            body: JSON.stringify(return_dict )
         };
  
      }
    }
    else{
      return Unauthorized;
    }
    return Unauthorized;
  } catch (error) {
    console.error('Server Error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: 'Internal Server Error',
        details: error.message // remove  this line in production
      })
    };
  }
});
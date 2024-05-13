import { Address4, Address6 } from 'ip-address';
import {
  DL_Organization,
  Cidr,
  Location,
  Sector,
  VulnScan,
  Ip,
  DL_Cve
} from '../models';
const { Client } = require('pg');
import { CommandOptions } from './ecs-client';
import saveVulnScan from './helpers/saveVulnScan';
import saveOrganizationToMdl from './helpers/saveOrganizationToMdl';
import saveIpToMdl from './helpers/saveIpToMdl';
import saveCveToMdl from './helpers/saveCveToMdl';
import { plainToClass } from 'class-transformer';

/** Removes a value for a given key from the dictionary and then returns it. */
function getValueAndDelete<T>(
  obj: { [key: string]: T },
  key: string
): T | undefined {
  if (obj.hasOwnProperty(key)) {
    const value = obj[key];
    delete obj[key];
    return value;
  } else {
    return undefined;
  }
}

const client = new Client({
  user: process.env.REDSHIFT_USER,
  host: process.env.REDSHIFT_HOST,
  database: process.env.REDSHIFT_DATABASE,
  password: process.env.REDSHIFT_PASSWORD,
  port: 5439
});

export const handler = async (commandOptions: CommandOptions) => {
  // Connect to Redshift and select requests table
  let requestArray;
  try {
    await client.connect();
    const startTime = Date.now();
    const query = 'SELECT * FROM vmtableau.requests;';
    const result = await client.query(query);
    const endTime = Date.now();
    const durationMs = endTime - startTime;
    const durationSeconds = Math.round(durationMs / 1000);
    requestArray = result.rows;
  } catch (error) {
    console.error(
      'Error connecting to redshift and getting requests data:',
      error
    );
    return error;
  }
  // A dictionary to associated the organizationId with the the acronym
  const org_id_dict: { [key: string]: string } = {};
  try {
    // Dictionary linking parents to children acronym:[list of chilren]
    const parent_child_dict: { [key: string]: string[] } = {};
    // Dictionary linking sectors to orgs
    const sector_child_dict: { [key: string]: string[] } = {};
    const non_sector_list: string[] = [
      'CRITICAL_INFRASTRUCTURE',
      'FEDERAL',
      'ROOT',
      'SLTT',
      'CATEGORIES',
      'INTERNATIONAL',
      'THIRD_PARTY'
    ];
    if (requestArray && Array.isArray(requestArray)) {
      for (const request of requestArray) {
        request.agency = JSON.parse(request.agency);
        request.networks = JSON.parse(request.networks);
        request.report_types = JSON.parse(request.report_types);
        request.scan_types = JSON.parse(request.scan_types);
        request.children = JSON.parse(request.children);

        // Sectors don't have types can use the type property to determine if its a sector
        if (!request.agency.hasOwnProperty('type')) {
          console.log('In sector section');
          // Do Sector Category and Tag logic here
          // If the sector is in the non_sector_list skip it, it doesn't link to any orgs just other sectors
          if (non_sector_list.includes(request._id)) {
            continue;
          }

          // If a sector has children create a sector object
          if (
            request.hasOwnProperty('children') &&
            Array.isArray(request.children) &&
            request.children.length > 0
          ) {
            const sector: Sector = plainToClass(Sector, {
              name: request.agency.name,
              acronym: request._id,
              retired: request?.retired ?? null
            });
            //Remove null fields so if we update, we don't remove valid data
            const sectorUpdatedValues = Object.keys(sector)
              .map((key) => {
                if (['acronym'].indexOf(key) > -1) return '';
                return sector[key] !== null ? key : '';
              })
              .filter((key) => key !== '');
            // Save the sector to the database, update sector if it already exists
            const sectorId: string = (
              await Sector.createQueryBuilder()
                .insert()
                .values(sector)
                .orUpdate({
                  conflict_target: ['acronym'],
                  overwrite: sectorUpdatedValues
                })
                .returning('id')
                .execute()
            ).identifiers[0].id;
            // Add sector and orgs to the sector_child_dict so we can link them after creating the orgs
            sector_child_dict[sectorId] = request.children;
          }
          // Go to the next request record
          continue;
        }
        // If the org has children add them to the dictionary which will be used to link them after the initial save
        if (
          request.hasOwnProperty('children') &&
          Array.isArray(request.children) &&
          request.children.length > 0
        ) {
          console.log('in parentChild link section');
          parent_child_dict[request._id] = request.children;
        }
        // Loop through the networks and create network objects
        const networkList: Cidr[] = [];
        for (const cidr of request.networks ?? []) {
          try {
            const address = cidr.includes(':')
              ? new Address6(cidr)
              : new Address4(cidr);
            const firstIP = address.startAddress().address;
            const lastIP = address.endAddress().address;

            networkList.push(
              plainToClass(Cidr, {
                network: cidr,
                startIp: firstIP,
                endIp: lastIP
              })
            );
          } catch (error) {
            console.error('Invalid CIDR format:', error.message);
            continue;
          }
        }

        //Create a Location object
        let location: Location | null = null;
        if (request.agency.location) {
          location = plainToClass(Location, {
            name: request.agency.location.name,
            countryAbrv: request.agency.location.country,
            country: request.agency.location.country_name,
            county: request.agency.location.county,
            countyFips: request.agency.location.county_fips,
            gnisId: request.agency.location.gnis_id,
            stateAbrv: request.agency.location.state,
            stateFips: request.agency.location.state_fips,
            state: request.agency.location.state_name
          });
        }

        // Create organization object
        const orgObj: DL_Organization = plainToClass(DL_Organization, {
          name: request.agency.name,
          acronym: request._id,
          retired: request?.retired ?? null,
          type: request?.agency?.type ?? null,
          stakeholder: request?.stakeholder ?? null,
          enrolledInVsTimestamp: request?.enrolled ?? null,
          periodStartVsTimestamp: request?.period_start ?? null,
          reportTypes: request?.report_types ?? null,
          scanTypes: request?.scan_types ?? null
        });

        //Save and link Orgs Location and Networks
        const org_id = await saveOrganizationToMdl(
          orgObj,
          networkList,
          location
        );
        // add the acronym: org_id pair to the dictionary so we can reference it later
        org_id_dict[request._id] = org_id;
      }

      // For any org that has child organnizations, link them here.
      for (const [key, value] of Object.entries(parent_child_dict)) {
        // Query the org using its id and bring along the children already associated with it
        const parent_promise = await DL_Organization.findOne(org_id_dict[key], {
          relations: ['children']
        });

        if (parent_promise) {
          const parent: DL_Organization = parent_promise;
          // Take the list of child acronyms and convert them to org_ids
          const children_ids: string[] = value.map(
            (acronym) => org_id_dict[acronym]
          );
          // Filter the list of children so there aren't duplicates with what is already linked to the org
          const new_children = children_ids.filter(
            (child) => !parent.children?.some((item) => item.id === child)
          );
          // Add the new children to the list already associated with the org
          parent.children?.push(
            ...new_children.map((childId) =>
              plainToClass(DL_Organization, { id: childId })
            )
          );
          await parent.save();
        }
      }

      // Do the same thing to link Sectors and Orgs
      for (const [key, value] of Object.entries(sector_child_dict)) {
        const sector_promise = await Sector.findOne(key, {
          relations: ['organizations']
        });
        if (sector_promise) {
          const sector: Sector = sector_promise;
          const organization_ids: string[] = value.map(
            (acronym) => org_id_dict[acronym]
          );
          // Remove orgs that did't have an id in our dictionary
          organization_ids.filter(
            (item) => item !== null && item !== undefined
          );
          const new_orgs = organization_ids.filter(
            (org_child) =>
              !sector.organizations?.some((item) => item.id === org_child)
          );
          sector.organizations?.push(
            ...new_orgs.map((org_childId) =>
              plainToClass(DL_Organization, { id: org_childId })
            )
          );
          await sector.save();
        }
      }
    }
  } catch (error) {
    console.error('Error reading requests file:', error);
    throw error;
  }

  // Connect to Redshift and select vuln_scans table
  let vulnScansArray;
  try {
    const startTime = Date.now();
    const query =
      'SELECT * FROM vmtableau.vulns_scans WHERE time >= DATE_SUB(NOW(), INTERVAL 2 DAY);';
    const result = await client.query(query);
    const endTime = Date.now();
    const durationMs = endTime - startTime;
    const durationSeconds = Math.round(durationMs / 1000);
    vulnScansArray = result.rows;
  } catch (error) {
    console.error(
      'Error connecting to redshift and getting requests data:',
      error
    );
    return error;
  }
  try {
    if (vulnScansArray && Array.isArray(vulnScansArray)) {
      const vuln_list: VulnScan[] = [];
      for (const vuln of vulnScansArray) {
        let ip_id: string | null = null;
        if (vuln.ip != null) {
          ip_id = await saveIpToMdl(
            plainToClass(Ip, {
              ip: vuln.ip,
              organization: { id: org_id_dict[vuln.owner] }
            })
          );
        }

        let cve_id: string | null = null;
        if (vuln.cve != null) {
          cve_id = await saveCveToMdl(
            plainToClass(DL_Cve, {
              name: vuln.cve
            })
          );
        }

        const vuln_id: string = getValueAndDelete(vuln, '_id') as string;
        const vulnScanObj: VulnScan = plainToClass(VulnScan, {
          id: vuln_id.replace("ObjectId('", '').replace("')", ''),
          assetInventory: getValueAndDelete(vuln, 'asset_inventory'),
          bid: getValueAndDelete(vuln, 'bid'),
          certId: getValueAndDelete(vuln, 'cert'),
          cisaKnownExploited: getValueAndDelete(vuln, 'cisa-known-exploited'),
          ciscoBugId: getValueAndDelete(vuln, 'cisco-bug-id'),
          ciscoSa: getValueAndDelete(vuln, 'cisco-sa'),
          cpe: getValueAndDelete(vuln, 'cpe'),
          cve: cve_id == null ? null : { id: cve_id },
          cveString: getValueAndDelete(vuln, 'cve'),
          cvss3BaseScore: getValueAndDelete(vuln, 'cvss3_base_score'),
          cvss3TemporalScore: getValueAndDelete(vuln, 'cvss3_temporal_score'),
          cvss3TemporalVector: getValueAndDelete(vuln, 'cvss3_temporal_vector'),
          cvss3Vector: getValueAndDelete(vuln, 'cvss3_vector'),
          cvssBaseScore: getValueAndDelete(vuln, 'cvss_base_score'),
          cvssScoreRationale: getValueAndDelete(vuln, 'cvss_score_rationale'),
          cvssScoreSource: getValueAndDelete(vuln, 'cvss_score_source'),
          cvssTemporalScore: getValueAndDelete(vuln, 'cvss_temporal_score'),
          cvssTemporalVector: getValueAndDelete(vuln, 'cvss_temporal_vector'),
          cvssVector: getValueAndDelete(vuln, 'cvss_vector'),
          cwe: getValueAndDelete(vuln, 'cwe'),
          description: getValueAndDelete(vuln, 'description'),
          exploitAvailable: getValueAndDelete(vuln, 'exploit_available'),
          exploitabilityEase: getValueAndDelete(vuln, 'exploit_ease'),
          exploitedByMalware: getValueAndDelete(vuln, 'exploited_by_malware'),
          fName: getValueAndDelete(vuln, 'fname'),
          ip: ip_id == null ? null : { id: ip_id },
          ipString: getValueAndDelete(vuln, 'ip'),
          latest: getValueAndDelete(vuln, 'latest'),
          organization: { id: org_id_dict[vuln.owner] }, // link to organization
          owner: getValueAndDelete(vuln, 'owner'),
          osvdbId: getValueAndDelete(vuln, 'osvdb'),
          patchPublicationTimestamp: getValueAndDelete(
            vuln,
            'patch_publication_date'
          ),
          pluginFamily: getValueAndDelete(vuln, 'plugin_family'),
          pluginId: getValueAndDelete(vuln, 'plugin_id'),
          pluginModificationDate: getValueAndDelete(
            vuln,
            'plugin_modification_date'
          ),
          pluginName: getValueAndDelete(vuln, 'plugin_name'),
          pluginOutput: getValueAndDelete(vuln, 'plugin_output'),
          pluginPublicationDate: getValueAndDelete(
            vuln,
            'plugin_publication_date'
          ),
          pluginType: getValueAndDelete(vuln, 'plugin_type'),
          port: getValueAndDelete(vuln, 'port'),
          portProtocol: getValueAndDelete(vuln, 'protocol'),
          riskFactor: getValueAndDelete(vuln, 'risk_factor'),
          scriptVersion: getValueAndDelete(vuln, 'script_version'),
          seeAlso: getValueAndDelete(vuln, 'see_also'),
          service: getValueAndDelete(vuln, 'service'),
          severity: getValueAndDelete(vuln, 'severity'),
          solution: getValueAndDelete(vuln, 'solution'),
          source: getValueAndDelete(vuln, 'source'),
          synopsis: getValueAndDelete(vuln, 'synopsis'),
          thoroughTests: getValueAndDelete(vuln, 'thorough_tests'),
          vulnDetectionTimestamp: getValueAndDelete(vuln, 'time'),
          vulnPublicationTimestamp: getValueAndDelete(
            vuln,
            'vuln_publication_date'
          ),
          xref: getValueAndDelete(vuln, 'xref'),
          otherFindings: vuln
        });

        await saveVulnScan(vulnScanObj);
      }
    }
  } catch (error) {
    console.error('Error parsing data', error);
    throw error;
  }
};

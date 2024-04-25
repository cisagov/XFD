import { S3 } from 'aws-sdk';
import { Address4, Address6 } from 'ip-address';
import {
    Organization,
    Domain,
    Vulnerability,
    connectToDatabase,
    Service,
    DL_Organization,
    Cidr,
    Location,
    Sector,
    VulnScan,
    Ip,
    DL_Cve,
    Contact,
    connectToDatalake
  } from '../models';

import getOrganizationFromAcronym from './helpers/getOrganizationFromAcronym';
import { CommandOptions } from './ecs-client';
import S3Client from './s3-client';
import stream from 'stream';
import * as tar from 'tar';
import * as fs from 'fs';
import * as path from 'path';
import * as unbzip2 from 'unbzip2-stream';
import * as dns from 'dns';
import saveDomainsReturn from './helpers/saveDomainsReturn';
import saveVulnScan from './helpers/saveVulnScan';
import saveOrganizationToMdl from './helpers/saveOrganizationToMdl';
import saveIpToMdl from './helpers/saveIpToMdl';
import saveCveToMdl from './helpers/saveCveToMdl';
import { plainToClass, classToPlain, plainToClassFromExist } from 'class-transformer';
import saveServicesToDb from './helpers/saveServicesToDb';
import saveVulnerabilitiesToDb from './helpers/saveVulnerabilitiesToDb';

const LOCAL_DIRECTORY = './extracted_files/';

// function breakCPE(cpe: string): { cpe: string | null, vendor: string, name: string, version: string | null } {
//   // Regular expression to match CPE format
//   const regex = /^cpe:\/{2}([^:]+):([^:]+):([^:]+)(?::(.*?))?$/;
  
//   // Executing the regular expression on the CPE string
//   const match = cpe.match(regex);
  
//   if (match && match.length >= 4) {
//       // Extracting vendor and productName
//       const vendor = match[1];
//       const name = match[2];
//       let version: string | null = null;
//       if (match[4] !== undefined) {
//           version = match[4];
//       }

//       return { cpe, vendor, name, version };
//   } else {
//       // If the CPE string doesn't match the expected format, return an empty object
//       return {cpe: null, vendor: '', name: '', version: null };
//   }
// }

/** Removes a value for a given key from the dictionary and then returns it. */
function getValueAndDelete<T>(obj: { [key: string]: T }, key: string): T | undefined {
  if (obj.hasOwnProperty(key)) {
      const value = obj[key];
      delete obj[key];
      return value;
  } else {
      return undefined;
  }
}

export const handler = async (commandOptions: CommandOptions) => {
  // A dictionary to associated the organizationId with the the acronym
  const org_id_dict:{[key: string]: string} = {}
      try{
        // Dictionary linking parents to children acronym:[list of chilren]
        const parent_child_dict:{[key: string]: string[]} = {}
        // Dictionary linking sectors to orgs
        const sector_child_dict:{[key: string]: string[]} = {}
        const requestsFilePath = '/app/worker/requests_sample.json'
        const requestJsonString = fs.readFileSync(requestsFilePath, 'utf-8')
        const requestArray = JSON.parse(requestJsonString)
        const non_sector_list: string[] = ['CRITICAL_INFRASTRUCTURE', 'FEDERAL', 'ROOT', 'SLTT', 'CATEGORIES', 'INTERNATIONAL', 'THIRD_PARTY']
        if (requestArray && Array.isArray(requestArray)) {
          
          for (const request of requestArray ?? []){
            request.agency = JSON.parse(request.agency)
            request.networks = JSON.parse(request.networks)
            request.report_types = JSON.parse(request.report_types)
            request.scan_types = JSON.parse(request.scan_types)
            request.children = JSON.parse(request.children)
            
            //Sectors don't have types can use the type property to determine if its a sector
            if (!request.agency.hasOwnProperty('type')){
              console.log('In sector section')
              // Do Sector Category and Tag logic here
              //If the sector is in the non_sector_list skip it, it doesn't link to any orgs just other sectors
              if (non_sector_list.includes(request._id)){
                  continue
                }
              
              // if a sector has children create a sector object
              if (request.hasOwnProperty("children") && Array.isArray(request.children) && request.children.length > 0){
                const sector: Sector = plainToClass(Sector,{
                  name: request.agency.name,
                  acronym: request._id,
                  retired: request?.retired ?? null,
                })
                //Remove null fields so if we update, we don't remove valid data
                const sectorUpdatedValues = Object.keys(sector)
                  .map((key) => {
                    if (['acronym'].indexOf(key) > -1)
                      return '';
                    return sector[key] !== null ? key : '';
                  })
                  .filter((key) => key !== '');
                  // Save the sector to the database, update sector if it already exists
                  let sectorId: string = (
                    await Sector.createQueryBuilder()
                      .insert()
                      .values(sector)
                      .orUpdate({
                        conflict_target: ["acronym"],
                        overwrite: sectorUpdatedValues  
                      }
                      )
                      .returning('id')
                      .execute()
                  ).identifiers[0].id;
                  // Add sector and orgs to the sector_child_dict so we can link them after creating the orgs
                  sector_child_dict[sectorId] = request.children 
              }
              // go to the next request record
              continue
            }
            // If the org has children add them to the dictionary which will be used to link them after the initial save
            if (request.hasOwnProperty("children") && Array.isArray(request.children) && request.children.length > 0){
              console.log('in parentChild link section')
              parent_child_dict[request._id] = request.children 
            }
            // Loop through the networks and create network objects
            const networkList: Cidr[] = [];
            for (const cidr of request.networks ?? []){
              try {
                const address = cidr.includes(':') ? new Address6(cidr) : new Address4(cidr);
                const firstIP = address.startAddress().address;
                const lastIP = address.endAddress().address;
                
                networkList.push(plainToClass(Cidr, {
                  network: cidr,
                  startIp: firstIP,
                  endIp: lastIP
                })
              )
              } catch (error) {
                console.error('Invalid CIDR format:', error.message);
                continue;
              }
            }
            
            // // Currently isn't coming through our pull
            // const contacts: Contact[] = [];
            // for (const contact of request.agency.contacts ?? []){
            //   try {
            //     contacts.push(plainToClass(Contact,{
            //       name: request.agency.contact.name
            //       email: string | null;
            //       phoneNumber: string | null;
            //       type: string | null;
            //       retired: boolean;
            //     }))
            //   } catch (error) {
            //     console.log('Invalid Contact format:', error.message)
            //     continue;
            //   }
            // }

            //Create a Location object
            let location:Location | null  = null;
            if (request.agency.location){
              location = plainToClass(Location,{
                name: request.agency.location.name,
                countryAbrv: request.agency.location.country,
                country: request.agency.location.country_name,
                county: request.agency.location.county,
                countyFips: request.agency.location.county_fips,
                gnisId: request.agency.location.gnis_id,
                stateAbrv: request.agency.location.state,
                stateFips: request.agency.location.state_fips,
                state: request.agency.location.state_name,
              })
            }
            
            
            // Create organization object
            const orgObj: DL_Organization = plainToClass(DL_Organization, {
              name: request.agency.name ,
              acronym: request._id,
              retired: request?.retired ?? null,
              type: request?.agency?.type ?? null,
              stakeholder: request?.stakeholder ?? null,
              enrolledInVsTimestamp:request?.enrolled ?? null,
              periodStartVsTimestamp:request?.period_start ?? null,  
              reportTypes: request?.report_types ?? null,
              scanTypes: request?.scan_types ?? null,
            })
            
            //Save and link Orgs Location and Networks
            const org_id = await saveOrganizationToMdl(orgObj, networkList, location)
            // add the acronym: org_id pair to the dictionary so we can reference it later
            org_id_dict[request._id] = org_id
          }
          
          // For any org that has child organnizations, link them here.
          for (const [key, value] of Object.entries(parent_child_dict)) {
            // Query the org using its id and bring along the children already associated with it
            const parent_promise = await DL_Organization.findOne(org_id_dict[key],{relations: ['children']})
            
            if(parent_promise){
              const parent: DL_Organization = parent_promise
              // Take the list of child acronyms and convert them to org_ids
              const children_ids: string[] = value.map(acronym => org_id_dict[acronym])
              // Filter the list of children so there aren't duplicates with what is already linked to the org
              const new_children = children_ids.filter(child => !parent.children?.some(item => item.id === child))
              // Add the new children to the list already associated with the org
              parent.children?.push(...new_children.map(childId => (plainToClass(DL_Organization,{ id: childId }))))
              await parent.save()
            }
          }
          
          // Do the same thing to link Sectors and Orgs
          for(const [key, value] of Object.entries(sector_child_dict)) {
            console.log(`Key: ${key}, Value: ${value}`);
            const sector_promise = await Sector.findOne(key,{relations: ['organizations']})
            if(sector_promise){
              const sector: Sector = sector_promise
              const organization_ids: string[] = value.map(acronym => org_id_dict[acronym])
              // Remove orgs that did't have an id in our dictionary
              organization_ids.filter(item => item !== null && item !== undefined)
              const new_orgs = organization_ids.filter(org_child => !sector.organizations?.some(item => item.id === org_child))
              sector.organizations?.push(...new_orgs.map(org_childId => (plainToClass(DL_Organization,{ id: org_childId }))))
              await sector.save()
            }
          }
        }
       
      }
    
      catch (error) {
        console.error("Error reading requests file:", error);
        throw error;
      }


      const vulnScanFilePath = '/app/worker/vuln_scan_sample.json'
      try{
        const jsonString = fs.readFileSync(vulnScanFilePath, 'utf-8');
        // Parse the JSON string to an object
        const jsonArray = JSON.parse(jsonString);
        if (jsonArray && Array.isArray(jsonArray)) {
          const vuln_list: VulnScan[] = []
          for (const vuln of jsonArray ?? []) {
            let ip_id:string | null = null;
            if (vuln.ip != null){
              ip_id = await saveIpToMdl(plainToClass(Ip,{
                ip: vuln.ip,
                organization: {id: org_id_dict[vuln.owner]}
              }))
            }
            
            let cve_id: string | null = null;
            if(vuln.cve != null){
              cve_id = await saveCveToMdl(plainToClass(DL_Cve,{
                name: vuln.cve,
              }))
            }
            
            const vuln_id:string = getValueAndDelete(vuln,'_id') as string
            const vulnScanObj: VulnScan = plainToClass(VulnScan, {
              id: vuln_id.replace("ObjectId('", "").replace("')", ""),
              assetInventory: getValueAndDelete(vuln,'asset_inventory'),
              bid: getValueAndDelete(vuln,'bid'),
              certId: getValueAndDelete(vuln,'cert'),
              cisaKnownExploited: getValueAndDelete(vuln,'cisa-known-exploited'), 
              ciscoBugId: getValueAndDelete(vuln,'cisco-bug-id'), 
              ciscoSa: getValueAndDelete(vuln,'cisco-sa'), 
              cpe: getValueAndDelete(vuln,'cpe'),
              // @ManyToOne((type) => Cve, (cve) => cve.vulnScans, {
              //   onDelete: 'CASCADE',
              //   nullable: true
              // })
              cve: cve_id == null ? null : {id: cve_id},
              cveString: getValueAndDelete(vuln,'cve'),
              cvss3BaseScore: getValueAndDelete(vuln,'cvss3_base_score'),
              cvss3TemporalScore: getValueAndDelete(vuln,'cvss3_temporal_score'),
              cvss3TemporalVector: getValueAndDelete(vuln,'cvss3_temporal_vector'),
              cvss3Vector: getValueAndDelete(vuln,'cvss3_vector'),
              cvssBaseScore: getValueAndDelete(vuln, 'cvss_base_score'),
              cvssScoreRationale: getValueAndDelete(vuln, 'cvss_score_rationale'),
              cvssScoreSource: getValueAndDelete(vuln, 'cvss_score_source'),
              cvssTemporalScore: getValueAndDelete(vuln, 'cvss_temporal_score'),
              cvssTemporalVector: getValueAndDelete(vuln, 'cvss_temporal_vector'),
              cvssVector: getValueAndDelete(vuln, 'cvss_vector'),
              cwe: getValueAndDelete(vuln, 'cwe'),
              description: getValueAndDelete(vuln, 'description'),
              exploitAvailable: getValueAndDelete(vuln, 'exploit_available'),
              exploitabilityEase: getValueAndDelete(vuln,'exploit_ease'),
              exploitedByMalware: getValueAndDelete(vuln,'exploited_by_malware'),
              fName: getValueAndDelete(vuln,'fname'), 
              ip: ip_id == null ? null : {id: ip_id},
              ipString: getValueAndDelete(vuln, 'ip'),
              latest:  getValueAndDelete(vuln, 'latest'),
              organization: {id: org_id_dict[vuln.owner]}, // link to organization
              owner:  getValueAndDelete(vuln, 'owner'),
              osvdbId:  getValueAndDelete(vuln, 'osvdb'),
              patchPublicationTimestamp: getValueAndDelete(vuln, 'patch_publication_date'),
              pluginFamily: getValueAndDelete(vuln, 'plugin_family'),
              pluginId: getValueAndDelete(vuln, 'plugin_id'),
              pluginModificationDate: getValueAndDelete(vuln, 'plugin_modification_date'),
              pluginName: getValueAndDelete(vuln, 'plugin_name'),
              pluginOutput: getValueAndDelete(vuln, 'plugin_output'),
              pluginPublicationDate: getValueAndDelete(vuln, 'plugin_publication_date'),
              pluginType: getValueAndDelete(vuln, 'plugin_type'),
              port: getValueAndDelete(vuln, 'port'),
              portProtocol: getValueAndDelete(vuln, 'protocol'),
              riskFactor: getValueAndDelete(vuln, 'risk_factor'),
              scriptVersion: getValueAndDelete(vuln, 'script_version'),
              seeAlso: getValueAndDelete(vuln, 'see_also'),
              service: getValueAndDelete(vuln, 'service'),
              severity: getValueAndDelete(vuln, 'severity'),
              // @ManyToMany((type) => Snapshot, (snapshot) => snapshot.vulnScans, {
              //   onDelete: 'CASCADE',
              //   onUpdate: 'CASCADE'
              // })
              // @JoinTable()
              // snapshots: Snapshot[];
              solution: getValueAndDelete(vuln, 'solution'),
              source: getValueAndDelete(vuln, 'source'),
              synopsis: getValueAndDelete(vuln, 'synopsis'),
              thoroughTests: getValueAndDelete(vuln, 'thorough_tests'),
              vulnDetectionTimestamp: getValueAndDelete(vuln, 'time'),
              vulnPublicationTimestamp: getValueAndDelete(vuln, 'vuln_publication_date'),
              xref: getValueAndDelete(vuln, 'xref'),
              otherFindings:vuln

              // bugtraqId:,
              // pluginFilename: string | null;
              // exploitFrameworkMetasploit: boolean;
              // metasploitName: string | null;
              // edbId: string | null;
              // exploitFrameworkCore: boolean;
              // stigSeverity: string | null;
              // iava: string | null;
              // iavb: string | null;
              // tra: string | null;
              // msft: string | null;
              // canvasPackage: string | null;
              // exploitFrameworkCanvas: boolean;
              // secunia: string | null;
              // agent: string | null;
              // rhsa: string | null;
              // inTheNews: boolean;
              // attachment: string | null;
              // vprScore: number | null;
              // threatSourcesLast28: string | null;
              // exploitCodeMaturity: string | null;
              // threatIntensityLast28: string | null;
              // ageOfVuln: string | null;
              // cvssV3ImpactScore: number | null;
              // threatRecency: string | null;
              // productCoverage: string | null;
              // exploitedByNessus: boolean;
              // unsupportedByVendor: boolean;
              // requiredKey: string | null;
              // requiredPort: number | null;
              // scriptCopyright: string | null;
              // mskb: string | null;
              // dependency: string | null;
            });

            await saveVulnScan(vulnScanObj)
          }
          }
        
      }
      catch (error) {
            console.error("Error reading json file:", error);
            throw error;
          }
      //   
      //     // Loop through each object in the array
          
      //       

      //         // Save discovered domains and ips to the Domain table
      //         let domainId;
      //         let service_domain;
      //         let service_ip;
      //         let ipOnly = false;
      //         let org_id: string;
      //         // await getOrgId(orgDictionary, vuln.owner)
      //         if (orgDictionary.hasOwnProperty(vuln.owner)) {
      //           org_id = orgDictionary[vuln.owner]
      //         } else {
      //           // switch to findOneBy once we update crossfeed
      //             connectToDatabase();
      //             const orgClass = await getOrganizationFromAcronym(vuln.owner);
      //             if (!orgClass) {
      //               console.log(`Could not find an Organization that matches the acronym ${vuln.owner}`)
      //               continue;
      //             }
      //             console.log(orgClass);
      //             const org = classToPlain(orgClass);
      //             orgDictionary[vuln.owner] = org.id;
      //             org_id = org.id
      //         }
              
      //         if (!org_id){
      //           console.log(`Could not find an Organization that matches the acronym ${vuln.owner}`)
      //           continue
      //         }
      //         try {
      //           // Lookup domain based on IP
                
      //             service_ip = vuln.ip;
      //             try {
      //               service_domain = (await dns.promises.reverse(service_ip))[0];
      //               // console.log(service_domain);
      //             } catch {
      //               console.log(`Setting domain to IP: ${service_ip}`);
      //               service_domain = service_ip;
      //               ipOnly = true;
      //             }
                
      //           [domainId] = await saveDomainsReturn([
      //             plainToClass(Domain, {
      //               name: service_domain,
      //               ip: service_ip,
      //               organization: { id: org_id },
      //               fromRootDomain: !ipOnly
      //                 ? service_domain.split('.').slice(-2).join('.')
      //                 : null,
      //               discoveredBy: { id: commandOptions.scanId },
      //               subdomainSource: `Vulnerability Scanning`,
      //               ipOnly: ipOnly
      //             })
      //           ]);
      //           console.log(`Successfully saved domain with id: ${domainId}`);
      //         } catch (e) {
      //           console.error(`Failed to save domain ${service_domain}`);
      //           console.error(e);
      //           console.error('Continuing to next vulnerability');
      //           continue;
      //         }
      
      //         let serviceId;
      //         if (vuln.port != null) {
      //           try {
                  
      //             // Save discovered services to the Service table
      //             [serviceId] = await saveServicesToDb([
      //               plainToClass(Service, {
      //                 domain: { id: domainId },
      //                 service: vuln.service,
      //                 discoveredBy: { id: commandOptions.scanId },
      //                 port: Number(vuln.port),
      //                 lastSeen: new Date(vuln.time),
      //                 serviceSource: "Vulnerability Scanning",
      //                 shodanResults:{},
      //                 products: vuln.cpe === null ? null : [breakCPE(vuln.cpe)]
      //               })
      //             ]);
      //             console.log('Saved services.');
      //           } catch (e) {
      //             console.error(
      //               'Could not save services. Continuing to next vulnerability.'
      //             );
      //             console.error(e);
      //             continue;
      //           }
      //         }
      
      //         try {
      //           const vulns: Vulnerability[] = [];
      //           vulns.push(
      //             plainToClass(Vulnerability, {
      //               domain: domainId,
      //               lastSeen: vuln.time,
      //               title: vuln.cve === null? vuln.fname : vuln.cve,
      //               cve: vuln.cve,
      //               cwe: vuln.cwe,
      //               description: vuln.description,
      //               cvss: vuln.cvss3_base_score,
      //               severity: vuln.severity,
      //               state: vuln.state,
      //               structuredData: {
      //                 "vs_id": vuln._id,
      //                 "asset_inventory": vuln.asset_inventory,
      //                 "bid": vuln.bid,
      //                 "cert": vuln.cert,
      //                 "cisa-known-exploited": vuln["cisa-known-exploited"],
      //                 "cisco-bug-id": vuln["cisco-bug-id"],
      //                 "cisco-sa": vuln["cisco-sa"],
      //                 "cvss3_base_score": vuln["cvss3_base_score"],
      //                 "cvss3_temporal_score": vuln["cvss3_temporal_score"],
      //                 "cvss3_temporal_vector": vuln["cvss3_temporal_vector"],
      //                 "cvss3_vector": vuln["cvss3_vector"],
      //                 "cvss_base_score": vuln["cvss_base_score"],
      //                 "cvss_score_rationale": vuln["cvss_score_rationale"],
      //                 "cvss_score_source": vuln["cvss_score_source"],
      //                 "cvss_temporal_score": vuln["cvss_temporal_score"],
      //                 "cvss_temporal_vector": vuln["cvss_temporal_vector"],
      //                 "cvss_vector": vuln["cvss_vector"],
      //                 "exploit_available": vuln["exploit_available"],
      //                 "exploit_ease": vuln["exploit_ease"],
      //                 "exploited_by_malware": vuln["exploited_by_malware"],
      //                 "fname": vuln["fname"],
      //                 "latest": vuln["latest"],
      //                 "owner": "AACG",
      //                 "osvdb": vuln["osvdb"],
      //                 "patch_publication_date": vuln["patch_publication_date"],
      //                 "plugin_family": vuln["plugin_family"],
      //                 "plugin_id": vuln["plugin_id"],
      //                 "plugin_modification_date": vuln["plugin_modification_date"],
      //                 "plugin_name": vuln["plugin_name"],
      //                 "plugin_output": vuln["plugin_output"],
      //                 "plugin_publication_date": vuln["plugin_publication_date"],
      //                 "plugin_type": vuln["plugin_type"],
      //                 "port": vuln["port"],
      //                 "protocol": vuln["protocol"],
      //                 "risk_factor": vuln["risk_factor"],
      //                 "script_version": vuln["script_version"],
      //                 "see_also": vuln["see_also"],
      //                 "service": vuln["service"],
      //                 "severity": vuln["severity"],
      //                 "snapshots": vuln["snapshots"],
      //                 "solution": vuln["solution"],
      //                 "source": vuln["source"],
      //                 "synopsis": vuln["synopsis"],
      //                 "thorough_tests": vuln["thorough_tests"],
      //                 "time": vuln["time"],
      //                 "vuln_publication_date": vuln["vuln_publication_date"],
      //                 "xref": vuln["xref"]
      //               },
      //               source: vuln.source,
      //               needsPopulation: vuln.needsPopulation,
      //               service: vuln.port == null ? null : { id: serviceId }
      //             })
      //           );
      //           await saveVulnerabilitiesToDb(vulns, false);
      //         } catch (e) {
      //           console.error('Could not save vulnerabilities. Continuing.');
      //           console.error(e);
      //         }
      //       }
              
          // };
      
    // }
    //   catch (error) {
    //     console.error("Error reading json file:", error);
    //     throw error;
    //   }
};

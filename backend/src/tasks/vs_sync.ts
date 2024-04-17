import { S3 } from 'aws-sdk';
import {
    Organization,
    Domain,
    Vulnerability,
    connectToDatabase,
    Service,
  } from '../models';
import getOrganizationId from './helpers/getOrganizationId';
import { CommandOptions } from './ecs-client';
import S3Client from './s3-client';
import stream from 'stream';
import * as tar from 'tar';
import * as fs from 'fs';
import * as path from 'path';
import * as unbzip2 from 'unbzip2-stream';
import * as dns from 'dns';
import saveDomainsReturn from './helpers/saveDomainsReturn';
import { plainToClass, classToPlain } from 'class-transformer';
import saveServicesToDb from './helpers/saveServicesToDb';
import saveVulnerabilitiesToDb from './helpers/saveVulnerabilitiesToDb';

const LOCAL_DIRECTORY = './extracted_files/';

function breakCPE(cpe: string): { cpe: string | null, vendor: string, name: string, version: string | null } {
  // Regular expression to match CPE format
  const regex = /^cpe:\/{2}([^:]+):([^:]+):([^:]+)(?::(.*?))?$/;
  
  // Executing the regular expression on the CPE string
  const match = cpe.match(regex);
  
  if (match && match.length >= 4) {
      // Extracting vendor and productName
      const vendor = match[1];
      const name = match[2];
      let version: string | null = null;
      if (match[4] !== undefined) {
          version = match[4];
      }

      return { cpe, vendor, name, version };
  } else {
      // If the CPE string doesn't match the expected format, return an empty object
      return {cpe: null, vendor: '', name: '', version: null };
  }
}

export const handler = async (commandOptions: CommandOptions) => {
    
      const jsonFilePath = '/app/worker/vuln_scan_sample.json'
      try{
        const jsonString = fs.readFileSync(jsonFilePath, 'utf-8');
        // Parse the JSON string to an object
        const jsonArray = JSON.parse(jsonString);
        let orgDictionary: { [key: string]: string } = {};
        if (jsonArray && Array.isArray(jsonArray)) {
          // Loop through each object in the array
          
            for (const vuln of jsonArray ?? []) {

              // Save discovered domains and ips to the Domain table
              let domainId;
              let service_domain;
              let service_ip;
              let ipOnly = false;
              let org_id: string;
              // await getOrgId(orgDictionary, vuln.owner)
              if (orgDictionary.hasOwnProperty(vuln.owner)) {
                org_id = orgDictionary[vuln.owner]
              } else {
                // switch to findOneBy once we update crossfeed
                  connectToDatabase();
                  const orgClass = await getOrganizationId(vuln.owner);
                  if (!orgClass) {
                    console.log(`Could not find an Organization that matches the acronym ${vuln.owner}`)
                    continue;
                  }
                  console.log(orgClass);
                  const org = classToPlain(orgClass);
                  orgDictionary[vuln.owner] = org.id;
                  org_id = org.id
              }
              console.log('printing test')
              console.log(orgDictionary)
              console.log(vuln.owner)
              if (!org_id){
                console.log(org_id)
                console.log(`Could not find an Organization that matches the acronym ${vuln.owner}`)
                continue
              }
              try {
                // Lookup domain based on IP
                
                  service_ip = vuln.ip;
                  try {
                    service_domain = (await dns.promises.reverse(service_ip))[0];
                    console.log(service_domain);
                  } catch {
                    console.log(`Setting domain to IP: ${service_ip}`);
                    service_domain = service_ip;
                    ipOnly = true;
                  }
                
                [domainId] = await saveDomainsReturn([
                  plainToClass(Domain, {
                    name: service_domain,
                    ip: service_ip,
                    organization: { id: org_id },
                    fromRootDomain: !ipOnly
                      ? service_domain.split('.').slice(-2).join('.')
                      : null,
                    discoveredBy: { id: commandOptions.scanId },
                    subdomainSource: `Vulnerability Scanning`,
                    ipOnly: ipOnly
                  })
                ]);
                console.log(`Successfully saved domain with id: ${domainId}`);
              } catch (e) {
                console.error(`Failed to save domain ${service_domain}`);
                console.error(e);
                console.error('Continuing to next vulnerability');
                continue;
              }
      
              let serviceId;
              if (vuln.port != null) {
                try {
                  
                  // Save discovered services to the Service table
                  [serviceId] = await saveServicesToDb([
                    plainToClass(Service, {
                      domain: { id: domainId },
                      service: vuln.service,
                      discoveredBy: { id: commandOptions.scanId },
                      port: Number(vuln.port),
                      lastSeen: new Date(vuln.time),
                      serviceSource: "Vulnerability Scanning",
                      shodanResults:{},
                      product: vuln.cpe === null ? null : [breakCPE(vuln.cpe)]
                    })
                  ]);
                  console.log('Saved services.');
                } catch (e) {
                  console.error(
                    'Could not save services. Continuing to next vulnerability.'
                  );
                  console.error(e);
                  continue;
                }
              }
      
              try {
                const vulns: Vulnerability[] = [];
                vulns.push(
                  plainToClass(Vulnerability, {
                    domain: domainId,
                    lastSeen: vuln.time,
                    title: vuln.cve,
                    cve: vuln.cve,
                    cwe: vuln.cwe,
                    description: vuln.description,
                    cvss: vuln.cvss3_base_score,
                    severity: vuln.severity,
                    state: vuln.state,
                    structuredData: {
                      "vs_id": vuln._id,
                      "asset_inventory": vuln.asset_inventory,
                      "bid": vuln.bid,
                      "cert": vuln.cert,
                      "cisa-known-exploited": vuln["cisa-known-exploited"],
                      "cisco-bug-id": vuln["cisco-bug-id"],
                      "cisco-sa": vuln["cisco-sa"],
                      "cvss3_base_score": vuln["cvss3_base_score"],
                      "cvss3_temporal_score": vuln["cvss3_temporal_score"],
                      "cvss3_temporal_vector": vuln["cvss3_temporal_vector"],
                      "cvss3_vector": vuln["cvss3_vector"],
                      "cvss_base_score": vuln["cvss_base_score"],
                      "cvss_score_rationale": vuln["cvss_score_rationale"],
                      "cvss_score_source": vuln["cvss_score_source"],
                      "cvss_temporal_score": vuln["cvss_temporal_score"],
                      "cvss_temporal_vector": vuln["cvss_temporal_vector"],
                      "cvss_vector": vuln["cvss_vector"],
                      "exploit_available": vuln["exploit_available"],
                      "exploit_ease": vuln["exploit_ease"],
                      "exploited_by_malware": vuln["exploited_by_malware"],
                      "fname": vuln["fname"],
                      "latest": vuln["latest"],
                      "owner": "AACG",
                      "osvdb": vuln["osvdb"],
                      "patch_publication_date": vuln["patch_publication_date"],
                      "plugin_family": vuln["plugin_family"],
                      "plugin_id": vuln["plugin_id"],
                      "plugin_modification_date": vuln["plugin_modification_date"],
                      "plugin_name": vuln["plugin_name"],
                      "plugin_output": vuln["plugin_output"],
                      "plugin_publication_date": vuln["plugin_publication_date"],
                      "plugin_type": vuln["plugin_type"],
                      "port": vuln["port"],
                      "protocol": vuln["protocol"],
                      "risk_factor": vuln["risk_factor"],
                      "script_version": vuln["script_version"],
                      "see_also": vuln["see_also"],
                      "service": vuln["service"],
                      "severity": vuln["severity"],
                      "snapshots": vuln["snapshots"],
                      "solution": vuln["solution"],
                      "source": vuln["source"],
                      "synopsis": vuln["synopsis"],
                      "thorough_tests": vuln["thorough_tests"],
                      "time": vuln["time"],
                      "vuln_publication_date": vuln["vuln_publication_date"],
                      "xref": vuln["xref"]
                    },
                    source: vuln.source,
                    needsPopulation: vuln.needsPopulation,
                    service: vuln.port == null ? null : { id: serviceId }
                  })
                );
                await saveVulnerabilitiesToDb(vulns, false);
              } catch (e) {
                console.error('Could not save vulnerabilities. Continuing.');
                console.error(e);
              }
            }
              
          };
      
    }
      catch (error) {
        console.error("Error reading json file:", error);
        throw error;
      }
};
    




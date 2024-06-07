import { int } from 'aws-sdk/clients/datapipeline';
import { CommandOptions } from './ecs-client';
import { Cpe, Cve } from '../models';
import axios from 'axios';
import { plainToClass } from 'class-transformer';
import {
  connectToDatabase,
  Domain,
  Service,
  Vulnerability,
  Organization
} from '../models';
import { isIP } from 'net';
import * as dns from 'dns';
import saveDomainsReturn from './helpers/saveDomainsReturn';

interface XpanseVulnOutput {
  alert_name: string;
  description: string;
  last_modified_ts: Date;
  local_insert_ts: Date;
  event_timestamp: Date[];
  host_name: string;
  alert_action: string;
  action_country: string[];
  action_remote_port: number[];
  external_id: string;
  related_external_id: string;
  alert_occurrence: number;
  severity: string;
  matching_status: string;
  alert_type: string;
  resolution_status: string;
  resolution_comment: string;
  last_observed: string;
  country_codes: string[];
  cloud_providers: string[];
  ipv4_addresses: string[];
  domain_names: string[];
  port_protocol: string;
  time_pulled_from_xpanse: string;
  action_pretty: string;
  attack_surface_rule_name: string;
  certificate: Record<string, any>; //Change this to a
  remediation_guidance: string;
  asset_identifiers: Record<string, any>[];
  services: XpanseServiceOutput[];
}
interface XpanseServiceOutput {
  service_id?: string;
  service_name?: string;
  service_type?: string;
  ip_address?: string[];
  domain?: string[];
  externally_detected_providers?: string[];
  is_active?: string;
  first_observed?: string;
  last_observed?: string;
  port?: number;
  protocol?: string;
  active_classifications?: string[];
  inactive_classifications?: string[];
  discovery_type?: string;
  externally_inferred_vulnerability_score?: string;
  externally_inferred_cves?: string[];
  service_key?: string;
  service_key_type?: string;
  cves?: XpanseCveOutput[];
}
interface XpanseCveOutput {
  cve_id?: string;
  cvss_score_v2?: string;
  cve_severity_v2?: string;
  cvss_score_v3?: string;
  cve_severity_v3?: string;
  inferred_cve_match_type?: string;
  product?: string;
  confidence?: string;
  vendor?: string;
  version_number?: string;
  activity_status?: string;
  first_observed?: string;
  last_observed?: string;
}
interface TaskResponse {
  task_id: string;
  status: string;
  result: null | {
    total_pages: number;
    current_page: number;
    data: XpanseVulnOutput[];
  };
  error: string | null;
}
function isIPAddress(input: string): boolean {
  // Regular expression to match an IP address
  const ipRegex = /^(?:\d{1,3}\.){3}\d{1,3}$/;

  return ipRegex.test(input);
}

const createTask = async (page: number, orgId: string) => {
  console.log('Creating task to fetch CVE data');
  try {
    const response = await axios({
      url: 'https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/xpanse_vulns',
      method: 'POST',
      headers: {
        Authorization: String(process.env.CF_API_KEY),
        access_token: String(process.env.PE_API_KEY),
        'Content-Type': '' //this is needed or else it breaks because axios defaults to application/json
      },
      data: {
        org_acronym: orgId,
        page: page,
        per_page: 100 // Tested with 150 and 200 but this results in 502 errors on certain pages with a lot of CPEs
      }
    });
    if (response.status >= 200 && response.status < 300) {
      //console.log('Request was successful');
    } else {
      console.log('Request failed');
    }
    return response.data as TaskResponse;
  } catch (error) {
    console.log(`Error making POST request: ${error}`);
  }
};
const fetchData = async (task_id: string) => {
  console.log('Fetching CVE data');
  try {
    const response = await axios({
      url: `https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/xpanse_vulns/task/${task_id}`,
      headers: {
        Authorization: String(process.env.CF_API_KEY),
        access_token: String(process.env.PE_API_KEY),
        'Content-Type': ''
      }
    });
    if (response.status >= 200 && response.status < 300) {
      //console.log('Request was successful');
    } else {
      console.log('Request failed');
    }
    return response.data as TaskResponse;
  } catch (error) {
    console.log(`Error making POST request: ${error}`);
  }
};
const getVulnData = async (org: Organization, commandOptions: CommandOptions) => {
  let done = false;
  let page = 1;
  let total_pages = 2;
  // let fullVulnArray: XpanseVulnOutput[] = [];
  while (!done) {
    let taskRequest = await createTask(page, org.acronym);
    console.log(`Fetching page ${page} of page ${total_pages}`);
    await new Promise((r) => setTimeout(r, 1000));
    if (taskRequest?.status == 'Processing') {
      while (taskRequest?.status == 'Processing') {
        //console.log('Waiting for task to complete');
        await new Promise((r) => setTimeout(r, 1000));
        taskRequest = await fetchData(taskRequest.task_id);
        //console.log(taskRequest?.status);
      }
      if (taskRequest?.status == 'Completed') {
        console.log(`Task completed successfully for page: ${page}`);
        const vulnArray = taskRequest?.result?.data || []; //TODO, change this to CveEntry[]
        // fullVulnArray = fullVulnArray.concat(vulnArray);
        saveXpanseAlert(vulnArray, org, commandOptions.scanId)
        total_pages = taskRequest?.result?.total_pages || 1;
        const current_page = taskRequest?.result?.current_page || 1;
        if (current_page >= total_pages) {
          done = true;
          console.log(`Finished fetching Xpanse Alert data`);
          return 1
        }
        page = page + 1;
      }
    } else {
      done = true;
      console.log(
        `Error fetching Xpanse Alert data: ${taskRequest?.error} and status: ${taskRequest?.status}`
      );
      return 1
    }
  }
};

const saveXpanseAlert = async(alerts:XpanseVulnOutput[], org: Organization, scan_id: string) => {
  for (const vuln of alerts) {
    console.log(vuln);
    let domainId;
    let service_domain;
    let service_ip;
    let ipOnly = false;
    try{
      if (isIPAddress(vuln.host_name)) {
        service_ip = vuln.host_name;
        try {
          service_domain = (await dns.promises.reverse(service_ip))[0];
        } catch {
          service_domain = service_ip;
          ipOnly = true;
        }
        service_ip = vuln.host_name
      } else {
        service_domain = vuln.host_name;
        try {
          service_ip = (await dns.promises.lookup(service_domain)).address;
        } catch {
          service_ip = null;
        }
      }
      [domainId] = await saveXpanseDomain([
        plainToClass(Domain, {
          name: service_domain,
          ip: service_ip,
          organization: {id: org.id},
          fromRootDomain: !ipOnly
          ? service_domain.split('.').slice(-2).join('.')
          : null,
          discoveredBy: { id: scan_id},
          subdomainSource: `Palo Alto Expanse`,
          ipOnly: ipOnly
        })
      ])
  
    } catch (e) {
      console.error(`Failed to save domain ${vuln.host_name}`);
      console.error(e);
      console.error('Continuing to next vulnerability');
      continue;
    }

    try {
      let resolution;
          if (vuln.resolution_status.includes("RESOLVED")) {
            resolution =  "closed";
        } else {
          resolution = "open";
        }
      
        const vuln_obj: Vulnerability = plainToClass(Vulnerability, {
          domain: domainId,
          last_seen: vuln.last_modified_ts, 
          title: vuln.alert_name,
          cve: "Xpanse Alert",
          description: vuln.description,
          severity: vuln.severity,
          state: resolution,
          structuredData:{

          },
          source: `Palo Alto Expanse`,
          needsPopulation: true,
          service: null
        })

          saveXpanseVuln(vuln_obj)
      // save vulns if this vulns hasn't been seen or if last_seen >= last_seen on alert in db
    } catch (e) {
      console.error('Could not save vulnerability. Continuing.');
      console.error(e);
    }

  }
}

export const handler = async (CommandOptions) => {
  try {
    await connectToDatabase();
    const allOrgs: Organization[] = await Organization.find();

    for (const org of allOrgs) {
      (await getVulnData(org, CommandOptions )) || [];
    }
  } catch (e) {
    console.error('Unknown failure.');
    console.error(e);
  }
 
};

import { int } from 'aws-sdk/clients/datapipeline';
import { Cpe, Cve } from '../models';
import axios from 'axios';
import { plainToClass } from 'class-transformer';

interface XpanseVulnOutput {
  alert_name?: string;
  description?: string;
  last_modified_ts?: Date;
  local_insert_ts?: Date;
  event_timestamp?: Date[];
  host_name?: string;
  alert_action?: string;
  action_country?: string[];
  action_remote_port?: number[];
  external_id?: string;
  related_external_id?: string;
  alert_occurrence?: number;
  severity?: string;
  matching_status?: string;
  alert_type?: string;
  resolution_status?: string;
  resolution_comment?: string;
  last_observed?: string;
  country_codes?: string[];
  cloud_providers?: string[];
  ipv4_addresses?: string[];
  domain_names?: string[];
  port_protocol?: string;
  time_pulled_from_xpanse?: string;
  action_pretty?: string;
  attack_surface_rule_name?: string;
  certificate?: Record<string, any>;
  remediation_guidance?: string;
  asset_identifiers?: Record<string, any>[];
  services?: XpanseServiceOutput[];
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

const createTask = async (page: number, orgId: string) => {
  console.log('Creating task to fetch CVE data');
  try {
    const response = await axios({
      url: 'https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/cves_by_modified_date',
      method: 'POST',
      headers: {
        Authorization: String(process.env.CF_API_KEY),
        access_token: String(process.env.PE_API_KEY),
        'Content-Type': '' //this is needed or else it breaks because axios defaults to application/json
      },
      data: {
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
      url: `https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/cves_by_modified_date/task/${task_id}`,
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
const getVulnData = async (orgId: string) => {
  let done = false;
  let page = 1;
  let total_pages = 2;
  let fullVulnArray: XpanseVulnOutput[] = [];
  while (!done) {
    let taskRequest = await createTask(page, orgId);
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
        fullVulnArray = fullVulnArray.concat(vulnArray);
        total_pages = taskRequest?.result?.total_pages || 1;
        const current_page = taskRequest?.result?.current_page || 1;
        if (current_page >= total_pages) {
          done = true;
          console.log(`Finished fetching CVE data`);
          return fullVulnArray;
        }
        page = page + 1;
      }
    } else {
      done = true;
      console.log(
        `Error fetching CVE data: ${taskRequest?.error} and status: ${taskRequest?.status}`
      );
    }
  }
};
async function main() {
  const org_id = 'ADF'; //testing purposes
  await getVulnData(org_id);

  getVulnData;
}
export const handler = async (CommandOptions) => {
  await main();
};
/**
 * 
class XpanseCveOutput(BaseModel):
    """XpanseCveOutput schema class."""

    cve_id: Optional[str] = None
    cvss_score_v2: Optional[str] = None
    cve_severity_v2: Optional[str] = None
    cvss_score_v3: Optional[str] = None
    cve_severity_v3: Optional[str] = None
    inferred_cve_match_type: Optional[str] = None
    product: Optional[str] = None
    confidence: Optional[str] = None
    vendor: Optional[str] = None
    version_number: Optional[str] = None
    activity_status: Optional[str] = None
    first_observed: Optional[str] = None
    last_observed: Optional[str] = None

class XpanseServiceOutput(BaseModel):
    """XpanseServiceOutput schema class."""

    service_id: Optional[str] = None
    service_name: Optional[str] = None
    service_type: Optional[str] = None
    ip_address: Optional[List[str]] = None
    domain: Optional[List[str]] = None
    externally_detected_providers: Optional[List[str]] = None
    is_active: Optional[str] = None
    first_observed: Optional[str] = None
    last_observed: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    active_classifications: Optional[List[str]] = None
    inactive_classifications: Optional[List[str]] = None
    discovery_type: Optional[str] = None
    externally_inferred_vulnerability_score: Optional[str] = None
    externally_inferred_cves: Optional[List[str]] = None
    service_key: Optional[str] = None
    service_key_type: Optional[str] = None
    cves: Optional[List[XpanseCveOutput]] = None 
class XpanseVulnOutput(BaseModel):
    """XpanseVulnOutput schhema class."""

    alert_name: Optional[str] = None
    description: Optional[str] = None
    last_modified_ts: Optional[datetime] = None
    local_insert_ts: Optional[datetime] = None
    event_timestamp: Optional[List[datetime]] = None
    host_name: Optional[str] = None
    alert_action: Optional[str] = None
    action_country: Optional[List[str]] = None
    action_remote_port: Optional[List[int]] = None
    external_id: Optional[str] = None
    related_external_id: Optional[str] = None
    alert_occurrence: Optional[int] = None
    severity: Optional[str] = None
    matching_status: Optional[str] = None
    alert_type: Optional[str] = None
    resolution_status: Optional[str] = None
    resolution_comment: Optional[str] = None
    last_observed: Optional[str] = None
    country_codes: Optional[List[str]] = None
    cloud_providers: Optional[List[str]] = None
    ipv4_addresses: Optional[List[str]] = None
    domain_names: Optional[List[str]] = None
    port_protocol: Optional[str] = None
    time_pulled_from_xpanse: Optional[str] = None
    action_pretty: Optional[str] = None
    attack_surface_rule_name: Optional[str] = None
    certificate: Optional[Dict] = None
    remediation_guidance: Optional[str] = None
    asset_identifiers: Optional[List[Dict]] = None
    services: Optional[List[XpanseServiceOutput]] = None
    */

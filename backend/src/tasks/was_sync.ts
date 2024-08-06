import { CommandOptions } from './ecs-client';
import {
  connectToDatabase,
  connectToDatalake2,
  Organization,
  DL_Organization,
  WasFinding
} from '../models';
import { plainToClass } from 'class-transformer';
import axios from 'axios';
import saveWasFindingToDb from './helpers/saveWasFindingToDb';

interface WasFindingResult {
  finding_uid: string;
  webapp_id: string;
  was_org_id: string;
  owasp_category: string;
  severity: number;
  times_detected: number;
  base_score: number;
  temporal_score: number;
  fstatus: string;
  last_detected: Date;
  first_detected: Date;
  is_remediated: boolean;
  potential: boolean;
  webapp_url: string;
  webapp_name: string;
  name: string;
  cvss_v3_attack_vector: string;
  cwe_list: number[];
  wasc_list: any[];
  last_tested: Date;
  fixed_date: Date;
  is_ignored: boolean;
  url: string;
  qid: number;
}
interface TaskResponse {
  task_id: string;
  status: 'Processing' | 'Pending' | 'Completed' | 'Failure';
  result?: {
    total_pages: number;
    current_page: number;
    data: WasFindingResult[];
  };
  error?: string;
}

const sleep = (milliseconds) => {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
};

const fetchWasFindingTask = async (org_acronym: string, page: number) => {
  console.log('Creating task to fetch WAS Finding data');
  try {
    console.log(String(process.env.CF_API_KEY));
    const response = await axios({
      url: 'https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/was_findings',
      method: 'POST',
      headers: {
        Authorization: String(process.env.CF_API_KEY),
        access_token: String(process.env.PE_API_KEY),
        'Content-Type': '' // This is needed or else it breaks because axios defaults to application/json
      },
      data: {
        org_acronym: org_acronym,
        page: page,
        per_page: 100 // Tested with 150 and 200 but this results in 502 errors on certain pages with a lot of CPEs
      }
    });
    if (response.status >= 200 && response.status < 300) {
      console.log('Task request was successful');
    } else {
      console.log('Task request failed');
    }
    return response.data as TaskResponse;
  } catch (error) {
    console.log(`Error making POST request: ${error}`);
  }
};

const fetchWasFindingData = async (task_id: string) => {
  console.log('Creating task to fetch was_findings data');
  try {
    const response = await axios({
      url: `https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/was_findings/task/${task_id}`,
      method: 'GET',
      headers: {
        Authorization: String(process.env.CF_API_KEY),
        access_token: String(process.env.PE_API_KEY),
        'Content-Type': '' // This is needed or else it breaks because axios defaults to application/json
      }
    });
    if (response.status >= 200 && response.status < 300) {
      console.log('Request was successful');
    } else {
      console.log('Request failed');
    }
    return response.data as TaskResponse;
  } catch (error) {
    console.log(`Error making GET request: ${error}`);
  }
};

export const handler = async (commandOptions: CommandOptions) => {
  console.log(
    `Scanning PE database for vulnerabilities & services for all orgs`
  );
  try {
    // Get all organizations
    await connectToDatabase();
    const allOrgs: Organization[] = await Organization.find();

    // For each organization, fetch Was finding data
    for (const org of allOrgs) {
      console.log(
        `Scanning PE database for vulnerabilities & services for ${org.acronym}, ${org.name}`
      );
      let datalakeConnnection = await connectToDatalake2();
      let dl_org = datalakeConnnection.getRepository(DL_Organization);
      const organization = await dl_org.findOne({
        where: { acronym: org.acronym }
      });
      console.log(`queried org ${organization}`);

      if (!organization) {
        console.log(
          `No organization found in the datalake with the acronym '${org.acronym}'`
        );
        continue;
      }
      let done = false;
      let page = 1;
      let total_pages = 1;

      while (!done) {
        let finished = false;

        console.log(`Fetching page ${page} of page ${total_pages}`);
        let taskRequest = await fetchWasFindingTask(org.acronym, page);
        console.log(`Fetching `);
        if (taskRequest?.task_id) {
          while (!finished) {
            if (
              taskRequest?.status === 'Processing' ||
              taskRequest?.status === 'Pending'
            ) {
              await new Promise((r) => setTimeout(r, 1000));
              taskRequest = await fetchWasFindingData(taskRequest.task_id);
            } else if (taskRequest?.status === 'Completed') {
              for (const finding of taskRequest?.result?.data ?? []) {
                try {
                  const finding_obj: WasFinding = plainToClass(WasFinding, {
                    id: finding.finding_uid,
                    webappId: finding.webapp_id,
                    wasOrgId: finding.was_org_id,
                    owaspCategory: finding.owasp_category,
                    severity: finding.severity,
                    timesDetected: finding.times_detected,
                    baseScore: finding.base_score,
                    temporalScore: finding.temporal_score,
                    fstatus: finding.fstatus,
                    lastDetected: finding.last_detected,
                    firstDetected: finding.first_detected,
                    isRemediated: finding.is_remediated,
                    potential: finding.potential,
                    webappUrl: finding.webapp_url,
                    webappName: finding.webapp_name,
                    name: finding.name,
                    cvssV3AttackVector: finding.cvss_v3_attack_vector,
                    cweList: finding.cwe_list,
                    wascList: finding.wasc_list,
                    lastTested: finding.last_tested,
                    fixedDate: finding.fixed_date,
                    isIgnored: finding.is_ignored,
                    url: finding.url,
                    qid: finding.qid,
                    organization: { id: organization.id }
                  });

                  await saveWasFindingToDb(finding_obj);
                } catch (e) {
                  console.error('Could not save WAS finding. Continuing.');
                  console.error(e);
                }
              }
              total_pages = taskRequest?.result?.total_pages || 1;
              const current_page = taskRequest?.result?.current_page || 1;
              if (current_page >= total_pages) {
                done = true;
                console.log(`Finished fetching WAS data for ${org.acronym}`);
              }
              finished = true;
              console.log(`Task completed successfully for page: ${page}`);
              page = page + 1;
            } else {
              finished = true;
              console.error(
                `Failed to recieve WAS finding task for org: ${org.acronym} on page ${page}`
              );
              page = page + 1;
            }
          }
        } else {
          done = true;
          console.log(
            `Error fetching WAS data: ${taskRequest?.error} and status: ${taskRequest?.status}`
          );
        }
      }
    }
  } catch (e) {
    console.error('Unknown failure.');
    console.error(e);
  }
  await sleep(1000);
  console.log(`Finished retrieving WAS findings for all orgs`);
};

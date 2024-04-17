import axios from 'axios';
import { Buffer } from 'buffer';
import { plainToClass } from 'class-transformer';
import {
  Assessment,
  connectToDatabase,
  Question,
  Response,
  User
} from '../models';
import { getRepository } from 'typeorm';
import * as console from 'console';

interface AssessmentEntry {
  metadata: Metadata;
  questions: Questions;
}
interface Metadata {
  sys_created_on: Date;
  sys_id: string;
  sys_updated_on: Date;
  u_contact_email: string;
}
interface Questions {
  [key: string]: string | null;
}

// This should be regularly compared with mission instance's API response to ensure it is current
function castApiResponseToAssessmentInterface(data: any[]): AssessmentEntry[] {
  return data.map((el) => ({
    metadata: {
      sys_created_on: new Date(el.sys_created_on),
      sys_id: el.sys_id,
      sys_updated_on: new Date(el.sys_updated_on),
      u_contact_email: el.u_contact_email
    },
    questions: {
      u_3rd_party_cyber_validation: el.u_3rd_party_cyber_validation || null,
      u_annual_cyber_training: el.u_annual_cyber_training || null,
      u_asset_inventory: el.u_asset_inventory || null,
      u_asset_recovery_plan: el.u_asset_recovery_plan || null,
      u_backup_access: el.u_backup_access || null,
      u_backup_auto: el.u_backup_auto || null,
      u_backup_data: el.u_backup_data || null,
      u_backup_method: el.u_backup_method || null,
      u_basline_config_documents: el.u_basline_config_documents || null,
      u_cia_data: el.u_cia_data || null,
      u_change_default_pw: el.u_change_default_pw || null,
      u_connect_deny_default: el.u_connect_deny_default || null,
      u_cyber_incident_plan: el.u_cyber_incident_plan || null,
      u_departing_employee_return: el.u_departing_employee_return || null,
      u_device_config: el.u_device_config || null,
      u_device_type: el.u_device_type || null,
      u_disable_svcs: el.u_disable_svcs || null,
      u_email_tls_dkim: el.u_email_tls_dkim || null,
      u_fw_av: el.u_fw_av || null,
      u_governance_training: el.u_governance_training || null,
      u_hw_software_firmware_approval:
        el.u_hw_software_firmware_approval || null,
      u_iam_security: el.u_iam_security || null,
      u_inc_reporting_policy: el.u_inc_reporting_policy || null,
      u_inc_response_plan: el.u_inc_response_plan || null,
      u_it_org_size: el.u_it_org_size || null,
      u_kev_mitagation: el.u_kev_mitagation || null,
      u_log_storage: el.u_log_storage || null,
      u_log_storage_detect_resp: el.u_log_storage_detect_resp || null,
      u_log_unsuccessful_login: el.u_log_unsuccessful_login || null,
      u_macros_disabled: el.u_macros_disabled || null,
      u_mfa_enabled: el.u_mfa_enabled || null,
      u_named_cyber_role: el.u_named_cyber_role || null,
      u_network_diagrams: el.u_network_diagrams || null,
      u_no_public_devices: el.u_no_public_devices || null,
      u_ot_cyber_training: el.u_ot_cyber_training || null,
      u_prohibit_unauth_devices: el.u_prohibit_unauth_devices || null,
      u_public_services_disabled: el.u_public_services_disabled || null,
      u_pw_different: el.u_pw_different || null,
      u_pw_length: el.u_pw_length || null,
      u_pw_strong: el.u_pw_strong || null,
      u_regular_backups: el.u_regular_backups || null,
      u_reputable_software: el.u_reputable_software || null,
      u_secure_credential_storage: el.u_secure_credential_storage || null,
      u_security_features: el.u_security_features || null,
      u_security_inc_sla: el.u_security_inc_sla || null,
      u_security_research_contact: el.u_security_research_contact || null,
      u_security_vuln_sla: el.u_security_vuln_sla || null,
      u_separate_admin: el.u_separate_admin || null,
      u_software_updates: el.u_software_updates || null,
      u_strong_mfa: el.u_strong_mfa || null,
      u_supply_chain_risk: el.u_supply_chain_risk || null,
      u_tls_enabled: el.u_tls_enabled || null,
      u_ttp_list: el.u_ttp_list || null,
      u_unique_svc_accounts: el.u_unique_svc_accounts || null,
      u_vendor_eval_docs: el.u_vendor_eval_docs || null,
      u_vul_management: el.u_vul_management || null
    }
  }));
}

export const handler = async () => {
  await fetchRecentAssessments();
};

const authorizationHeader = Buffer.from(
  `${process.env.MI_ACCOUNT_NAME}:${process.env.MI_PASSWORD}`,
  'utf8'
).toString('base64');

// Creates a temporary dictionary to reduce calls to the database
const generateQuestionDictionary = async (): Promise<{
  [key: string]: string;
}> => {
  await connectToDatabase();
  const questionRepository = getRepository(Question);
  const questions = await questionRepository.find({ select: ['id', 'name'] });
  return questions.reduce((acc, question) => {
    acc[question.name] = question.id;
    return acc;
  }, {});
};
let questionDictionary: { [key: string]: string } = {};

const fetchRecentAssessments = async () => {
  console.log('Fetching assessments');

  // Create a date object and subtract 48 hours
  const date = new Date();
  date.setHours(date.getHours() - 48);
  const formattedDate = date.toISOString().replace('T', ' ').split('.')[0];

  try {
    const response = await axios({
      url: `https://cisadev.servicenowservices.com/api/now/table/x_g_dhs_rsc_rsc_data?sysparm_query=sys_updated_on>=${formattedDate}`,
      method: 'GET',
      headers: {
        Authorization: `Basic ${authorizationHeader}`
      }
    });
    console.log('response: ', response);
    await saveAssessmentsToDb(response.data.result);
  } catch (error) {
    console.error('Error fetching assessments', error);
  }
};

// TODO: Tie this to RSC user registration
export const fetchAssessmentsByUser = async (email: string) => {
  console.log('Fetching assessments for user');
  try {
    const response = await axios({
      url: `https://cisadev.servicenowservices.com/api/now/table/x_g_dhs_rsc_rsc_data?sysparm_query=u_contact_email=${email}`,
      method: 'GET',
      headers: {
        Authorization: `Basic ${authorizationHeader}`
      }
    });
    await saveAssessmentsToDb(response.data.result);
  } catch (error) {
    console.error('Error fetching assessments for user', error);
  }
};

const getUserIdByEmail = async (email: string): Promise<string | null> => {
  const user = await User.findOne({ where: { email } });
  return user ? user.id : null;
};

const saveAssessmentsToDb = async (assessments: any[]) => {
  console.log('Saving assessments to database');
  await connectToDatabase();
  const assessmentRepository = getRepository(Assessment);
  questionDictionary = await generateQuestionDictionary();

  assessments = castApiResponseToAssessmentInterface(
    assessments
  ) as AssessmentEntry[];

  for (const assessment of assessments) {
    console.log('assessment: ', assessment);

    const user = await getUserIdByEmail(assessment.metadata.u_contact_email);
    if (!user) {
      console.error(
        `Assessment not saved: ${assessment.metadata.u_contact_email} is not registered`
      );
      continue;
    }

    const assessmentToSave = plainToClass(Assessment, {
      createdAt: new Date(assessment.metadata.sys_created_on),
      updatedAt: new Date(assessment.metadata.sys_updated_on),
      rscId: assessment.metadata.sys_id,
      type: assessment.questions.u_it_org_size,
      user: user
    });

    let savedAssessment: Assessment;
    const existingAssessment = await assessmentRepository.findOne({
      where: { rscId: assessmentToSave.rscId }
    });

    if (existingAssessment) {
      if (
        existingAssessment.updatedAt.getTime() !==
        new Date(assessmentToSave.updatedAt).getTime()
      ) {
        savedAssessment = await assessmentRepository.save({
          ...existingAssessment,
          ...assessmentToSave
        });
      } else {
        savedAssessment = existingAssessment;
        // Check if updatedAt dates are the same
        if (
          existingAssessment.updatedAt.getTime() ===
          new Date(assessmentToSave.updatedAt).getTime()
        ) {
          console.log(
            'Existing assessment with same updatedAt date, skipping saveResponsesToDb'
          );
          continue; // Skip saveResponsesToDb if updatedAt dates are the same
        }
      }
    } else {
      savedAssessment = await assessmentRepository.save(assessmentToSave);
    }

    await saveResponsesToDb(assessment, savedAssessment.id);
  }
};

const saveResponsesToDb = async (
  assessment: AssessmentEntry,
  assessmentId: string
) => {
  console.log('assessmentId: ', assessmentId);
  const responseRepository = getRepository(Response);
  await responseRepository
    .createQueryBuilder()
    .delete()
    .from(Response)
    .where('assessmentId = :assessmentId', { assessmentId })
    .execute();
  const responseArray: Response[] = [];
  for (const [question, response] of Object.entries(assessment.questions)) {
    const questionId = questionDictionary[question];
    if (response) {
      responseArray.push(
        plainToClass(Response, {
          selection: response,
          assessment: assessmentId,
          question: questionId
        })
      );
    }
  }
  console.log('responseArray: ', responseArray);
  await Response.save(responseArray);
};

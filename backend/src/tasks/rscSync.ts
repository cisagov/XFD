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
  u_customer_email: string;
}
interface Questions {
  [key: string]: string | null;
}

function castApiResponseToAssessmentInterface(data: any[]): AssessmentEntry[] {
  return data.map((q) => ({
    metadata: {
      sys_created_on: new Date(q.sys_created_on),
      sys_id: q.sys_id,
      u_customer_email: q.u_customer_email
    },
    questions: {
      u_3rd_party_cyber_validation: q.u_3rd_party_cyber_validation || null,
      u_annual_cyber_training: q.u_annual_cyber_training || null,
      u_asset_inventory: q.u_asset_inventory || null,
      u_asset_recovery_plan: q.u_asset_recovery_plan || null,
      u_backup_access: q.u_backup_access || null,
      u_backup_auto: q.u_backup_auto || null,
      u_backup_data: q.u_backup_data || null,
      u_backup_method: q.u_backup_method || null,
      u_basline_config_documents: q.u_basline_config_documents || null,
      u_change_default_pw: q.u_change_default_pw || null,
      u_connect_deny_default: q.u_connect_deny_default || null,
      u_cyber_incident_plan: q.u_cyber_incident_plan || null,
      u_departing_employee_return: q.u_departing_employee_return || null,
      u_device_config: q.u_device_config || null,
      u_device_type: q.u_device_type || null,
      u_disable_svcs: q.u_disable_svcs || null,
      u_email_tls_dkim: q.u_email_tls_dkim || null,
      u_fw_av: q.u_fw_av || null,
      u_governance_training: q.u_governance_training || null,
      u_hw_software_firmware_approval:
        q.u_hw_software_firmware_approval || null,
      u_iam_security: q.u_iam_security || null,
      u_inc_reporting_policy: q.u_inc_reporting_policy || null,
      u_inc_response_plan: q.u_inc_response_plan || null,
      u_it_org_size: q.u_it_org_size || null,
      u_kev_mitagation: q.u_kev_mitagation || null,
      u_log_storage: q.u_log_storage || null,
      u_log_storage_detect_resp: q.u_log_storage_detect_resp || null,
      u_log_unsuccessful_login: q.u_log_unsuccessful_login || null,
      u_macros_disabled: q.u_macros_disabled || null,
      u_mfa_enabled: q.u_mfa_enabled || null,
      u_named_cyber_role: q.u_named_cyber_role || null,
      u_network_diagrams: q.u_network_diagrams || null,
      u_no_public_devices: q.u_no_public_devices || null,
      u_ot_cyber_training: q.u_ot_cyber_training || null,
      u_prohibit_unauth_devices: q.u_prohibit_unauth_devices || null,
      u_public_services_disabled: q.u_public_services_disabled || null,
      u_pw_different: q.u_pw_different || null,
      u_pw_length: q.u_pw_length || null,
      u_pw_strong: q.u_pw_strong || null,
      u_regular_backups: q.u_regular_backups || null,
      u_reputable_software: q.u_reputable_software || null,
      u_secure_credential_storage: q.u_secure_credential_storage || null,
      u_security_features: q.u_security_features || null,
      u_security_inc_sla: q.u_security_inc_sla || null,
      u_security_research_contact: q.u_security_research_contact || null,
      u_security_vuln_sla: q.u_security_vuln_sla || null,
      u_separate_admin: q.u_separate_admin || null,
      u_software_updates: q.u_software_updates || null,
      u_strong_mfa: q.u_strong_mfa || null,
      u_supply_chain_risk: q.u_supply_chain_risk || null,
      u_tls_enabled: q.u_tls_enabled || null,
      u_ttp_list: q.u_ttp_list || null,
      u_unique_svc_accounts: q.u_unique_svc_accounts || null,
      u_vendor_eval_docs: q.u_vendor_eval_docs || null,
      u_vul_management: q.u_vul_management || null
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
      url: `https://cisadev.servicenowservices.com/api/now/table/x_g_dhs_rsc_rsc_data?sysparm_query=sys_created_on>=${formattedDate}`,
      method: 'GET',
      headers: {
        Authorization: `Basic ${authorizationHeader}`
      }
    });
  } catch (error) {
    console.error('Error fetching assessments', error);
  }
};

// TODO: Tie this to RSC user registration
export const fetchAssessmentsByUser = async (email: string) => {
  console.log('Fetching assessments for user');
  try {
    const response = await axios({
      url: `https://cisadev.servicenowservices.com/api/now/table/x_g_dhs_rsc_rsc_data?sysparm_query=u_customer_email=${email}`,
      method: 'GET',
      headers: {
        Authorization: `Basic ${authorizationHeader}`
      }
    });
  } catch (error) {
    console.error('Error fetching assessments for user', error);
  }
};

const getUserIdByEmail = async (email: string): Promise<string | null> => {
  const user = await User.findOne({ where: { email } });
  return user ? user.id : null;
};

export const saveAssessmentsToDb = async (assessments: any[]) => {
  console.log('Saving assessments to database');
  await connectToDatabase();
  questionDictionary = await generateQuestionDictionary();
  assessments = castApiResponseToAssessmentInterface(
    assessments
  ) as AssessmentEntry[];
  try {
    for (const assessment of assessments) {
      const user = await getUserIdByEmail(assessment.metadata.u_customer_email);
      if (!user) {
        console.error(
          'Assessment not saved: the associated user is not registered'
        );
        continue;
      }
      const assessmentToSave = plainToClass(Assessment, {
        createdAt: assessment.metadata.sys_created_on,
        rscId: assessment.metadata.sys_id,
        type: assessment.questions.u_it_org_size,
        user
      });
      const assessmentRepository = getRepository(Assessment);
      const savedAssessment = await assessmentRepository.save(assessmentToSave);
      await saveResponsesToDb(assessment, savedAssessment.id);
    }
  } catch (error) {
    console.error('Error saving assessments to database', error);
  }
};

const saveResponsesToDb = async (
  assessment: AssessmentEntry,
  assessmentId: string
) => {
  const responseArray: Response[] = [];
  console.log('assessmentId: ', assessmentId);
  for (const [question, response] of Object.entries(assessment.questions)) {
    const questionId = questionDictionary[question];
    console.log(`\nquestion: `, question);
    console.log('response: ', response);
    console.log('questionId: ', questionId);
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

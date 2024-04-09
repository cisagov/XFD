import axios from 'axios';
import { Buffer } from 'buffer';
import { plainToClass } from 'class-transformer';
import { Assessment, Question, Response, User } from '../models';
import { getRepository } from 'typeorm';

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
  u_3rd_party_cyber_validation?: string | null;
  u_annual_cyber_training?: string | null;
  u_asset_inventory?: string | null;
  u_asset_recovery_plan?: string | null;
  u_backup_access?: string | null;
  u_backup_auto?: string | null;
  u_backup_data?: string | null;
  u_backup_method?: string | null;
  u_basline_config_documents?: string | null;
  u_change_default_pw?: string | null;
  u_connect_deny_default?: string | null;
  u_cyber_incident_plan?: string | null;
  u_departing_employee_return?: string | null;
  u_device_config?: string | null;
  u_device_type?: string | null;
  u_disable_svcs?: string | null;
  u_email_tls_dkim?: string | null;
  u_first_name?: string | null;
  u_fw_av?: string | null;
  u_governance_training?: string | null;
  u_hw_software_firmware_approval?: string | null;
  u_iam_security?: string | null;
  u_inc_reporting_policy?: string | null;
  u_inc_response_plan?: string | null;
  u_it_org_size?: string | null;
  u_kev_mitagation?: string | null;
  u_last_name?: string | null;
  u_log_storage?: string | null;
  u_log_storage_detect_resp?: string | null;
  u_log_unsuccessful_login?: string | null;
  u_macros_disabled?: string | null;
  u_mfa_enabled?: string | null;
  u_named_cyber_role?: string | null;
  u_network_diagrams?: string | null;
  u_no_public_devices?: string | null;
  u_ot_cyber_training?: string | null;
  u_prohibit_unauth_devices?: string | null;
  u_public_services_disabled?: string | null;
  u_pw_different?: string | null;
  u_pw_length?: string | null;
  u_pw_strong?: string | null;
  u_regular_backups?: string | null;
  u_reputable_software?: string | null;
  u_secure_credential_storage?: string | null;
  u_security_features?: string | null;
  u_security_inc_sla?: string | null;
  u_security_research_contact?: string | null;
  u_security_vuln_sla?: string | null;
  u_separate_admin?: string | null;
  u_software_updates?: string | null;
  u_strong_mfa?: string | null;
  u_supply_chain_risk?: string | null;
  u_tls_enabled?: string | null;
  u_ttp_list?: string | null;
  u_unique_svc_accounts?: string | null;
  u_vendor_eval_docs?: string | null;
  u_vul_management?: string | null;
}

const authorizationHeader = Buffer.from(
  `${process.env.MI_ACCOUNT_NAME}:${process.env.MI_PASSWORD}`,
  'utf8'
).toString('base64');

const questionDictionary = async (): Promise<{
  [key: string]: string;
}> => {
  const questionRepository = getRepository(Question);
  const questions = await questionRepository.find({ select: ['id', 'name'] });
  return questions.reduce((acc, question) => {
    acc[question.name] = question.id;
    return acc;
  }, {});
};

// Intended to run every 6 hours; retrieves assessments created in the last 48 hours
export const fetchRecentAssessments = async () => {
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

// Intended to run on user registration
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

const saveAssessmentsToDb = async (assessments: AssessmentEntry[]) => {
  console.log('Saving assessments to database');
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

export const saveResponsesToDb = async (
  assessment: AssessmentEntry,
  assessmentId: string
) => {
  const responseArray: Response[] = [];
  for (const [question, response] of Object.entries(assessment.questions)) {
    responseArray.push(
      plainToClass(Response, {
        selection: response,
        assessmentId,
        questionId: questionDictionary[question]
      })
    );
  }
  await Response.save(responseArray);
};

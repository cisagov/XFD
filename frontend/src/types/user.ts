import { Role } from './role';
import { ApiKey } from './api-key';

export interface User {
  id: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
  full_name: string;
  invite_pending: boolean;
  first_login: boolean;
  user_type: 'standard' | 'globalView' | 'globalAdmin' | 'regionalAdmin';
  email: string;
  roles: Role[];
  date_accepted_terms: string | null;
  accepted_terms_version: string | null;
  last_logged_in: string | null;
  apiKeys: ApiKey[];
  region_id?: string | null;
  state?: string | null;
  organizations?: Array<string>;
  isRegistered?: boolean | null;
  login_blocked_by_maintenance?: boolean | false;
}

export type UserFormValues = {
  id?: string;
  first_name: string;
  last_name: string;
  email: string;
  user_type: 'standard' | 'globalView' | 'globalAdmin' | 'regionalAdmin';
  state: string;
  region_id: string;
  org_name: string;
  org_id: string;
  originalOrgId: string;
  originalRoleId: string;
  invite_pending: boolean;
};

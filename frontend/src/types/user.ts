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

export const initializeUser: User = {
  id: '',
  created_at: '',
  updated_at: '',
  first_name: '',
  last_name: '',
  full_name: '',
  invite_pending: true,
  user_type: 'standard',
  email: '',
  roles: [],
  date_accepted_terms: null,
  accepted_terms_version: null,
  last_logged_in: null,
  apiKeys: [],
  region_id: null,
  state: null,
  organizations: [],
  isRegistered: null
};

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
};

export const initialUserFormValues: UserFormValues = {
  first_name: '',
  last_name: '',
  email: '',
  user_type: 'standard',
  state: '',
  region_id: '',
  org_name: '',
  org_id: '',
  originalOrgId: '',
  originalRoleId: ''
};

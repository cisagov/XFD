import { AuthUser } from 'context';

export const testUser: AuthUser = {
  id: 'd7d6e913-0370-4f43-aebc-6bd727adc70e',
  created_at: '2020-08-23T03:36:57.231Z',
  updated_at: '2020-08-23T03:36:57.231Z',
  last_logged_in: new Date().toISOString(),
  first_name: 'John',
  last_name: 'Smith',
  full_name: 'John Smith',
  invite_pending: false,
  user_type: 'standard',
  email: 'test@crossfeed.gov',
  roles: [],
  date_accepted_terms: new Date().toISOString(),
  accepted_terms_version: 'v1-user',
  isRegistered: true,
  apiKeys: [],
  region_id: '1234',
  state: 'LA',
  first_login: false
};

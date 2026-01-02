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
  region_id: '3',
  state: 'VA',
  first_login: false
};

export const regionalAdminUser: AuthUser = {
  id: 'c3d4e5f6-7890-abcd-ef12-34567890abcd',
  created_at: '2022-03-22T09:15:45.123Z',
  updated_at: '2022-03-22T09:15:45.123Z',
  last_logged_in: new Date().toISOString(),
  first_name: 'Bob',
  last_name: 'Smith',
  full_name: 'Bob Smith',
  invite_pending: false,
  user_type: 'regionalAdmin',
  email: 'bob.smith@crossfeed.gov',
  roles: [],
  date_accepted_terms: new Date().toISOString(),
  accepted_terms_version: 'v1-user',
  isRegistered: true,
  apiKeys: [],
  region_id: '2',
  state: 'NY',
  first_login: false
};

export const globalViewUser: AuthUser = {
  id: 'b2a1c3d4-e5f6-7890-abcd-ef1234567890',
  created_at: '2021-05-10T14:30:00.000Z',
  updated_at: '2021-05-10T14:30:00.000Z',
  last_logged_in: new Date().toISOString(),
  first_name: 'Jane',
  last_name: 'Doe',
  full_name: 'Jane Doe',
  invite_pending: false,
  user_type: 'globalView',
  email: 'jane.doe@crossfeed.gov',
  roles: [],
  date_accepted_terms: new Date().toISOString(),
  accepted_terms_version: 'v1-user',
  isRegistered: true,
  apiKeys: [],
  region_id: '9',
  state: 'CA',
  first_login: false
};

export const globalAdminUser: AuthUser = {
  id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  created_at: '2021-01-15T10:20:30.400Z',
  updated_at: '2021-01-15T10:20:30.400Z',
  last_logged_in: new Date().toISOString(),
  first_name: 'Alice',
  last_name: 'Johnson',
  full_name: 'Alice Johnson',
  invite_pending: false,
  user_type: 'globalAdmin',
  email: 'alice.johnson@crossfeed.gov',
  roles: [],
  date_accepted_terms: new Date().toISOString(),
  accepted_terms_version: 'v1-user',
  isRegistered: true,
  apiKeys: [],
  region_id: '4',
  state: 'FL',
  first_login: false
};

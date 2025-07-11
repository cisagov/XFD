import { User } from 'types';

export const testUsers: User[] = [
  {
    id: 'abc-123',
    created_at: '2023-10-18T16:51:30.906Z',
    last_logged_in: '2023-11-03T21:17:11.774Z',
    updated_at: '2023-11-03T21:17:11.774Z',
    date_accepted_terms: '2023-11-03T21:17:11.774Z',
    first_login: false,
    full_name: 'Joe Johnson',
    first_name: 'Joe',
    last_name: 'Johnson',
    email: 'joe.johnson@test.gov',
    invite_pending: false,
    user_type: 'globalAdmin',
    roles: [],
    accepted_terms_version: null,
    apiKeys: [],
    state: 'Virginia',
    region_id: '1',
    organizations: [
      'Organization 1',
      'Organization 2',
      'Organization 3',
      'Organization 4',
      'Organization 5'
    ]
  },
  {
    id: 'def-456',
    created_at: '2023-10-18T16:51:30.906Z',
    last_logged_in: '2023-11-03T21:17:11.774Z',
    updated_at: '2023-11-03T21:17:11.774Z',
    date_accepted_terms: '2023-11-03T21:17:11.774Z',
    first_login: false,
    full_name: 'John Smith',
    first_name: 'John',
    last_name: 'Smith',
    email: 'john.smith@test.gov',
    invite_pending: true,
    user_type: 'globalAdmin',
    roles: [],
    accepted_terms_version: null,
    apiKeys: [],
    region_id: '1',
    state: 'New Jersey',
    organizations: []
  },
  {
    id: 'ghi-789',
    created_at: '2023-10-18T16:51:30.906Z',
    last_logged_in: '2023-11-03T21:17:11.774Z',
    updated_at: '2023-11-03T21:17:11.774Z',
    date_accepted_terms: '2023-11-03T21:17:11.774Z',
    first_login: false,
    full_name: 'Jane Doe',
    first_name: 'Jane',
    last_name: 'Doe',
    email: 'jane.doe@test.gov',
    invite_pending: true,
    user_type: 'globalAdmin',
    roles: [],
    accepted_terms_version: null,
    apiKeys: [],
    region_id: '1',
    state: 'Virginia',
    organizations: []
  },
  {
    id: 'jkl-123',
    created_at: '2023-10-18T16:51:30.906Z',
    last_logged_in: '2023-11-03T21:17:11.774Z',
    updated_at: '2023-11-03T21:17:11.774Z',
    date_accepted_terms: '2023-11-03T21:17:11.774Z',
    first_login: false,
    full_name: 'Harry Jones',
    first_name: 'Harry',
    last_name: 'Jones',
    email: 'harry.jones@test.gov',
    invite_pending: false,
    user_type: 'globalAdmin',
    roles: [],
    accepted_terms_version: null,
    apiKeys: [],
    region_id: '1',
    state: 'Virginia',
    organizations: []
  },
  {
    id: 'mno-456',
    created_at: '2023-10-18T16:51:30.906Z',
    last_logged_in: '2023-11-03T21:17:11.774Z',
    updated_at: '2023-11-03T21:17:11.774Z',
    date_accepted_terms: '2023-11-03T21:17:11.774Z',
    first_login: false,
    full_name: 'Ronald Potter',
    first_name: 'Ronald',
    last_name: 'Potter',
    email: 'ronald.potter@test.gov',
    invite_pending: false,
    user_type: 'globalAdmin',
    roles: [],
    accepted_terms_version: null,
    apiKeys: [],
    region_id: '2',
    state: 'California',
    organizations: []
  }
];
type organizations = {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  user_type?: string;
  root_domains: Array<String>;
  ip_blocks: Array<String>;
  is_passive: boolean;
  pending_domains: Array<String>;
  user_roles: Array<String>;
  members?: number;
  tags: Array<Object>;
};
export const testOrganizations: organizations[] = [
  {
    id: 'xyz-123',
    created_at: '2023-11-03T20:19:08.411Z',
    updated_at: '2023-11-03T20:19:08.411Z',
    name: 'Affectionate Agency',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 5,
    tags: [
      {
        id: 'abc-789',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'qrs-123',
    created_at: '2023-11-03T20:19:09.899Z',
    updated_at: '2023-11-03T20:19:09.899Z',
    name: 'Boring City',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 30,
    tags: [
      {
        id: 'lmn-123',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'efg-456',
    created_at: '2023-11-03T20:19:10.872Z',
    updated_at: '2023-11-03T20:19:10.872Z',
    name: 'Brave Agency',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 6,
    tags: [
      {
        id: 'hij-789',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'bcd-234',
    created_at: '2023-11-03T20:19:07.327Z',
    updated_at: '2023-11-03T20:19:07.327Z',
    name: 'Competent County',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 15,
    tags: [
      {
        id: 'nop-567',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'qrs-345',
    created_at: '2023-11-03T20:19:11.724Z',
    updated_at: '2023-11-03T20:19:11.724Z',
    name: 'Condescending City',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 14,
    tags: [
      {
        id: 'tuv-678',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'wxy-789',
    created_at: '2023-11-03T20:19:08.930Z',
    updated_at: '2023-11-03T20:19:08.930Z',
    name: 'Distracted Agency',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    tags: [
      {
        id: 'efg-567',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'hij-123',
    created_at: '2023-11-03T20:19:07.901Z',
    updated_at: '2023-11-03T20:19:07.901Z',
    name: 'Optimistic County',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 12,
    tags: [
      {
        id: 'cde-234',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'rst-123',
    created_at: '2023-11-03T20:19:10.343Z',
    updated_at: '2023-11-03T20:19:10.343Z',
    name: 'Peaceful Department',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 0,
    tags: [
      {
        id: 'efg-567',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'klm-456',
    created_at: '2023-11-03T20:19:11.296Z',
    updated_at: '2023-11-03T20:19:11.296Z',
    name: 'Sharp County',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 30,
    tags: [
      {
        id: 'lmn-567',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'ghi-678',
    created_at: '2023-11-03T20:19:06.677Z',
    updated_at: '2023-11-03T20:19:06.677Z',
    name: 'Tender Department',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 10,
    tags: [
      {
        id: 'ijk-789',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  },
  {
    id: 'mno-345',
    created_at: '2023-11-03T20:19:09.380Z',
    updated_at: '2023-11-03T20:19:09.380Z',
    name: 'Zealous Agency',
    root_domains: ['crossfeed.local'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    user_roles: [],
    members: 3,
    tags: [
      {
        id: 'stu-234',
        created_at: '2023-10-03T20:38:45.889Z',
        updated_at: '2023-10-03T20:38:45.889Z',
        name: 'Sample Data'
      }
    ]
  }
];

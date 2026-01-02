import { testOrganization } from './organization';
import { testUser } from './user';

export const testRole = {
  id: 'role-1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  role: 'user' as 'user' | 'admin',
  user: testUser,
  organization: testOrganization,
  approved: true
};

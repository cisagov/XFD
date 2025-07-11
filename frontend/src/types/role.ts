import { User } from './user';
import { Organization } from './organization';

export interface Role {
  id: string;
  created_at: string;
  updated_at: string;
  role: 'user' | 'admin';
  user: User;
  organization: Organization;
  approved: boolean;
}

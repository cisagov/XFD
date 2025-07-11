import { User } from './user';

export interface ApiKey {
  id: string;
  created_at: string;
  updated_at: string;
  user: User;
  hashed_key: string;
  last_four: string;
  last_used: string;
}

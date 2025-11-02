import { User } from './user';

export interface SavedSearch {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  search_term: string;
  count: number;
  filters: { field: string; values: any[]; type: string }[];
  created_by: User;
  search_path: string;
  sortField: string;
  sortDirection: string;
}

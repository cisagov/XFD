import { SortingRule, Filters } from 'react-table';

export interface OrgQuery<T extends object> {
  sort: SortingRule<T>[];
  page: number;
  filters: Filters<T>;
  pageSize?: number;
}

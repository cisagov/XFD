// import type { SortingRule, Filters } from 'react-table';
import type {
  LegacySortingRule,
  LegacyFilters
} from '../types/reactTableLegacy';

export interface OrgQuery<T extends object> {
  sort: LegacySortingRule<T>[];
  page: number;
  filters: LegacyFilters<T>;
  pageSize?: number;
}

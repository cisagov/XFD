import type {
  LegacySortingRule,
  LegacyFilters
} from '../types/reactTableLegacy';

/**
 * This local type defines the structure of an organization query, including sorting, pagination, and filtering options.
 * It is only used in the legacy ScanTasksView component.
 * It can be removed when the legacy ScanTasksView component is refactored under CRASM-3730 Standardize Frontend Component and Styling Libraries.
 */
export interface OrgQuery<T extends object> {
  sort: LegacySortingRule<T>[];
  page: number;
  filters: LegacyFilters<T>;
  pageSize?: number;
}

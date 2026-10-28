/**
 * This local type defines the structure of legacy sorting and filtering rules for tables.
 * It is used in the legacy ScanTasksView component.
 * It can be removed once the legacy ScanTasksView component is refactored under CRASM-3730 Standardize Frontend Component and Styling Libraries.
 */

export type LegacySortingRule<T extends object = Record<string, unknown>> = {
  id: keyof T | string;
  desc?: boolean;
};

export type LegacyFilter<T extends object = Record<string, unknown>> = {
  id: keyof T | string;
  value: string | boolean | undefined;
};

export type LegacyFilters<T extends object = Record<string, unknown>> =
  LegacyFilter<T>[];

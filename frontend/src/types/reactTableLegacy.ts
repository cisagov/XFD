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

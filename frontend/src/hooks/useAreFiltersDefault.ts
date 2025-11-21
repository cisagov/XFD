import { ContextType } from 'context';
import { useMemo } from 'react';

type UseAreFiltersDefault = (
  filters: ContextType['filters'],
  initialFilters: ContextType['filters']
) => boolean;

export const useAreFiltersDefault: UseAreFiltersDefault = (
  filters: ContextType['filters'],
  initialFilters: ContextType['filters']
): boolean => {
  return useMemo(() => {
    return filters.every((filter) => {
      const initialFilter = initialFilters.find(
        (initFilter) => initFilter.field === filter.field
      );
      if (!initialFilter) return false;

      const current = filter.values || [];
      const initial = initialFilter.values || [];

      if (current.length !== initial.length) return false;

      const currentIds = current.map((val: any) =>
        typeof val === 'object' && val !== null ? (val.id ?? val.name) : val
      );
      const initialIds = initial.map((val: any) =>
        typeof val === 'object' && val !== null ? (val.id ?? val.name) : val
      );

      return (
        JSON.stringify(currentIds.sort()) === JSON.stringify(initialIds.sort())
      );
    });
  }, [filters, initialFilters]);
};

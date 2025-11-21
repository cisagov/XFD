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
        (f) => f.field === filter.field
      );
      // console.log(
      //   'Comparing filter:',
      //   filter,
      //   'with initialFilter:',
      //   initialFilter
      // );
      // if (!initialFilter || !initialFilter.values) return false;

      const initialValuesSet = new Set(initialFilter.values);
      const currentValuesSet = new Set(filter.values);

      // console.log(
      //   `Filter Field: ${filter.field}, Initial Values: ${Array.from(
      //     initialValuesSet
      //   )}, Current Values: ${Array.from(currentValuesSet)}`
      // );
      // console.log(
      //   `Initial Values Set Size: ${initialValuesSet.size}, Current Values Set Size: ${currentValuesSet.size}`
      // );

      // if (initialValuesSet.size !== currentValuesSet.size) return false;

      for (const value of initialValuesSet) {
        if (!currentValuesSet.has(value)) return false;
      }
      return true;
    });
  }, [filters, initialFilters]);
};

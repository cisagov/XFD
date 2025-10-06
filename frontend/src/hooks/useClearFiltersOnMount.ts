import { useEffect } from 'react';

export function useClearFiltersOnMount(filters: any[], removeFilter: Function) {
  useEffect(() => {
    filters.forEach((filter) => {
      removeFilter(filter.field, filter.values[0], filter.type);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

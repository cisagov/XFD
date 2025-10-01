import { useEffect } from 'react';
import { ORGANIZATION_FILTER_KEY } from 'components/FilterDrawer/VSDashRegionAndOrgFilters';

export function useClearFiltersOnMount(filters: any[], removeFilter: Function) {
  useEffect(() => {
    // Only clear non-organization filters when mounting VulnerabilityScan
    filters.forEach((filter) => {
      if (filter.field !== ORGANIZATION_FILTER_KEY && filter.field !== 'organization.region_id') {
        removeFilter(filter.field, filter.values[0], filter.type);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

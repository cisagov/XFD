import { useEffect } from 'react';
import { ORGANIZATION_FILTER_KEY } from 'components/FilterDrawer/VSDashRegionAndOrgFilters';
import { useNavigationContext } from 'context/NavigationContext';

export function useClearFiltersOnMount(filters: any[], removeFilter: Function) {
  const { isDrillDown, clearDrillDown } = useNavigationContext();
  
  useEffect(() => {
    // NEW LOGIC: Only clear filters if we're NOT in a drill-down scenario
    // - If user is returning from drill-down, preserve filters
    // - If user is doing general navigation, clear non-essential filters
    
    if (isDrillDown) {
      console.log('[useClearFiltersOnMount] Drill-down context detected, preserving filters');
      // Don't clear filters when returning from drill-down
      // Clear the drill-down state since we've handled the return
      clearDrillDown();
      return;
    }
    
    console.log('[useClearFiltersOnMount] General navigation, clearing non-essential filters');
    
    // Only clear non-organization filters when mounting VulnerabilityScan during general navigation
    filters.forEach((filter) => {
      if (filter.field !== ORGANIZATION_FILTER_KEY && filter.field !== 'organization.region_id') {
        removeFilter(filter.field, filter.values[0], filter.type);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

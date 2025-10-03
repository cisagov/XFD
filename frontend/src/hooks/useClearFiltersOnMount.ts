import { useEffect } from 'react';
import { useNavigationContext } from 'context/NavigationContext';

export function useClearFiltersOnMount(filters: any[], removeFilter: Function) {
  const { isDrillDown, clearDrillDown } = useNavigationContext();
  
  useEffect(() => {
    console.log('CLEAR FILTERS ON MOUNT TRIGGERED');
    
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
        removeFilter(filter.field, filter.values[0], filter.type);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

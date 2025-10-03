import { useEffect } from 'react';
import { useNavigationContext } from 'context/NavigationContext';

export function useClearFiltersOnMount(filters: any[], removeFilter: Function) {
  const { isDrillDown, clearDrillDown } = useNavigationContext();

  useEffect(() => {
    if (isDrillDown) {
      // Don't clear filters when returning from drill-down
      // Clear the drill-down state since we've handled the return
      clearDrillDown();
      return;
    }

    filters.forEach((filter) => {
      removeFilter(filter.field, filter.values[0], filter.type);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

/*
    Author: Jesse Salinas
    Date: 2025-09-24
    Description: Custom hook to restore filters from localStorage
    Updated for CRASM-3004: Use NavigationContext for drill-down aware filter persistence
*/
import { useEffect } from 'react';
import { ContextType } from 'context';
import { FILTER_ENABLED_PATHS } from 'constants/filterPaths';
import { useNavigationContext, isVSDashboard } from 'context/NavigationContext';

export const useFilterRestore = (
  filters: ContextType['filters'],
  addFilter: ContextType['addFilter'],
  pathname: string
) => {
  const { isDrillDown } = useNavigationContext();
  
  useEffect(() => {
    // Only restore filters on specific paths where filter persistence is needed
    const shouldRestoreFilters = FILTER_ENABLED_PATHS.some(path => 
      pathname === path || pathname.startsWith(path)
    );

    // NEW LOGIC: Only restore filters if we're in a drill-down scenario or NOT on VS Dashboard
    // - If we're returning from a drill-down, always restore filters
    // - If we're navigating normally to VS Dashboard, skip restoration (use user defaults)
    // - If we're navigating normally to other pages, restore as usual
    
    const isVSDashboardPath = isVSDashboard(pathname);
    
    if (!shouldRestoreFilters) {
      console.log('[useFilterRestore] Path not filter-enabled, skipping restoration');
      return;
    }
    
    if (isVSDashboardPath && !isDrillDown) {
      console.log('[useFilterRestore] VS Dashboard without drill-down context, using user defaults');
      return;
    }

    // If we already have filters in state, don't restore (avoid duplicate restoration)
    if (filters && filters.length > 0) {
      console.log('[useFilterRestore] Filters already in state, skipping restoration');
      return;
    }

    console.log(`[useFilterRestore] Restoring filters for ${pathname}, isDrillDown: ${isDrillDown}`);

    try {
      const storedFilters = localStorage.getItem('es-search-filters');
      if (storedFilters) {
        const parsedFilters = JSON.parse(storedFilters);
        
        // Use setTimeout to ensure components are mounted before restoring filters
        setTimeout(() => {
          // Restore each filter
          parsedFilters.forEach((filter: any) => {
            if (filter.field && filter.values && filter.type) {
              filter.values.forEach((value: any) => {
                addFilter(filter.field, value, filter.type);
              });
            }
          });
          console.log(`[useFilterRestore] Successfully restored ${parsedFilters.length} filters`);
        }, 100); // Small delay to ensure components are ready
      }
    } catch (error) {
      console.warn('Failed to restore filters from localStorage:', error);
    }
  }, [pathname, filters, addFilter, isDrillDown]);
};

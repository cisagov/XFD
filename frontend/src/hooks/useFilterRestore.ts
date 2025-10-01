/*
    Author: Jesse Salinas
    Date: 2025-09-24
    Description: Custom hook to restore filters from localStorage
*/
import { useEffect } from 'react';
import { ContextType } from 'context';
import { FILTER_ENABLED_PATHS } from 'constants/filterPaths';

export const useFilterRestore = (
  filters: ContextType['filters'],
  addFilter: ContextType['addFilter'],
  pathname: string
) => {
  useEffect(() => {
    // Only restore filters on specific paths where filter persistence is needed
    const shouldRestoreFilters = FILTER_ENABLED_PATHS.some(path => 
      pathname === path || pathname.startsWith(path)
    );

    // Skip filter restoration on VS Dashboard - it should always start fresh with user defaults
    const isVSDashboard = pathname === '/VSDashboard' || pathname.startsWith('/VSDashboard');
    
    if (!shouldRestoreFilters || isVSDashboard) {
      return;
    }

    // If we already have filters in state, don't restore (avoid duplicate restoration)
    if (filters && filters.length > 0) {
      return;
    }

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
        }, 100); // Small delay to ensure components are ready
      }
    } catch (error) {
      console.warn('Failed to restore filters from localStorage:', error);
    }
  }, [pathname, filters, addFilter]);
};

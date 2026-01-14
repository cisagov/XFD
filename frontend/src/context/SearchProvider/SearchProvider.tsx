import React from 'react';
import { logger } from '@/utils/logger';
import applyDisjunctiveFaceting from './applyDisjunctiveFaceting';
import buildState from './buildState';
import { useAuthContext } from 'context';
import { SearchProvider as ESProvider } from '@elastic/react-search-ui';
import { ENDPOINTS } from '@/constants/endpoints';

interface ApiResponse {
  suggest: any;
}
interface SearchProviderProps {
  children: React.ReactNode;
}
export const SearchProvider: React.FC<SearchProviderProps> = ({ children }) => {
  const { apiPost } = useAuthContext();

  const config = {
    debug: false,
    alwaysSearchOnInitialLoad: false,
    trackUrlState: false,
    initialState: {
      resultsPerPage: 15,
      sortField: 'name',
      sortDirection: 'asc'
    },

    onResultClick: () => {
      /* Not implemented */
    },
    onAutocompleteResultClick: (e: any, f: any) => {
      logger.error(
        'SearchProvider.onAutocompleteResultClick: Not implemented',
        { e, f }
      );
    },
    onAutocomplete: async () => {
      // Not implemented - using custom organization search in FilterDrawer components
    },
    onSearch: async (state: any) => {
      const {
        current,
        filters,
        resultsPerPage,
        searchTerm,
        sortDirection,
        sortField
      } = state;
      const body: any = {
        current,
        filters,
        resultsPerPage,
        searchTerm,
        sortDirection,
        sortField
      };

      const responseJson = await apiPost<ApiResponse>(ENDPOINTS.SEARCH_ES, {
        body
      });
      const responseJsonWithDisjunctiveFacetCounts =
        await applyDisjunctiveFaceting(responseJson, state, [
          'from_root_domain'
        ]);
      return buildState(responseJsonWithDisjunctiveFacetCounts, resultsPerPage);
    }
  };

  // Use an organization-specific key so that the search results
  // page properly resets when the current organization is changed.
  return (
    <ESProvider
      config={config}
      // key={`es-provider-${currentOrganization?.name}-${showAllOrganizations}`}
    >
      {children}
    </ESProvider>
  );
};

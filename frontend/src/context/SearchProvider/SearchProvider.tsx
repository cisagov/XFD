import React from 'react';
import applyDisjunctiveFaceting from './applyDisjunctiveFaceting';
import buildState from './buildState';
import { useAuthContext } from 'context';
import { SearchProvider as ESProvider } from '@elastic/react-search-ui';

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
      sort_field: 'name',
      sort_direction: 'asc'
    },
    // debug: false,
    // alwaysSearchOnInitialLoad: false,
    // trackUrlState: false,
    // initialState: {
    //   resultsPerPage: 15,
    //   sort_field: 'name',
    //   sort_direction: 'asc'
    // },
    // searchQuery: {
    //   search_fields: {
    //     name: {}
    //   },
    //   result_fields: {
    //     name: {
    //       raw: {}
    //     }
    //   }
    // },
    // autocompleteQuery: {
    //   suggestions: {
    //     types: {
    //       documents: {
    //         fields: ['name']
    //       }
    //     }
    //   }
    // },

    onResultClick: () => {
      /* Not implemented */
    },
    onAutocompleteResultClick: (e: any, f: any) => {
      console.error(e, f);
    },
    onAutocomplete: async ({ search_term }: { search_term: string }) => {
      // const requestBody = buildAutocompleteRequest({ search_term });
      // const json = await apiPost<ApiResponse>('/search', {
      //   body: {
      //     ...requestBody
      //   },
      //   showLoading: false
      // });
      // // const state = buildState(json);
      // const state = {
      //   results: json.suggest['main-suggest'][0].options.map((e: any) => ({
      //     text: { raw: e.text },
      //     id: { raw: e._source.id }
      //   }))
      // };
      // // console.error(state.results);
      // return {
      //   autocompletedResults: state.results
      // };
    },
    onSearch: async (state: any) => {
      const {
        current,
        filters,
        resultsPerPage,
        searchTerm,
        sort_direction,
        sort_field
      } = state;
      const body: any = {
        current,
        filters,
        resultsPerPage,
        searchTerm,
        sort_direction,
        sort_field
      };

      const responseJson = await apiPost<ApiResponse>('/search', {
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

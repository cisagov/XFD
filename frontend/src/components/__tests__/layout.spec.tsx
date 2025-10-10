import React from 'react';
import { render } from 'test-utils/test-utils';
import { afterAll, describe, expect, it, vi } from 'vitest';
import { Layout } from '../Layout';
import { StaticsContext, StaticsContextType } from 'context/StaticsContext';
import {
  ContextType,
  FilterDrawerContextProvider,
  SearchProvider
} from 'context';
import { NavigationProvider } from 'context/NavigationContextProvider';

const testContext: ContextType = {
  addFilter: (field: string, value: any, type: 'any' | 'all' | 'none') => {},
  removeFilter: (field: string, value: any, type: 'any' | 'all' | 'none') => {},
  filters: [],
  clearFilters: () => {},
  saveSearch: '',
  setSearchTerm: (s: string, opts?: any) => {},
  autocompletedResults: [],
  autocompletedResultsRequestId: 'string',
  autocompletedSuggestions: '',
  current: 1,
  error: 'string',
  facets: '',
  isLoading: false,
  pagingEnd: 1,
  pagingStart: 1,
  requestId: 'string',
  reset: () => {},
  resultSearchTerm: 'string',
  results: [],
  resultsPerPage: 1,
  searchTerm: 'string',
  setCurrent: (current: number) => {},
  setFilter: () => {},
  setResultsPerPage: () => {},
  setSort: (field: 'string', direction: 'asc' | 'desc') => {},
  sortDirection: '',
  sortField: 'string',
  totalPages: 1,
  totalResults: 1,
  wasSearched: false,
  noResults: false
};

const value: StaticsContextType = {
  regions: [],
  setRegions: (regions: string[]) => {}
};

vi.mock('components/Header/Header', () => ({
  Header: () => <div>HEADER</div>
}));
vi.mock('components/GovBanner', () => ({
  GovBanner: () => <div>GOV_BANNER</div>
}));
vi.mock('@mui/x-data-grid', () => ({
  DataGrid: () => <div>DATA_GRID</div>
}));

afterAll(() => {
  vi.restoreAllMocks();
});

describe('Layout component', () => {
  it('matches snapshot', () => {
    const { asFragment } = render(
      <SearchProvider>
        <StaticsContext.Provider value={value}>
          <FilterDrawerContextProvider>
            <NavigationProvider>
              <Layout {...testContext} />
            </NavigationProvider>
          </FilterDrawerContextProvider>
        </StaticsContext.Provider>
      </SearchProvider>
    );
    expect(asFragment()).toMatchSnapshot();
  });

  it('renders children', () => {
    const { getByText } = render(
      <SearchProvider>
        <StaticsContext.Provider value={value}>
          <FilterDrawerContextProvider>
            <NavigationProvider>
              <Layout {...testContext}>some children</Layout>
            </NavigationProvider>
          </FilterDrawerContextProvider>
        </StaticsContext.Provider>
      </SearchProvider>
    );
    expect(getByText('some children')).toBeInTheDocument();
  });
});

import React from 'react';
import { render } from 'test-utils/test-utils';
import { Layout } from '../Layout';
import { StaticsContext, StaticsContextType } from 'context/StaticsContext';
import { ContextType, SearchProvider } from 'context';

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

jest.mock('components/Header', () => ({
  Header: () => <div>HEADER</div>
}));
jest.mock('components/GovBanner', () => ({
  GovBanner: () => <div>GOV_BANNER</div>
}));

afterAll(() => {
  jest.restoreAllMocks();
});

describe('Layout component', () => {
  it('matches snapshot', () => {
    const { asFragment } = render(
      <SearchProvider>
        <StaticsContext.Provider value={value}>
          <Layout {...testContext} />
        </StaticsContext.Provider>
      </SearchProvider>
    );
    expect(asFragment()).toMatchSnapshot();
  });

  it('renders children', () => {
    const { getByText } = render(
      <SearchProvider>
        <StaticsContext.Provider value={value}>
          <Layout {...testContext}>some children</Layout>
        </StaticsContext.Provider>
      </SearchProvider>
    );
    expect(getByText('some children')).toBeInTheDocument();
  });
});

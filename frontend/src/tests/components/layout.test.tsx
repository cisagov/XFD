import React from 'react';
import { render } from 'test-utils/test-utils';
import { afterAll, describe, expect, it, vi } from 'vitest';
import { act } from '@testing-library/react';
import { Layout } from '../../components/Layout';
import { StaticsContext, StaticsContextType } from 'context/StaticsContext';
import {
  ContextType,
  FilterDrawerContextProvider,
  SearchProvider
} from 'context';
import { NavigationProvider } from 'context/NavigationContextProvider';

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}));

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
vi.mock('components/FilterDrawer/FilterDrawerV2', () => ({
  FilterDrawerV2: () => <div>FILTER_DRAWER</div>
}));
afterAll(() => {
  vi.restoreAllMocks();
});
describe('Layout component', () => {
  const renderWithProviders = (ui: React.ReactElement) => {
    return render(
      <SearchProvider>
        <StaticsContext.Provider value={value}>
          <FilterDrawerContextProvider>
            <NavigationProvider>{ui}</NavigationProvider>
          </FilterDrawerContextProvider>
        </StaticsContext.Provider>
      </SearchProvider>
    );
  };

  it('matches snapshot', () => {
    const { asFragment } = renderWithProviders(<Layout {...testContext} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('renders children', () => {
    const { getByText } = renderWithProviders(
      <Layout {...testContext}>some children</Layout>
    );
    expect(getByText('some children')).toBeInTheDocument();
  });

  it('saves alert preference to localStorage when closed', async () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
    const { getByLabelText } = renderWithProviders(<Layout {...testContext} />);
    const closeButton = getByLabelText(/close/i);
    await act(async () => {
      closeButton.click();
    });
    expect(setItemSpy).toHaveBeenCalledWith('siteWideAlertOff', 'true');
  });

  it('ensures the outer wrapper prevents body scrolling', () => {
    const { container } = renderWithProviders(<Layout {...testContext} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveStyle({
      height: '100vh',
      overflow: 'hidden'
    });
  });
});

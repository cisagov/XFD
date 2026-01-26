import { ContextType } from 'context/SearchProvider/types';
import { vi } from 'vitest';

export const searchCtx: ContextType = {
  addFilter: vi.fn(),
  removeFilter: vi.fn(),
  filters: [],
  clearFilters: vi.fn(),
  saveSearch: '',
  setSearchTerm: vi.fn(),
  current: 1,
  error: 'string',
  facets: '',
  isLoading: false,
  pagingEnd: 1,
  pagingStart: 1,
  requestId: 'string',
  reset: vi.fn(),
  resultSearchTerm: 'string',
  results: [],
  resultsPerPage: 1,
  searchTerm: 'string',
  setCurrent: vi.fn(),
  setFilter: vi.fn(),
  setResultsPerPage: vi.fn(),
  setSort: vi.fn(),
  sortDirection: '',
  sortField: 'string',
  totalPages: 1,
  totalResults: 1,
  wasSearched: false,
  noResults: false
};

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { SearchProvider } from '../../context/SearchProvider/SearchProvider';
import { AuthContext } from '../../context/AuthContext';
import { authCtx } from '../../test-utils/authCtx';
import { ENDPOINTS } from '@/constants/endpoints';

// Mock the external dependencies
vi.mock('../../utils/logger', () => ({
  logger: {
    error: vi.fn()
  }
}));

vi.mock('../../context/SearchProvider/applyDisjunctiveFaceting', () => ({
  default: vi.fn((responseJson, state, fields) => ({
    ...responseJson,
    facetsWithDisjunctive: true
  }))
}));

vi.mock('../../context/SearchProvider/buildState', () => ({
  default: vi.fn((responseJson, resultsPerPage) => ({
    results: [
      { id: { raw: '1' }, name: { raw: 'Test Domain 1' } },
      { id: { raw: '2' }, name: { raw: 'Test Domain 2' } }
    ],
    totalResults: 2,
    current: 1,
    totalPages: 1
  }))
}));

// Mock the Elastic Search UI Provider
vi.mock('@elastic/react-search-ui', () => ({
  SearchProvider: ({ children, config }: any) => {
    // Store the config for testing
    (global as any).lastSearchConfig = config;
    return <div data-testid="elastic-search-provider">{children}</div>;
  }
}));

describe('SearchProvider', () => {
  const mockApiPost = vi.fn();
  const mockAuthContext = {
    ...authCtx,
    apiPost: mockApiPost
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPost.mockResolvedValue({
      body: { hits: { hits: [] } },
      suggest: {}
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const renderWithProvider = (children: React.ReactNode) => {
    return render(
      <AuthContext.Provider value={mockAuthContext}>
        <SearchProvider>{children}</SearchProvider>
      </AuthContext.Provider>
    );
  };

  describe('Provider Integration', () => {
    it('renders children within Elastic SearchProvider', () => {
      renderWithProvider(<div data-testid="test-child">Test Child</div>);

      expect(screen.getByTestId('elastic-search-provider')).toBeInTheDocument();
      expect(screen.getByTestId('test-child')).toBeInTheDocument();
    });

    it('passes correct config to Elastic SearchProvider', () => {
      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      expect(config).toEqual({
        debug: false,
        alwaysSearchOnInitialLoad: false,
        trackUrlState: false,
        initialState: {
          resultsPerPage: 15,
          sortField: 'name',
          sortDirection: 'asc'
        },
        onResultClick: expect.any(Function),
        onAutocompleteResultClick: expect.any(Function),
        onAutocomplete: expect.any(Function),
        onSearch: expect.any(Function)
      });
    });
  });

  describe('Configuration Properties', () => {
    it('has correct initial state configuration', () => {
      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      expect(config.initialState).toEqual({
        resultsPerPage: 15,
        sortField: 'name',
        sortDirection: 'asc'
      });
    });

    it('has debug disabled', () => {
      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      expect(config.debug).toBe(false);
    });

    it('has trackUrlState disabled', () => {
      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      expect(config.trackUrlState).toBe(false);
    });

    it('has alwaysSearchOnInitialLoad disabled', () => {
      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      expect(config.alwaysSearchOnInitialLoad).toBe(false);
    });
  });

  describe('Event Handlers', () => {
    describe('onResultClick', () => {
      it('is defined but not implemented', () => {
        renderWithProvider(<div>Test</div>);

        const config = (global as any).lastSearchConfig;
        expect(config.onResultClick).toBeDefined();
        expect(typeof config.onResultClick).toBe('function');

        // Should not throw when called
        expect(() => config.onResultClick()).not.toThrow();
      });
    });

    describe('onAutocompleteResultClick', () => {
      it('logs error when called', async () => {
        const { logger } = await import('../../utils/logger');
        renderWithProvider(<div>Test</div>);

        const config = (global as any).lastSearchConfig;
        const mockEvent = { preventDefault: vi.fn() };
        const mockResult = { id: 'test' };

        config.onAutocompleteResultClick(mockEvent, mockResult);

        expect(logger.error).toHaveBeenCalledWith(
          'SearchProvider.onAutocompleteResultClick: Not implemented',
          { e: mockEvent, f: mockResult }
        );
      });
    });

    describe('onAutocomplete', () => {
      it('returns undefined (not implemented)', async () => {
        renderWithProvider(<div>Test</div>);

        const config = (global as any).lastSearchConfig;
        const result = await config.onAutocomplete('test search');

        expect(result).toBeUndefined();
      });
    });
  });

  describe('onSearch functionality', () => {
    const mockSearchState = {
      current: 1,
      filters: [{ field: 'organization', values: ['test-org'] }],
      resultsPerPage: 20,
      searchTerm: 'test search',
      sortDirection: 'desc',
      sortField: 'updated_at'
    };

    it('calls apiPost with correct endpoint and body', async () => {
      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      await config.onSearch(mockSearchState);

      expect(mockApiPost).toHaveBeenCalledWith(ENDPOINTS.SEARCH_ES, {
        body: mockSearchState
      });
    });

    it('applies disjunctive faceting to search results', async () => {
      const applyDisjunctiveFaceting = (
        await import('../../context/SearchProvider/applyDisjunctiveFaceting')
      ).default;

      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      await config.onSearch(mockSearchState);

      expect(applyDisjunctiveFaceting).toHaveBeenCalledWith(
        expect.any(Object), // responseJson
        mockSearchState,
        ['from_root_domain']
      );
    });

    it('builds and returns search state', async () => {
      const buildState = (
        await import('../../context/SearchProvider/buildState')
      ).default;

      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      const result = await config.onSearch(mockSearchState);

      expect(buildState).toHaveBeenCalledWith(
        expect.objectContaining({ facetsWithDisjunctive: true }),
        mockSearchState.resultsPerPage
      );

      expect(result).toEqual({
        results: [
          { id: { raw: '1' }, name: { raw: 'Test Domain 1' } },
          { id: { raw: '2' }, name: { raw: 'Test Domain 2' } }
        ],
        totalResults: 2,
        current: 1,
        totalPages: 1
      });
    });

    it('handles search with empty filters', async () => {
      const stateWithoutFilters = {
        ...mockSearchState,
        filters: []
      };

      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      await config.onSearch(stateWithoutFilters);

      expect(mockApiPost).toHaveBeenCalledWith(ENDPOINTS.SEARCH_ES, {
        body: stateWithoutFilters
      });
    });

    it('handles search with empty search term', async () => {
      const stateWithoutSearchTerm = {
        ...mockSearchState,
        searchTerm: ''
      };

      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      await config.onSearch(stateWithoutSearchTerm);

      expect(mockApiPost).toHaveBeenCalledWith(ENDPOINTS.SEARCH_ES, {
        body: stateWithoutSearchTerm
      });
    });

    it('handles API errors gracefully', async () => {
      const apiError = new Error('API Error');
      mockApiPost.mockRejectedValueOnce(apiError);

      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;

      await expect(config.onSearch(mockSearchState)).rejects.toThrow(
        'API Error'
      );
    });
  });

  describe('State Management Integration', () => {
    it('preserves search state parameters correctly', async () => {
      const complexSearchState = {
        current: 3,
        filters: [
          { field: 'organization_id', values: ['org1', 'org2'] },
          { field: 'severity', values: ['high', 'critical'] }
        ],
        resultsPerPage: 50,
        searchTerm: 'vulnerability',
        sortDirection: 'asc',
        sortField: 'severity'
      };

      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      await config.onSearch(complexSearchState);

      expect(mockApiPost).toHaveBeenCalledWith(ENDPOINTS.SEARCH_ES, {
        body: complexSearchState
      });
    });
  });

  describe('Error Handling', () => {
    it('handles undefined search state gracefully', async () => {
      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;

      await expect(config.onSearch(undefined)).rejects.toThrow();
    });

    it('handles malformed search state', async () => {
      renderWithProvider(<div>Test</div>);

      const config = (global as any).lastSearchConfig;
      const malformedState = { invalidField: 'invalid' };

      await config.onSearch(malformedState);

      expect(mockApiPost).toHaveBeenCalledWith(ENDPOINTS.SEARCH_ES, {
        body: {
          current: undefined,
          filters: undefined,
          resultsPerPage: undefined,
          searchTerm: undefined,
          sortDirection: undefined,
          sortField: undefined
        }
      });
    });
  });
});

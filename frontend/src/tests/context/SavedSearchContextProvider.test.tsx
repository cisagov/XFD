import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import { SavedSearchContextProvider } from '@context/SavedSearchContextProvider';
import { SavedSearchContext } from '@context/SavedSearchContext';
import { ENDPOINTS } from '@/constants/endpoints';

import type { SavedSearch } from '@/types/saved-search';

// ----------------------
// Mocks
// ----------------------
const mockLoggerError = vi.fn();
vi.mock('@/utils/logger', () => ({
  logger: {
    error: (...loggerArgs: unknown[]) => mockLoggerError(...loggerArgs)
  }
}));

const mockApiGet = vi.fn();
vi.mock('@context/AuthContext', () => ({
  useAuthContext: () => ({
    apiGet: mockApiGet,
    user: { id: 'user-123' }
  })
}));

function createSavedSearch(overrides: Partial<SavedSearch> = {}): SavedSearch {
  const nowIsoString = new Date().toISOString();

  return {
    id: 'search-001',
    created_at: nowIsoString,
    updated_at: nowIsoString,
    name: 'Saved Search',
    search_term: '',
    count: 0,
    filters: [],
    created_by: { id: 'user-1' } as any,
    search_path: '/inventory',
    sortField: 'name',
    sortDirection: 'asc',
    ...overrides
  };
}

const Consumer: React.FC = () => {
  const savedSearchContext = React.useContext(SavedSearchContext);

  return (
    <div>
      <div data-testid="searches-length">
        {savedSearchContext.savedSearches.length}
      </div>

      <div data-testid="count">
        {String(savedSearchContext.savedSearchCount)}
      </div>
      <div data-testid="active-id">{savedSearchContext.activeSearchId}</div>
      <div data-testid="active-search">
        {savedSearchContext.activeSearch
          ? savedSearchContext.activeSearch.id
          : ''}
      </div>

      <button
        type="button"
        onClick={() =>
          savedSearchContext.setSavedSearches([
            createSavedSearch({ id: 'search-002', name: 'Second Search' })
          ])
        }
      >
        Set Searches
      </button>

      <button
        type="button"
        onClick={() => savedSearchContext.setSavedSearchCount(1)}
      >
        Set Count
      </button>

      <button
        type="button"
        onClick={() => savedSearchContext.setActiveSearchId('search-002')}
      >
        Set Active
      </button>

      <button
        type="button"
        onClick={() => savedSearchContext.setActiveSearchId('')}
      >
        Clear Active
      </button>
    </div>
  );
};

// ----------------------
// Tests
// ----------------------

describe('SavedSearchContextProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  /** Loads saved searches on mount and sets count to the API result length. */
  it('initializes savedSearches from API on mount and sets savedSearchCount to response length', async () => {
    mockApiGet.mockResolvedValueOnce({
      result: [
        createSavedSearch({ id: 'search-001', name: 'First Search' }),
        createSavedSearch({ id: 'search-002', name: 'Second Search' })
      ]
    });

    render(
      <SavedSearchContextProvider>
        <Consumer />
      </SavedSearchContextProvider>
    );

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(ENDPOINTS.SAVED_SEARCHES);
    });

    expect(screen.getByTestId('searches-length')).toHaveTextContent('2');
    expect(screen.getByTestId('count')).toHaveTextContent('2');
    expect(screen.getByTestId('active-id')).toHaveTextContent('');
    expect(screen.getByTestId('active-search')).toHaveTextContent('');
  });

  /** Updates savedSearches state and re-renders children with new values. */
  it('setSavedSearches updates state and children receive new value', async () => {
    mockApiGet.mockResolvedValueOnce({ result: [] });

    const user = userEvent.setup();

    render(
      <SavedSearchContextProvider>
        <Consumer />
      </SavedSearchContextProvider>
    );

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(ENDPOINTS.SAVED_SEARCHES);
    });

    expect(screen.getByTestId('searches-length')).toHaveTextContent('0');

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Set Searches' }));
    });

    expect(screen.getByTestId('searches-length')).toHaveTextContent('1');
  });

  /** Sets activeSearch when an id is set, and clears it when id is cleared. */
  it('activeSearch is set/cleared correctly when setActiveSearchId is called', async () => {
    mockApiGet.mockResolvedValueOnce({
      result: [createSavedSearch({ id: 'search-002', name: 'Second Search' })]
    });

    const user = userEvent.setup();

    render(
      <SavedSearchContextProvider>
        <Consumer />
      </SavedSearchContextProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('searches-length')).toHaveTextContent('1');
    });

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Set Active' }));
    });

    expect(screen.getByTestId('active-id')).toHaveTextContent('search-002');
    expect(screen.getByTestId('active-search')).toHaveTextContent('search-002');

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Clear Active' }));
    });

    expect(screen.getByTestId('active-id')).toHaveTextContent('');
    expect(screen.getByTestId('active-search')).toHaveTextContent('');
  });

  /** Confirms count stays the same when searches change, unless setSavedSearchCount is called. */
  it('savedSearchCount does not change when setSavedSearches is called (current provider behavior)', async () => {
    mockApiGet.mockResolvedValueOnce({ result: [] });

    const user = userEvent.setup();

    render(
      <SavedSearchContextProvider>
        <Consumer />
      </SavedSearchContextProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('count')).toHaveTextContent('0');
    });

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Set Searches' }));
    });

    expect(screen.getByTestId('searches-length')).toHaveTextContent('1');
    expect(screen.getByTestId('count')).toHaveTextContent('0');

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Set Count' }));
    });

    expect(screen.getByTestId('count')).toHaveTextContent('1');
  });

  /** Logs an error if the API request fails. */
  it('logs an error when apiGet fails', async () => {
    mockApiGet.mockRejectedValueOnce(new Error('Network error'));

    render(
      <SavedSearchContextProvider>
        <Consumer />
      </SavedSearchContextProvider>
    );

    await waitFor(() => {
      expect(mockLoggerError).toHaveBeenCalled();
    });
  });
});

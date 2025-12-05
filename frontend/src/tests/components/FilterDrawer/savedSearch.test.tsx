import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { SaveSearchModal } from '@/components/SaveSearchModal/SaveSearchModal';
import { useAreFiltersDefault } from '@/hooks/useAreFiltersDefault';
import { useSavedSearchContext } from 'context/SavedSearchContext';
import { SavedSearch } from '@/types';

// Mock hooks
vi.mock('@/hooks/useAreFiltersDefault');
vi.mock('context/SavedSearchContext');

// Mock auth context
vi.mock('context', async () => {
  const actual = await vi.importActual('context');
  return {
    ...actual,
    useAuthContext: () => ({
      apiGet: vi.fn().mockResolvedValue({ result: [] }),
      apiPost: vi.fn().mockResolvedValue({})
    })
  };
});

describe('SaveSearchModal - button disabled state', () => {
  const defaultProps = {
    searchTerm: 'test',
    filters: [],
    totalResults: 10,
    sortField: 'name',
    sortDirection: 'asc',
    initialFilters: []
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables Save New button when filters match initial filters', () => {
    vi.mocked(useAreFiltersDefault).mockReturnValue(true);
    vi.mocked(useSavedSearchContext).mockReturnValue({
      savedSearches: [],
      setSavedSearches: vi.fn(),
      setSavedSearchCount: vi.fn(),
      activeSearch: undefined,
      savedSearchCount: 0,
      activeSearchId: '',
      setActiveSearchId: vi.fn()
    });

    render(<SaveSearchModal {...defaultProps} />);

    const saveButton = screen.getByRole('button', { name: /save new/i });
    expect(saveButton).toBeDisabled();
  });

  it('enables Save New button when filters differ from initial filters', () => {
    vi.mocked(useAreFiltersDefault).mockReturnValue(false);
    vi.mocked(useSavedSearchContext).mockReturnValue({
      savedSearches: [],
      setSavedSearches: vi.fn(),
      setSavedSearchCount: vi.fn(),
      activeSearch: undefined,
      savedSearchCount: 0,
      activeSearchId: '',
      setActiveSearchId: vi.fn()
    });

    render(<SaveSearchModal {...defaultProps} />);

    const saveButton = screen.getByRole('button', { name: /save new/i });
    expect(saveButton).not.toBeDisabled();
  });

  it('renders Update button when active search is present', () => {
    vi.mocked(useAreFiltersDefault).mockReturnValue(true);
    vi.mocked(useSavedSearchContext).mockReturnValue({
      savedSearches: [
        {
          id: '1',
          name: 'My Search'
        } as SavedSearch
      ],
      setSavedSearches: vi.fn(),
      setSavedSearchCount: vi.fn(),
      activeSearch: {
        id: '1',
        name: 'My Search'
      } as SavedSearch,
      savedSearchCount: 1,
      activeSearchId: '1',
      setActiveSearchId: vi.fn()
    });

    render(<SaveSearchModal {...defaultProps} />);

    const saveNewButton = screen.queryByRole('button', { name: /save new/i });
    const updateButton = screen.getByRole('button', {
      name: /update saved filter/i
    });

    expect(saveNewButton).not.toBeInTheDocument();
    expect(updateButton).toBeInTheDocument();
  });

  it('does not render Update button when activeSearch is undefined or not present', () => {
    vi.mocked(useAreFiltersDefault).mockReturnValue(false);
    vi.mocked(useSavedSearchContext).mockReturnValue({
      savedSearches: [
        {
          id: '1',
          name: 'My Search'
        } as SavedSearch
      ],
      setSavedSearches: vi.fn(),
      setSavedSearchCount: vi.fn(),
      activeSearch: undefined,
      savedSearchCount: 1,
      activeSearchId: '2',
      setActiveSearchId: vi.fn()
    });

    render(<SaveSearchModal {...defaultProps} />);

    const saveNewButton = screen.getByRole('button', { name: /save new/i });
    const updateButton = screen.queryByRole('button', {
      name: /update saved filter/i
    });

    expect(saveNewButton).toBeInTheDocument();
    expect(updateButton).not.toBeInTheDocument();
  });
});

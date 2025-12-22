import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { SaveSearchModal } from '@/components/SaveSearchModal/SaveSearchModal';
import { useAreFiltersDefault } from '@/hooks/useAreFiltersDefault';
import { useSavedSearchContext } from 'context/SavedSearchContext';
import { SavedSearch } from '@/types';

// Mock hooks
vi.mock('@/hooks/useAreFiltersDefault');
vi.mock('context/SavedSearchContext');

// Mock auth context hook
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

describe('SaveSearchModal functionality', () => {
  const modalProps = {
    searchTerm: '',
    filters: [
      {
        field: 'vulnerabilities.severity',
        values: ['High'],
        type: 'any'
      }
    ],
    totalResults: 10,
    sortField: 'name',
    sortDirection: 'asc',
    initialFilters: []
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });
  describe('Button state', () => {
    it('disables Save New button when filters match initial filters', () => {
      // Mock the useAreFiltersDefault hook to return true. This should disable the Save New button.
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

      render(<SaveSearchModal {...modalProps} />);

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

      render(<SaveSearchModal {...modalProps} />);

      const saveButton = screen.getByRole('button', { name: /save new/i });
      expect(saveButton).not.toBeDisabled();
    });
  });

  describe('Conditional rendering of Save New and Update buttons', () => {
    it('renders Update button when active search is present', () => {
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

      render(<SaveSearchModal {...modalProps} />);

      const saveNewButton = screen.queryByRole('button', { name: /save new/i });
      const updateButton = screen.getByRole('button', {
        name: /update saved filter/i
      });

      expect(saveNewButton).not.toBeInTheDocument();
      expect(updateButton).toBeInTheDocument();
    });

    it('does not render Update button when activeSearch is undefined or not present', () => {
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

      render(<SaveSearchModal {...modalProps} />);

      const saveNewButton = screen.getByRole('button', { name: /save new/i });
      const updateButton = screen.queryByRole('button', {
        name: /update saved filter/i
      });

      expect(saveNewButton).toBeInTheDocument();
      expect(updateButton).not.toBeInTheDocument();
    });
  });

  describe('Modal open behavior', () => {
    it('opens save new modal when Save New button is clicked', async () => {
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

      render(<SaveSearchModal {...modalProps} />);

      const saveNewButton = screen.getByRole('button', { name: /save new/i });
      expect(saveNewButton).toBeInTheDocument();

      const user = userEvent.setup();
      await user.click(saveNewButton);

      const modal = screen.getByRole('dialog', {
        name: /save search/i
      });
      expect(modal).toBeInTheDocument();
    });

    it('opens update search modal when Update button is clicked', async () => {
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

      render(<SaveSearchModal {...modalProps} />);

      const updateButton = screen.getByRole('button', {
        name: /update saved filter/i
      });

      const user = userEvent.setup();
      await user.click(updateButton);

      const modal = screen.getByRole('dialog', {
        name: /update search/i
      });
      await waitFor(() => {
        expect(modal).toBeInTheDocument();
      });
    });
    describe('Modal close behavior', () => {
      it('closes save new modal when cancel button is clicked', async () => {
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

        render(<SaveSearchModal {...modalProps} />);

        const saveNewButton = screen.getByRole('button', { name: /save new/i });
        expect(saveNewButton).toBeInTheDocument();

        const user = userEvent.setup();
        await user.click(saveNewButton);

        const cancelButton = screen.getByRole('button', { name: /cancel/i });
        expect(cancelButton).toBeInTheDocument();

        await user.click(cancelButton);

        await waitFor(() => {
          expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        });
      });
    });

    it('closes update search modal when cancel button is clicked', async () => {
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

      render(<SaveSearchModal {...modalProps} />);

      const updateButton = screen.getByRole('button', {
        name: /update saved filter/i
      });

      const user = userEvent.setup();
      await user.click(updateButton);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      expect(cancelButton).toBeInTheDocument();

      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('Focus management', () => {
    it('shifts focus to input field when update search modal opens', async () => {
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
        activeSearch: {
          id: '1',
          name: 'My Search'
        } as SavedSearch,
        savedSearchCount: 1,
        activeSearchId: '1',
        setActiveSearchId: vi.fn()
      });

      render(<SaveSearchModal {...modalProps} />);

      const updateButton = screen.getByRole('button', {
        name: /update saved filter/i
      });

      const user = userEvent.setup();
      await user.click(updateButton);

      const inputField = screen.getByRole('textbox', {
        name: /enter a name for your saved filter/i
      });

      expect(inputField).toBeInTheDocument();
      await waitFor(() => {
        expect(inputField).toHaveFocus();
      });
    });

    it('shifts focus to input field when save new search modal opens', async () => {
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

      render(<SaveSearchModal {...modalProps} />);

      const saveNewButton = screen.getByRole('button', { name: /save new/i });
      expect(saveNewButton).toBeInTheDocument();

      const user = userEvent.setup();
      await user.click(saveNewButton);

      const inputField = screen.getByRole('textbox', {
        name: /Enter a name for your saved search/i
      });

      expect(inputField).toBeInTheDocument();
      await waitFor(() => {
        expect(inputField).toHaveFocus();
      });
    });
  });
});

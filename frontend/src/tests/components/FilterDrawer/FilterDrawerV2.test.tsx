import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import { FilterDrawer } from '@components/FilterDrawer/FilterDrawerV2';
import { ROUTES } from '@/constants/routes';

const FilterDrawerForTests = FilterDrawer as unknown as React.FC<any>;

// ----------------------
// Mocks
// ----------------------
const mockUseLocation = vi.fn();

vi.mock('react-router-dom', async () => {
  const actualModule =
    await vi.importActual<Record<string, unknown>>('react-router-dom');
  return {
    ...actualModule,
    useLocation: () => mockUseLocation()
  };
});

vi.mock('@mui/material/styles', () => ({
  useTheme: () => ({
    palette: {
      neutrals: {
        light: '#dddddd'
      }
    }
  })
}));

const mockMatchPath = vi.fn();

vi.mock('utils/stringUtils', () => ({
  matchPath: (routesToMatch: string[], pathname: string) =>
    mockMatchPath(routesToMatch, pathname)
}));

vi.mock('@components/FilterDrawer/DrawerInterior', () => ({
  DrawerInterior: () => <div data-testid="drawer-interior">DrawerInterior</div>
}));

vi.mock('@components/FilterDrawer/RegionAndOrganizationFilters', () => ({
  RegionAndOrganizationFilters: () => (
    <div data-testid="region-org-filters">RegionAndOrganizationFilters</div>
  )
}));

vi.mock('@components/FilterDrawer/VSDashRegionAndOrgFilters', () => ({
  VSDashRegionAndOrgFilters: () => (
    <div data-testid="vsdash-region-org-filters">VSDashRegionAndOrgFilters</div>
  )
}));

const mockUseAreFiltersDefault = vi.fn();

vi.mock('@/hooks/useAreFiltersDefault', () => ({
  useAreFiltersDefault: (...hookArgs: unknown[]) =>
    mockUseAreFiltersDefault(...hookArgs)
}));

const mockSetActiveSearchId = vi.fn();

vi.mock('context', () => ({
  useSavedSearchContext: () => ({
    setActiveSearchId: mockSetActiveSearchId
  })
}));

vi.mock('@mui/material/Drawer', () => {
  type DrawerProps = {
    open: boolean;
    onClose?: () => void;
    children: React.ReactNode;
  };

  const MockDrawer: React.FC<DrawerProps> = ({ open, onClose, children }) => {
    if (!open) {
      return null;
    }

    return (
      <div data-testid="mui-drawer">
        <button
          type="button"
          data-testid="trigger-onclose"
          onClick={() => onClose?.()}
        >
          Trigger onClose
        </button>
        {children}
      </div>
    );
  };

  return { default: MockDrawer };
});

function ensureMainLayoutContainer(): void {
  const existingContainer = document.getElementById('main-layout');
  if (existingContainer) {
    return;
  }
  const containerElement = document.createElement('div');
  containerElement.id = 'main-layout';
  document.body.appendChild(containerElement);
}

type FilterDrawerTestOverrides = Partial<{
  isMobile: boolean;
  isFilterDrawerOpen: boolean;
  setIsFilterDrawerOpen: (isOpen: boolean) => void;
  addFilter: (...args: unknown[]) => void;
  removeFilter: (...args: unknown[]) => void;
  facets: unknown[];
  searchTerm: string;
  setSearchTerm: (...args: unknown[]) => void;
  filters: unknown[];
  initialFilters: any[];
  autocompletedResults: unknown[];
  autocompletedSuggestions: unknown[];
  results: unknown[];
  topOffset: number;
}>;

function createProps(
  overrides: FilterDrawerTestOverrides = {}
): Record<string, unknown> {
  return {
    isMobile: true,
    isFilterDrawerOpen: true,
    setIsFilterDrawerOpen: vi.fn(),
    addFilter: vi.fn(),
    removeFilter: vi.fn(),
    facets: [],
    searchTerm: '',
    setSearchTerm: vi.fn(),
    filters: [],
    initialFilters: [],
    autocompletedResults: [],
    autocompletedSuggestions: [],
    results: [],
    topOffset: 84,
    ...overrides
  };
}

// ----------------------
// Tests
// ----------------------

describe('FilterDrawerV2 (FilterDrawer)', () => {
  beforeEach(() => {
    ensureMainLayoutContainer();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders drawer content when open is true', () => {
    mockUseLocation.mockReturnValue({ pathname: ROUTES.INVENTORY });
    mockMatchPath.mockImplementation(
      (routesToMatch: string[], pathname: string) =>
        routesToMatch.includes(pathname)
    );
    mockUseAreFiltersDefault.mockReturnValue(false);

    render(<FilterDrawerForTests {...createProps()} />);

    expect(screen.getByTestId('mui-drawer')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Filter' })).toBeInTheDocument();
    expect(screen.getByLabelText('close-filter-drawer')).toBeInTheDocument();

    expect(screen.getByTestId('region-org-filters')).toBeInTheDocument();
    expect(screen.getByTestId('drawer-interior')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Reset Filters' })
    ).toBeInTheDocument();
  });

  it('invokes setIsFilterDrawerOpen(false) when close icon is clicked', async () => {
    mockUseLocation.mockReturnValue({ pathname: ROUTES.INVENTORY });
    mockMatchPath.mockImplementation(
      (routesToMatch: string[], pathname: string) =>
        routesToMatch.includes(pathname)
    );
    mockUseAreFiltersDefault.mockReturnValue(false);

    const user = userEvent.setup();
    const setIsFilterDrawerOpenSpy = vi.fn();

    render(
      <FilterDrawerForTests
        {...createProps({ setIsFilterDrawerOpen: setIsFilterDrawerOpenSpy })}
      />
    );

    await user.click(screen.getByLabelText('close-filter-drawer'));
    expect(setIsFilterDrawerOpenSpy).toHaveBeenCalledWith(false);
  });

  it('invokes setIsFilterDrawerOpen(false) when Drawer onClose fires', async () => {
    mockUseLocation.mockReturnValue({ pathname: ROUTES.INVENTORY });
    mockMatchPath.mockImplementation(
      (routesToMatch: string[], pathname: string) =>
        routesToMatch.includes(pathname)
    );
    mockUseAreFiltersDefault.mockReturnValue(false);

    const user = userEvent.setup();
    const setIsFilterDrawerOpenSpy = vi.fn();

    render(
      <FilterDrawerForTests
        {...createProps({ setIsFilterDrawerOpen: setIsFilterDrawerOpenSpy })}
      />
    );

    await user.click(screen.getByTestId('trigger-onclose'));
    expect(setIsFilterDrawerOpenSpy).toHaveBeenCalledWith(false);
  });

  it('Reset button calls setSearchTerm clear + restores initial filters (inventory) + clears active search', async () => {
    mockUseLocation.mockReturnValue({ pathname: ROUTES.INVENTORY });
    mockMatchPath.mockImplementation(
      (routesToMatch: string[], pathname: string) =>
        routesToMatch.includes(pathname)
    );
    mockUseAreFiltersDefault.mockReturnValue(false);

    const user = userEvent.setup();

    const setSearchTermSpy = vi.fn();
    const addFilterSpy = vi.fn();

    const initialFilters = [
      { field: 'region', values: ['Region A', 'Region B'] },
      { field: 'org', values: ['Org 1'] }
    ];

    render(
      <FilterDrawerForTests
        {...createProps({
          searchTerm: 'previous',
          setSearchTerm: setSearchTermSpy,
          addFilter: addFilterSpy,
          initialFilters
        })}
      />
    );

    await user.click(screen.getByRole('button', { name: 'Reset Filters' }));

    expect(setSearchTermSpy).toHaveBeenCalledWith('', {
      shouldClearFilters: true,
      autocompleteResults: false
    });

    expect(addFilterSpy).toHaveBeenCalledWith('region', 'Region A', 'any');
    expect(addFilterSpy).toHaveBeenCalledWith('region', 'Region B', 'any');
    expect(addFilterSpy).toHaveBeenCalledWith('org', 'Org 1', 'any');

    expect(mockSetActiveSearchId).toHaveBeenCalledWith('');
  });

  it('Reset button disabled when useAreFiltersDefault returns true', () => {
    mockUseLocation.mockReturnValue({ pathname: ROUTES.INVENTORY });
    mockMatchPath.mockImplementation(
      (routesToMatch: string[], pathname: string) =>
        routesToMatch.includes(pathname)
    );
    mockUseAreFiltersDefault.mockReturnValue(true);

    render(<FilterDrawerForTests {...createProps()} />);

    expect(
      screen.getByRole('button', { name: 'Reset Filters' })
    ).toBeDisabled();
  });
});

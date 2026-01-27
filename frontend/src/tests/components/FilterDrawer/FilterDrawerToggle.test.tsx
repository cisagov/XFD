// FilterDrawerToggle.spec.tsx
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import FilterDrawerToggle from '@components/FilterDrawer/FilterDrawerToggle';

// ----------------------
// Mock
// ----------------------
const mockSetIsFilterDrawerOpen = vi.fn();
let mockIsFilterDrawerOpenValue = false;

let mockSelectedRegionId = 'initial';
let mockSelectedOrgName = 'initial';

vi.mock('@/context/FilterDrawerContext', () => ({
  useFilterDrawerContext: () => ({
    isFilterDrawerOpen: mockIsFilterDrawerOpenValue,
    setIsFilterDrawerOpen: mockSetIsFilterDrawerOpen,
    get selectedRegionId() {
      return mockSelectedRegionId;
    },
    get selectedOrgName() {
      return mockSelectedOrgName;
    }
  })
}));

vi.mock('@mui/material/AppBar', () => ({
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="appbar">{children}</div>
  )
}));

vi.mock('@mui/material/Toolbar', () => ({
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="toolbar">{children}</div>
  )
}));

vi.mock('@mui/material/Button', () => ({
  default: ({
    children,
    onClick,
    'aria-label': ariaLabel
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    'aria-label'?: string;
  }) => (
    <button type="button" aria-label={ariaLabel} onClick={onClick}>
      {children}
    </button>
  )
}));

vi.mock('@mui/icons-material/FilterAlt', () => ({
  default: () => <span aria-hidden="true">FilterIcon</span>
}));

// ----------------------
// Tests
// ----------------------

describe('FilterDrawerToggle', () => {
  beforeEach(() => {
    mockIsFilterDrawerOpenValue = false;
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  /** Renders the toggle button with the expected accessible label. */
  it('renders a button with correct accessible name', () => {
    render(<FilterDrawerToggle />);

    expect(
      screen.getByRole('button', { name: 'Toggle Filter Drawer' })
    ).toBeInTheDocument();
  });

  /** Clicking the button calls the context setter to open the drawer. */
  it('clicking the button toggles drawer open state via context setter', async () => {
    const user = userEvent.setup();
    render(<FilterDrawerToggle />);

    await user.click(
      screen.getByRole('button', { name: 'Toggle Filter Drawer' })
    );

    expect(mockSetIsFilterDrawerOpen).toHaveBeenCalledWith(true);
  });

  /** Allows keyboard activation with Enter and Space. */
  it('supports keyboard activation using Enter and Space', async () => {
    const user = userEvent.setup();
    render(<FilterDrawerToggle />);

    const toggleButton = screen.getByRole('button', {
      name: 'Toggle Filter Drawer'
    });

    toggleButton.focus();
    expect(toggleButton).toHaveFocus();

    await user.keyboard('{Enter}');
    expect(mockSetIsFilterDrawerOpen).toHaveBeenCalledWith(true);

    mockSetIsFilterDrawerOpen.mockClear();

    await user.keyboard(' ');
    expect(mockSetIsFilterDrawerOpen).toHaveBeenCalledWith(true);
  });

  /** Updates committedRegionId and committedOrgName when context values change */
  it('updates committed region and organization when context values change', () => {
    mockSelectedRegionId = 'region-1';
    mockSelectedOrgName = 'Org A';

    const { rerender } = render(<FilterDrawerToggle />);

    expect(screen.getByText('Region:')).toBeInTheDocument();
    expect(screen.getByText('region-1')).toBeInTheDocument();
    expect(screen.getByText('Organization:')).toBeInTheDocument();
    expect(screen.getByText('Org A')).toBeInTheDocument();

    mockSelectedRegionId = 'region-2';
    mockSelectedOrgName = 'Org B';

    rerender(<FilterDrawerToggle />);

    expect(screen.getByText('region-2')).toBeInTheDocument();
    expect(screen.getByText('Org B')).toBeInTheDocument();
  });
});

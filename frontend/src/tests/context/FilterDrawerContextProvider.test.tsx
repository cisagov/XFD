import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import { FilterDrawerContextProvider } from 'context/FilterDrawerContextProvider';
import { FilterDrawerContext } from 'context/FilterDrawerContext';

// ----------------------
// Mock
// ----------------------
const mockUsePersistentState = vi.fn();

vi.mock('hooks', async () => {
  const ReactModule = await vi.importActual<typeof React>('react');

  function usePersistentState<TValue>(
    storageKey: string,
    defaultValue: TValue
  ): [TValue, (nextValue: TValue) => void] {
    mockUsePersistentState(storageKey, defaultValue);

    const [storedValue, setStoredValue] = ReactModule.useState<TValue>(() => {
      const rawValue = window.localStorage.getItem(storageKey);
      if (rawValue === null) {
        return defaultValue;
      }
      return JSON.parse(rawValue) as TValue;
    });

    const setPersistentValue = (nextValue: TValue) => {
      setStoredValue(nextValue);
      window.localStorage.setItem(storageKey, JSON.stringify(nextValue));
    };

    return [storedValue, setPersistentValue];
  }

  return { usePersistentState };
});

const DrawerContextConsumer: React.FC = () => {
  const drawerContext = React.useContext(FilterDrawerContext);

  return (
    <div>
      <div data-testid="open-state">
        {String(drawerContext.isFilterDrawerOpen)}
      </div>

      <button
        type="button"
        onClick={() => drawerContext.setIsFilterDrawerOpen(true)}
      >
        Open
      </button>

      <button
        type="button"
        onClick={() => drawerContext.setIsFilterDrawerOpen(false)}
      >
        Close
      </button>
    </div>
  );
};

// ----------------------
// Tests
// ----------------------

describe('FilterDrawerContextProvider', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
  });

  /** Defaults to closed when there is no saved value in localStorage. */
  it('initializes with isFilterDrawerOpen=false when localStorage is empty', () => {
    render(
      <FilterDrawerContextProvider>
        <DrawerContextConsumer />
      </FilterDrawerContextProvider>
    );

    expect(mockUsePersistentState).toHaveBeenCalledWith(
      'filterDrawerOpen',
      false
    );
    expect(screen.getByTestId('open-state')).toHaveTextContent('false');
  });

  /** Uses the saved localStorage value as the initial drawer state. */
  it('reads initial drawer state from localStorage on mount', () => {
    window.localStorage.setItem('filterDrawerOpen', 'true');

    render(
      <FilterDrawerContextProvider>
        <DrawerContextConsumer />
      </FilterDrawerContextProvider>
    );

    expect(screen.getByTestId('open-state')).toHaveTextContent('true');
  });

  /** Saves drawer state changes back to localStorage. */
  it('writes updated drawer state to localStorage when state changes', async () => {
    const user = userEvent.setup();

    render(
      <FilterDrawerContextProvider>
        <DrawerContextConsumer />
      </FilterDrawerContextProvider>
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Open' }));
    });

    expect(screen.getByTestId('open-state')).toHaveTextContent('true');
    expect(window.localStorage.getItem('filterDrawerOpen')).toBe('true');

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Close' }));
    });

    expect(screen.getByTestId('open-state')).toHaveTextContent('false');
    expect(window.localStorage.getItem('filterDrawerOpen')).toBe('false');
  });

  /** Handles quick open/close updates and ends in the last state. */
  it('handles rapid open/close calls without ending in an inconsistent state', async () => {
    const user = userEvent.setup();

    render(
      <FilterDrawerContextProvider>
        <DrawerContextConsumer />
      </FilterDrawerContextProvider>
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Open' }));
      await user.click(screen.getByRole('button', { name: 'Close' }));
      await user.click(screen.getByRole('button', { name: 'Open' }));
      await user.click(screen.getByRole('button', { name: 'Close' }));
    });

    expect(screen.getByTestId('open-state')).toHaveTextContent('false');
    expect(window.localStorage.getItem('filterDrawerOpen')).toBe('false');
  });
});

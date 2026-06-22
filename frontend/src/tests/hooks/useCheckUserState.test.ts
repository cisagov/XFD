import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useCheckUserState } from '../../hooks/useCheckUserState';

const userWithState = { state: 'VA' };
const userWithoutState = { state: null };
const userWithEmptyState = { state: '' };

describe('useCheckUserState', () => {
  it('opens the form when user has no state', () => {
    const { result } = renderHook(() =>
      useCheckUserState(userWithoutState, false)
    );
    expect(result.current.isUpdateStateFormOpen).toBe(true);
  });

  it('opens the form when user state is empty string', () => {
    const { result } = renderHook(() =>
      useCheckUserState(userWithEmptyState, false)
    );
    expect(result.current.isUpdateStateFormOpen).toBe(true);
  });

  it('does not open the form when user has state', () => {
    const { result } = renderHook(() =>
      useCheckUserState(userWithState, false)
    );
    expect(result.current.isUpdateStateFormOpen).toBe(false);
  });

  it('does not open the form when isLoggingOut is true', () => {
    const { result } = renderHook(() =>
      useCheckUserState(userWithoutState, true)
    );
    expect(result.current.isUpdateStateFormOpen).toBe(false);
  });

  it('does not open the form when user is null', () => {
    const { result } = renderHook(() => useCheckUserState(null, false));
    expect(result.current.isUpdateStateFormOpen).toBe(false);
  });

  it('opens the form when isLoggingOut transitions from true to false', () => {
    const { result, rerender } = renderHook(
      ({ isLoggingOut }) => useCheckUserState(userWithoutState, isLoggingOut),
      { initialProps: { isLoggingOut: true as boolean | null } }
    );
    expect(result.current.isUpdateStateFormOpen).toBe(false);

    rerender({ isLoggingOut: false });
    expect(result.current.isUpdateStateFormOpen).toBe(true);
  });

  it('exposes setIsUpdateStateFormOpen to allow closing the form', () => {
    const { result } = renderHook(() =>
      useCheckUserState(userWithoutState, false)
    );
    expect(result.current.isUpdateStateFormOpen).toBe(true);

    act(() => {
      result.current.setIsUpdateStateFormOpen(false);
    });
    expect(result.current.isUpdateStateFormOpen).toBe(false);
  });
});

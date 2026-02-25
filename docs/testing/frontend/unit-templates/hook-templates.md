# Hook Test Templates

Templates for testing custom React hooks in the XFD (CyHy Dashboard) frontend application.

> **📝 Important Note**: The XFD codebase currently has mixed import patterns for test-utils. These templates use the recommended pattern (`import { renderHook } from 'test-utils'`), but you may see existing tests using `'@testing-library/react'` directly or other patterns. For new tests, use the patterns shown in these templates.

## Table of Contentsk Test Templates

Templates for testing custom React hooks in the XFD frontend application.

## Table of Contents

- [Basic Hook Template](#basic-hook-template)
- [Hook with Parameters Template](#hook-with-parameters-template)
- [Hook with API Integration Template](#hook-with-api-integration-template)
- [Hook with LocalStorage Template](#hook-with-localstorage-template)
- [Hook with Context Template](#hook-with-context-template)
- [Hook with Side Effects Template](#hook-with-side-effects-template)

---

## Basic Hook Template

Use this for simple hooks that manage state or provide utility functions.

```tsx
import React from 'react';
import { renderHook, act } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { useYourHook } from '../../hooks/useYourHook';

describe('useYourHook', () => {
  it('returns initial state correctly', () => {
    const { result } = renderHook(() => useYourHook());
    
    expect(result.current.value).toBe('initialValue');
    expect(result.current.isLoading).toBe(false);
    expect(typeof result.current.setValue).toBe('function');
  });

  it('updates state when setValue is called', () => {
    const { result } = renderHook(() => useYourHook());
    
    act(() => {
      result.current.setValue('newValue');
    });
    
    expect(result.current.value).toBe('newValue');
  });

  it('handles multiple state updates', () => {
    const { result } = renderHook(() => useYourHook());
    
    act(() => {
      result.current.setValue('first');
    });
    expect(result.current.value).toBe('first');
    
    act(() => {
      result.current.setValue('second');
    });
    expect(result.current.value).toBe('second');
  });

  it('provides stable function references', () => {
    const { result, rerender } = renderHook(() => useYourHook());
    
    const firstSetValue = result.current.setValue;
    
    rerender();
    
    expect(result.current.setValue).toBe(firstSetValue);
  });
});
```

---

## Hook with Parameters Template

Use this for hooks that accept parameters and need to test different parameter combinations.

```tsx
import React from 'react';
import { renderHook, act } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { useYourParameterizedHook } from '../../hooks/useYourParameterizedHook';

describe('useYourParameterizedHook', () => {
  it('works with default parameters', () => {
    const { result } = renderHook(() => useYourParameterizedHook());
    
    expect(result.current.data).toBe(null);
    expect(result.current.error).toBe(null);
  });

  it('works with custom parameters', () => {
    const initialValue = 'test-value';
    const options = { enableCache: true };
    
    const { result } = renderHook(() => 
      useYourParameterizedHook(initialValue, options)
    );
    
    expect(result.current.data).toBe(initialValue);
    expect(result.current.isCacheEnabled).toBe(true);
  });

  it('updates when parameters change', () => {
    let initialValue = 'initial';
    
    const { result, rerender } = renderHook(
      ({ value }) => useYourParameterizedHook(value),
      { initialProps: { value: initialValue } }
    );
    
    expect(result.current.data).toBe('initial');
    
    // Update parameter
    rerender({ value: 'updated' });
    
    expect(result.current.data).toBe('updated');
  });

  it('handles parameter validation', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    const { result } = renderHook(() => 
      useYourParameterizedHook('invalid-parameter')
    );
    
    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.message).toContain('Invalid parameter');
    
    consoleError.mockRestore();
  });

  it('handles optional parameters', () => {
    const { result: withOptions } = renderHook(() => 
      useYourParameterizedHook('value', { timeout: 5000 })
    );
    
    const { result: withoutOptions } = renderHook(() => 
      useYourParameterizedHook('value')
    );
    
    expect(withOptions.current.timeout).toBe(5000);
    expect(withoutOptions.current.timeout).toBe(3000); // default
  });
});
```

---

## Hook with API Integration Template

Use this for hooks that make API calls or handle data fetching.

```tsx
import React from 'react';
import { renderHook, act, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useYourAPIHook } from '../../hooks/useYourAPIHook';

// Mock the API
vi.mock('../../api/endpoints', () => ({
  fetchData: vi.fn(),
  postData: vi.fn()
}));

import { fetchData, postData } from '../../api/endpoints';
const mockFetchData = vi.mocked(fetchData);
const mockPostData = vi.mocked(postData);

describe('useYourAPIHook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns initial loading state', () => {
    const { result } = renderHook(() => useYourAPIHook());
    
    expect(result.current.data).toBe(null);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('fetches data successfully', async () => {
    const mockData = [{ id: 1, name: 'Test Item' }];
    mockFetchData.mockResolvedValue({ data: mockData, status: 200 });
    
    const { result } = renderHook(() => useYourAPIHook());
    
    await act(async () => {
      result.current.fetchData();
    });
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBe(null);
    expect(mockFetchData).toHaveBeenCalledTimes(1);
  });

  it('handles loading states correctly', async () => {
    mockFetchData.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ data: [] }), 100))
    );
    
    const { result } = renderHook(() => useYourAPIHook());
    
    act(() => {
      result.current.fetchData();
    });
    
    expect(result.current.isLoading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('handles API errors', async () => {
    const error = new Error('API Error');
    mockFetchData.mockRejectedValue(error);
    
    const { result } = renderHook(() => useYourAPIHook());
    
    await act(async () => {
      result.current.fetchData();
    });
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.data).toBe(null);
    expect(result.current.error).toBe(error);
  });

  it('handles data posting', async () => {
    const newData = { name: 'New Item' };
    const responseData = { id: 2, ...newData };
    mockPostData.mockResolvedValue({ data: responseData, status: 201 });
    
    const { result } = renderHook(() => useYourAPIHook());
    
    await act(async () => {
      await result.current.postData(newData);
    });
    
    expect(mockPostData).toHaveBeenCalledWith(newData);
    expect(result.current.data).toEqual(responseData);
  });

  it('handles concurrent API calls', async () => {
    mockFetchData
      .mockResolvedValueOnce({ data: 'first', status: 200 })
      .mockResolvedValueOnce({ data: 'second', status: 200 });
    
    const { result } = renderHook(() => useYourAPIHook());
    
    // Start two concurrent requests
    const promise1 = act(async () => result.current.fetchData());
    const promise2 = act(async () => result.current.fetchData());
    
    await Promise.all([promise1, promise2]);
    
    // Should use the result from the last call
    expect(result.current.data).toBe('second');
    expect(mockFetchData).toHaveBeenCalledTimes(2);
  });

  it('cancels pending requests on unmount', async () => {
    mockFetchData.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ data: [] }), 1000))
    );
    
    const { result, unmount } = renderHook(() => useYourAPIHook());
    
    act(() => {
      result.current.fetchData();
    });
    
    expect(result.current.isLoading).toBe(true);
    
    // Unmount before request completes
    unmount();
    
    // Should not throw any errors or warnings
    await waitFor(() => {}, { timeout: 1100 });
  });
});
```

---

## Hook with LocalStorage Template

Use this for hooks that interact with browser localStorage.

```tsx
import React from 'react';
import { renderHook, act } from 'test-utils';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { useYourStorageHook } from '../../hooks/useYourStorageHook';

// Mock localStorage
const mockSetItem = vi.fn();
const mockGetItem = vi.fn();
const mockRemoveItem = vi.fn();

vi.stubGlobal('localStorage', {
  setItem: mockSetItem,
  getItem: mockGetItem,
  removeItem: mockRemoveItem,
  clear: vi.fn()
});

describe('useYourStorageHook', () => {
  const storageKey = 'test-key';
  const defaultValue = 'default';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('returns default value when localStorage is empty', () => {
    mockGetItem.mockReturnValue(null);
    
    const { result } = renderHook(() => 
      useYourStorageHook(storageKey, defaultValue)
    );
    
    expect(result.current[0]).toBe(defaultValue);
    expect(mockGetItem).toHaveBeenCalledWith(storageKey);
  });

  it('returns stored value when localStorage has data', () => {
    const storedValue = 'stored-value';
    mockGetItem.mockReturnValue(JSON.stringify(storedValue));
    
    const { result } = renderHook(() => 
      useYourStorageHook(storageKey, defaultValue)
    );
    
    expect(result.current[0]).toBe(storedValue);
  });

  it('updates localStorage when value changes', () => {
    mockGetItem.mockReturnValue(null);
    
    const { result } = renderHook(() => 
      useYourStorageHook(storageKey, defaultValue)
    );
    
    const newValue = 'new-value';
    
    act(() => {
      result.current[1](newValue);
    });
    
    expect(result.current[0]).toBe(newValue);
    expect(mockSetItem).toHaveBeenCalledWith(
      storageKey, 
      JSON.stringify(newValue)
    );
  });

  it('handles function updates', () => {
    mockGetItem.mockReturnValue(JSON.stringify(5));
    
    const { result } = renderHook(() => 
      useYourStorageHook(storageKey, 0)
    );
    
    act(() => {
      result.current[1](prev => prev + 1);
    });
    
    expect(result.current[0]).toBe(6);
    expect(mockSetItem).toHaveBeenCalledWith(
      storageKey, 
      JSON.stringify(6)
    );
  });

  it('handles complex objects', () => {
    const complexObject = { id: 1, nested: { value: 'test' } };
    mockGetItem.mockReturnValue(JSON.stringify(complexObject));
    
    const { result } = renderHook(() => 
      useYourStorageHook(storageKey, {})
    );
    
    expect(result.current[0]).toEqual(complexObject);
    
    const updatedObject = { ...complexObject, new: 'property' };
    
    act(() => {
      result.current[1](updatedObject);
    });
    
    expect(mockSetItem).toHaveBeenCalledWith(
      storageKey, 
      JSON.stringify(updatedObject)
    );
  });

  it('handles localStorage errors gracefully', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetItem.mockImplementation(() => {
      throw new Error('localStorage error');
    });
    
    const { result } = renderHook(() => 
      useYourStorageHook(storageKey, defaultValue)
    );
    
    expect(result.current[0]).toBe(defaultValue);
    
    consoleError.mockRestore();
  });

  it('handles JSON parse errors', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetItem.mockReturnValue('invalid-json{');
    
    const { result } = renderHook(() => 
      useYourStorageHook(storageKey, defaultValue)
    );
    
    expect(result.current[0]).toBe(defaultValue);
    
    consoleError.mockRestore();
  });

  it('removes item when value is undefined', () => {
    mockGetItem.mockReturnValue(JSON.stringify('some-value'));
    
    const { result } = renderHook(() => 
      useYourStorageHook(storageKey, defaultValue)
    );
    
    act(() => {
      result.current[1](undefined);
    });
    
    expect(mockRemoveItem).toHaveBeenCalledWith(storageKey);
    expect(result.current[0]).toBe(defaultValue);
  });
});
```

---

## Hook with Context Template

Use this for hooks that consume React Context.

```tsx
import React from 'react';
import { renderHook } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { useYourContextHook } from '../../hooks/useYourContextHook';
import { YourContext, YourContextProvider } from '../../context/YourContext';

// Mock context value
const mockContextValue = {
  data: 'test-data',
  isLoading: false,
  updateData: vi.fn(),
  resetData: vi.fn()
};

describe('useYourContextHook', () => {
  it('returns context value when used within provider', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={mockContextValue}>
        {children}
      </YourContextProvider>
    );
    
    const { result } = renderHook(() => useYourContextHook(), { wrapper });
    
    expect(result.current).toEqual(mockContextValue);
  });

  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      renderHook(() => useYourContextHook());
    }).toThrow('useYourContextHook must be used within YourContextProvider');
    
    consoleError.mockRestore();
  });

  it('provides stable function references', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={mockContextValue}>
        {children}
      </YourContextProvider>
    );
    
    const { result, rerender } = renderHook(() => useYourContextHook(), { wrapper });
    
    const firstUpdateData = result.current.updateData;
    
    rerender();
    
    expect(result.current.updateData).toBe(firstUpdateData);
  });

  it('updates when context value changes', () => {
    let contextValue = { ...mockContextValue, data: 'initial' };
    
    const CustomProvider = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={contextValue}>
        {children}
      </YourContextProvider>
    );
    
    const { result, rerender } = renderHook(() => useYourContextHook(), {
      wrapper: CustomProvider
    });
    
    expect(result.current.data).toBe('initial');
    
    // Update context value
    contextValue = { ...contextValue, data: 'updated' };
    rerender();
    
    expect(result.current.data).toBe('updated');
  });

  it('handles context with authentication', () => {
    const authContextValue = {
      ...mockContextValue,
      user: { id: 1, name: 'Test User' },
      isAuthenticated: true
    };
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={authContextValue}>
        {children}
      </YourContextProvider>
    );
    
    const { result } = renderHook(() => useYourContextHook(), { wrapper });
    
    expect(result.current.user).toEqual({ id: 1, name: 'Test User' });
    expect(result.current.isAuthenticated).toBe(true);
  });
});
```

---

## Hook with Side Effects Template

Use this for hooks that handle side effects like subscriptions, timers, or event listeners.

```tsx
import React from 'react';
import { renderHook, act } from 'test-utils';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { useYourEffectHook } from '../../hooks/useYourEffectHook';

describe('useYourEffectHook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('sets up side effect on mount', () => {
    const mockSetup = vi.fn();
    const mockCleanup = vi.fn();
    
    vi.doMock('../../utils/sideEffect', () => ({
      setupSideEffect: mockSetup.mockReturnValue(mockCleanup)
    }));
    
    const { unmount } = renderHook(() => useYourEffectHook());
    
    expect(mockSetup).toHaveBeenCalledTimes(1);
    
    unmount();
    
    expect(mockCleanup).toHaveBeenCalledTimes(1);
  });

  it('handles timer-based effects', () => {
    const mockCallback = vi.fn();
    
    const { result } = renderHook(() => useYourEffectHook({
      callback: mockCallback,
      interval: 1000
    }));
    
    expect(mockCallback).not.toHaveBeenCalled();
    
    // Fast-forward time
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    
    expect(mockCallback).toHaveBeenCalledTimes(1);
    
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    
    expect(mockCallback).toHaveBeenCalledTimes(3);
  });

  it('cleans up timers on unmount', () => {
    const mockCallback = vi.fn();
    
    const { unmount } = renderHook(() => useYourEffectHook({
      callback: mockCallback,
      interval: 1000
    }));
    
    unmount();
    
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    
    expect(mockCallback).not.toHaveBeenCalled();
  });

  it('handles event listeners', () => {
    const mockEventListener = vi.fn();
    const mockAddEventListener = vi.spyOn(window, 'addEventListener');
    const mockRemoveEventListener = vi.spyOn(window, 'removeEventListener');
    
    const { unmount } = renderHook(() => useYourEffectHook({
      eventListener: mockEventListener,
      eventType: 'resize'
    }));
    
    expect(mockAddEventListener).toHaveBeenCalledWith('resize', mockEventListener);
    
    unmount();
    
    expect(mockRemoveEventListener).toHaveBeenCalledWith('resize', mockEventListener);
  });

  it('handles dependency changes', () => {
    const mockEffect = vi.fn();
    const mockCleanup = vi.fn();
    mockEffect.mockReturnValue(mockCleanup);
    
    let dependency = 'initial';
    
    const { rerender } = renderHook(
      ({ dep }) => useYourEffectHook({ effect: mockEffect, dependency: dep }),
      { initialProps: { dep: dependency } }
    );
    
    expect(mockEffect).toHaveBeenCalledTimes(1);
    
    // Change dependency
    dependency = 'updated';
    rerender({ dep: dependency });
    
    expect(mockCleanup).toHaveBeenCalledTimes(1);
    expect(mockEffect).toHaveBeenCalledTimes(2);
  });

  it('handles async effects', async () => {
    const mockAsyncEffect = vi.fn().mockResolvedValue('result');
    
    const { result, waitForNextUpdate } = renderHook(() => useYourEffectHook({
      asyncEffect: mockAsyncEffect
    }));
    
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBe(null);
    
    await waitForNextUpdate();
    
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBe('result');
    expect(mockAsyncEffect).toHaveBeenCalledTimes(1);
  });

  it('handles effect errors', async () => {
    const mockAsyncEffect = vi.fn().mockRejectedValue(new Error('Effect error'));
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    const { result, waitForNextUpdate } = renderHook(() => useYourEffectHook({
      asyncEffect: mockAsyncEffect
    }));
    
    await waitForNextUpdate();
    
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('Effect error');
    
    consoleError.mockRestore();
  });

  it('prevents effects after unmount', async () => {
    const mockAsyncEffect = vi.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve('result'), 100))
    );
    
    const { result, unmount } = renderHook(() => useYourEffectHook({
      asyncEffect: mockAsyncEffect
    }));
    
    expect(result.current.isLoading).toBe(true);
    
    // Unmount before effect completes
    unmount();
    
    // Advance timers
    act(() => {
      vi.advanceTimersByTime(200);
    });
    
    // Should not update state after unmount
    expect(result.current.isLoading).toBe(true);
  });
});
```

---

## Best Practices for Hook Testing

1. **Use `renderHook` instead of creating wrapper components** - cleaner and more focused
2. **Test the hook's interface** - return values, function signatures, stability
3. **Test side effects and cleanup** - ensure proper cleanup on unmount
4. **Mock external dependencies** - APIs, browser APIs, complex utilities
5. **Test parameter changes** - how the hook responds to prop/parameter updates
6. **Test error scenarios** - how the hook handles failures and edge cases
7. **Use `act()` for state updates** - ensures proper batching and timing
8. **Test cleanup and memory leaks** - especially important for hooks with subscriptions
9. **Keep tests isolated** - each test should be independent
10. **Test both sync and async behavior** - handle promises and loading states

---

**Last Updated**: February 2026

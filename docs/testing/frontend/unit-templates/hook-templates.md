# Hook Test Templates

General patterns for testing custom React hooks in the XFD frontend application.

## Basic Hook Template

```tsx
import { describe, expect, it } from 'vitest';
import { renderHook, act } from 'test-utils';
import { useYourHook } from '@/hooks/useYourHook';

describe('useYourHook', () => {
  it('returns initial state', () => {
    const { result } = renderHook(() => useYourHook());
    
    expect(result.current.value).toBe(null);
    expect(result.current.loading).toBe(false);
  });

  it('updates state correctly', () => {
    const { result } = renderHook(() => useYourHook());
    
    act(() => {
      result.current.setValue('new value');
    });
    
    expect(result.current.value).toBe('new value');
  });
});
```

## Hook with Authentication Context

```tsx
import { describe, expect, it } from 'vitest';
import { renderHook } from 'test-utils';
import { testUser } from 'test-utils';
import { useYourHook } from '@/hooks/useYourHook';

describe('useYourHook with authentication', () => {
  it('works with authenticated user', () => {
    const { result } = renderHook(() => useYourHook(), {
      authContext: { 
        user: testUser, 
        isAuthenticated: true 
      }
    });
    
    expect(result.current.userSpecificData).toBeDefined();
  });

  it('handles unauthenticated state', () => {
    const { result } = renderHook(() => useYourHook(), {
      authContext: { 
        user: null, 
        isAuthenticated: false 
      }
    });
    
    expect(result.current.userSpecificData).toBeNull();
  });
});
```

## Hook with API Calls

```tsx
import { describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from 'test-utils';
import { fetchData } from '@/api/service';
import { useYourApiHook } from '@/hooks/useYourApiHook';

// Mock the API
vi.mock('@/api/service');

describe('useYourApiHook', () => {
  it('fetches data successfully', async () => {
    const mockData = { id: 1, name: 'Test' };
    vi.mocked(fetchData).mockResolvedValue(mockData);
    
    const { result } = renderHook(() => useYourApiHook());
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  it('handles API errors', async () => {
    vi.mocked(fetchData).mockRejectedValue(new Error('API Error'));
    
    const { result } = renderHook(() => useYourApiHook());
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeTruthy();
  });
});
```

## Key Patterns

### Standard Setup
- Use `renderHook` from `test-utils`
- Import hooks with `@` aliases
- Use `act()` for state updates

### Common Test Cases
- **Initial State**: Verify default values
- **State Updates**: Test state changes
- **Dependencies**: Test with different dependencies
- **Side Effects**: Test useEffect behavior

### With Context
- Pass context values through renderHook options
- Test both authenticated and unauthenticated states
- Use mock data from `test-utils`

### Async Hooks
- Use `waitFor()` for async operations
- Mock API dependencies with `vi.mock()`
- Test loading, success, and error states

---

**Last Updated**: March 2026

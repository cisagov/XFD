# Utility Function Test Templates

General patterns for testing utility functions in the XFD frontend application.

## Basic Utility Function Template

```tsx
import { describe, expect, it } from 'vitest';
import { yourUtilityFunction } from '@/utils/yourUtilityFunction';

describe('yourUtilityFunction', () => {
  it('returns expected result for valid input', () => {
    const input = 'test input';
    const result = yourUtilityFunction(input);
    
    expect(result).toBe('expected output');
  });

  it('handles edge cases', () => {
    expect(yourUtilityFunction('')).toBe('');
    expect(yourUtilityFunction(null)).toBe(null);
    expect(yourUtilityFunction(undefined)).toBe(undefined);
  });

  it('throws error for invalid input', () => {
    expect(() => yourUtilityFunction(123)).toThrow('Invalid input type');
  });
});
```

## Pure Function with Complex Logic

```tsx
import { describe, expect, it } from 'vitest';
import { processData } from '@/utils/dataProcessor';

describe('processData', () => {
  it('processes data correctly', () => {
    const input = { 
      items: [1, 2, 3], 
      multiplier: 2 
    };
    
    const result = processData(input);
    
    expect(result).toEqual({
      items: [2, 4, 6],
      total: 12,
      processed: true
    });
  });

  it('handles empty arrays', () => {
    const result = processData({ items: [], multiplier: 2 });
    
    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
  });

  it('validates input parameters', () => {
    expect(() => processData()).toThrow();
    expect(() => processData({})).toThrow();
  });
});
```

## Function with External Dependencies

```tsx
import { describe, expect, it, vi } from 'vitest';
import { request } from '@/api/client';
import { apiCall } from '@/utils/apiHelper';

// Mock external dependencies
vi.mock('@/api/client');

describe('apiCall', () => {
  it('makes API request with correct parameters', async () => {
    const mockRequest = vi.mocked(request);
    mockRequest.mockResolvedValue({ data: 'success' });
    
    const result = await apiCall('/endpoint', { param: 'value' });
    
    expect(mockRequest).toHaveBeenCalledWith('/endpoint', { param: 'value' });
    expect(result).toEqual({ data: 'success' });
  });

  it('handles API errors', async () => {
    const mockRequest = vi.mocked(request);
    mockRequest.mockRejectedValue(new Error('Network error'));
    
    await expect(apiCall('/endpoint')).rejects.toThrow('Network error');
  });
});
```

## Key Patterns

### Standard Setup
- Import functions with `@` aliases
- Test return values and side effects
- Mock external dependencies

### Common Test Cases
- **Valid Input**: Expected behavior with correct data
- **Edge Cases**: Empty values, boundary conditions
- **Error Handling**: Invalid input, thrown errors
- **Side Effects**: Function calls, state changes

### Pure Functions
- Focus on input/output relationships
- Test with various data combinations
- Verify no side effects

### Async Functions
- Use `async/await` or `.resolves/.rejects`
- Mock external API calls
- Test loading and error states

---

**Last Updated**: March 2026
    
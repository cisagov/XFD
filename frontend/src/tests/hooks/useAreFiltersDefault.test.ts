import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useAreFiltersDefault } from '../../hooks/useAreFiltersDefault';

// -------------------- Test Suite --------------------

describe('useAreFiltersDefault hook', () => {
  it('should return true when filters match initial filters', () => {
    const { result } = renderHook(() =>
      useAreFiltersDefault(
        [{ field: 'organization.region_id', values: ['1'], type: 'any' }],
        [{ field: 'organization.region_id', values: ['1'], type: 'any' }]
      )
    );

    expect(result.current).toBe(true);
  });

  it('should return false when filters differ', () => {
    const { result } = renderHook(() =>
      useAreFiltersDefault(
        [
          { field: 'organization.region_id', values: ['1'], type: 'any' },
          { field: 'organization_id', values: ['org-123'], type: 'any' }
        ],
        [{ field: 'organization.region_id', values: ['1'], type: 'any' }]
      )
    );

    expect(result.current).toBe(false);
  });

  it('should return false when values differ', () => {
    const { result } = renderHook(() =>
      useAreFiltersDefault(
        [{ field: 'organization.region_id', values: ['2'], type: 'any' }],
        [{ field: 'organization.region_id', values: ['1'], type: 'any' }]
      )
    );

    expect(result.current).toBe(false);
  });

  it('should return true for empty filters', () => {
    const { result } = renderHook(() => useAreFiltersDefault([], []));
    expect(result.current).toBe(true);
  });
});

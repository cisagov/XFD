import { describe, expect, it } from 'vitest';
import { isFilterModelEmpty } from '@/utils/tableUtils';

describe('isFilterModelEmpty', () => {
  it('returns true for an empty filter model', () => {
    const model = { items: [] };
    expect(isFilterModelEmpty(model)).toBe(true);
  });

  it('returns true for a filter model with an undefined values', () => {
    const model = {
      items: [{ field: 'name', operator: 'contains', value: undefined }]
    };
    expect(isFilterModelEmpty(model)).toBe(true);
  });

  it('returns true for a filter model with null values', () => {
    const model = {
      items: [{ field: 'name', operator: 'contains', value: null }]
    };
    expect(isFilterModelEmpty(model)).toBe(true);
  });

  it('returns true for a filter model with empty string values', () => {
    const model = {
      items: [{ field: 'name', operator: 'contains', value: '' }]
    };
    expect(isFilterModelEmpty(model)).toBe(true);
  });

  it('returns false for a filter model with a defined value', () => {
    const model = {
      items: [{ field: 'name', operator: 'contains', value: 'Test' }]
    };
    expect(isFilterModelEmpty(model)).toBe(false);
  });
});

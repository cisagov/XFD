import { describe, expect, it } from 'vitest';
import { getActiveItems } from '@/utils/tableUtils';

describe('getActiveItems', () => {
  it('returns only active filter items with defined, non-null, non-empty values', () => {
    const items = [
      { field: 'name', operator: 'contains', value: 'Test' },
      { field: 'severity', operator: 'equals', value: '' },
      { field: 'status', operator: 'equals', value: null },
      { field: 'type', operator: 'equals', value: undefined },
      { field: 'date', operator: 'after', value: '2024-01-01' }
    ];

    const activeItems = getActiveItems(items);
    expect(activeItems).toEqual([
      { field: 'name', operator: 'contains', value: 'Test' },
      { field: 'date', operator: 'after', value: '2024-01-01' }
    ]);
  });
});

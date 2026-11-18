import { describe, expect, it } from 'vitest';
import {
  DATA_GRID_PAGE_SIZE_OPTIONS,
  DEFAULT_DATA_GRID_PAGE_SIZE,
  SERVER_FILTER_DEBOUNCE_MS
} from '@/constants/dataGrid';

describe('Data Grid constants', () => {
  it('uses a 500 millisecond server-side filter debounce', () => {
    expect(SERVER_FILTER_DEBOUNCE_MS).toBe(500);
  });

  it('uses the shared default page size and page-size options', () => {
    expect(DEFAULT_DATA_GRID_PAGE_SIZE).toBe(15);
    expect(DATA_GRID_PAGE_SIZE_OPTIONS).toEqual([15, 30, 50, 100]);
  });
});

import { describe, expect, it } from 'vitest';
import { SERVER_FILTER_DEBOUNCE_MS } from '@/constants/dataGrid';

describe('Data Grid constants', () => {
  it('uses a 500 millisecond server-side filter debounce', () => {
    expect(SERVER_FILTER_DEBOUNCE_MS).toBe(500);
  });
});

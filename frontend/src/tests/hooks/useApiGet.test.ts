import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// mock apiGet
const mockApiGet = vi.fn();

vi.mock('context/AuthContext', () => ({
  useAuthContext: () => ({
    apiGet: mockApiGet
  })
}));

import { useApiGet } from '@/hooks/useApiGet';

describe('useApiGet', () => {
  beforeEach(() => {
    mockApiGet.mockReset();
  });

  it('returns data from apiGet', async () => {
    mockApiGet.mockResolvedValueOnce({ name: 'Acme' });

    const { result } = renderHook(() => useApiGet('/orgs'));

    await waitFor(() => {
      expect(result.current.data).toEqual({ name: 'Acme' });
    });
  });

  it('captures apiGet errors', async () => {
    mockApiGet.mockRejectedValueOnce(new Error('fail'));

    const { result } = renderHook(() => useApiGet('/bad'));

    await waitFor(() => {
      expect(result.current.error).contains('fail');
    });
  });
});

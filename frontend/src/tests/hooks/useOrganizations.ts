import { renderHook, waitFor } from '@testing-library/react';
import { vi, describe, it, beforeEach, expect } from 'vitest';
import { useOrganizations } from '@/hooks/useOrganizations';

const mockApiGet = vi.fn();

vi.mock('context/AuthContext', () => ({
  useAuthContext: () => ({
    apiGet: mockApiGet
  })
}));

describe('useOrganizations', () => {
  beforeEach(() => mockApiGet.mockReset());

  it('does nothing if regionId is null', async () => {
    renderHook(() => useOrganizations(undefined));
    expect(mockApiGet).not.toHaveBeenCalled();
  });

  it('fetches organizations for a regionId', async () => {
    mockApiGet.mockResolvedValueOnce([{ id: 1, name: 'OrgX' }]);

    const { result } = renderHook(() => useOrganizations('r1'));

    await waitFor(() => {
      expect(result.current.organizations).toEqual([{ id: 1, name: 'OrgX' }]);
      expect(result.current.error).toBe('');
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('handles errors correctly', async () => {
    mockApiGet.mockRejectedValueOnce(new Error('fail'));

    const { result } = renderHook(() => useOrganizations('r2'));

    await waitFor(() => {
      expect(result.current.error).toContain('fail');
      expect(result.current.organizations).toEqual([]);
      expect(result.current.isLoading).toBe(false);
    });
  });
});

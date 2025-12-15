import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useOrganizationsByRegion } from '@/hooks/useOrganizationsByRegion';
import type { Organization } from 'types';
import { useAuthContext } from 'context';

vi.mock('context', () => ({
  useAuthContext: vi.fn()
}));

describe('useOrganizationsByRegion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches organizations for the given region id and exposes them', async () => {
    const mockOrganizations: Organization[] = [
      { id: 'org-1', name: 'Org One', acronym: 'ONE' } as Organization
    ];

    const apiGet = vi.fn().mockResolvedValue(mockOrganizations);
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => useOrganizationsByRegion('region-1'));

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.errorMessage).toBe('');
    expect(result.current.organizations).toEqual(mockOrganizations);

    expect(apiGet).toHaveBeenCalledTimes(1);
    const [calledPath] = apiGet.mock.calls[0];
    expect(String(calledPath)).toContain('region-1');
  });

  it('does not call API when region id is null', async () => {
    const apiGet = vi.fn();
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() =>
      useOrganizationsByRegion(null as unknown as string)
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(apiGet).not.toHaveBeenCalled();
    expect(result.current.organizations).toEqual([]);
    expect(result.current.errorMessage).toBe('');
  });

  it('sets errorMessage when API call fails', async () => {
    const error = Object.assign(new Error('Request failed'), {
      response: { data: { detail: 'Something went wrong' } }
    });

    const apiGet = vi.fn().mockRejectedValue(error);
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => useOrganizationsByRegion('region-2'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.organizations).toEqual([]);
    expect(result.current.errorMessage).toContain('Request failed');
    expect(result.current.errorMessage).toContain('Something went wrong');
  });
});

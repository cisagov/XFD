import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useUpdateUser } from '@/hooks/useUpdateUser';

vi.mock('@/hooks/usePostApi', () => ({
  usePostApi: vi.fn()
}));

import * as postApiModule from '@/hooks/usePostApi';

describe('useUpdateUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Verifies the hook calls the update endpoint with the correct user id
   * and passes the provided body as the request payload.
   */
  it('calls the correct endpoint with the provided body', async () => {
    const mockPostApi = vi.fn().mockResolvedValue(undefined);

    // usePostApi is a vi.fn() because of the vi.mock above
    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useUpdateUser());

    const body = {
      first_name: 'Jane',
      last_name: 'Doe',
      state: 'VA',
      region_id: '1',
      user_type: 'standard'
    };

    await act(async () => {
      await result.current.updateUser(123, body);
    });

    expect(mockPostApi).toHaveBeenCalledTimes(1);

    const [calledPath, calledInit] = mockPostApi.mock.calls[0];

    expect(String(calledPath)).toContain('/123');
    expect(calledInit.body).toEqual(body);
  });

  /**
   * Verifies the hook does not swallow errors and re-throws failures
   * from the underlying post request.
   */
  it('propagates errors from postApi', async () => {
    const error = new Error('Request failed');
    const mockPostApi = vi.fn().mockRejectedValue(error);

    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useUpdateUser());

    await expect(
      result.current.updateUser(456, {
        first_name: 'John',
        last_name: 'Smith',
        state: 'CA',
        region_id: '2'
      })
    ).rejects.toThrow('Request failed');
  });
});

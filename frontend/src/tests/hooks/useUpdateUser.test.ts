import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
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
   * and passes the context headers and matching payload cleanly.
   */
  it('calls the correct endpoint with the provided body and headers', async () => {
    const mockPostApi = vi.fn().mockResolvedValue(undefined);
    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useUpdateUser());

    const userPayload = {
      first_name: 'Jane',
      last_name: 'Doe',
      state: 'VA',
      region_id: '1',
      user_type: 'standard'
    };

    let errorThrown = null;
    try {
      await result.current.updateUser({
        userId: '123',
        origin_path: 'user-management',
        body: userPayload
      });
    } catch (err) {
      errorThrown = err;
    }

    // Ensure it ran without throwing any unexpected errors
    expect(errorThrown).toBeNull();
    expect(mockPostApi).toHaveBeenCalledTimes(1);

    const [calledPath, calledInit] = mockPostApi.mock.calls[0];

    // Verifies path and body separation
    expect(String(calledPath)).toContain('/123');
    expect(calledInit.body).toEqual(userPayload);

    expect(calledInit.headers).toEqual({
      'X-Origin-Path': 'user-management'
    });
  });

  /**
   * Verifies the hook bubbles up underlying network errors to the caller.
   */
  it('bubbles up errors thrown by postApi', async () => {
    const error = new Error('Request failed');
    const mockPostApi = vi.fn().mockRejectedValue(error);
    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useUpdateUser());

    let errorThrown: any = null;
    try {
      await result.current.updateUser({
        userId: '456',
        origin_path: 'user-registration',
        body: {
          first_name: 'John',
          last_name: 'Smith',
          state: 'CA',
          region_id: '2'
        }
      });
    } catch (err) {
      errorThrown = err;
    }
    // Verify that the error was thrown and matches the backend failure message
    expect(errorThrown).toBeInstanceOf(Error);
    expect(errorThrown.message).toBe('Request failed');
  });
});

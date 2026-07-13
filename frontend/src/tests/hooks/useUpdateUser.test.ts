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

    let response;
    await act(async () => {
      response = await result.current.updateUser({
        userId: '123',
        origin_path: 'user-management',
        body: userPayload
      });
    });

    expect(mockPostApi).toHaveBeenCalledTimes(1);

    const [calledPath, calledInit] = mockPostApi.mock.calls[0];

    // Verifies path and body separation
    expect(String(calledPath)).toContain('/123');
    expect(calledInit.body).toEqual(userPayload);

    expect(calledInit.headers).toEqual({
      'X-Origin-Path': 'user-management'
    });

    expect(response).toEqual({
      success: true,
      body: 'User profile successfully updated.'
    });
  });

  /**
   * Verifies the hook catches underlying network errors and
   * returns a failed object state instead of throwing.
   */
  it('gracefully handles and returns errors from postApi', async () => {
    const error = new Error('Request failed');
    const mockPostApi = vi.fn().mockRejectedValue(error);
    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useUpdateUser());

    let response;
    await act(async () => {
      response = await result.current.updateUser({
        userId: '456',
        origin_path: 'user-registration',
        body: {
          first_name: 'John',
          last_name: 'Smith',
          state: 'CA',
          region_id: '2'
        }
      });
    });

    expect(response).toEqual({
      success: false,
      body: 'Request failed'
    });
  });
});

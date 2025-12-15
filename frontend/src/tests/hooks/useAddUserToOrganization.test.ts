import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAddUserToOrganization } from '@/hooks/useAddUserToOrganization';

vi.mock('@/hooks/usePostApi', () => ({
  usePostApi: vi.fn()
}));

import * as postApiModule from '@/hooks/usePostApi';

describe('useAddUserToOrganization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls the correct endpoint with organization id, user id, and role', async () => {
    const mockPostApi = vi.fn().mockResolvedValue(undefined);
    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useAddUserToOrganization());

    const organizationId = 'org-123';
    const userId = 456;
    const role = 'user';

    await act(async () => {
      await result.current.addUserToOrganization(organizationId, userId, role);
    });

    expect(mockPostApi).toHaveBeenCalledTimes(1);
    const [calledPath, calledInit] = mockPostApi.mock.calls[0];

    expect(String(calledPath)).toContain(organizationId);
    expect(calledInit.body).toEqual({
      user_id: userId,
      role
    });
  });

  it('propagates errors from postApi', async () => {
    const error = new Error('Add user failed');
    const mockPostApi = vi.fn().mockRejectedValue(error);
    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useAddUserToOrganization());

    await expect(
      result.current.addUserToOrganization('org-999', 999, 'admin')
    ).rejects.toThrow('Add user failed');
  });
});

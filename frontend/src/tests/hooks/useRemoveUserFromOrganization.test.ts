import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRemoveUserFromOrganization } from '@/hooks/useRemoveUserFromOrganization';

vi.mock('@/hooks/usePostApi', () => ({
  usePostApi: vi.fn()
}));

import * as postApiModule from '@/hooks/usePostApi';

describe('useRemoveUserFromOrganization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls the correct endpoint with organization id and role id', async () => {
    const mockPostApi = vi.fn().mockResolvedValue(undefined);
    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useRemoveUserFromOrganization());

    const organizationId = 'org-123';
    const roleId = 'role-456';

    await act(async () => {
      await result.current.removeUserFromOrganization(organizationId, roleId);
    });

    expect(mockPostApi).toHaveBeenCalledTimes(1);
    const [calledPath, calledInit] = mockPostApi.mock.calls[0];

    expect(String(calledPath)).toContain(organizationId);
    expect(String(calledPath)).toContain(roleId);
    expect(calledInit.body).toEqual({});
  });

  it('propagates errors from postApi', async () => {
    const error = new Error('Remove user failed');
    const mockPostApi = vi.fn().mockRejectedValue(error);
    vi.mocked(postApiModule.usePostApi).mockReturnValue(mockPostApi);

    const { result } = renderHook(() => useRemoveUserFromOrganization());

    await expect(
      result.current.removeUserFromOrganization('org-999', 'role-999')
    ).rejects.toThrow('Remove user failed');
  });
});

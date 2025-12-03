import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, beforeEach, expect } from 'vitest';
import { useUpdateUser } from '@/hooks/useUpdateUser';
import { ENDPOINTS } from '@/constants/endpoints';

const mockApiPost = vi.fn();

vi.mock('context/AuthContext', () => ({
  useAuthContext: () => ({
    apiPost: mockApiPost
  })
}));

describe('useUpdateUser', () => {
  beforeEach(() => mockApiPost.mockReset());

  it('calls apiPost with correct endpoint and body', async () => {
    mockApiPost.mockResolvedValueOnce({ success: true });

    const { result } = renderHook(() => useUpdateUser());

    let response;
    await act(async () => {
      response = await result.current.updateUser('42', { first_name: 'Alice' });
    });

    expect(mockApiPost).toHaveBeenCalledWith(
      ENDPOINTS.USER_UPDATE_V2.replace('{user_id}', '42'),
      { body: { first_name: 'Alice' } }
    );

    expect(response).toEqual({ success: true });
  });

  it('propagates errors', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('boom'));

    const { result } = renderHook(() => useUpdateUser());

    await act(async () => {
      await expect(result.current.updateUser('99', {})).rejects.toThrow('boom');
    });
  });
});

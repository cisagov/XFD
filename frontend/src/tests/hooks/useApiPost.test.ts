import { renderHook, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockApiPost = vi.fn();

vi.mock('context/AuthContext', () => ({
  useAuthContext: () => ({
    apiPost: mockApiPost
  })
}));

import { useApiPost } from '@/hooks/useApiPost';

describe('useApiPost', () => {
  beforeEach(() => mockApiPost.mockReset());

  it('calls apiPost and returns data', async () => {
    mockApiPost.mockResolvedValueOnce({ ok: true });

    const { result } = renderHook(() => useApiPost());

    let response;
    await act(async () => {
      response = await result.current.postData('/save', { body: 123 });
    });

    expect(mockApiPost).toHaveBeenCalledWith('/save', { body: 123 });
    expect(response).toEqual({ ok: true });
  });

  it('handles post errors', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('nope'));

    const { result } = renderHook(() => useApiPost());

    await act(async () => {
      await expect(result.current.postData('/err', {})).rejects.toThrow('nope');
    });

    // you can also assert that the error state inside the hook updated
    expect(result.current.error).toContain('nope');
  });
});

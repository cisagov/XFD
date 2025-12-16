import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

import { usePostApi } from '@/hooks/usePostApi';
import { useAuthContext } from 'context';

vi.mock('context', () => ({
  useAuthContext: vi.fn()
}));

describe('usePostApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Verifies the hook calls apiPost with the provided path + init options
   * and returns the resolved response.
   */
  it('calls apiPost with the provided path and init and returns the result', async () => {
    const apiPost = vi.fn().mockResolvedValue({ id: '123' });
    vi.mocked(useAuthContext).mockReturnValue({
      apiPost
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => usePostApi());

    const payload = { name: 'Jane' };
    const response = await result.current<{ id: string }>('/test/path', {
      body: payload,
      showLoading: true,
      headers: { 'content-type': 'application/json' }
    });

    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(apiPost).toHaveBeenCalledWith('/test/path', {
      body: payload,
      showLoading: true,
      headers: { 'content-type': 'application/json' }
    });
    expect(response).toEqual({ id: '123' });
  });

  /**
   * Verifies the hook passes an empty init object to apiPost when init is omitted.
   */
  it('uses an empty init object when none is provided', async () => {
    const apiPost = vi.fn().mockResolvedValue('ok');
    vi.mocked(useAuthContext).mockReturnValue({
      apiPost
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => usePostApi());

    const response = await result.current<string>('/test/path');

    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(apiPost).toHaveBeenCalledWith('/test/path', {});
    expect(response).toBe('ok');
  });

  /**
   * Verifies errors from apiPost are not swallowed and bubble up to the caller.
   */
  it('propagates errors from apiPost', async () => {
    const error = new Error('Post failed');
    const apiPost = vi.fn().mockRejectedValue(error);
    vi.mocked(useAuthContext).mockReturnValue({
      apiPost
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => usePostApi());

    await expect(result.current('/test/path')).rejects.toThrow('Post failed');
  });
});

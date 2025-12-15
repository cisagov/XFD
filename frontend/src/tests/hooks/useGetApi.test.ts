import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

import { useGetApi } from '@/hooks/useGetApi';
import { useAuthContext } from 'context';

vi.mock('context', () => ({
  useAuthContext: vi.fn()
}));

describe('useGetApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls apiGet with the provided path and init and returns the result', async () => {
    const apiGet = vi.fn().mockResolvedValue({ ok: true });
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => useGetApi());

    const response = await result.current<{ ok: boolean }>('/test/path', {
      showLoading: true,
      headers: { 'x-test': '1' }
    });

    expect(apiGet).toHaveBeenCalledTimes(1);
    expect(apiGet).toHaveBeenCalledWith('/test/path', {
      showLoading: true,
      headers: { 'x-test': '1' }
    });
    expect(response).toEqual({ ok: true });
  });

  it('uses an empty init object when none is provided', async () => {
    const apiGet = vi.fn().mockResolvedValue('value');
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => useGetApi());

    const response = await result.current<string>('/test/path');

    expect(apiGet).toHaveBeenCalledTimes(1);
    expect(apiGet).toHaveBeenCalledWith('/test/path', {});
    expect(response).toBe('value');
  });

  it('propagates errors from apiGet', async () => {
    const error = new Error('Request failed');
    const apiGet = vi.fn().mockRejectedValue(error);
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => useGetApi());

    await expect(result.current('/test/path')).rejects.toThrow(
      'Request failed'
    );
  });
});

// useApi.test.ts
import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useApi } from '@/hooks';
import { API } from 'aws-amplify';

vi.mock('aws-amplify', () => ({
  API: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn()
  }
}));

describe('useApi Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    document.cookie =
      'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
  });

  it('should include credentials and base headers in all requests', async () => {
    const { result } = renderHook(() => useApi());

    (API.get as any).mockResolvedValue({ success: true });

    await act(async () => {
      result.current.apiGet('/test-path');
    });

    const [apiName, path, init] = (API.get as any).mock.calls[0];

    expect(apiName).toBe('crossfeed');
    expect(path).toBe('/test-path');
    expect(init.credentials).toBe('include');
    expect(init.withCredentials).toBe(true);
    expect(init.headers['Content-Type']).toBe('application/json');
  });

  it('should NOT add x-csrf-token to GET requests even if cookie exists', async () => {
    document.cookie = 'csrf_token=secret-signature-123';

    const { result } = renderHook(() => useApi());
    (API.get as any).mockResolvedValue({});

    await act(async () => {
      result.current.apiGet('/test-path');
    });

    const init = (API.get as any).mock.calls[0][2];
    expect(init.headers['x-csrf-token']).toBeUndefined();
  });

  it('should add x-csrf-token to POST requests when cookie is present', async () => {
    document.cookie = 'csrf_token=secret-signature-123';

    const { result } = renderHook(() => useApi());
    (API.post as any).mockResolvedValue({});

    await act(async () => {
      result.current.apiPost('/update-data', { body: { key: 'value' } });
    });

    const init = (API.post as any).mock.calls[0][2];
    expect(init.headers['x-csrf-token']).toBe('secret-signature-123');
  });

  it('should track loading state correctly', async () => {
    let resolveRequest: any;
    const promise = new Promise((resolve) => {
      resolveRequest = resolve;
    });
    (API.get as any).mockReturnValue(promise);

    const { result } = renderHook(() => useApi());

    expect(result.current.loading).toBe(false);

    let apiCall: any;

    await act(async () => {
      apiCall = result.current.apiGet('/loading-test');
    });

    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolveRequest({});
      await apiCall;
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  it('should call onError callback when a 401 error occurs', async () => {
    const onError = vi.fn();
    const error401 = { response: { status: 401 }, message: 'Unauthorized' };
    (API.get as any).mockRejectedValue(error401);

    const { result } = renderHook(() => useApi(onError));

    await act(async () => {
      try {
        await result.current.apiGet('/private');
        throw new Error('Hook should have thrown an error but did not');
      } catch (e: any) {
        expect(e.message).toBe('Unauthorized');
        expect(e.response.status).toBe(401);
      }
    });

    expect(onError).toHaveBeenCalledWith(error401);
    expect(onError).toHaveBeenCalledWith(error401);
    expect(result.current.loading).toBe(false);
  });
});

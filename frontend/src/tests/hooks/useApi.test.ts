import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const jsonResponse = (body: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init
  });

describe('useApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    global.fetch = vi.fn();

    Object.defineProperty(global.navigator, 'sendBeacon', {
      value: vi.fn(),
      writable: true,
      configurable: true
    });
  });

  it('sends GET requests with the stored bearer token and custom headers', async () => {
    localStorage.setItem('token', JSON.stringify('test-token'));
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse({ id: 'user-1' })
    );

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    let response: object | undefined;
    await act(async () => {
      response = await result.current.apiGet('/users/me', {
        headers: { 'X-Test-Header': 'test-value' }
      });
    });
    expect(response).toEqual({ id: 'user-1' });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/users\/me$/),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Accept: 'application/json',
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
          'X-Test-Header': 'test-value'
        })
      })
    );
  });

  it.each([
    ['apiPost', 'POST'],
    ['apiDelete', 'DELETE']
  ] as const)('serializes JSON bodies for %s', async (apiMethod, method) => {
    vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await act(async () => {
      await result.current[apiMethod]('/items', {
        body: { name: 'example' }
      });
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/items$/),
      expect.objectContaining({
        method,
        body: JSON.stringify({ name: 'example' })
      })
    );
  });

  it('returns blob data and response headers when requested', async () => {
    const csv = new Blob(['name\nexample'], { type: 'text/csv' });
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(csv, {
        headers: { 'Content-Disposition': 'attachment; filename="data.csv"' }
      })
    );

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    let response!: { data: Blob; headers: Record<string, string> };
    await act(async () => {
      response = await result.current.apiGet('/export', {
        response: true,
        responseType: 'blob',
        withCredentials: true
      });
    });

    expect(response.data.size).toBeGreaterThan(0);
    expect(response.headers['content-disposition']).toBe(
      'attachment; filename="data.csv"'
    );
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/export$/),
      expect.objectContaining({ credentials: 'include' })
    );
  });

  it('rejects non-success responses with the compatible error shape', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse(
        { detail: 'Not allowed' },
        {
          status: 403,
          headers: { 'x-amzn-requestid': 'request-id' }
        }
      )
    );

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    let error: any;
    await act(async () => {
      error = await result.current.apiGet('/restricted').catch((e) => e);
    });

    expect(error).toMatchObject({
      message: 'Not allowed',
      statusCode: 403,
      body: { detail: 'Not allowed' },
      response: { status: 403 }
    });
    expect(error.response.headers.get('x-amzn-requestid')).toBe('request-id');
  });

  it('normalizes message-only authentication errors and calls onError', async () => {
    const onError = vi.fn().mockResolvedValue(undefined);
    vi.mocked(global.fetch).mockRejectedValueOnce(
      new Error('JWT expired while validating request')
    );

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi(onError));

    let error: any;
    await act(async () => {
      try {
        await result.current.apiGet('/users/me');
      } catch (e) {
        error = e;
      }
    });

    expect(error).toMatchObject({
      message: 'JWT expired while validating request',
      statusCode: 401,
      response: { status: 401 }
    });

    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        statusCode: 401,
        response: { status: 401 }
      })
    );
  });

  it('tracks loading while a request is pending', async () => {
    let resolveRequest!: (response: Response) => void;
    vi.mocked(global.fetch).mockReturnValueOnce(
      new Promise<Response>((resolve) => {
        resolveRequest = resolve;
      })
    );

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    let request!: Promise<object>;
    act(() => {
      request = result.current.apiGet('/slow');
    });
    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolveRequest(jsonResponse({ done: true }));
      await request;
    });
    expect(result.current.loading).toBe(false);
  });
});

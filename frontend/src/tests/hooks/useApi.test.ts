import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, isApiError } from '../../hooks/useApi';
import type { ApiResponse } from '../../hooks/useApi';
import { jsonResponse } from '../../test-utils/jsonResponse';

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

    let response: { id: string } | undefined;

    await act(async () => {
      response = await result.current.apiGet<{ id: string }>('/users/me', {
        headers: { 'X-Test-Header': 'test-value' }
      });
    });
    expect(response).toEqual({ id: 'user-1' });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
      RequestInfo | URL,
      RequestInit
    ];

    expect(url).toEqual(expect.stringMatching(/\/users\/me$/));
    expect(options.method).toBe('GET');

    const headers = new Headers(options.headers);
    expect(headers.get('Accept')).toBe('application/json');
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.get('Authorization')).toBe('Bearer test-token');
    expect(headers.get('X-Test-Header')).toBe('test-value');
  });

  it.each([
    ['apiPost', 'POST'],
    ['apiDelete', 'DELETE']
  ] as const)('serializes JSON bodies for %s', async (apiMethod, method) => {
    vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await act(async () => {
      await result.current[apiMethod]<{ ok: boolean }>('/items', {
        body: { name: 'example' }
      });
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
      RequestInfo | URL,
      RequestInit
    ];
    expect(url).toEqual(expect.stringMatching(/\/items$/));
    expect(options.method).toBe(method);
    expect(options.body).toBe(JSON.stringify({ name: 'example' }));

    const headers = new Headers(options.headers);
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.get('Accept')).toBe('application/json');
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

    let apiResponse!: ApiResponse<Blob>;

    await act(async () => {
      apiResponse = await result.current.apiGet<Blob>('/export', {
        includeResponse: true,
        parseAs: 'blob',
        credentials: 'include'
      });
    });

    expect(apiResponse.data.size).toBeGreaterThan(0);
    expect(apiResponse.headers['content-disposition']).toBe(
      'attachment; filename="data.csv"'
    );
    expect(apiResponse.response).toBeInstanceOf(Response);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/export$/),
      expect.objectContaining({ credentials: 'include' })
    );
  });

  it('throws an ApiError for 401 responses', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse(
        { detail: 'Unauthorized' },
        {
          status: 401,
          statusText: 'Unauthorized',
          headers: { 'x-amzn-requestid': 'request-id' }
        }
      )
    );

    const onError = vi.fn();
    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi(onError));

    await act(async () => {
      await expect(result.current.apiGet('/protected')).rejects.toMatchObject({
        isApiError: true,
        name: 'ApiError',
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        message: 'Unauthorized',
        headers: { 'x-amzn-requestid': 'request-id' },
        payload: { detail: 'Unauthorized' },
        payloadMessage: 'Unauthorized',
        bodyUsed: true
      });
    });

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        status: 401,
        statusText: 'Unauthorized'
      })
    );
    const errorArg = onError.mock.calls[0][0];
    expect(errorArg).toBeInstanceOf(ApiError);
    expect(isApiError(errorArg)).toBe(true);

    if (isApiError(errorArg)) {
      expect(errorArg.status).toBe(401);
      expect(errorArg.statusText).toBe('Unauthorized');
      expect(errorArg.message).toBe('Unauthorized');
      expect(errorArg.headers['x-amzn-requestid']).toBe('request-id');
      expect(errorArg.payload).toEqual({ detail: 'Unauthorized' });
      expect(errorArg.payloadMessage).toBe('Unauthorized');
    }
  });

  it('throws an ApiError for 403 responses', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse(
        { detail: 'Not allowed' },
        {
          status: 403,
          statusText: 'Forbidden',
          headers: { 'x-amzn-requestid': 'request-id' }
        }
      )
    );

    const onError = vi.fn();
    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi(onError));

    await act(async () => {
      await expect(result.current.apiGet('/restricted')).rejects.toMatchObject({
        isApiError: true,
        name: 'ApiError',
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        message: 'Not allowed',
        headers: { 'x-amzn-requestid': 'request-id' },
        payload: { detail: 'Not allowed' },
        payloadMessage: 'Not allowed',
        bodyUsed: true
      });
    });

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        status: 403,
        statusText: 'Forbidden'
      })
    );
    const errorArg = onError.mock.calls[0][0];
    expect(errorArg).toBeInstanceOf(ApiError);
    expect(isApiError(errorArg)).toBe(true);

    if (isApiError(errorArg)) {
      expect(errorArg.status).toBe(403);
      expect(errorArg.statusText).toBe('Forbidden');
      expect(errorArg.message).toBe('Not allowed');
      expect(errorArg.headers['x-amzn-requestid']).toBe('request-id');
      expect(errorArg.payload).toEqual({ detail: 'Not allowed' });
      expect(errorArg.payloadMessage).toBe('Not allowed');
    }
  });

  it('throws an ApiError for 404 responses', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse(
        { detail: 'Not found' },
        {
          status: 404,
          statusText: 'Not Found',
          headers: { 'x-amzn-requestid': 'request-id' }
        }
      )
    );

    const onError = vi.fn();
    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi(onError));

    await act(async () => {
      await expect(result.current.apiGet('/nonexistent')).rejects.toMatchObject(
        {
          isApiError: true,
          name: 'ApiError',
          ok: false,
          status: 404,
          statusText: 'Not Found',
          message: 'Not found',
          headers: { 'x-amzn-requestid': 'request-id' },
          payload: { detail: 'Not found' },
          payloadMessage: 'Not found',
          bodyUsed: true
        }
      );
    });

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        status: 404,
        statusText: 'Not Found'
      })
    );
    const errorArg = onError.mock.calls[0][0];
    expect(errorArg).toBeInstanceOf(ApiError);
    expect(isApiError(errorArg)).toBe(true);

    if (isApiError(errorArg)) {
      expect(errorArg.status).toBe(404);
      expect(errorArg.statusText).toBe('Not Found');
      expect(errorArg.message).toBe('Not found');
      expect(errorArg.headers['x-amzn-requestid']).toBe('request-id');
      expect(errorArg.payload).toEqual({ detail: 'Not found' });
      expect(errorArg.payloadMessage).toBe('Not found');
    }
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

  it('does not convert network failures into ApiError', async () => {
    vi.mocked(global.fetch).mockRejectedValueOnce(
      new TypeError('Network failure')
    );

    const onError = vi.fn().mockResolvedValue(undefined);
    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi(onError));

    await expect(result.current.apiGet('/network-failure')).rejects.toThrow(
      'Network failure'
    );

    expect(onError).toHaveBeenCalledTimes(1);
  });

  describe('ApiError', () => {
    it('extends Error and exposes fetch response fields', () => {
      const response = jsonResponse(
        { detail: 'Not allowed' },
        {
          status: 403,
          statusText: 'Forbidden',
          headers: {
            'x-amzn-requestid': 'request-id'
          }
        }
      );
      const error = new ApiError(response, { detail: 'Not allowed' });

      expect(error).toBeInstanceOf(Error);
      expect(error.isApiError).toBe(true);
      expect(error.name).toBe('ApiError');
      expect(error.ok).toBe(false);
      expect(error.status).toBe(403);
      expect(error.statusText).toBe('Forbidden');
      expect(error.message).toBe('Not allowed');
      expect(error.headers['x-amzn-requestid']).toBe('request-id');
      expect(error.payload).toEqual({ detail: 'Not allowed' });
      expect(error.payloadMessage).toBe('Not allowed');
      expect(error.bodyUsed).toBe(false);
    });

    it('uses explicit constructor message before payload detail', () => {
      const response = jsonResponse(
        { detail: 'Not allowed' },
        { status: 403, statusText: 'Forbidden' }
      );
      const error = new ApiError(
        response,
        { detail: 'Not allowed' },
        'Custom message'
      );

      expect(error.message).toBe('Custom message');
      expect(error.payload).toEqual({ detail: 'Not allowed' });
    });

    it('uses payload.message when payload.detail is absent', () => {
      const response = jsonResponse(
        { message: 'Not allowed' },
        { status: 403, statusText: 'Forbidden' }
      );
      const error = new ApiError(response, { message: 'Not allowed' });

      expect(error.message).toBe('Not allowed');
      expect(error.payload).toEqual({ message: 'Not allowed' });
    });

    it('uses payload.detail when both payload.detail and payload.message are present', () => {
      const response = jsonResponse(
        { detail: 'Not allowed', message: 'This should be ignored' },
        { status: 403, statusText: 'Forbidden' }
      );
      const error = new ApiError(response, {
        detail: 'Not allowed',
        message: 'This should be ignored'
      });

      expect(error.message).toBe('Not allowed');
      expect(error.payload).toEqual({
        detail: 'Not allowed',
        message: 'This should be ignored'
      });
    });

    it('uses payload.error when detail and message are absent', () => {
      const response = jsonResponse(
        { error: 'Unexpected backend error' },
        { status: 500, statusText: 'Internal Server Error' }
      );
      const error = new ApiError(response, {
        error: 'Unexpected backend error'
      });

      expect(error.message).toBe('Unexpected backend error');
      expect(error.payload).toEqual({ error: 'Unexpected backend error' });
    });

    it('falls back to statusText when no detail, message, or error is present', () => {
      const response = jsonResponse(
        { code: 'SOME_ERROR' },
        { status: 404, statusText: 'Not Found' }
      );
      const error = new ApiError(response, { code: 'SOME_ERROR' });

      expect(error.message).toBe('Not Found');
      expect(error.payloadMessage).toBeUndefined();
    });

    it('falls back to generic status message when statusText is empty', () => {
      const response = jsonResponse({}, { status: 500, statusText: '' });
      const error = new ApiError(response);

      expect(error.message).toBe('Request failed with status 500');
      expect(error.payloadMessage).toBeUndefined();
    });

    it('is an instance of ApiError', () => {
      const response = jsonResponse(
        { detail: 'Not allowed' },
        { status: 403, statusText: 'Forbidden' }
      );
      const error = new ApiError(response, { detail: 'Not allowed' });

      expect(error).toBeInstanceOf(ApiError);
    });

    it('is recognized by isApiError', () => {
      const response = jsonResponse(
        { detail: 'Unauthorized' },
        { status: 401, statusText: 'Unauthorized' }
      );
      const error = new ApiError(response, { detail: 'Unauthorized' });

      expect(isApiError(error)).toBe(true);
      expect(isApiError(new Error('plain error'))).toBe(false);
      expect(isApiError(null)).toBe(false);
      expect(isApiError(undefined)).toBe(false);
    });
  });
});

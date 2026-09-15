import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, isApiError } from '../../hooks/useApi';

// const jsonResponse = (body: unknown, init: ResponseInit = {}) =>
//   new Response(JSON.stringify(body), {
//     status: 200,
//     headers: { 'Content-Type': 'application/json' },
//     ...init
//   });

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    statusText: init.statusText,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers as Record<string, string> | undefined)
    }
  });
}

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

  it('throws an ApiError for non-ok responses(200-299)', async () => {
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
        detail: 'Not allowed',
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
      expect(errorArg.detail).toBe('Not allowed');
    }
  });

  // it('normalizes message-only authentication errors and calls onError', async () => {
  //   const onError = vi.fn().mockResolvedValue(undefined);
  //   vi.mocked(global.fetch).mockRejectedValueOnce(
  //     new Error('JWT expired while validating request')
  //   );

  //   const { useApi } = await import('../../hooks/useApi');
  //   const { result } = renderHook(() => useApi(onError));

  //   let error: any;
  //   await act(async () => {
  //     try {
  //       await result.current.apiGet('/users/me');
  //     } catch (e) {
  //       error = e;
  //     }
  //   });

  //   expect(error).toMatchObject({
  //     message: 'JWT expired while validating request',
  //     status: 401,
  //     payload: { detail: 'JWT expired while validating request' },
  //     detail: 'JWT expired while validating request',
  //   });

  //   expect(onError).toHaveBeenCalledWith(
  //     expect.objectContaining({
  //       status: 401,
  //       response: { status: 401 }
  //     })
  //   );
  // });

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
      expect(error.detail).toBe('Not allowed');
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
      expect(error.detail).toBeUndefined();
    });

    it('falls back to generic status message when statusText is empty', () => {
      const response = jsonResponse({}, { status: 500, statusText: '' });
      const error = new ApiError(response);

      expect(error.message).toBe('Request failed with status 500');
      expect(error.detail).toBeUndefined();
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

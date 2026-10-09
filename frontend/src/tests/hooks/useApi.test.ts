import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, isApiError, parseResponse } from '../../hooks/useApi';
import type { ApiResult } from '../../hooks/useApi';
import { jsonResponse } from '../../test-utils/jsonResponse';

/**
 * Tests for the useApi hook.
 */

/**
 * jsonResponse utility function for creating mock JSON responses in tests.
 * Automatically sets the 'Content-Type' header to 'application/json' and serializes the body to JSON.
 */

describe('useApi hook tests', () => {
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
    expect(options.body).toBeUndefined();

    const headers = new Headers(options.headers);

    expect(headers.get('Accept')).toBe('application/json');
    expect(headers.get('Content-Type')).toBeNull();
    expect(headers.get('Authorization')).toBe('Bearer test-token');
    expect(headers.get('X-Test-Header')).toBe('test-value');
  });

  it('does not include a body for GET requests', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse([]));

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await act(async () => {
      await result.current.apiGet<{ id: string; name: string }>('/items');
    });

    const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
      RequestInfo | URL,
      RequestInit
    ];
    expect(options.body).toBeUndefined();
  });

  it.each([
    ['apiPost', 'POST'],
    ['apiDelete', 'DELETE']
  ] as const)('serializes JSON bodies for %s', async (apiMethod, method) => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse({ id: '1', name: 'new item' })
    );

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await act(async () => {
      await result.current[apiMethod]<{ ok: boolean }>('/items', {
        body: { name: 'new item' }
      });
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
      RequestInfo | URL,
      RequestInit
    ];
    expect(url).toEqual(expect.stringMatching(/\/items$/));
    expect(options.method).toBe(method);
    expect(options.body).toBe(JSON.stringify({ name: 'new item' }));

    const headers = new Headers(options.headers);
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.get('Accept')).toBe('application/json');
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

  describe('Response Parsing Hook Level Tests', () => {
    it('returns valid JSON from a successful response', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(
        jsonResponse({ name: 'John Doe', id: 1 })
      );

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      let response: unknown;

      await act(async () => {
        response = await result.current.apiGet<{
          name: string;
          id: number;
        }>('/users');
        expect(response).toEqual({ name: 'John Doe', id: 1 });
      });
    });

    it('returns undefined for a 200 response with all whitespace body', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response('   ', { status: 200 })
      );
      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      let response: unknown;

      await act(async () => {
        response = await result.current.apiGet<undefined>('/items');
      });
      expect(response).toBeUndefined();
    });

    it('returns undefined for when a 200 response with an empty body', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse(undefined));
      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      let response: unknown;

      await act(async () => {
        response = await result.current.apiGet<undefined>('/items');
      });
      expect(response).toBeUndefined();
    });

    it('returns undefined for a 204 No Content response', async () => {
      // Simulate a 204 No Content response with no body
      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response(null, { status: 204 })
      );
      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      let response: unknown;

      await act(async () => {
        response = await result.current.apiGet<undefined>('/items');
      });
      expect(response).toBeUndefined();
    });

    it('returns undefined for a 205 Reset Content response', async () => {
      // Simulate a 205 Reset Content response with no body
      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response(null, { status: 205 })
      );
      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      let response: unknown;

      await act(async () => {
        response = await result.current.apiGet<undefined>('/items');
      });
      expect(response).toBeUndefined();
    });

    it('throws for malformed non-empty successful JSON responses', async () => {
      // Simulate a malformed JSON response with a 200 status code
      // jsonResponse would not work here because it automatically stringifies the body, which would not produce a malformed JSON.
      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response('{"malformed": "json"', {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        })
      );

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await act(async () => {
        await expect(result.current.apiGet('/items')).rejects.toThrow();
      });
    });

    it('returns undefined for a 200 response with parseAs "none" set', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response('{"key": "value"}', { status: 200 })
      );
      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      let response: unknown;

      await act(async () => {
        response = await result.current.apiGet<undefined>('/items', {
          parseAs: 'none'
        });
      });
      expect(response).toBeUndefined();
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

      let apiResponse!: ApiResult<Blob>;

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
      expect(apiResponse.rawResponse).toBeInstanceOf(Response);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/export$/),
        expect.objectContaining({ credentials: 'include' })
      );
    });
  });

  describe('Error Response Parsing Hook Level Tests', () => {
    it('throws ApiError with a JSON payload for a non-OK blob request', async () => {
      vi.mocked(global.fetch).mockResolvedValue(
        jsonResponse(
          { detail: 'Session expired' },
          {
            status: 401,
            statusText: 'Unauthorized',
            headers: { 'x-amzn-requestid': 'some-request-id' }
          }
        )
      );

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await expect(
        result.current.apiGet('/some-blob-endpoint', { parseAs: 'blob' })
      ).rejects.toMatchObject({
        isApiError: true,
        status: 401,
        payload: { detail: 'Session expired' },
        payloadMessage: 'Session expired',
        message: 'Session expired'
      });
    });

    it('throws ApiError with a JSON payload for a non-OK FormData request', async () => {
      vi.mocked(global.fetch).mockResolvedValue(
        jsonResponse(
          {
            detail: 'The uploaded file exceeds the 10mb limit'
          },
          { status: 400, statusText: 'Bad Request' }
        )
      );

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await expect(
        result.current.apiPost('/documents/upload', {
          body: new FormData(),
          parseAs: 'formData'
        })
      ).rejects.toMatchObject({
        isApiError: true,
        status: 400,
        payload: { detail: 'The uploaded file exceeds the 10mb limit' },
        payloadMessage: 'The uploaded file exceeds the 10mb limit',
        message: 'The uploaded file exceeds the 10mb limit'
      });
    });

    it('returns error fallback message when the error body cannot be read', async () => {
      const response = new Response('Invalid JSON', {
        status: 500,
        statusText: 'Internal Server Error'
      });

      vi.spyOn(response, 'text').mockRejectedValue(
        new TypeError('Failed to read response body')
      );
      vi.mocked(global.fetch).mockResolvedValue(response);

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await expect(
        result.current.apiGet('/some-endpoint', { parseAs: 'json' })
      ).rejects.toMatchObject({
        isApiError: true,
        status: 500,
        payload: {
          detail:
            'The request failed, but the server error message could not be read.'
        },
        payloadMessage:
          'The request failed, but the server error message could not be read.',
        message:
          'The request failed, but the server error message could not be read.'
      });
    });
  });

  describe('Header Handling', () => {
    it('sets the correct headers for JSON requests', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await act(async () => {
        await result.current.apiPost<{ ok: boolean }>('/items', {
          body: { name: 'example' }
        });
      });

      const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
        RequestInfo | URL,
        RequestInit
      ];
      const headers = new Headers(options.headers);
      expect(headers.get('Content-Type')).toBe('application/json');
      expect(headers.get('Accept')).toBe('application/json');
    });

    it('sets the correct headers for Blob requests if the blob has a type', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

      const body = new Blob(['test'], { type: 'text/csv' });

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await act(async () => {
        await result.current.apiPost<{ ok: boolean }>('/items', {
          body
        });
      });

      const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
        RequestInfo | URL,
        RequestInit
      ];
      const headers = new Headers(options.headers);

      expect(headers.get('Content-Type')).toBe('text/csv');
      expect(headers.get('Accept')).toBe('application/json');
    });

    it('sets the correct headers for Blob requests if the blob has no type', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

      const body = new Blob(['test']);

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await act(async () => {
        await result.current.apiPost<{ ok: boolean }>('/items', {
          body
        });
      });

      const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
        RequestInfo | URL,
        RequestInit
      ];
      const headers = new Headers(options.headers);

      expect(headers.get('Content-Type')).toBeNull();
      expect(headers.get('Accept')).toBe('application/json');
    });

    it('sets the correct headers for FormData requests', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

      const body = new FormData();
      body.append('file', new Blob(['test'], { type: 'text/csv' }), 'test.csv');

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await act(async () => {
        await result.current.apiPost<{ ok: boolean }>('/items', {
          body
        });
      });

      const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
        RequestInfo | URL,
        RequestInit
      ];
      const headers = new Headers(options.headers);

      expect(headers.get('Content-Type')).toBeNull();
      expect(headers.get('Accept')).toBe('application/json');
    });

    it('sets the correct headers for ArrayBuffer requests', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

      const body = new ArrayBuffer(8);

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await act(async () => {
        await result.current.apiPost<{ ok: boolean }>('/items', {
          body
        });
      });

      const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
        RequestInfo | URL,
        RequestInit
      ];
      const headers = new Headers(options.headers);

      expect(headers.get('Content-Type')).toBe('application/octet-stream');
      expect(headers.get('Accept')).toBe('application/json');
    });

    it('sets the correct headers for URLSearchParams requests', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

      const body = new URLSearchParams();
      body.append('key', 'value');

      const { useApi } = await import('../../hooks/useApi');
      const { result } = renderHook(() => useApi());

      await act(async () => {
        await result.current.apiPost<{ ok: boolean }>('/items', {
          body
        });
      });

      const [url, options] = vi.mocked(global.fetch).mock.calls[0] as [
        RequestInfo | URL,
        RequestInit
      ];
      const headers = new Headers(options.headers);

      expect(headers.get('Content-Type')).toBe(
        'application/x-www-form-urlencoded; charset=UTF-8'
      );
      expect(headers.get('Accept')).toBe('application/json');
    });
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
        await expect(result.current.apiGet('/protected')).rejects.toMatchObject(
          {
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
          }
        );
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
        await expect(
          result.current.apiGet('/restricted')
        ).rejects.toMatchObject({
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
        await expect(
          result.current.apiGet('/nonexistent')
        ).rejects.toMatchObject({
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
        });
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

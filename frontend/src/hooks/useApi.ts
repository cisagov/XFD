import { useState, useCallback, useMemo } from 'react';
import { API } from 'aws-amplify';

const baseHeaders: HeadersInit = {
  'Content-Type': 'application/json',
  Accept: 'application/json'
};

type ApiMethod = (apiName: string, path: string, init?: any) => Promise<any>;
type OnError = (e: Error) => Promise<void>;

const isLocal = import.meta.env.VITE_IS_LOCAL === '1';

const normalizeHeaders = (header: any): Record<string, string> => {
  if (!header) return {};

  if (
    typeof header === 'object' &&
    !('forEach' in header) &&
    !('entries' in header)
  ) {
    const out: Record<string, string> = {};
    for (const [name, value] of Object.entries(header)) {
      out[String(name).toLowerCase()] = String(value);
    }
    return out;
  }

  if (typeof header?.forEach === 'function') {
    const out: Record<string, string> = {};
    header.forEach((v: any, k: any) => {
      out[String(k).toLowerCase()] = String(v);
    });
    return out;
  }

  if (typeof header?.entries === 'function') {
    const out: Record<string, string> = {};
    for (const [name, value] of header.entries()) {
      out[String(name).toLowerCase()] = String(value);
    }
    return out;
  }

  return {};
};

const sendClientTelemetry = (payload: any) => {
  try {
    const body = JSON.stringify(payload);

    if (navigator.sendBeacon) {
      navigator.sendBeacon(
        '/client-telemetry',
        new Blob([body], { type: 'application/json' })
      );
      return;
    }

    fetch('/client-telemetry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
      credentials: 'include'
    }).catch(() => undefined);
  } catch {
    // Never let telemetry break the original error behavior
  }
};

// ---- NEW: cookie helpers + CSRF token extraction ----
const getCookie = (name: string): string => {
  // Safe cookie parse without dependencies
  const parts = document.cookie.split(';').map((p) => p.trim());
  for (const part of parts) {
    if (part.startsWith(name + '=')) {
      return decodeURIComponent(part.slice(name.length + 1));
    }
  }
  return '';
};

const getCsrfToken = (): string => getCookie('csrf_token'); // must match backend cookie name

const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete', 'del']);

export const useApi = (onError?: OnError) => {
  const [requestCount, setRequestCount] = useState(0);

  // ---- UPDATED: prepareInit no longer sets Authorization, and correctly includes cookies ----
  const prepareInit = useCallback(async (init: any) => {
    const { headers, ...rest } = init;

    return {
      ...rest,
      // For fetch-based adapters, this matters.
      credentials: 'include',
      // Some Amplify adapters ignore this and rely on `withCredentials`.
      withCredentials: true,
      headers: {
        ...baseHeaders,
        ...headers
      }
    };
  }, []);

  // ---- UPDATED: apiMethod now takes the verb and injects X-CSRF-Token when needed ----
  const apiMethod = useCallback(
    (method: ApiMethod, verb: string) =>
      async <T extends object = any>(path: string, init: any = {}) => {
        const { showLoading = true, ...rest } = init;

        try {
          showLoading && setRequestCount((cnt) => cnt + 1);

          const csrf = getCsrfToken();
          const addCsrf =
            UNSAFE_METHODS.has(verb.toLowerCase()) &&
            typeof csrf === 'string' &&
            csrf.length > 0;

          const options = await prepareInit({
            ...rest,
            headers: {
              ...(rest.headers || {}),
              ...(addCsrf ? { 'x-csrf-token': csrf } : {})
            }
          });

          const result = await method('crossfeed', path, options);

          showLoading && setRequestCount((cnt) => cnt - 1);
          return result as T;
        } catch (e: any) {
          showLoading && setRequestCount((cnt) => cnt - 1);

          if (!isLocal) {
            try {
              const status =
                e?.response?.status ?? e?.status ?? e?.statusCode ?? undefined;

              const headersRaw =
                e?.response?.headers ??
                e?.headers ??
                e?.response?.header ??
                undefined;

              const headers = normalizeHeaders(headersRaw);

              const apigwId = headers['x-amz-apigw-id'] ?? '';
              const amznReqId = headers['x-amzn-requestid'] ?? '';
              const reachedApigw = !!(apigwId || amznReqId);

              if (!reachedApigw) {
                sendClientTelemetry({
                  type: 'backend_blocked_before_apigw',
                  path,
                  status: status ?? null,
                  server: headers['server'] ?? null,
                  via: headers['via'] ?? null,
                  cfRay: headers['cf-ray'] ?? null,
                  cfCacheStatus: headers['cf-cache-status'] ?? null,
                  ts: Date.now()
                });
              }
            } catch {
              // Never let logging break the original error behavior
            }
          }

          onError && onError(e);
          throw e;
        }
      },
    [prepareInit, onError]
  );

  const api = {
    apiGet: useMemo(() => apiMethod(API.get.bind(API), 'get'), [apiMethod]),
    apiPost: useMemo(() => apiMethod(API.post.bind(API), 'post'), [apiMethod]),
    apiDelete: useMemo(() => apiMethod(API.del.bind(API), 'del'), [apiMethod])
  };

  return {
    ...api,
    loading: requestCount > 0
  };
};

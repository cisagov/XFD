import { useState, useCallback, useMemo } from 'react';
// import { useMatomo } from '@datapunt/matomo-tracker-react';

const baseHeaders: HeadersInit = {
  'Content-Type': 'application/json',
  Accept: 'application/json'
};

type ApiMethod = 'GET' | 'POST' | 'DELETE';
type OnError = (e: Error) => Promise<void>;

const isLocal = import.meta.env.VITE_IS_LOCAL === '1';
const apiBaseUrl = String(import.meta.env.VITE_API_URL || '').replace(
  /\/$/,
  ''
);

/**
 * Normalize header-ish shapes to support both Fetch Headers and plain objects.
 */
const normalizeHeaders = (header: any): Record<string, string> => {
  if (!header) return {};

  // Plain object
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

  // Headers-like (forEach)
  if (typeof header?.forEach === 'function') {
    const out: Record<string, string> = {};
    header.forEach((v: any, k: any) => {
      out[String(k).toLowerCase()] = String(v);
    });
    return out;
  }

  // Iterable (entries)
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
      credentials: 'omit'
    }).catch(() => undefined);
  } catch {
    // Never let telemetry break the original error behavior
  }
};

export const useApi = (onError?: OnError) => {
  const [requestCount, setRequestCount] = useState(0);

  const getToken = () => {
    const token = localStorage.getItem('token');
    try {
      return token ? JSON.parse(token) : token || '';
    } catch {
      return token || '';
    }
  };

  const prepareInit = useCallback(async (init: any) => {
    const { headers, ...rest } = init;
    const token = getToken();

    return {
      ...rest,
      headers: {
        ...baseHeaders, // put base first
        ...headers, // allow caller to override (e.g., Accept: text/csv)
        ...(token
          ? {
              Authorization: token.startsWith('Bearer ')
                ? token
                : `Bearer ${token}`
            }
          : {})
      }
    };
  }, []);

  const apiMethod = useCallback(
    (method: ApiMethod) =>
      async <T extends object = any>(path: string, init: any = {}) => {
        const { showLoading = true, ...rest } = init;
        try {
          showLoading && setRequestCount((cnt) => cnt + 1);
          const options = await prepareInit(rest);
          const {
            body,
            response: includeResponse,
            responseType,
            withCredentials
          } = options;
          const requestPath = path.startsWith('/') ? path : `/${path}`;
          const response = await fetch(`${apiBaseUrl}${requestPath}`, {
            method,
            headers: options.headers,
            body:
              body === undefined ||
              body instanceof FormData ||
              typeof body === 'string'
                ? body
                : JSON.stringify(body),
            credentials: withCredentials ? 'include' : undefined
          });

          const statusCode = response.status;

          let result: any;
          try {
            result =
              responseType === 'blob'
                ? await response.blob()
                : await response.json();
          } catch {
            result = undefined;
          }

          // If status is 401, immediately throw standardized error
          if (statusCode === 401) {
            const error = new Error(
              result?.detail ||
                result?.message ||
                `Request failed with status code 401`
            );

            throw Object.assign(error, {
              statusCode: 401,
              body: result,
              response: {
                status: 401,
                headers: response.headers
              }
            });
          }

          if (!response.ok) {
            const error = new Error(
              result?.detail ||
                result?.message ||
                `Request failed with status code ${statusCode}`
            );
            throw Object.assign(error, {
              statusCode,
              body: result,
              response: { status: statusCode, headers: response.headers }
            });
          }

          showLoading && setRequestCount((cnt) => cnt - 1);
          if (includeResponse) {
            return {
              data: result,
              headers: Object.fromEntries(response.headers.entries())
            } as T;
          }
          return result as T;
        } catch (e: any) {
          showLoading && setRequestCount((cnt) => cnt - 1);

          const status =
            e?.response?.statusCode ??
            e?.response?.status ??
            e?.status ??
            e?.statusCode ??
            (e?.message?.includes('401') ? 401 : undefined);

          const errorDetail = (
            e?.message ||
            e?.body?.detail ||
            e?.response?.data?.detail ||
            ''
          ).toLowerCase();

          // TODO: CRASM-4093 Add more robust checks for expired tokens and other error codes; current implementation may not cover all cases.

          // 2. Detect if this is an expired token:
          //    - Explicit 401 status
          //    - Error message referencing explicit token expiration or invalidity
          const isAuthError =
            status === 401 ||
            errorDetail.includes('token has expired') ||
            errorDetail.includes('jwt expired') ||
            errorDetail.includes('invalid token') ||
            errorDetail.includes('not authenticated');

          if (isAuthError) {
            // Standardize error shape so AuthContextProvider.handleError receives status 401
            e.statusCode = 401;
            if (!e.response) {
              e.response = { status: 401 };
            }
          }

          if (!isLocal) {
            try {
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

          // Pass standardized error to AuthContextProvider
          if (onError) {
            await onError(e);
          }
          throw e;
        }
      },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [prepareInit, onError]
  );

  const api = {
    apiGet: useMemo(() => apiMethod('GET'), [apiMethod]),
    apiPost: useMemo(() => apiMethod('POST'), [apiMethod]),
    apiDelete: useMemo(() => apiMethod('DELETE'), [apiMethod])
  };

  return {
    ...api,
    loading: requestCount > 0
  };
};

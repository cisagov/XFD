import { useState, useCallback, useMemo } from 'react';
import { post, get, del } from 'aws-amplify/api';
import {
  ApiInput,
  Operation,
  RestApiOptionsBase,
  RestApiResponse
} from '@aws-amplify/api-rest/dist/esm/types';
// import { useMatomo } from '@datapunt/matomo-tracker-react';

const baseHeaders: HeadersInit = {
  'Content-Type': 'application/json',
  Accept: 'application/json'
};

type ApiMethod = (
  input: ApiInput<RestApiOptionsBase>
) => Operation<RestApiResponse>;
type OnError = (e: Error) => Promise<void>;

const isLocal = import.meta.env.VITE_IS_LOCAL === '1';

/**
 * Normalize header-ish shapes to a lower-cased plain object.
 * Amplify error shapes vary across versions/adapters.
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
      return token ? JSON.parse(token) : '';
    } catch {
      return '';
    }
  };

  const prepareInit = useCallback(async (init: any) => {
    const { headers, ...rest } = init;
    return {
      ...rest,
      headers: {
        ...baseHeaders, // put base first
        ...headers, // allow caller to override (e.g., Accept: text/csv)
        Authorization: getToken()
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
          // const result = await method('crossfeed', path, options);
          const response = await method({ apiName: 'crossfeed', path, options })
            .response;
          const result = await response.body.json();
          showLoading && setRequestCount((cnt) => cnt - 1);
          return result as T;
        } catch (e: any) {
          showLoading && setRequestCount((cnt) => cnt - 1);

          if (!isLocal) {
            // Detection of blocks before API Gateway
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [prepareInit, onError]
  );

  const api = {
    apiGet: useMemo(() => apiMethod(get), [apiMethod]),
    apiPost: useMemo(() => apiMethod(post), [apiMethod]),
    apiDelete: useMemo(() => apiMethod(del), [apiMethod])
  };

  return {
    ...api,
    loading: requestCount > 0
  };
};

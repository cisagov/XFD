import { useState, useCallback, useMemo } from 'react';
// import { useMatomo } from '@datapunt/matomo-tracker-react';

/**
 * Helper function to extract a human-readable error message from an API response payload.
 * Many files in the project may include API responses with a `detail`, `message`, or `error` field.
 */

function getPayloadMessage(payload: unknown): string | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined;
  }

  const value = payload as Record<string, unknown>;

  if (typeof value.detail === 'string') {
    return value.detail;
  }

  if (typeof value.message === 'string') {
    return value.message;
  }

  if (typeof value.error === 'string') {
    return value.error;
  }

  return undefined;
}

/**
 * Type guard to check if an error is an instance of ApiError.
 */

export function isApiError(error: unknown): error is ApiError {
  return (
    !!error &&
    typeof error === 'object' &&
    (
      error as {
        isApiError?: unknown;
      }
    ).isApiError === true
  );
}

/**
 * Custom error class for API errors, encapsulating the response and payload.
 */
export class ApiError<TPayload = unknown> extends Error {
  readonly name = 'ApiError';
  readonly isApiError = true;

  readonly ok: Response['ok'];
  readonly status: Response['status'];
  readonly statusText: Response['statusText'];
  readonly headers: Record<string, string>;
  readonly url: Response['url'];
  readonly redirected: Response['redirected'];
  readonly type: Response['type'];
  readonly bodyUsed: Response['bodyUsed'];

  readonly payload: TPayload; // Raw payload from the API response
  readonly payloadMessage?: string; // User-friendly message extracted from the payload

  constructor(response: Response, payload?: TPayload, message?: string) {
    const payloadMessage = getPayloadMessage(payload);

    /**
     * Construct the error message using the provided message, the extracted user-friendly message from the payload,
     * the response status text, or a default message.
     */

    super(
      message ||
        payloadMessage ||
        response.statusText ||
        `Request failed with status ${response.status}`
    );

    Object.setPrototypeOf(this, ApiError.prototype);

    this.ok = response.ok;
    this.status = response.status;
    this.statusText = response.statusText;

    /**
     * Need to double check if normalizeHeaders is necessary anymore
     */
    this.headers = normalizeHeaders(
      Object.fromEntries(response.headers.entries())
    );
    this.url = response.url;
    this.redirected = response.redirected;
    this.type = response.type;
    this.bodyUsed = response.bodyUsed;

    this.payload = payload as TPayload;
    this.payloadMessage = payloadMessage;
  }
}

const baseHeaders: HeadersInit = {
  'Content-Type': 'application/json',
  Accept: 'application/json'
};

type ApiMethod = 'GET' | 'POST' | 'DELETE';
type OnError = (e: Error) => Promise<void>;
type ParseAs = 'json' | 'text' | 'blob' | 'arrayBuffer' | 'formData' | 'none';

const isLocal = import.meta.env.VITE_IS_LOCAL === '1';
const apiBaseUrl = String(import.meta.env.VITE_API_URL || '').replace(
  /\/$/,
  ''
);

type ApiInit = Omit<RequestInit, 'method' | 'body'> & {
  body?: unknown; // The request payload, will be JSON-stringified if provided
  showLoading?: boolean; // Whether to show a loading indicator during the request
  includeResponse?: false; // Does not includethe full response object in the return value
  parseAs?: ParseAs; // The expected response type, used to parse the response accordingly
};

type ApiInitWithResponse = Omit<ApiInit, 'includeResponse'> & {
  includeResponse: true; // Force inclusion of the full response object in the return value
};

export type ApiResponse<T> = {
  data: T;
  headers: Record<string, string>;
  response?: Response;
};

type ApiFn = {
  <T = unknown>(
    path: string,
    init: ApiInitWithResponse
  ): Promise<ApiResponse<T>>;

  <T = unknown>(path: string, init?: ApiInit): Promise<T>;
};

/**
 * Normalize header-ish shapes to support both Fetch Headers and plain objects.
 */

const normalizeHeaders = (
  headers: HeadersInit | undefined
): Record<string, string> => {
  if (!headers) {
    return {};
  }

  const normalized = new Headers(headers);
  const out: Record<string, string> = {};

  normalized.forEach((value, key) => {
    out[key.toLowerCase()] = value;
  });

  return out;
};

// const normalizeHeaders = (header: any): Record<string, string> => {
//   if (!header) return {};

//   // Plain object
//   if (
//     typeof header === 'object' &&
//     !('forEach' in header) &&
//     !('entries' in header)
//   ) {
//     const out: Record<string, string> = {};
//     for (const [name, value] of Object.entries(header)) {
//       out[String(name).toLowerCase()] = String(value);
//     }
//     return out;
//   }

//   // Headers-like (forEach)
//   if (typeof header?.forEach === 'function') {
//     const out: Record<string, string> = {};
//     header.forEach((v: any, k: any) => {
//       out[String(k).toLowerCase()] = String(v);
//     });
//     return out;
//   }

//   // Iterable (entries)
//   if (typeof header?.entries === 'function') {
//     const out: Record<string, string> = {};
//     for (const [name, value] of header.entries()) {
//       out[String(name).toLowerCase()] = String(value);
//     }
//     return out;
//   }

//   return {};
// };

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

  const createFetchOptions = useCallback(
    (
      method: ApiMethod,
      init: ApiInit | ApiInitWithResponse = {}
    ): RequestInit => {
      const {
        headers,
        body,
        showLoading,
        includeResponse,
        parseAs,
        ...fetchOptions
      } = init;

      const token = getToken();

      const mergedHeaders = new Headers(baseHeaders);

      if (headers) {
        new Headers(headers).forEach((value, key) => {
          mergedHeaders.set(key, value);
        });
      }

      if (token) {
        mergedHeaders.set(
          'Authorization',
          token.startsWith('Bearer ') ? token : `Bearer ${token}`
        );
      }

      const options: RequestInit = {
        ...fetchOptions,
        method,
        headers: mergedHeaders
      };

      if (body !== undefined && method !== 'GET') {
        if (body instanceof FormData) {
          options.body = body;
          mergedHeaders.delete('Content-Type');
        } else if (
          body instanceof Blob ||
          body instanceof ArrayBuffer ||
          typeof body === 'string'
        ) {
          options.body = body as BodyInit;
        } else {
          options.body = JSON.stringify(body);
        }
      }
      return options;
    },
    []
  );

  // const prepareInit = useCallback(async (init: any) => {
  //   const { headers, ...rest } = init;
  //   const token = getToken();

  //   return {
  //     ...rest,
  //     headers: {
  //       ...baseHeaders, // put base first
  //       ...headers, // allow caller to override (e.g., Accept: text/csv)
  //       ...(token
  //         ? {
  //             Authorization: token.startsWith('Bearer ')
  //               ? token
  //               : `Bearer ${token}`
  //           }
  //         : {})
  //     }
  //   };
  // }, []);

  const apiMethod = useCallback(
    (method: ApiMethod): ApiFn => {
      const fn = async <T = unknown>(
        path: string,
        init: ApiInit | ApiInitWithResponse = {}
      ): Promise<T | ApiResponse<T>> => {
        const {
          showLoading = true,
          includeResponse = false,
          parseAs = 'json'
        } = init;

        try {
          if (showLoading) {
            setRequestCount((cnt) => cnt + 1);
          }

          const requestPath = path.startsWith('/') ? path : `/${path}`;
          const response = await fetch(
            `${apiBaseUrl}${requestPath}`,
            createFetchOptions(method, init)
          );

          let result: unknown;

          try {
            if (parseAs === 'none' || response.status === 204) {
              result = undefined;
            } else if (parseAs === 'json') {
              result = await response.json();
            } else if (parseAs === 'text') {
              result = await response.text();
            } else if (parseAs === 'blob') {
              result = await response.blob();
            }
          } catch (error) {
            // Handle parsing errors if necessary
            result = undefined;
          }

          if (!response.ok) {
            throw new ApiError(response, result);
          }

          if (includeResponse) {
            return {
              data: result as T,
              headers: Object.fromEntries(response.headers.entries()),
              response
            };
          }

          return result as T;
        } catch (e: unknown) {
          const error = e instanceof Error ? e : new Error(String(e));

          const status = isApiError(e) ? e.status : undefined;

          if (!isLocal) {
            try {
              const headers = isApiError(error) ? error.headers : {};

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
          if (onError) {
            await onError(error);
          }
          throw error;
        } finally {
          if (showLoading) {
            setRequestCount((cnt) => cnt - 1);
          }
        }
      };
      return fn as ApiFn;
    },
    [createFetchOptions, onError]
  );

  // const apiMethod = useCallback(
  //   (method: ApiMethod) =>
  //     async <T extends object = any>(path: string, init: any = {}) => {
  //       const { showLoading = true, ...rest } = init;
  //       try {
  //         showLoading && setRequestCount((cnt) => cnt + 1);
  //         const options = await prepareInit(rest);
  //         const {
  //           body,
  //           response: includeResponse,
  //           responseType,
  //           withCredentials
  //         } = options;
  //         const requestPath = path.startsWith('/') ? path : `/${path}`;
  //         const response = await fetch(`${apiBaseUrl}${requestPath}`, {
  //           method,
  //           headers: options.headers,
  //           body:
  //             body === undefined ||
  //             body instanceof FormData ||
  //             typeof body === 'string'
  //               ? body
  //               : JSON.stringify(body),
  //           credentials: withCredentials ? 'include' : undefined
  //         });

  //         let result: any;
  //         try {
  //           result =
  //             responseType === 'blob'
  //               ? await response.blob()
  //               : await response.json();
  //         } catch {
  //           result = undefined;
  //         }

  //         if (!response.ok) {
  //           throw new ApiError(response, result);
  //         }

  //         showLoading && setRequestCount((cnt) => cnt - 1);
  //         if (includeResponse) {
  //           return {
  //             data: result,
  //             headers: Object.fromEntries(response.headers.entries())
  //           } as T;
  //         }
  //         return result as T;
  //       } catch (e: any) {
  //         showLoading && setRequestCount((cnt) => cnt - 1);

  //         const status = isApiError(e) ? e.status : undefined;

  //         // TODO: CRASM-4093 Add more robust checks for expired tokens and other error codes; current implementation may not cover all cases.

  //         if (!isLocal) {
  //           try {
  //             const headersRaw =
  //               e?.response?.headers ??
  //               e?.headers ??
  //               e?.response?.header ??
  //               undefined;

  //             const headers = normalizeHeaders(headersRaw);

  //             const apigwId = headers['x-amz-apigw-id'] ?? '';
  //             const amznReqId = headers['x-amzn-requestid'] ?? '';
  //             const reachedApigw = !!(apigwId || amznReqId);

  //             if (!reachedApigw) {
  //               sendClientTelemetry({
  //                 type: 'backend_blocked_before_apigw',
  //                 path,
  //                 status: status ?? null,
  //                 server: headers['server'] ?? null,
  //                 via: headers['via'] ?? null,
  //                 cfRay: headers['cf-ray'] ?? null,
  //                 cfCacheStatus: headers['cf-cache-status'] ?? null,
  //                 ts: Date.now()
  //               });
  //             }
  //           } catch {
  //             // Never let logging break the original error behavior
  //           }
  //         }

  //         // Pass standardized error to AuthContextProvider
  //         if (onError) {
  //           await onError(e);
  //         }
  //         throw e;
  //       }
  //     },
  //   // eslint-disable-next-line react-hooks/exhaustive-deps
  //   [prepareInit, onError]
  // );

  const api = useMemo(
    () => ({
      apiGet: apiMethod('GET'),
      apiPost: apiMethod('POST'),
      apiDelete: apiMethod('DELETE')
    }),
    [apiMethod]
  );

  // const api = {
  //   apiGet: useMemo(() => apiMethod('GET'), [apiMethod]),
  //   apiPost: useMemo(() => apiMethod('POST'), [apiMethod]),
  //   apiDelete: useMemo(() => apiMethod('DELETE'), [apiMethod])
  // };

  return {
    ...api,
    loading: requestCount > 0
  };
};

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('aws-amplify/api', () => ({
  get: vi.fn(),
  post: vi.fn(),
  del: vi.fn()
}));

const getAmplifyAPI = async () => {
  const mod = await import('aws-amplify/api');
  return {
    get: mod.get as any,
    post: mod.post as any,
    del: mod.del as any
  };
};

describe('useApi telemetry', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 🧠 Mock global.navigator.sendBeacon
    Object.defineProperty(global.navigator, 'sendBeacon', {
      value: vi.fn(),
      writable: true,
      configurable: true
    });

    // 🧠 Mock global.fetch fallback
    global.fetch = vi.fn(() => Promise.resolve({ ok: true })) as any;

    // 🧠 Mock Blob so .text() works in JSDOM
    if (typeof global.Blob === 'undefined') {
      global.Blob = class {
        constructor(
          public parts: any[],
          public options: any
        ) {}
        text() {
          return Promise.resolve(this.parts.join(''));
        }
      } as any;
    }
  });

  it('does not send telemetry when API Gateway headers are present', async () => {
    const { get } = await getAmplifyAPI();

    const error = {
      response: {
        status: 500,
        headers: {
          'x-amzn-requestid': 'abc123'
        }
      }
    };
    // v6: get(...) returns an Operation object; .response is the promise
    get.mockReturnValueOnce({ response: Promise.reject(error) });

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await expect(
      act(async () => {
        await result.current.apiGet('/test');
      })
    ).rejects.toBeDefined();

    const sendBeaconSpy = global.navigator.sendBeacon as any;
    const fetchSpy = global.fetch as any;

    expect(sendBeaconSpy).not.toHaveBeenCalled();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('rethrows the original error after telemetry handling', async () => {
    const { get } = await getAmplifyAPI();

    // v6: get(...) returns an Operation object; .response is the promise
    get.mockReturnValueOnce({ response: Promise.reject(new Error('boom')) });

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await expect(
      act(async () => {
        await result.current.apiGet('/test');
      })
    ).rejects.toThrow('boom');
  });
});

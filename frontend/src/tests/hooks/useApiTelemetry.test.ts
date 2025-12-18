import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('aws-amplify', () => ({
  API: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
    patch: vi.fn()
  }
}));

const getAmplifyAPI = async () => {
  const mod = await import('aws-amplify');
  return mod.API as any;
};

describe('useApi telemetry', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Make sure sendBeacon is writable/defined in jsdom
    Object.defineProperty(global.navigator, 'sendBeacon', {
      value: vi.fn(),
      writable: true,
      configurable: true
    });

    // Stub fetch fallback too
    // @ts-ignore
    global.fetch = vi.fn(() => Promise.resolve({ ok: true })) as any;
  });

  it('sends client telemetry when backend error lacks API Gateway headers', async () => {
    const API = await getAmplifyAPI();

    API.get.mockRejectedValueOnce({
      response: {
        status: 403,
        headers: {
          server: 'cloudflare'
        }
      }
    });

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await expect(
      act(async () => {
        await result.current.apiGet('/test');
      })
    ).rejects.toBeDefined();

    const sendBeaconSpy = global.navigator.sendBeacon as any;
    const fetchSpy = global.fetch as any;

    // It should use sendBeacon if available; but allow fetch fallback in case jsdom behaves oddly.
    expect(
      sendBeaconSpy.mock.calls.length + fetchSpy.mock.calls.length
    ).toBeGreaterThan(0);

    if (sendBeaconSpy.mock.calls.length > 0) {
      const [, blob] = sendBeaconSpy.mock.calls[0];
      const payload = JSON.parse(await blob.text());
      expect(payload.type).toBe('backend_blocked_before_apigw');
      expect(payload.path).toBe('/test');
      expect(payload.status).toBe(403);
    } else {
      // fetch('/client-telemetry', { body: JSON.stringify(payload) })
      const [, init] = fetchSpy.mock.calls[0];
      const payload = JSON.parse(init.body);
      expect(payload.type).toBe('backend_blocked_before_apigw');
      expect(payload.path).toBe('/test');
      expect(payload.status).toBe(403);
    }
  });

  it('does not send telemetry when API Gateway headers are present', async () => {
    const API = await getAmplifyAPI();

    API.get.mockRejectedValueOnce({
      response: {
        status: 500,
        headers: {
          'x-amzn-requestid': 'abc123'
        }
      }
    });

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
    const API = await getAmplifyAPI();

    API.get.mockRejectedValueOnce(new Error('boom'));

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await expect(
      act(async () => {
        await result.current.apiGet('/test');
      })
    ).rejects.toThrow('boom');
  });
});

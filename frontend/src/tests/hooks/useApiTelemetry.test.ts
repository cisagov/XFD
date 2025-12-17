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

    // Ensure sendBeacon exists for tests
    // @ts-ignore
    global.navigator.sendBeacon = vi.fn();
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
    expect(sendBeaconSpy).toHaveBeenCalledTimes(1);

    const [, blob] = sendBeaconSpy.mock.calls[0];
    const payload = JSON.parse(await blob.text());

    expect(payload.type).toBe('backend_blocked_before_apigw');
    expect(payload.path).toBe('/test');
    expect(payload.status).toBe(403);
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
    expect(sendBeaconSpy).not.toHaveBeenCalled();
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

import { it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useApi } from '../../hooks/useApi';

// Mock aws-amplify
vi.mock('aws-amplify', () => ({
  API: {
    get: vi.fn()
  }
}));

it('sends client telemetry when backend error lacks API Gateway headers', async () => {
  const sendBeaconSpy = vi.fn();
  // @ts-ignore
  global.navigator.sendBeacon = sendBeaconSpy;

  const error = {
    response: {
      status: 403,
      headers: {
        server: 'cloudflare'
      }
    }
  };

  const { API } = await import('aws-amplify');
  (API.get as any).mockRejectedValueOnce(error);

  const { result } = renderHook(() => useApi());

  await expect(act(() => result.current.apiGet('/test'))).rejects.toBeDefined();

  expect(sendBeaconSpy).toHaveBeenCalledTimes(1);

  const [, blob] = sendBeaconSpy.mock.calls[0];
  const payload = JSON.parse(await blob.text());

  expect(payload.type).toBe('backend_blocked_before_apigw');
  expect(payload.status).toBe(403);
});

it('does not send telemetry when API Gateway headers are present', async () => {
  const sendBeaconSpy = vi.fn();
  // @ts-ignore
  global.navigator.sendBeacon = sendBeaconSpy;

  const error = {
    response: {
      status: 500,
      headers: {
        'x-amzn-requestid': 'abc123'
      }
    }
  };

  const { API } = await import('aws-amplify');
  (API.get as any).mockRejectedValueOnce(error);

  const { result } = renderHook(() => useApi());

  await expect(act(() => result.current.apiGet('/test'))).rejects.toBeDefined();

  expect(sendBeaconSpy).not.toHaveBeenCalled();
});

it('rethrows the original error after telemetry handling', async () => {
  const error = new Error('boom');

  const { API } = await import('aws-amplify');
  (API.get as any).mockRejectedValueOnce(error);

  const { result } = renderHook(() => useApi());

  await expect(act(() => result.current.apiGet('/test'))).rejects.toThrow(
    'boom'
  );
});

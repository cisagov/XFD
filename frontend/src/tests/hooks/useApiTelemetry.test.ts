import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

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
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers({ 'x-amzn-requestid': 'abc123' }),
      json: vi.fn().mockResolvedValue({ detail: 'server error' })
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
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('rethrows the original error after telemetry handling', async () => {
    global.fetch = vi.fn().mockRejectedValueOnce(new Error('boom'));

    const { useApi } = await import('../../hooks/useApi');
    const { result } = renderHook(() => useApi());

    await expect(
      act(async () => {
        await result.current.apiGet('/test');
      })
    ).rejects.toThrow('boom');
  });
});

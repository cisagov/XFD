import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useVulnScanData } from '../../hooks/useVulnScanData';
import { useAuthContext } from 'context';
import { InitialVSData } from '@/constants/vsdashdata';
import { NO_DATA_FALLBACK_LABEL } from '@/constants/vsdashdata';
import { transformVulnScanData } from '@/utils/transformVulnScanData';

// -------------------- Mocks --------------------
vi.mock('context', () => ({
  useAuthContext: vi.fn()
}));

vi.mock('@/utils/transformVulnScanData', () => ({
  transformVulnScanData: vi.fn((data) => data)
}));

// -------------------- Test Suite --------------------
describe('useVulnScanData', () => {
  let mockApiPost: any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPost = vi.fn();
    vi.mocked(useAuthContext).mockReturnValue({
      apiPost: mockApiPost
    } as any);
  });

  it('sets error and initial data when orgId is empty', async () => {
    const { result } = renderHook(() => useVulnScanData(''));

    expect(result.current.error).toBe(
      "Please join an organization to be shown your organization's vulnerability scan data."
    );
    expect(result.current.data).toEqual(InitialVSData);
    expect(result.current.loading).toBe(false);
  });

  it('sets initial data and error when API returns empty scan data', async () => {
    mockApiPost.mockResolvedValue({
      host_summaries: [],
      port_scan_summaries: [],
      port_scan_service_summaries: [],
      vuln_scan_summaries: []
    });

    const { result } = renderHook(() => useVulnScanData('org-1'));

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(InitialVSData);
    expect(result.current.error).toBe(
      'No recent scan data was found for the selected organization.'
    );
    expect(result.current.loading).toBe(false);
  });

  it('sets initial data and error when vulnScanSummary fallback label is NO_DATA', async () => {
    const apiResponse = {
      vuln_scan_summaries: [{ vulnerabilityScan: NO_DATA_FALLBACK_LABEL }]
    };
    mockApiPost.mockResolvedValue(apiResponse);

    // Mock transformVulnScanData to return the expected structure for this test
    vi.mocked(transformVulnScanData).mockReturnValue({
      vulnScanSummary: [{ vulnerabilityScan: NO_DATA_FALLBACK_LABEL }]
    } as any);

    const { result } = renderHook(() => useVulnScanData('org-2'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(InitialVSData);
    expect(result.current.error).toBe('NO_DATA');
    expect(result.current.loading).toBe(false);
  });

  it('sets transformed data when API returns valid scan data', async () => {
    const apiResponse = {
      vuln_scan_summaries: [{ vulnerabilityScan: '2025-01-01' }]
    };
    mockApiPost.mockResolvedValue(apiResponse);

    const transformedData = {
      vulnScanSummary: [{ vulnerabilityScan: '2025-01-01' }]
    };
    vi.mocked(transformVulnScanData).mockReturnValue(transformedData as any);

    const { result } = renderHook(() => useVulnScanData('org-3'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(transformedData);
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('sets error when API call throws', async () => {
    const err = new Error('Network failure');
    mockApiPost.mockRejectedValue(err);

    const { result } = renderHook(() => useVulnScanData('org-4'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(InitialVSData);
    expect(result.current.error).toBe(
      'Network failure. Failed to load vulnerability scan data. See the console log for more details.'
    );
    expect(result.current.loading).toBe(false);
  });
});

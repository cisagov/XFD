import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, it, vi, beforeEach, expect } from 'vitest';
import { VSDashboardGate } from '../VSDashboardGate';
import { InitialVSData, EmptyVSData } from '@/constants/vsdashdata';

vi.mock('@/context/AuthContext', () => ({
  useAuthContext: () => ({
    user: { user_type: 'standard' },
    currentOrganization: { id: 'org-1', name: 'Test Org' }
  })
}));

vi.mock('@/context/NavigationContext', () => ({
  useNavigationContext: () => ({
    navigate: vi.fn(),
    currentPage: 'dashboard',
    setCurrentPage: vi.fn()
  })
}));

vi.mock('@/hooks/useOrgInfo', () => ({
  useOrgInfo: () => ({ orgId: 'org-1', orgName: 'Test Org' })
}));

vi.mock('@/utils/transformVulnScanData', async () => {
  const actual: any = await vi.importActual('@/utils/transformVulnScanData');
  return {
    ...actual,
    default: vi.fn(),
    isEmptyAfterScans: vi.fn()
  };
});

vi.mock('@/hooks/useVulnScanData', () => ({
  useVulnScanData: vi.fn(() => ({
    data: EmptyVSData,
    loading: false,
    error: null
  }))
}));

import { useVulnScanData } from '@/hooks/useVulnScanData';
import isDataEmpty, { isEmptyAfterScans } from '@/utils/transformVulnScanData';

const mockFilters = [{ field: 'region', values: ['us-east'], type: 'string' }];
const mockIsDataEmpty = isDataEmpty as unknown as ReturnType<typeof vi.fn>;
const mockIsEmptyAfterScans = isEmptyAfterScans as unknown as ReturnType<
  typeof vi.fn
>;
const mockUseVulnScanData = vi.mocked(useVulnScanData);

beforeEach(() => {
  vi.clearAllMocks();
  mockIsEmptyAfterScans.mockReturnValue(false);
});

describe('VSDashboardGate', () => {
  it('shows NoDataMessage when error is present', () => {
    mockUseVulnScanData.mockReturnValueOnce({
      data: InitialVSData,
      loading: false,
      error: 'Some error'
    });
    render(
      <MemoryRouter>
        <VSDashboardGate filters={mockFilters} removeFilter={vi.fn()} />
      </MemoryRouter>
    );
    expect(
      screen.getByText(/No matching data available./i)
    ).toBeInTheDocument();
  });

  it('shows NoDataMessage when data is empty', () => {
    mockIsDataEmpty.mockReturnValueOnce(true);
    mockUseVulnScanData.mockReturnValueOnce({
      data: InitialVSData,
      loading: false,
      error: null
    });
    render(
      <MemoryRouter>
        <VSDashboardGate filters={mockFilters} removeFilter={vi.fn()} />
      </MemoryRouter>
    );
    expect(
      screen.getByText(/No matching data available./i)
    ).toBeInTheDocument();
  });

  it('shows NoDataMessage when assetsOwned and hostsScanned are 0', () => {
    mockUseVulnScanData.mockReturnValueOnce({
      data: {
        ...InitialVSData,
        vulnScanSummary: [
          {
            ...InitialVSData.vulnScanSummary[0],
            assetsOwned: 0,
            hostsScanned: 0
          }
        ]
      },
      loading: false,
      error: null
    });
    render(
      <MemoryRouter>
        <VSDashboardGate filters={mockFilters} removeFilter={vi.fn()} />
      </MemoryRouter>
    );
    expect(screen.getByText(/no data available/i)).toBeInTheDocument();
  });

  it('shows NoDataMessage when recentlyEnrolled and hostsScanned is 0', () => {
    mockUseVulnScanData.mockReturnValueOnce({
      data: {
        ...InitialVSData,
        vulnScanSummary: [
          {
            ...InitialVSData.vulnScanSummary[0],
            recentlyEnrolled: true,
            hostsScanned: 0
          }
        ]
      },
      loading: false,
      error: null
    });
    render(
      <MemoryRouter>
        <VSDashboardGate filters={mockFilters} removeFilter={vi.fn()} />
      </MemoryRouter>
    );
    expect(screen.getByText(/no data available/i)).toBeInTheDocument();
  });

  it('shows alert when there is assetsOwned and hostsScanned but no other data', () => {
    mockIsEmptyAfterScans.mockReturnValueOnce(true);
    mockUseVulnScanData.mockReturnValueOnce({
      data: {
        ...InitialVSData,
        vulnScanSummary: [
          {
            ...InitialVSData.vulnScanSummary[0],
            assetsOwned: 10,
            hostsScanned: 10
          }
        ],
        vulnScanKeyMetrics: [
          {
            title: 'Detected Vulnerabilities',
            value: 0
          }
        ]
      },
      loading: false,
      error: null
    });
    render(
      <MemoryRouter>
        <VSDashboardGate filters={mockFilters} removeFilter={vi.fn()} />
      </MemoryRouter>
    );
    expect(screen.getByText(/No Data Found/i)).toBeInTheDocument();
  });

  it('shows alert when there is assetsOwned but no hostsScanned or other data', () => {
    mockIsEmptyAfterScans.mockReturnValue(true);
    mockUseVulnScanData.mockReturnValueOnce({
      data: {
        ...InitialVSData,
        vulnScanSummary: [
          {
            ...InitialVSData.vulnScanSummary[0],
            assetsOwned: 10,
            hostsScanned: 0
          }
        ],
        vulnScanKeyMetrics: [
          {
            title: 'Detected Vulnerabilities',
            value: 0
          }
        ]
      },
      loading: false,
      error: null
    });
    render(
      <MemoryRouter>
        <VSDashboardGate filters={mockFilters} removeFilter={vi.fn()} />
      </MemoryRouter>
    );

    expect(screen.getByText(/No Hosts Found/i)).toBeInTheDocument();
  });

  it('shows VulnerabilityScan default when data is present', () => {
    mockUseVulnScanData.mockReturnValueOnce({
      data: {
        ...EmptyVSData,
        vulnScanSummary: [
          {
            ...EmptyVSData.vulnScanSummary[0],
            assetsOwned: 10,
            hostsScanned: 10
          }
        ],
        vulnScanKeyMetrics: EmptyVSData.vulnScanKeyMetrics.map((metric) =>
          metric.title === 'Detected Vulnerabilities'
            ? { ...metric, value: 5 }
            : metric
        )
      },
      loading: false,
      error: null
    });
    render(
      <MemoryRouter>
        <VSDashboardGate filters={mockFilters} removeFilter={vi.fn()} />
      </MemoryRouter>
    );
    expect(
      screen.getByText(/Latest vulnerability scan on hosts/i)
    ).toBeInTheDocument();
  });
});

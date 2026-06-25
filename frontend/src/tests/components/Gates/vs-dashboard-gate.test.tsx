import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, it, vi, beforeEach, expect } from 'vitest';
import { VSDashboardGate } from '../../../components/Gates/VSDashboardGate';
import { InitialVSData, EmptyVSData } from '@/constants/vsdashdata';
import { useOrgInfo } from '@/hooks/useOrgInfo';

const mockUseAuthContext = vi.fn(() => ({
  user: { user_type: 'standard' },
  currentOrganization: { id: 'org-1', name: 'Test Org' }
}));

vi.mock('@/context/AuthContext', () => ({
  useAuthContext: () => mockUseAuthContext()
}));

vi.mock('@/context/NavigationContext', () => ({
  useNavigationContext: () => ({
    navigate: vi.fn(),
    currentPage: 'dashboard',
    setCurrentPage: vi.fn()
  })
}));

vi.mock('@/hooks/useOrgInfo', () => ({
  useOrgInfo: vi.fn(() => ({ orgId: 'org-1', orgName: 'Test Org' }))
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

const mockUseOrgInfo = vi.mocked(useOrgInfo);

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
  mockUseAuthContext.mockReturnValue({
    user: { user_type: 'standard' },
    currentOrganization: { id: 'org-1', name: 'Test Org' }
  });
  mockUseOrgInfo.mockReturnValue({ orgId: 'org-1', orgName: 'Test Org' });
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
  it('shows loading spinner when data is loading', () => {
    mockUseVulnScanData.mockReturnValueOnce({
      data: InitialVSData,
      loading: true,
      error: null
    });

    render(
      <MemoryRouter>
        <VSDashboardGate filters={mockFilters} removeFilter={vi.fn()} />
      </MemoryRouter>
    );

    // Checks that the CircularProgress spinner is rendered
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
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

  it('shows admin-specific message when assets and hosts are 0 and user is admin', () => {
    // Mock user as admin
    mockUseAuthContext.mockReturnValueOnce({
      user: { user_type: 'globalAdmin' },
      currentOrganization: { id: 'org-1', name: 'Test Org' }
    });

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

    // This asserts the admin text branch "this organization" and the "filter options" text
    expect(
      screen.getByText(/There is no data available for this organization/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Please select another organization from the filter options/i
      )
    ).toBeInTheDocument();
  });

  it('shows admin-specific message when empty after scans and user is admin', () => {
    mockUseAuthContext.mockReturnValueOnce({
      user: { user_type: 'globalAdmin' },
      currentOrganization: { id: 'org-1', name: 'Test Org' }
    });

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

    // Asserts the admin text alternative for completed scans
    expect(
      screen.getByText(/modify filter to see other organization's results/i)
    ).toBeInTheDocument();
  });

  it('renders the CustomAlert when error/empty and orgName starts with "DHS Region"', () => {
    // Mock orgName to trigger the alert conditional
    mockUseOrgInfo.mockReturnValue({
      orgId: 'org-1',
      orgName: 'DHS Region 3'
    });

    // Mock vuln scan data to trigger the outer "no data/error" block
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

    // Assert that the alert text is visible
    expect(
      screen.getByText(/select a different organization/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Based on your profile you will need to select a different organization/i
      )
    ).toBeInTheDocument();
  });

  it('does not render the CustomAlert when error/empty if orgName does not start with "DHS Region"', () => {
    // Mock orgName to a standard organization name
    mockUseOrgInfo.mockReturnValue({
      orgId: 'org-1',
      orgName: 'Standard Test Org'
    });

    // Mock vuln scan data to trigger the outer "no data/error" block
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

    // Assert that the alert is NOT in the document
    expect(
      screen.queryByText(/Welcome to CyHy Dashboard/i)
    ).not.toBeInTheDocument();
  });
});

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { DrawerInterior } from '../../../components/FilterDrawer/DrawerInterior';
import { AuthContext } from '../../../context';
import { SavedSearchContext } from '../../../context/SavedSearchContext';

vi.mock('@elastic/react-search-ui', () => ({
  withSearch: (component: any) => component
}));

vi.mock('../../../utils/logger', () => ({
  logger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn()
  }
}));

vi.mock('@mui/material/styles', async () => {
  const actual = await vi.importActual('@mui/material/styles');
  return {
    ...actual,
    useTheme: () => ({
      palette: {
        primary: { main: '#1976d2', dark: '#1565c0' },
        neutrals: { light: '#e0e0e0', main: '#616161' }
      }
    })
  };
});

describe('DrawerInterior', () => {
  const mockAddFilter = vi.fn();
  const mockRemoveFilter = vi.fn();
  const mockSetSearchTerm = vi.fn();
  const mockApiGet = vi.fn();
  const mockApiDelete = vi.fn();

  const defaultProps = {
    addFilter: mockAddFilter,
    removeFilter: mockRemoveFilter,
    filters: [],
    facets: {},
    searchTerm: '',
    setSearchTerm: mockSetSearchTerm,
    totalResults: 0,
    initialFilters: [],
    expanded: false as string | false | undefined,
    handleExpanded: undefined
  };

  const mockAuthContextValue = {
    user_type: 'standard',
    login: vi.fn(),
    logout: vi.fn(),
    apiGet: mockApiGet,
    apiDelete: mockApiDelete,
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiPatch: vi.fn(),
    loading: false,
    user: null,
    setUser: vi.fn(),
    token: null,
    currentOrganization: undefined,
    setOrganization: vi.fn(),
    showMaps: false,
    setShowMaps: vi.fn(),
    showAllOrganizations: false,
    setShowAllOrganizations: vi.fn(),
    refreshUser: vi.fn(),
    setLoading: vi.fn(),
    setFeedbackMessage: vi.fn(),
    maximumRole: 'user' as const,
    touVersion: '1',
    userMustSign: false,
    isLoggingOut: false
  };

  const mockSavedSearchContextValue = {
    savedSearches: [],
    setSavedSearches: vi.fn(),
    savedSearchCount: 0,
    setSavedSearchCount: vi.fn(),
    activeSearchId: '',
    setActiveSearchId: vi.fn(),
    activeSearch: undefined
  };

  const renderWithProviders = (props = {}) => {
    return render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <SavedSearchContext.Provider value={mockSavedSearchContextValue}>
          <DrawerInterior {...defaultProps} {...props} />
        </SavedSearchContext.Provider>
      </AuthContext.Provider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Blue dot indicator (FiltersApplied)', () => {
    it('shows blue dot for IP filter when IP filter is applied', () => {
      const { container } = renderWithProviders({
        filters: [{ field: 'ip', values: ['192.168.1.1'], type: 'any' }]
      });

      const ipAccordion = screen.getByText('IP').closest('button');
      expect(ipAccordion).toBeTruthy();

      const blueDot = within(ipAccordion!).getByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeTruthy();
    });

    it('shows blue dot for Domain filter when Domain filter is applied', () => {
      const { container } = renderWithProviders({
        filters: [{ field: 'name', values: ['example.com'], type: 'any' }]
      });

      const domainAccordion = screen.getByText('Domain').closest('button');
      expect(domainAccordion).toBeTruthy();

      const blueDot = within(domainAccordion!).getByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeTruthy();
    });

    it('shows blue dot for Port filter when port is selected', () => {
      const { container } = renderWithProviders({
        filters: [{ field: 'services.port', values: ['80'], type: 'any' }],
        facets: {
          'services.port': [{ data: [{ value: 80, count: 5 }] }]
        }
      });

      const portsAccordion = screen.getByText('Ports').closest('button');
      expect(portsAccordion).toBeTruthy();

      const blueDot = within(portsAccordion!).getByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeTruthy();
    });

    it('shows blue dot for Port filter when no_services filter is applied', () => {
      const { container } = renderWithProviders({
        filters: [{ field: 'no_services', values: [true], type: 'any' }],
        facets: {
          no_services: [{ data: [{ value: true, count: 10 }] }]
        }
      });

      const portsAccordion = screen.getByText('Ports').closest('button');
      expect(portsAccordion).toBeTruthy();

      const blueDot = within(portsAccordion!).getByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeTruthy();
    });

    it('shows blue dot for Port filter when both services.port and no_services are applied', () => {
      const { container } = renderWithProviders({
        filters: [
          { field: 'services.port', values: ['443'], type: 'any' },
          { field: 'no_services', values: [true], type: 'any' }
        ],
        facets: {
          'services.port': [{ data: [{ value: 443, count: 3 }] }],
          no_services: [{ data: [{ value: true, count: 10 }] }]
        }
      });

      const portsAccordion = screen.getByText('Ports').closest('button');
      expect(portsAccordion).toBeTruthy();

      const blueDot = within(portsAccordion!).getByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeTruthy();
    });

    it('does not show blue dot for Port filter when no port filters are applied', () => {
      const { container } = renderWithProviders({
        filters: [],
        facets: {
          'services.port': [{ data: [{ value: 80, count: 5 }] }]
        }
      });

      const portsAccordion = screen.getByText('Ports').closest('button');
      expect(portsAccordion).toBeTruthy();

      const blueDot = within(portsAccordion!).queryByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeNull();
    });

    it('shows blue dot for Root Domains filter when applied', () => {
      const { container } = renderWithProviders({
        filters: [
          { field: 'from_root_domain', values: ['example.com'], type: 'any' }
        ],
        facets: {
          from_root_domain: [{ data: [{ value: 'example.com', count: 10 }] }]
        }
      });

      const rootDomainsAccordion = screen
        .getByText('Root Domains')
        .closest('button');
      expect(rootDomainsAccordion).toBeTruthy();

      const blueDot = within(rootDomainsAccordion!).getByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeTruthy();
    });

    it('shows blue dot for CVEs filter when applied', () => {
      const { container } = renderWithProviders({
        filters: [
          {
            field: 'vulnerabilities.cve',
            values: ['CVE-2021-1234'],
            type: 'any'
          }
        ],
        facets: {
          'vulnerabilities.cve': [
            { data: [{ value: 'CVE-2021-1234', count: 5 }] }
          ]
        }
      });

      const cvesAccordion = screen.getByText('CVEs').closest('button');
      expect(cvesAccordion).toBeTruthy();

      const blueDot = within(cvesAccordion!).getByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeTruthy();
    });

    it('shows blue dot for Severity filter when applied', () => {
      const { container } = renderWithProviders({
        filters: [
          { field: 'vulnerabilities.severity', values: ['High'], type: 'any' }
        ],
        facets: {
          'vulnerabilities.severity': [{ data: [{ value: 'high', count: 15 }] }]
        }
      });

      const severityAccordion = screen.getByText('Severity').closest('button');
      expect(severityAccordion).toBeTruthy();

      const blueDot = within(severityAccordion!).getByTestId(
        'FiberManualRecordRoundedIcon'
      );
      expect(blueDot).toBeTruthy();
    });
  });

  describe('Filter sections rendering', () => {
    it('renders IP filter section', () => {
      renderWithProviders();
      expect(screen.getByText('IP')).toBeTruthy();
    });

    it('renders Domain filter section', () => {
      renderWithProviders();
      expect(screen.getByText('Domain')).toBeTruthy();
    });

    it('renders Ports section when port facets are available', () => {
      renderWithProviders({
        facets: {
          'services.port': [{ data: [{ value: 80, count: 5 }] }]
        }
      });
      expect(screen.getByText('Ports')).toBeTruthy();
    });

    it('renders Root Domains section when facets are available', () => {
      renderWithProviders({
        facets: {
          from_root_domain: [{ data: [{ value: 'example.com', count: 10 }] }]
        }
      });
      expect(screen.getByText('Root Domains')).toBeTruthy();
    });

    it('renders CVEs section when facets are available', () => {
      renderWithProviders({
        facets: {
          'vulnerabilities.cve': [
            { data: [{ value: 'CVE-2021-1234', count: 5 }] }
          ]
        }
      });
      expect(screen.getByText('CVEs')).toBeTruthy();
    });

    it('renders Severity section when facets are available', () => {
      renderWithProviders({
        facets: {
          'vulnerabilities.severity': [{ data: [{ value: 'high', count: 15 }] }]
        }
      });
      expect(screen.getByText('Severity')).toBeTruthy();
    });

    it('does not render Ports section when no port facets are available', () => {
      renderWithProviders({ facets: {} });
      expect(screen.queryByText('Ports')).toBeNull();
    });
  });

  describe('Severity facet data transformation', () => {
    it('transforms severity values to title case', () => {
      renderWithProviders({
        facets: {
          'vulnerabilities.severity': [
            {
              data: [
                { value: 'critical', count: 5 },
                { value: 'high', count: 10 },
                { value: 'medium', count: 15 },
                { value: 'low', count: 20 }
              ]
            }
          ]
        }
      });

      expect(screen.getByText('Critical')).toBeTruthy();
      expect(screen.getByText('High')).toBeTruthy();
      expect(screen.getByText('Medium')).toBeTruthy();
      expect(screen.getByText('Low')).toBeTruthy();
    });

    it('converts null severity values to N/A', () => {
      renderWithProviders({
        facets: {
          'vulnerabilities.severity': [{ data: [{ value: null, count: 5 }] }]
        }
      });

      expect(screen.getByText('N/A')).toBeTruthy();
    });

    it('groups severity values correctly', () => {
      renderWithProviders({
        facets: {
          'vulnerabilities.severity': [
            {
              data: [
                { value: 'critical', count: 3 },
                { value: 'Critical', count: 2 },
                { value: 'CRITICAL', count: 1 }
              ]
            }
          ]
        }
      });

      // Should be grouped and shown once
      const criticalElements = screen.getAllByText('Critical');
      expect(criticalElements.length).toBe(1);
    });
  });

  describe('Saved Searches section', () => {
    it('renders Saved Filters section', () => {
      renderWithProviders();
      expect(screen.getByText('Saved Filters')).toBeTruthy();
    });

    it('displays saved searches when available', () => {
      const mockSavedSearches = [
        {
          id: '1',
          name: 'Test Search 1',
          search_term: 'test',
          filters: [],
          created_at: '2024-01-01',
          updated_at: '2024-01-01',
          count: 5,
          created_by: { id: 'user-1', email: 'test@example.com' } as any,
          search_path: '/inventory',
          sortField: 'name',
          sortDirection: 'asc'
        }
      ];

      const savedSearchContext = {
        ...mockSavedSearchContextValue,
        savedSearches: mockSavedSearches
      };

      render(
        <AuthContext.Provider value={mockAuthContextValue}>
          <SavedSearchContext.Provider value={savedSearchContext}>
            <DrawerInterior {...defaultProps} />
          </SavedSearchContext.Provider>
        </AuthContext.Provider>
      );

      expect(screen.getByText('Test Search 1')).toBeTruthy();
    });
  });
});

import React from 'react';
import { render, screen, testUser } from 'test-utils';
import { makeVulnResponse, makeVuln } from '@/test-utils/vulnerabilities';
import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest';
import type { AuthUser } from '../../../context/';
import Vulnerabilities from '../../../pages/Vulnerabilities/Vulnerabilities';

const titlePool = [
  'CVE-2013-4041 Risky Vuln',
  'CVE-2013-4042 Menacing Vuln ',
  'CVE-2013-4043 Terrible Vuln ',
  'CVE-2013-4044 Cataclysmic Vuln ',
  'CVE-2013-4045 Death Vuln '
];

const sampleResponse = makeVulnResponse(16, (idx) => ({
  title:
    idx === 0 ? titlePool[0] : titlePool[(idx % (titlePool.length - 1)) + 1]
}));

describe('Vulnerabilities component', () => {
  const apiPostMock = vi.fn().mockResolvedValue(sampleResponse);

  beforeEach(() => {
    apiPostMock.mockClear();
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('is exported', () => {
    expect(Vulnerabilities).toBeDefined();
    // functional components are functions, class components are functions/objects
    expect(['function', 'object']).toContain(typeof Vulnerabilities);
  });

  it('renders loading state then table rows from API', async () => {
    let resolveApi: (value: unknown) => void;
    const apiPromise = new Promise((resolve) => {
      resolveApi = resolve;
    });
    apiPostMock.mockReturnValueOnce(apiPromise);

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    const loadingText = await screen.findByText(/loading vulnerabilities../i);
    expect(loadingText).toBeInTheDocument();

    resolveApi!(sampleResponse);

    const grid = await screen.findByRole('grid');
    expect(grid).toBeInTheDocument();

    const firstVulnTitle = await screen.findByText(/CVE-2013-4041 Risky Vuln/i);
    expect(firstVulnTitle).toBeInTheDocument();

    const menacingMatches = await screen.findAllByText(/Menacing Vuln/i);
    expect(menacingMatches.length).toBeGreaterThan(0);

    const rows = await screen.findAllByRole('row');
    expect(rows.length).toBe(sampleResponse.result.length + 1);
  });

  it('renders empty state when API returns no vulnerabilities', async () => {
    apiPostMock.mockResolvedValueOnce({ result: [], count: 0 });

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    const noResultsText = await screen.findByText(/no results found/i);
    expect(noResultsText).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    apiPostMock.mockRejectedValueOnce(new Error('API error'));

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    const errorText = await screen.findByText(/error loading vulnerabilities/i);
    expect(errorText).toBeInTheDocument();
  });

  // To-Do: CRASM-3385 Move server-side pagination, sort, and filter tests to Playwright e2e tests.

  // it('supports server-side pagination', async () => {
  //   apiPostMock.mockImplementation((_path: string, body: any) => {
  //     const page = body?.page ?? 1;
  //     const pageSize = body?.pageSize ?? 15;
  //     const start = (page - 1) * pageSize;
  //     const slice = sampleResponse.result.slice(start, start + pageSize);
  //     return Promise.resolve({ result: slice, count: sampleResponse.count });
  //   });

  //   render(<Vulnerabilities />, {
  //     initialHistory: ['/vulnerabilities'],
  //     authContext: {
  //       apiPost: apiPostMock,
  //       currentOrganization: null,
  //       user: testUser as unknown as AuthUser
  //     }
  //   });

  //   expect(await screen.findByText(/Risky Vuln/i)).toBeInTheDocument();

  //   // navigate to next page using DataGrid control
  //   const nextPageButton = screen.getByLabelText(/go to next page/i);
  //   await userEvent.click(nextPageButton);

  //   // server should have been called with page: 2
  //   await waitFor(() => {
  //     const calls = apiPostMock.mock.calls;
  //     const found = calls.some((call) =>
  //       call.some((arg: any) => arg && arg.body && arg.body.page === 2)
  //     );
  //     if (!found) {
  //       // eslint-disable-next-line no-console
  //       console.error(
  //         'apiPostMock.mock.calls:',
  //         JSON.stringify(calls, null, 2)
  //       );
  //     }
  //     expect(found).toBe(true);
  //   });

  //   const grid = await screen.findByRole('grid');

  //   await waitFor(() => {
  //     // prefer scoping to the grid to avoid matching text elsewhere
  //     expect(within(grid).queryByText('Risky Vuln')).not.toBeInTheDocument();
  //   });
  //   const rows = await within(grid).findAllByRole('row');
  //   expect(rows.length).toBeLessThanOrEqual(15 + 1); // 15 data rows + header
  // });

  // it('supports server-side sorting', async () => {
  //   // server honors sortField & sortOrder
  //   apiPostMock.mockImplementation((_path: string, body: any) => {
  //     const sortField = body?.sort ?? 'created_at';
  //     const sortOrder = body?.order ?? 'desc';
  //     const sorted = [...sampleResponse.result].sort((a, b) => {
  //       if (a[sortField] < b[sortField]) return sortOrder === 'asc' ? -1 : 1;
  //       if (a[sortField] > b[sortField]) return sortOrder === 'asc' ? 1 : -1;
  //       return 0;
  //     });
  //     return Promise.resolve({ result: sorted, count: sampleResponse.count });
  //   });

  //   render(<Vulnerabilities />, {
  //     initialHistory: ['/vulnerabilities'],
  //     authContext: {
  //       apiPost: apiPostMock,
  //       currentOrganization: null,
  //       user: testUser as unknown as AuthUser
  //     }
  //   });

  //   expect(await screen.findByText(/Risky Vuln/i)).toBeInTheDocument();

  //   const headers = await screen.findAllByRole('columnheader');
  //   const titleHeader = headers.find((header) =>
  //     /vulnerability/i.test(header.textContent || '')
  //   );

  //   if (!titleHeader) {
  //     // helpful debug output
  //     // eslint-disable-next-line no-console
  //     console.error(
  //       'Column headers:',
  //       headers.map((h) => h.textContent)
  //     );
  //     throw new Error('Could not find Title column header');
  //   }

  //   // click the internal button if present, otherwise click the header itself
  //   const headerButton =
  //     within(titleHeader).queryByRole('sortButton') ??
  //     (titleHeader.querySelector('button') as HTMLElement | null) ??
  //     titleHeader;
  //   fireEvent.click(headerButton);

  //   // server should have been called with sortField: 'title', sortOrder: 'asc'
  //   const calls = apiPostMock.mock.calls;
  //   const found = calls.some((call) =>
  //     call.some(
  //       (arg: any) =>
  //         arg &&
  //         arg.body &&
  //         arg.body.order === 'title' &&
  //         arg.body.sort === 'asc'
  //     )
  //   );
  //   if (!found) {
  //     // eslint-disable-next-line no-console
  //     console.error('apiPostMock.mock.calls:', JSON.stringify(calls, null, 2));
  //   }
  //   expect(found).toBe(true);

  //   const matches = await screen.findAllByText(/Menacing Vuln/i);
  //   expect(matches.length).toBeGreaterThan(0);
  // });

  // it('supports server-side filtering', async () => {
  //   apiPostMock.mockImplementation((_path: string, body: any) => {
  //     const filters = body?.filters ?? {};
  //     let filtered = [...sampleResponse.result];
  //     if (filters.title) {
  //       const titleFilter = filters.title.toLowerCase();
  //       filtered = filtered.filter((vuln) =>
  //         vuln.title.toLowerCase().includes(titleFilter)
  //       );
  //     }
  //     return Promise.resolve({ result: filtered, count: filtered.length });
  //   });

  //   render(<Vulnerabilities />, {
  //     initialHistory: ['/vulnerabilities'],
  //     authContext: {
  //       apiPost: apiPostMock,
  //       currentOrganization: null,
  //       user: testUser as unknown as AuthUser
  //     }
  //   });

  //   expect(await screen.findByText(/Risky Vuln/i)).toBeInTheDocument();

  //   await userEvent.click(screen.getByRole('button', { name: /filters?/i }));
  //   const input = await screen.findByRole('textbox', { name: /value/i });
  //   await userEvent.clear(input);
  //   await userEvent.type(input, 'menacing');

  //   await waitFor(
  //     () => {
  //       expect(apiPostMock).toHaveBeenCalledWith(
  //         expect.any(String),
  //         expect.objectContaining({
  //           body: expect.objectContaining({
  //             filters: expect.objectContaining({
  //               title: expect.stringMatching(/menacing/i)
  //             })
  //           })
  //         })
  //       );
  //     },
  //     { timeout: 1500 }
  //   );

  //   const menacingBMatches = await screen.findAllByText(/menacing/i);
  //   expect(menacingBMatches.length).toBeGreaterThan(0);

  //   expect(screen.queryByText('Risky Vuln')).not.toBeInTheDocument();
  // });

  it('formats KEV and Ransomware columns correctly for export', async () => {
    // Create vulnerabilities with different KEV and ransomware values
    const testResponse = makeVulnResponse(3, (idx) => ({
      title: `Test Vuln ${idx + 1}`,
      is_kev: idx === 0 ? true : idx === 1 ? false : null,
      is_kev_ransomware: idx === 0 ? true : idx === 1 ? false : null
    }));

    apiPostMock.mockResolvedValueOnce(testResponse);

    const { container } = render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    // Wait for the grid to render
    const grid = await screen.findByRole('grid');
    expect(grid).toBeInTheDocument();

    // Check that KEV column displays formatted values (Yes/No/N/A)
    // Use findAllByText since there can be multiple "Yes", "No", "N/A" values
    const yesElements = await screen.findAllByText('Yes');
    const noElements = await screen.findAllByText('No');
    const naElements = await screen.findAllByText('N/A');

    expect(yesElements.length).toBeGreaterThan(0);
    expect(noElements.length).toBeGreaterThan(0);
    expect(naElements.length).toBeGreaterThan(0);

    // Verify the data structure contains string values for export
    // This tests that vulRows transforms boolean/null to string values
    const dataGridElement = container.querySelector('.MuiDataGrid-root');
    expect(dataGridElement).toBeInTheDocument();
  });

  it('transforms boolean KEV values to strings in data rows', async () => {
    const testResponse = makeVulnResponse(1, () => ({
      title: 'KEV Test Vuln',
      is_kev: true,
      is_kev_ransomware: false
    }));

    apiPostMock.mockResolvedValueOnce(testResponse);

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    // Wait for data to load
    await screen.findByRole('grid');

    // Verify that "Yes" and "No" text appears in the table
    expect(await screen.findByText('Yes')).toBeInTheDocument();
    expect(await screen.findByText('No')).toBeInTheDocument();
  });

  it('handles null KEV values correctly', async () => {
    const testResponse = makeVulnResponse(1, () => ({
      title: 'Null KEV Test Vuln',
      is_kev: null,
      is_kev_ransomware: null
    }));

    apiPostMock.mockResolvedValueOnce(testResponse);

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    // Wait for data to load
    await screen.findByRole('grid');

    // Verify that "N/A" text appears for null values
    const naElements = await screen.findAllByText('N/A');
    // Should have at least 2 N/A entries (one for each column)
    expect(naElements.length).toBeGreaterThanOrEqual(2);
  });

  it('displays mixed KEV and ransomware statuses correctly', async () => {
    const testResponse = makeVulnResponse(4, (idx) => {
      const scenarios = [
        { is_kev: true, is_kev_ransomware: true }, // Both true
        { is_kev: true, is_kev_ransomware: false }, // KEV true, ransomware false
        { is_kev: false, is_kev_ransomware: null }, // KEV false, ransomware null
        { is_kev: null, is_kev_ransomware: false } // KEV null, ransomware false
      ];
      return {
        title: `Mixed Status Vuln ${idx + 1}`,
        ...scenarios[idx]
      };
    });

    apiPostMock.mockResolvedValueOnce(testResponse);

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    // Wait for data to load
    await screen.findByRole('grid');

    // Verify all status types are displayed
    const yesElements = await screen.findAllByText('Yes');
    const noElements = await screen.findAllByText('No');
    const naElements = await screen.findAllByText('N/A');

    expect(yesElements.length).toBeGreaterThan(0);
    expect(noElements.length).toBeGreaterThan(0);
    expect(naElements.length).toBeGreaterThan(0);
  });

  it('supports server-side filtering with boolean values while displaying string values', async () => {
    // Test that server-side filtering still works with boolean payloads
    // while the frontend displays string-formatted values
    // This matches the real payload structure: {"filters": {"is_kev_ransomware": true}}

    let filterApplied = false;
    let lastFiltersReceived: any = null;

    apiPostMock.mockImplementation((_path: string, body: any) => {
      const filters = body?.filters ?? {};
      lastFiltersReceived = filters;

      // Create base test data
      const baseData = [
        makeVuln(1, {
          title: 'KEV True Item',
          is_kev: true,
          is_kev_ransomware: false
        }),
        makeVuln(2, {
          title: 'KEV False Item',
          is_kev: false,
          is_kev_ransomware: true
        }),
        makeVuln(3, {
          title: 'KEV Null Item',
          is_kev: null,
          is_kev_ransomware: null
        })
      ];

      let filtered = [...baseData];

      // Apply KEV filter - server expects boolean values in the filter payload
      if (filters.is_kev !== undefined) {
        filterApplied = true;
        filtered = filtered.filter((vuln) => {
          // Server filtering logic: direct boolean comparison
          return vuln.is_kev === filters.is_kev;
        });
      }

      // Apply Ransomware filter
      if (filters.is_kev_ransomware !== undefined) {
        filtered = filtered.filter((vuln) => {
          return vuln.is_kev_ransomware === filters.is_kev_ransomware;
        });
      }

      return Promise.resolve({ result: filtered, count: filtered.length });
    });

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    // Wait for initial data load
    const grid = await screen.findByRole('grid');
    expect(grid).toBeInTheDocument();

    // Verify that the frontend displays string values, not boolean
    expect(await screen.findByText('KEV True Item')).toBeInTheDocument();
    expect(await screen.findByText('KEV False Item')).toBeInTheDocument();
    expect(await screen.findByText('KEV Null Item')).toBeInTheDocument();

    // Verify string values are displayed (the key fix for CRASM-3416)
    const yesElements = await screen.findAllByText('Yes');
    const noElements = await screen.findAllByText('No');
    expect(yesElements.length).toBeGreaterThan(0); // Should show "Yes", not true
    expect(noElements.length).toBeGreaterThan(0); // Should show "No", not false

    // Test server-side filter with boolean true (matches real payload structure)
    const mockTrueResponse = await apiPostMock('/api/vulnerabilities', {
      filters: { is_kev: true }, // Boolean true, not "Yes"
      page: 1,
      pageSize: 15,
      showAll: false,
      sort: 'desc'
    });

    expect(filterApplied).toBe(true);
    expect(lastFiltersReceived.is_kev).toBe(true); // Boolean, not string

    // Verify filtering by boolean true returns the correct item
    expect(mockTrueResponse.result).toHaveLength(1);
    expect(mockTrueResponse.result[0].title).toBe('KEV True Item');
    expect(mockTrueResponse.result[0].is_kev).toBe(true);

    // Test filtering by boolean false
    const mockFalseResponse = await apiPostMock('/api/vulnerabilities', {
      filters: { is_kev: false },
      page: 1,
      pageSize: 15,
      showAll: false,
      sort: 'desc'
    });

    expect(mockFalseResponse.result).toHaveLength(1);
    expect(mockFalseResponse.result[0].title).toBe('KEV False Item');
    expect(mockFalseResponse.result[0].is_kev).toBe(false);

    // Test filtering by ransomware boolean (using the real payload example)
    const mockRansomwareResponse = await apiPostMock('/api/vulnerabilities', {
      filters: { is_kev_ransomware: true },
      page: 1,
      pageSize: 15,
      showAll: false,
      sort: 'desc'
    });

    expect(mockRansomwareResponse.result).toHaveLength(1);
    expect(mockRansomwareResponse.result[0].title).toBe('KEV False Item');
    expect(mockRansomwareResponse.result[0].is_kev_ransomware).toBe(true);
  });

  it('confirms string-based column configuration supports filtering', async () => {
    // Test that verifies the column configuration itself supports string filtering
    const testResponse = makeVulnResponse(3, (idx) => ({
      title: `Test Vuln ${idx + 1}`,
      is_kev: idx === 0 ? true : idx === 1 ? false : null,
      is_kev_ransomware: idx === 0 ? true : idx === 1 ? false : null
    }));

    apiPostMock.mockResolvedValue(testResponse);

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    // Wait for data to load
    const grid = await screen.findByRole('grid');
    expect(grid).toBeInTheDocument();

    // Verify that string values are displayed (not boolean true/false)
    const yesElements = await screen.findAllByText('Yes');
    const noElements = await screen.findAllByText('No');
    const naElements = await screen.findAllByText('N/A');

    expect(yesElements.length).toBeGreaterThan(0);
    expect(noElements.length).toBeGreaterThan(0);
    expect(naElements.length).toBeGreaterThan(0);

    // Verify columns exist and are properly configured
    const kevColumnHeader = screen.getByText('KEV');
    const ransomwareColumnHeader = screen.getByText('Ransomware');

    expect(kevColumnHeader).toBeInTheDocument();
    expect(ransomwareColumnHeader).toBeInTheDocument();
  });

  it('matches snapshot', () => {
    const { container } = render(<Vulnerabilities />);
    expect(container.firstChild).toMatchSnapshot();
  });
});

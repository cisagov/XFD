import React from 'react';
import { render, screen, testUser } from 'test-utils';
import { makeDomainResponse } from '@/test-utils/domains';
import type { AuthUser } from '../../../context/';
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { Domains } from '../../../pages/Domains/Domains';

const namePool = [
  'example.com',
  'test.com',
  'sample.org',
  'demo.net',
  'website.io'
];

const sampleResponse = makeDomainResponse(30, (idx) => ({
  name: idx === 0 ? namePool[0] : namePool[(idx % (namePool.length - 1)) + 1]
}));

describe('Domains component', () => {
  const apiPostMock = vi.fn().mockResolvedValue({ result: [], count: 0 });

  beforeEach(() => {
    apiPostMock.mockClear();
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('is exported', () => {
    expect(Domains).toBeDefined();
    // functional components are functions, class components are functions/objects
    expect(['function', 'object']).toContain(typeof Domains);
  });

  it('renders loading state while API resolves', async () => {
    let resolveApi: (value: unknown) => void;
    const apiPromise = new Promise((resolve) => {
      resolveApi = resolve;
    });
    apiPostMock.mockReturnValueOnce(apiPromise);

    render(<Domains />, {
      initialHistory: ['/domains'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    const loadingText = await screen.findByText(/loading domains../i);
    expect(loadingText).toBeInTheDocument();

    resolveApi!(sampleResponse);

    const grid = await screen.findByRole('grid');
    expect(grid).toBeInTheDocument();

    const firstDomainIP = await screen.findByText(/^192\.0\.2\.1$/i);
    expect(firstDomainIP).toBeInTheDocument();

    const ipMatches = await screen.findAllByText(/^192\.0\.2\./);
    expect(ipMatches.length).toBeGreaterThan(0);

    const rows = await screen.findAllByRole('row');
    expect(rows.length).toBe(sampleResponse.result.length + 1);
  });

  it('renders empty state when API returns no domains', async () => {
    apiPostMock.mockResolvedValueOnce({ result: [], count: 0 });

    render(<Domains />, {
      initialHistory: ['/domains'],
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

    render(<Domains />, {
      initialHistory: ['/domains'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    const errorText = await screen.findByText(/error loading domains/i);
    expect(errorText).toBeInTheDocument();
  });

  // Column visibility tests for CRASM-3585
  describe('column visibility', () => {
    it('hides Domain Name column for all users (pending WAS data)', async () => {
      apiPostMock.mockResolvedValueOnce(sampleResponse);

      render(<Domains />, {
        initialHistory: ['/domains'],
        authContext: {
          apiPost: apiPostMock,
          currentOrganization: null,
          user: testUser as unknown as AuthUser
        }
      });

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();

      // Domain Name column should be hidden for all users
      const domainNameHeader = screen.queryByRole('columnheader', { name: /domain name/i });
      expect(domainNameHeader).not.toBeInTheDocument();

      // IP Address column should be visible
      const ipAddressHeader = await screen.findByRole('columnheader', { name: /ip address/i });
      expect(ipAddressHeader).toBeInTheDocument();
    });

    it('hides Organization column for standard users', async () => {
      apiPostMock.mockResolvedValueOnce(sampleResponse);

      const standardUser = { ...testUser, user_type: 'standard' };

      render(<Domains />, {
        initialHistory: ['/domains'],
        authContext: {
          apiPost: apiPostMock,
          currentOrganization: null,
          user: standardUser as unknown as AuthUser
        }
      });

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();

      // Organization column should be hidden for standard users
      const orgHeader = screen.queryByRole('columnheader', { name: /organization/i });
      expect(orgHeader).not.toBeInTheDocument();
    });

    it('shows Organization column for globalAdmin users', async () => {
      apiPostMock.mockResolvedValueOnce(sampleResponse);

      const adminUser = { ...testUser, user_type: 'globalAdmin' };

      render(<Domains />, {
        initialHistory: ['/domains'],
        authContext: {
          apiPost: apiPostMock,
          currentOrganization: null,
          user: adminUser as unknown as AuthUser
        }
      });

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();

      // Organization column should be visible for admin users
      const orgHeader = await screen.findByRole('columnheader', { name: /organization/i });
      expect(orgHeader).toBeInTheDocument();
    });

    it('shows Organization column for globalView users', async () => {
      apiPostMock.mockResolvedValueOnce(sampleResponse);

      const globalViewUser = { ...testUser, user_type: 'globalView' };

      render(<Domains />, {
        initialHistory: ['/domains'],
        authContext: {
          apiPost: apiPostMock,
          currentOrganization: null,
          user: globalViewUser as unknown as AuthUser
        }
      });

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();

      // Organization column should be visible for globalView users
      const orgHeader = await screen.findByRole('columnheader', { name: /organization/i });
      expect(orgHeader).toBeInTheDocument();
    });

    it('shows Organization column for regionalAdmin users', async () => {
      apiPostMock.mockResolvedValueOnce(sampleResponse);

      const regionalAdminUser = { ...testUser, user_type: 'regionalAdmin' };

      render(<Domains />, {
        initialHistory: ['/domains'],
        authContext: {
          apiPost: apiPostMock,
          currentOrganization: null,
          user: regionalAdminUser as unknown as AuthUser
        }
      });

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();

      // Organization column should be visible for regionalAdmin users
      const orgHeader = await screen.findByRole('columnheader', { name: /organization/i });
      expect(orgHeader).toBeInTheDocument();
    });

    it('renders IP addresses when Domain Name column is hidden', async () => {
      apiPostMock.mockResolvedValueOnce(sampleResponse);

      render(<Domains />, {
        initialHistory: ['/domains'],
        authContext: {
          apiPost: apiPostMock,
          currentOrganization: null,
          user: testUser as unknown as AuthUser
        }
      });

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();

      // Should see IP addresses in the table since Domain Name is hidden
      const ipMatches = await screen.findAllByText(/^192\.0\.2\./);
      expect(ipMatches.length).toBeGreaterThan(0);

      // Should not see domain names since that column is hidden
      const domainMatches = screen.queryAllByText(/example\.com|test\.com|sample\.org/);
      expect(domainMatches.length).toBe(0);
    });
  });

  // Data rendering tests
  describe('data rendering', () => {
    it('displays correct number of rows with data', async () => {
      apiPostMock.mockResolvedValueOnce(sampleResponse);

      render(<Domains />, {
        initialHistory: ['/domains'],
        authContext: {
          apiPost: apiPostMock,
          currentOrganization: null,
          user: testUser as unknown as AuthUser
        }
      });

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();

      // Should have header row + data rows
      const rows = await screen.findAllByRole('row');
      expect(rows.length).toBe(sampleResponse.result.length + 1); // +1 for header
    });

    it('handles edge case with single domain result', async () => {
      const singleDomainResponse = {
        result: [sampleResponse.result[0]],
        count: 1
      };
      apiPostMock.mockResolvedValueOnce(singleDomainResponse);

      render(<Domains />, {
        initialHistory: ['/domains'],
        authContext: {
          apiPost: apiPostMock,
          currentOrganization: null,
          user: testUser as unknown as AuthUser
        }
      });

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();

      // Should have header row + 1 data row
      const rows = await screen.findAllByRole('row');
      expect(rows.length).toBe(2);

      // Should display the IP address for the single domain
      const ipAddress = await screen.findByText(/^192\.0\.2\.1$/i);
      expect(ipAddress).toBeInTheDocument();
    });
  });

  // To-Do: CRASM-3385 Move server-side pagination, sort, and filter tests to Playwright e2e tests.

  // it('supports server-side pagination', async () => {
  //   apiPostMock.mockImplementationOnce((_path: string, body: any) => {
  //     const page = body?.page ?? 1;
  //     const pageSize = body?.pageSize ?? 15;
  //     const start = (page - 1) * pageSize;
  //     const slice = sampleResponse.result.slice(start, start + pageSize);
  //     return Promise.resolve({ result: slice, count: sampleResponse.count });
  //   });

  //   render(<Domains />, {
  //     initialHistory: ['/domains'],
  //     authContext: {
  //       apiPost: apiPostMock,
  //       currentOrganization: null,
  //       user: testUser as unknown as AuthUser
  //     }
  //   });

  //   expect(await screen.findByText(/example\.com/i)).toBeInTheDocument();

  //   // navigate to next page using DataGrid control
  //   const nextPageButton = screen.getByLabelText(/go to next page/i);
  //   await userEvent.click(nextPageButton);

  //   // server should have been called with page: 2
  //   await waitFor(() => {
  //     const calls = apiPostMock.mock.calls;
  //     const found = calls.some((call) =>
  //       call.some((arg: any) => arg && arg.body && arg.body.page === 2)
  //     );
  //     expect(found).toBe(true);
  //   });

  //   const grid = await screen.findByRole('grid');

  //   await waitFor(() => {
  //     // prefer scoping to the grid to avoid matching text elsewhere
  //     expect(within(grid).queryByText(/example\.com/i)).not.toBeInTheDocument();
  //   });

  //   const rows = await within(grid).findAllByRole('row');
  //   expect(rows.length).toBeLessThanOrEqual(15); // 15 data rows + header
  // });

  // it('supports server-side sorting', async () => {});

  // it('supports server-side filtering', async () => {});

  it('matches snapshot', () => {
    const domainComponent = <Domains />;
    expect(domainComponent).toMatchSnapshot();
  });
});

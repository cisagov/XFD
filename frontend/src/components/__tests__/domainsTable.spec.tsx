import React from 'react';
import { render, screen, testUser, waitFor, within } from 'test-utils';
import { makeDomainResponse } from '@/test-utils/domains';
import userEvent from '@testing-library/user-event';
import type { AuthUser } from '../../context/';
import { describe, it, expect, vi } from 'vitest';
import { Domains } from '../../pages/Domains/Domains';
import { a } from 'vitest/dist/chunks/suite.d.FvehnV49';

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

    const firstDomainName = await screen.findByText(/^example\.com$/i);
    expect(firstDomainName).toBeInTheDocument();

    const websiteMatches = await screen.findAllByText(/^website\.io$/i);
    expect(websiteMatches.length).toBeGreaterThan(0);

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

import React from 'react';
import {
  fireEvent,
  render,
  screen,
  testUser,
  waitFor,
  within
} from 'test-utils';
import { makeVulnResponse } from '@/test-utils/vulnerabilities';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import type { AuthUser } from '../../context/';
import Vulnerabilities from '../../pages/Vulnerabilities/Vulnerabilities';

const titlePool = [
  'CVE-2013-4041 Risky Vuln',
  'CVE-2013-4042 Menacing Vuln ',
  'CVE-2013-4043 Terrible Vuln ',
  'CVE-2013-4044 Cataclysmic Vuln ',
  'CVE-2013-4045 Death Vuln '
];

const sampleResponse = makeVulnResponse(30, (idx) => ({
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

  it('renders loading state then table rows from apiPost', async () => {
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

    // Wait for the table rows to appear
    resolveApi!(sampleResponse);
    const firstVulnTitle = await screen.findByText(/CVE-2013-4041 Risky Vuln/i);
    const menacingMatches = await screen.findAllByText(/Menacing Vuln/i);
    expect(firstVulnTitle).toBeInTheDocument();
    expect(menacingMatches.length).toBeGreaterThan(0);
  });

  it('supports server-side pagination', async () => {
    apiPostMock.mockImplementation((_path: string, body: any) => {
      const page = body?.page ?? 1;
      const pageSize = body?.pageSize ?? 15;
      const start = (page - 1) * pageSize;
      const slice = sampleResponse.result.slice(start, start + pageSize);
      return Promise.resolve({ result: slice, count: sampleResponse.count });
    });

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    expect(await screen.findByText(/Risky Vuln/i)).toBeInTheDocument();
    const menacingOnFirst = await screen.findAllByText(/Menacing Vuln/i);
    expect(menacingOnFirst.length).toBeGreaterThan(0);

    // navigate to next page using DataGrid control
    const nextButton = screen.getByLabelText(/go to next page/i);
    fireEvent.click(nextButton);

    // server should have been called with page: 2
    const calls = apiPostMock.mock.calls;
    const found = calls.some((call) =>
      call.some((arg: any) => arg && arg.body && arg.body.page === 2)
    );
    if (!found) {
      // eslint-disable-next-line no-console
      console.error('apiPostMock.mock.calls:', JSON.stringify(calls, null, 2));
    }
    expect(found).toBe(true);
    expect(await screen.findByText(/Risky Vuln/i)).toBeInTheDocument();
    const menacingOnSecond = await screen.findAllByText(/Menacing Vuln/i);
    expect(menacingOnSecond.length).toBeGreaterThan(0);
  });

  it('supports server-side sorting', async () => {
    // server honors sortField & sortOrder
    apiPostMock.mockImplementation((_path: string, body: any) => {
      const sortField = body?.sort ?? 'created_at';
      const sortOrder = body?.order ?? 'desc';
      const sorted = [...sampleResponse.result].sort((a, b) => {
        if (a[sortField] < b[sortField]) return sortOrder === 'asc' ? -1 : 1;
        if (a[sortField] > b[sortField]) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
      return Promise.resolve({ result: sorted, count: sampleResponse.count });
    });

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    expect(await screen.findByText(/Risky Vuln/i)).toBeInTheDocument();

    const headers = await screen.findAllByRole('columnheader');
    const titleHeader = headers.find((header) =>
      /vulnerability/i.test(header.textContent || '')
    );

    if (!titleHeader) {
      // helpful debug output
      // eslint-disable-next-line no-console
      console.error(
        'Column headers:',
        headers.map((h) => h.textContent)
      );
      throw new Error('Could not find Title column header');
    }

    // click the internal button if present, otherwise click the header itself
    const headerButton =
      within(titleHeader).queryByRole('sortButton') ??
      (titleHeader.querySelector('button') as HTMLElement | null) ??
      titleHeader;
    fireEvent.click(headerButton);

    // server should have been called with sortField: 'title', sortOrder: 'asc'
    const calls = apiPostMock.mock.calls;
    const found = calls.some((call) =>
      call.some(
        (arg: any) =>
          arg &&
          arg.body &&
          arg.body.order === 'title' &&
          arg.body.sort === 'asc'
      )
    );
    if (!found) {
      // eslint-disable-next-line no-console
      console.error('apiPostMock.mock.calls:', JSON.stringify(calls, null, 2));
    }
    expect(found).toBe(true);

    const matches = await screen.findAllByText(/Menacing Vuln/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  it('supports server-side filtering', async () => {
    apiPostMock.mockImplementation((_path: string, body: any) => {
      const filters = body?.filters ?? {};
      let filtered = [...sampleResponse.result];
      if (filters.title) {
        const titleFilter = filters.title.toLowerCase();
        filtered = filtered.filter((vuln) =>
          vuln.title.toLowerCase().includes(titleFilter)
        );
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

    expect(await screen.findByText(/Risky Vuln/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /filters?/i }));
    const input = await screen.findByRole('textbox', { name: /value/i });
    await userEvent.clear(input);
    await userEvent.type(input, 'menacing');

    await waitFor(
      () => {
        expect(apiPostMock).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            body: expect.objectContaining({
              filters: expect.objectContaining({
                title: expect.stringMatching(/menacing/i)
              })
            })
          })
        );
      },
      { timeout: 1500 }
    );

    const menacingBMatches = await screen.findAllByText(/menacing/i);
    expect(menacingBMatches.length).toBeGreaterThan(0);
  });

  it('renders empty state when api returns no results', async () => {
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

  it('matches snapshot', () => {
    const { container } = render(<Vulnerabilities />);
    expect(container.firstChild).toMatchSnapshot();
  });
});

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
import { describe, it, expect, vi, Mock } from 'vitest';
import type { AuthUser } from '../../context/';
import { useAuthContext } from '@/context';
import Vulnerabilities from '../../pages/Vulnerabilities/Vulnerabilities';

const titlePool = [
  'CVE-2013-4041 Super Risky Vuln',
  'CVE-2013-4041 Super Menacing Vuln A',
  'CVE-2013-4041 Super Menacing Vuln B',
  'CVE-2013-4041 Super Menacing Vuln C',
  'CVE-2013-4041 Super Menacing Vuln D'
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
    const firstVulnTitle = await screen.findByText(
      /CVE-2013-4041 Super Risky Vuln/i
    );
    const menacingMatches = await screen.findAllByText(/Super Menacing Vuln/i);
    expect(firstVulnTitle).toBeInTheDocument();
    expect(menacingMatches.length).toBeGreaterThan(0);
  });

  it('supports server-side pagination', async () => {
    // server honors page & pageSize; default pageSize = 15
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

    expect(await screen.findByText(/Super Risky Vuln/i)).toBeInTheDocument();
    const menacingOnFirst = await screen.findAllByText(/Super Menacing Vuln/i);
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
    expect(await screen.findByText(/Super Risky Vuln/i)).toBeInTheDocument();
    const menacingOnSecond = await screen.findAllByText(/Super Menacing Vuln/i);
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

    expect(await screen.findByText(/Super Risky Vuln/i)).toBeInTheDocument();

    //click on sort icon button in Title header to sort by Title ascending
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

    const matches = await screen.findAllByText(/Super Menacing Vuln A/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  // it('supports server-side filtering', async () => {
  //   // server honors filters in body.filters
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

  //   expect(await screen.findByText(/Super Risky Vuln/i)).toBeInTheDocument();

  //   // // enter filter text into Title filter input
  //   // const titleFilterInput = screen.getByLabelText(/filter value/i);
  //   // fireEvent.change(titleFilterInput, {
  //   //   target: { value: 'Menacing Vuln B' }
  //   // });
  //   // open filters panel and enter filter text into the Title filter "Value" box
  //   const filtersButton =
  //     screen.queryByRole('button', { name: /filters?/i }) ||
  //     screen.queryByLabelText(/filters?/i) ||
  //     screen.getByRole('button', { name: /filter/i });

  //   fireEvent.click(filtersButton);

  //   // locate the "Value" input (try label, placeholder or fallback to any textbox)
  //   let titleFilterInput: HTMLElement | null = null;
  //   try {
  //     titleFilterInput = await screen.findByLabelText(/value/i);
  //   } catch {
  //     titleFilterInput =
  //       screen.queryByPlaceholderText(/value/i) ??
  //       screen.queryByLabelText(/value/i) ??
  //       (await screen.findByRole('textbox'));
  //   }
  //   // clear and type value using fireEvent to avoid relying on testUser's methods
  //   fireEvent.change(titleFilterInput as Element, { target: { value: '' } });
  //   fireEvent.change(titleFilterInput as Element, {
  //     target: { value: 'menacing' }
  //   });

  //   // wait for the debounced request to be sent and assert server received the filter
  //   await waitFor(() => {
  //     const calls = apiPostMock.mock.calls;
  //     const found = calls.some((call) =>
  //       call.some(
  //         (arg: any) =>
  //           arg &&
  //           arg.body &&
  //           arg.body.filters &&
  //           typeof arg.body.filters.title === 'string' &&
  //           arg.body.filters.title.toLowerCase().includes('menacing')
  //       )
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
  // });

  // it('renders empty state when api returns no results', async () => {
  //   apiPostMock.mockResolvedValueOnce({ result: [], count: 0 });

  //   render(<Vulnerabilities />, {
  //     initialHistory: ['/vulnerabilities'],
  //     authContext: {
  //       apiPost: apiPostMock,
  //       currentOrganization: null,
  //       user: testUser as unknown as AuthUser
  //     }
  //   });

  //   const noResultsText = await screen.findByText(/no results found/i);
  //   expect(noResultsText).toBeInTheDocument();
  // });

  it('matches snapshot', () => {
    const { container } = render(<Vulnerabilities />);
    expect(container.firstChild).toMatchSnapshot();
  });
});

import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryHistory } from 'history';
import { Router } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError } from '@/hooks/useApi';
import { useAuthContext } from 'context';
import { CFThemeProvider } from 'context/Theme';
import { useDomainApi } from 'hooks';
import { DomainDetails, generateWebpageTree } from 'pages/Domain/DomainDetails';

const { mockGetDomain } = vi.hoisted(() => ({
  mockGetDomain: vi.fn()
}));

vi.mock('hooks', () => ({
  useDomainApi: vi.fn()
}));

vi.mock('context', () => ({
  useAuthContext: vi.fn()
}));

const mockUseDomainApi = vi.mocked(useDomainApi);
const mockUseAuthContext = vi.mocked(useAuthContext);

beforeEach(() => {
  vi.clearAllMocks();
  mockUseDomainApi.mockReturnValue({
    getDomain: mockGetDomain,
    listDomains: vi.fn()
  } as ReturnType<typeof useDomainApi>);
  mockUseAuthContext.mockReturnValue({
    user: { user_type: 'standard' }
  } as ReturnType<typeof useAuthContext>);
});

describe('generateWebpageTree', () => {
  it('no path', () => {
    const pages = [
      {
        url: 'https://www.cisa.gov/'
      }
    ];
    const tree = generateWebpageTree(pages as any);
    expect(tree).toMatchSnapshot();
  });
  it('basic path', () => {
    const pages = [
      {
        url: 'https://www.cisa.gov/a/b/c'
      }
    ];
    const tree = generateWebpageTree(pages as any);
    expect(tree).toMatchSnapshot();
  });
  it('single path', () => {
    const pages = [
      {
        url: 'https://www.cisa.gov/a'
      }
    ];
    const tree = generateWebpageTree(pages as any);
    expect(tree).toMatchSnapshot();
  });
  it('trailing slash', () => {
    const pages = [
      {
        url: 'https://www.cisa.gov/a/'
      }
    ];
    const tree = generateWebpageTree(pages as any);
    expect(tree).toMatchSnapshot();
  });
});

describe('DomainDetails API error handling', () => {
  it('redirects a forbidden response to the 403 page', async () => {
    const history = createMemoryHistory({
      initialEntries: ['/inventory/domain/domain-1']
    });
    mockGetDomain.mockRejectedValueOnce(
      new ApiError(
        new Response(null, { status: 403, statusText: 'Forbidden' }),
        { detail: 'You do not have access to this domain.' }
      )
    );

    render(
      <CFThemeProvider>
        <Router history={history}>
          <DomainDetails domainId="domain-1" />
        </Router>
      </CFThemeProvider>
    );

    await waitFor(() => expect(history.location.pathname).toBe('/403'));
  });

  it('redirects a not-found response to the 404 page', async () => {
    const history = createMemoryHistory({
      initialEntries: ['/inventory/domain/domain-1']
    });
    mockGetDomain.mockRejectedValueOnce(
      new ApiError(
        new Response(null, { status: 404, statusText: 'Not Found' }),
        { detail: 'Domain not found.' }
      )
    );

    render(
      <CFThemeProvider>
        <Router history={history}>
          <DomainDetails domainId="domain-1" />
        </Router>
      </CFThemeProvider>
    );

    await waitFor(() => expect(history.location.pathname).toBe('/404'));
  });

  it('keeps authorized domain details visible for a successful response', async () => {
    mockGetDomain.mockResolvedValueOnce({
      name: 'example.com',
      ip: '192.0.2.1',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      country: null,
      cloud_hosted: false,
      organization: { name: 'Example Organization' },
      services: [],
      vulnerabilities: [],
      webpages: []
    });
    const history = createMemoryHistory({
      initialEntries: ['/inventory/domain/domain-1']
    });

    render(
      <CFThemeProvider>
        <Router history={history}>
          <DomainDetails domainId="domain-1" />
        </Router>
      </CFThemeProvider>
    );

    expect(
      await screen.findByRole('heading', { name: 'example.com' })
    ).toBeInTheDocument();
    expect(history.location.pathname).toBe('/inventory/domain/domain-1');
  });
});

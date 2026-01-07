import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor, render } from 'test-utils';
import userEvent from '@testing-library/user-event';
import { Router } from 'react-router-dom';
import { createMemoryHistory } from 'history';

import Organizations from '@/pages/Organizations';

// -----------------------
// Mocks
// -----------------------
const mockApiPost = vi.fn();
const mockSetFeedbackMessage = vi.fn();

vi.mock('context', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('context');
  return {
    ...actual,
    useAuthContext: () => ({
      apiPost: mockApiPost,
      setFeedbackMessage: mockSetFeedbackMessage
    })
  };
});

vi.mock('@/constants/endpoints', () => ({
  ENDPOINTS: {
    ORGANIZATIONS_SEARCH: '/api/organizations/search',
    ORGANIZATIONS: '/api/organizations'
  }
}));

vi.mock('@/constants/routes', () => ({
  ROUTES: {
    ORGANIZATION: '/organizations/:organizationId'
  }
}));

vi.mock('@/utils/logger', () => ({
  logger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn()
  }
}));

vi.mock('components/DataGrid/CustomToolbar', () => ({
  default: () => <div data-testid="mock-toolbar">Toolbar</div>
}));

vi.mock('components/Dialog/InfoDialog', () => ({
  default: ({
    isOpen,
    title,
    content
  }: {
    isOpen: boolean;
    title: React.ReactNode;
    content: React.ReactNode;
  }) => {
    if (!isOpen) return null;
    return (
      <div data-testid="mock-info-dialog">
        <div>{title}</div>
        <div>{content}</div>
      </div>
    );
  }
}));

vi.mock('@/pages/Organizations/OrganizationForm', () => ({
  OrganizationForm: ({
    open,
    setOpen,
    onSubmit
  }: {
    open: boolean;
    setOpen: (openValue: boolean) => void;
    onSubmit: (body: Record<string, unknown>) => Promise<void> | void;
  }) => {
    return (
      <div data-testid="mock-org-form">
        {!open && (
          <button type="button" onClick={() => setOpen(true)}>
            Open Create Organization
          </button>
        )}
        {open && (
          <button
            type="button"
            onClick={() => onSubmit({ name: 'New Org', acronym: 'NO' })}
          >
            Submit Create Organization
          </button>
        )}
      </div>
    );
  }
}));

vi.mock('@mui/x-data-grid', () => {
  const DataGrid = (props: any) => {
    const ToolbarComponent = props?.slots?.toolbar;

    return (
      <div>
        {props.showToolbar && ToolbarComponent && (
          <div data-testid="mock-datagrid-toolbar">
            <ToolbarComponent {...(props.slotProps?.toolbar ?? {})} />
          </div>
        )}

        {props.loading && <div role="progressbar">Loading</div>}

        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
          <button
            type="button"
            onClick={() =>
              props.onPaginationModelChange?.({
                page: 1,
                pageSize: props.paginationModel.pageSize
              })
            }
          >
            Next Page
          </button>

          <button
            type="button"
            onClick={() =>
              props.onPaginationModelChange?.({
                page: 0,
                pageSize: 30
              })
            }
          >
            Page Size 30
          </button>

          <button
            type="button"
            onClick={() =>
              props.onSortModelChange?.([{ field: 'name', sort: 'asc' }])
            }
          >
            Sort Name Asc
          </button>

          <button
            type="button"
            onClick={() =>
              props.onFilterModelChange?.({
                items: [{ field: 'name', value: 'A' }]
              })
            }
          >
            Filter Name "A"
          </button>

          <button
            type="button"
            onClick={() =>
              props.onFilterModelChange?.({
                items: [{ field: 'name', value: 'Ac' }]
              })
            }
          >
            Filter Name "Ac"
          </button>
        </div>

        <div data-testid="mock-datagrid-rows">
          {Array.isArray(props.rows) && props.rows.length === 0 && (
            <div>No rows</div>
          )}

          {Array.isArray(props.rows) &&
            props.rows.map((row: any) => (
              <div key={row.id} data-testid={`row-${row.id}`}>
                {props.columns.map((column: any) => (
                  <div
                    key={column.field}
                    data-testid={`cell-${row.id}-${column.field}`}
                  >
                    {column.renderCell
                      ? column.renderCell({ row })
                      : String(row[column.field] ?? '')}
                  </div>
                ))}
              </div>
            ))}
        </div>
      </div>
    );
  };

  return {
    DataGrid
  };
});

// -----------------------
// Helpers
// -----------------------
type DeferredPromise<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
};

function createDeferred<T>(): DeferredPromise<T> {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;

  const promise = new Promise<T>((resolveFn, rejectFn) => {
    resolve = resolveFn;
    reject = rejectFn;
  });

  return { promise, resolve, reject };
}

function renderWithHistory() {
  const history = createMemoryHistory();
  render(
    <Router history={history}>
      <Organizations />
    </Router>
  );
  return history;
}

// -----------------------
// Tests
// -----------------------
describe('Organizations page', () => {
  beforeEach(() => {
    mockApiPost.mockReset();
    mockSetFeedbackMessage.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // Verifies initial organizations fetch succeeds and rendered fields/actions appear.
  it('fetches organizations on mount (success) and renders fields', async () => {
    mockApiPost.mockResolvedValueOnce({
      result: [
        {
          id: 'org-1',
          name: 'Example Org',
          acronym: 'EO',
          state: 'VA',
          region_id: '1'
        }
      ],
      count: 1
    });

    renderWithHistory();

    await waitFor(() =>
      expect(mockApiPost).toHaveBeenCalledWith('/api/organizations/search', {
        body: {
          page: 1,
          pageSize: 15,
          sort: undefined,
          order: undefined,
          filters: {}
        }
      })
    );

    expect(
      screen.getByLabelText('Organization Name: Example Org')
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Acronym Name: EO')).toBeInTheDocument();
    expect(
      screen.getByLabelText('State for Organization Example Org: VA')
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Region for Organization Example Org: 1')
    ).toBeInTheDocument();

    expect(
      screen.getByRole('button', {
        name: 'View or Edit Organization Example Org'
      })
    ).toBeInTheDocument();
  });

  // Verifies loading indicator shows during pending fetch and disappears after resolve.
  it('shows loading state while request is pending and hides after resolve', async () => {
    const deferredResponse = createDeferred<{
      result: unknown[];
      count: number;
    }>();

    mockApiPost.mockReturnValueOnce(deferredResponse.promise);

    renderWithHistory();

    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    deferredResponse.resolve({ result: [], count: 0 });

    await waitFor(() =>
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    );
  });

  // Verifies fetch error renders error UI and retry triggers a successful refetch.
  it('shows error alert + retry button on fetch error, and retries successfully', async () => {
    mockApiPost
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({ result: [], count: 0 });

    renderWithHistory();

    await waitFor(() =>
      expect(
        screen.getByText('Error Loading Organizations!')
      ).toBeInTheDocument()
    );

    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));

    await waitFor(() => expect(mockApiPost).toHaveBeenCalledTimes(2));
    expect(screen.getByText('No rows')).toBeInTheDocument();
  });

  // Verifies empty results render an empty-state without crashing.
  it('handles empty data gracefully', async () => {
    mockApiPost.mockResolvedValueOnce({ result: [], count: 0 });

    renderWithHistory();

    await waitFor(() => expect(mockApiPost).toHaveBeenCalledTimes(1));
    expect(screen.getByText('No rows')).toBeInTheDocument();
  });

  // Verifies clicking View/Edit navigates to the correct organization detail route.
  it('navigates to the org detail route when View/Edit is clicked', async () => {
    const history = createMemoryHistory();

    mockApiPost.mockResolvedValueOnce({
      result: [
        {
          id: 'org-123',
          name: 'Navigate Org',
          acronym: 'NAV',
          state: 'NY',
          region_id: '2'
        }
      ],
      count: 1
    });

    render(
      <Router history={history}>
        <Organizations />
      </Router>
    );

    await waitFor(() =>
      expect(
        screen.getByRole('button', {
          name: 'View or Edit Organization Navigate Org'
        })
      ).toBeInTheDocument()
    );

    await userEvent.click(
      screen.getByRole('button', {
        name: 'View or Edit Organization Navigate Org'
      })
    );

    expect(history.location.pathname).toBe('/organizations/org-123');
  });

  // Verifies pagination updates send the correct request payload to the server.
  it('supports server pagination and sends correct request body', async () => {
    const user = userEvent.setup();

    mockApiPost.mockResolvedValueOnce({ result: [], count: 0 });
    mockApiPost.mockResolvedValueOnce({ result: [], count: 0 });
    mockApiPost.mockResolvedValueOnce({ result: [], count: 0 });

    renderWithHistory();

    await waitFor(() => expect(mockApiPost).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole('button', { name: 'Next Page' }));

    await waitFor(() =>
      expect(mockApiPost).toHaveBeenLastCalledWith(
        '/api/organizations/search',
        {
          body: {
            page: 2,
            pageSize: 15,
            sort: undefined,
            order: undefined,
            filters: {}
          }
        }
      )
    );

    await user.click(screen.getByRole('button', { name: 'Page Size 30' }));

    await waitFor(() =>
      expect(mockApiPost).toHaveBeenLastCalledWith(
        '/api/organizations/search',
        {
          body: {
            page: 1,
            pageSize: 30,
            sort: undefined,
            order: undefined,
            filters: {}
          }
        }
      )
    );
  });

  // Verifies sort changes send the correct sort/order payload to the server.
  it('supports server sorting and sends sort/order', async () => {
    const user = userEvent.setup();

    mockApiPost.mockResolvedValueOnce({ result: [], count: 0 });
    mockApiPost.mockResolvedValueOnce({ result: [], count: 0 });

    renderWithHistory();

    await waitFor(() => expect(mockApiPost).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole('button', { name: 'Sort Name Asc' }));

    await waitFor(() =>
      expect(mockApiPost).toHaveBeenLastCalledWith(
        '/api/organizations/search',
        {
          body: {
            page: 1,
            pageSize: 15,
            sort: 'name',
            order: 'asc',
            filters: {}
          }
        }
      )
    );
  });

  // Verifies filtering is debounced and only applies when input meets length rules.
  it('supports server filtering with debounce and name length gate', async () => {
    const user = userEvent.setup();

    mockApiPost.mockResolvedValue({ result: [], count: 0 });

    renderWithHistory();

    await waitFor(() => expect(mockApiPost).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole('button', { name: 'Filter Name "A"' }));

    await waitFor(() =>
      expect(mockApiPost).toHaveBeenLastCalledWith(
        '/api/organizations/search',
        {
          body: {
            page: 1,
            pageSize: 15,
            sort: undefined,
            order: undefined,
            filters: {}
          }
        }
      )
    );

    await user.click(screen.getByRole('button', { name: 'Filter Name "Ac"' }));

    await waitFor(() =>
      expect(mockApiPost).toHaveBeenLastCalledWith(
        '/api/organizations/search',
        {
          body: {
            page: 1,
            pageSize: 15,
            sort: undefined,
            order: undefined,
            filters: { name: 'Ac' }
          }
        }
      )
    );
  });

  // Verifies creating an organization posts the correct payload and shows success UI.
  it('creates an organization (submit success) and shows success dialog', async () => {
    const user = userEvent.setup();

    mockApiPost.mockResolvedValueOnce({ result: [], count: 0 });

    mockApiPost.mockResolvedValueOnce({
      id: 'org-new',
      name: 'New Org',
      acronym: 'NO',
      state: 'CA',
      region_id: '3'
    });

    renderWithHistory();

    await waitFor(() => expect(mockApiPost).toHaveBeenCalledTimes(1));

    await user.click(
      screen.getByRole('button', { name: 'Open Create Organization' })
    );

    await user.click(
      screen.getByRole('button', { name: 'Submit Create Organization' })
    );

    await waitFor(() =>
      expect(mockApiPost).toHaveBeenCalledWith('/api/organizations', {
        body: { name: 'New Org', acronym: 'NO' }
      })
    );

    expect(screen.getByTestId('mock-info-dialog')).toBeInTheDocument();
    expect(
      screen.getByText('The new organization was successfully added.')
    ).toBeInTheDocument();

    expect(screen.getByTestId('row-org-new')).toBeInTheDocument();
  });

  // Verifies create submission 422 errors surface via feedback messaging.
  it('handles create submission error by calling setFeedbackMessage (422 path)', async () => {
    const user = userEvent.setup();

    mockApiPost.mockResolvedValueOnce({ result: [], count: 0 });

    mockApiPost.mockRejectedValueOnce({ status: 422 });

    renderWithHistory();

    await waitFor(() => expect(mockApiPost).toHaveBeenCalledTimes(1));

    await user.click(
      screen.getByRole('button', { name: 'Open Create Organization' })
    );

    await user.click(
      screen.getByRole('button', { name: 'Submit Create Organization' })
    );

    await waitFor(() =>
      expect(mockSetFeedbackMessage).toHaveBeenCalledWith({
        message: 'Error when submitting organization entry.',
        type: 'error'
      })
    );
  });
});

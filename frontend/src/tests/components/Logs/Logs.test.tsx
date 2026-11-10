import React from 'react';
import userEvent from '@testing-library/user-event';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Logs } from '@/components/Logs/Logs';
import { ENDPOINTS } from '@/constants/endpoints';
const contextMocks = vi.hoisted(() => ({
  useAuthContext: vi.fn()
}));

vi.mock('@/context', () => ({
  AuthContext: {
    Provider: ({ children }: { children: React.ReactNode }) => children
  },
  useAuthContext: contextMocks.useAuthContext
}));

const renderLogs = (apiPost: any) =>
  (() => {
    contextMocks.useAuthContext.mockReturnValue({ apiPost });
    return render(<Logs />);
  })();

vi.mock('@/components/DataGrid/CustomToolbar', () => ({
  default: ({ hasActiveFilters }: { hasActiveFilters?: boolean }) => (
    <span data-testid="logs-filter-badge">{String(hasActiveFilters)}</span>
  )
}));

vi.mock('../../../components/DataGrid/CustomDataGrid', () => ({
  default: ({
    rows,
    slotProps,
    slots,
    loading,
    onFilterModelChange,
    onPaginationModelChange,
    columns
  }: any) => {
    const Toolbar = slots?.toolbar;
    const detailsColumn = columns.find(
      (column: any) => column.field === 'details'
    );

    return (
      <div data-testid="logs-grid">
        <span data-testid="logs-loading">{String(loading)}</span>
        {Toolbar && <Toolbar {...slotProps?.toolbar} />}
        <button
          type="button"
          data-testid="apply-log-filter"
          onClick={() =>
            onFilterModelChange({
              items: [
                {
                  field: 'event_type',
                  operator: 'contains',
                  value: 'login'
                }
              ]
            })
          }
        >
          Apply filter
        </button>
        <button
          type="button"
          data-testid="next-log-page"
          onClick={() => onPaginationModelChange({ page: 1, pageSize: 15 })}
        >
          Next page
        </button>
        {rows.map((row: any) => (
          <div key={row.id}>
            {detailsColumn?.renderCell?.({ row, tabIndex: 0, value: null })}
          </div>
        ))}
      </div>
    );
  }
}));

describe('Logs', () => {
  const logResponse = {
    count: 1,
    result: [
      {
        id: 'log-1',
        created_at: '2024-01-01T00:00:00Z',
        event_type: 'login',
        result: 'success',
        payload: { user: { email: 'user@example.com' } }
      }
    ]
  };

  it('keeps the grid mounted while logs are loading', () => {
    const apiPost = vi.fn(() => new Promise(() => {}));

    renderLogs(apiPost);

    expect(screen.getByTestId('logs-grid')).toBeInTheDocument();
    expect(screen.getByTestId('logs-loading').textContent).toBe('true');
  });

  it('debounces server-side filters and maps the field to the API request', async () => {
    const apiPost = vi.fn().mockResolvedValue(logResponse);
    const user = userEvent.setup();

    renderLogs(apiPost);
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    await user.click(screen.getByTestId('apply-log-filter'));
    expect(screen.getByTestId('logs-filter-badge').textContent).toBe('true');

    await new Promise((resolve) => setTimeout(resolve, 250));
    expect(apiPost).toHaveBeenCalledTimes(1);

    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(2), {
      timeout: 1000
    });
    expect(apiPost.mock.calls[1]).toEqual([
      ENDPOINTS.LOGS_FILTERED_SEARCH,
      {
        body: {
          page: 1,
          page_size: 15,
          filters: {
            event_type: { value: 'login', operator: 'contains' }
          }
        }
      }
    ]);
  });

  it('requests the next server-side page', async () => {
    const apiPost = vi.fn().mockResolvedValue(logResponse);
    const user = userEvent.setup();

    renderLogs(apiPost);
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    await user.click(screen.getByTestId('next-log-page'));

    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(2));
    expect(apiPost.mock.calls[1][1]).toEqual({
      body: { page: 2, page_size: 15, filters: {} }
    });
  });

  it('opens the payload details dialog for a log row', async () => {
    const apiPost = vi.fn().mockResolvedValue(logResponse);
    const user = userEvent.setup();

    renderLogs(apiPost);
    await screen.findByLabelText('Details for Log 0');
    await user.click(screen.getByLabelText('Details for Log 0'));

    expect(await screen.findByText('Payload Details')).toBeInTheDocument();
  });
});

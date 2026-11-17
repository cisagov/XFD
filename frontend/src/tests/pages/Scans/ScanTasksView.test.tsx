import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ScanTasksView from '@/pages/Scans/ScanTasksView';
import { ENDPOINTS } from '@/constants/endpoints';
import { authCtx } from '@/test-utils/authCtx';
import { useAuthContext } from '@/context';

vi.mock('@/context', () => ({
  useAuthContext: vi.fn()
}));

vi.mock('@/components/DataGrid/CustomToolbar', () => ({
  default: ({ hasActiveFilters }: { hasActiveFilters?: boolean }) => (
    <span data-testid="scan-task-filter-badge">{String(hasActiveFilters)}</span>
  )
}));

vi.mock('@/components/DataGrid/CustomPagination', () => ({
  default: () => <div data-testid="scan-task-pagination" />
}));

vi.mock('@/components/DataGrid/CustomDataGrid', () => ({
  default: ({ loading, slotProps, slots, onFilterModelChange, rows }: any) => {
    const Toolbar = slots?.toolbar;
    return (
      <div data-testid="scan-task-grid">
        <span data-testid="scan-task-loading">{String(loading)}</span>
        {Toolbar && <Toolbar {...slotProps?.toolbar} />}
        <button
          type="button"
          data-testid="apply-scan-task-filter"
          onClick={() =>
            onFilterModelChange({
              items: [
                { field: 'status', operator: 'contains', value: 'failed' }
              ]
            })
          }
        >
          Apply filter
        </button>
        <button
          type="button"
          data-testid="clear-scan-task-filter"
          onClick={() => onFilterModelChange({ items: [] })}
        >
          Clear filter
        </button>
        {rows.map((row: { id: string }) => (
          <span key={row.id}>{row.id}</span>
        ))}
      </div>
    );
  }
}));

describe('ScanTasksView', () => {
  const scanTaskResponse = {
    result: [
      {
        id: 'task-1',
        status: 'finished',
        input: '{}',
        output: '{}',
        created_at: '2024-01-01T00:00:00Z',
        started_at: '2024-01-01T00:00:00Z',
        requested_at: '2024-01-01T00:00:00Z',
        finished_at: '2024-01-01T00:00:00Z',
        concurrency_index: 1,
        fargate_task_arn: '',
        scan: { name: 'censys' }
      }
    ],
    count: 1
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuthContext).mockReturnValue({
      ...authCtx,
      apiPost: vi.fn().mockResolvedValue(scanTaskResponse)
    });
  });

  it('keeps the grid mounted while the initial request is pending', () => {
    const apiPost = vi.fn(() => new Promise(() => {}));
    vi.mocked(useAuthContext).mockReturnValue({
      ...authCtx,
      apiPost
    });

    render(<ScanTasksView />);

    expect(screen.getByTestId('scan-task-grid')).toBeInTheDocument();
    expect(screen.getByTestId('scan-task-loading').textContent).toBe('true');
  });

  it('sends a server-side filter request after the debounce delay', async () => {
    const apiPost = vi.fn().mockResolvedValue(scanTaskResponse);
    vi.mocked(useAuthContext).mockReturnValue({
      ...authCtx,
      apiPost
    });

    const user = userEvent.setup();

    render(<ScanTasksView />);

    // Wait for initial load and rendered state, rather than assuming one request.
    await waitFor(() => {
      expect(screen.getByText('task-1')).toBeInTheDocument();
    });

    // Ignore initial-load requests but retain the mock's resolved-value behavior.
    apiPost.mockClear();

    await user.click(screen.getByTestId('apply-scan-task-filter'));

    // The request must not be immediate.
    expect(apiPost).not.toHaveBeenCalled();

    // Assert the debounced request is eventually made with the intended filter.
    await waitFor(
      () => {
        expect(apiPost).toHaveBeenCalledWith(ENDPOINTS.SCANS_TASK_SEARCH, {
          body: expect.objectContaining({
            filters: {
              status: 'failed'
            }
          })
        });
      },
      { timeout: 1500 }
    );
  });
  it('clears the server-side filter and active-filter badge immediately', async () => {
    const apiPost = vi.fn().mockResolvedValue(scanTaskResponse);
    vi.mocked(useAuthContext).mockReturnValue({
      ...authCtx,
      apiPost
    });
    const user = userEvent.setup();

    render(<ScanTasksView />);

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(
        ENDPOINTS.SCANS_TASK_SEARCH,
        expect.anything()
      );
    });
    await user.click(screen.getByTestId('apply-scan-task-filter'));
    await waitFor(
      () => {
        expect(apiPost.mock.calls.at(-1)?.[1]?.body?.filters).toEqual({
          status: 'failed'
        });
      },
      { timeout: 1000 }
    );

    expect(screen.getByTestId('scan-task-filter-badge')).toHaveTextContent(
      'true'
    );

    const callCountBeforeClear = apiPost.mock.calls.length;

    await user.click(screen.getByTestId('clear-scan-task-filter'));
    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledTimes(callCountBeforeClear + 1);
    });

    expect(apiPost.mock.calls.at(-1)?.[1]?.body?.filters).toEqual({});
    expect(screen.getByTestId('scan-task-filter-badge')).toHaveTextContent(
      'false'
    );
  });
});

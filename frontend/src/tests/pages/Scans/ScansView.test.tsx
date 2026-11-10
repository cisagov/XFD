import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ScansView from '@/pages/Scans/ScansView';
import { useAuthContext } from 'context';
import { ENDPOINTS } from '@/constants/endpoints';
import { logger } from '@/utils/logger';
const apiGet = vi.fn();
const apiPost = vi.fn();
const apiDelete = vi.fn();
vi.mock('context', () => ({
  useAuthContext: vi.fn()
}));
vi.mock('@/utils/logger', () => ({
  logger: {
    error: vi.fn()
  }
}));
/**
The real DataGrid is tested separately. This mock renders:
- Toolbar children, including "Add New Scan"
- Each row's cell renderers

It allows these tests to exercise the page's action-column callbacks
without requiring MUI DataGrid virtualization support in jsdom.
**/
vi.mock('@/components/DataGrid/CustomDataGrid', () => ({
  default: ({ rows, columns, slotProps }: any) => (
    <div data-testid="custom-data-grid">
      <div data-testid="grid-toolbar">{slotProps?.toolbar?.children}</div>
      <span data-testid="has-active-filters">
        {String(slotProps?.toolbar?.hasActiveFilters)}
      </span>
      {rows.map((row: Record<string, unknown>) => (
        <div key={String(row.id)} data-testid={`scan-row-${row.id}`}>
          {columns.map((column: any) => (
            <div
              key={column.field}
              data-testid={`cell-${row.id}-${column.field}`}
            >
              {column.renderCell
                ? column.renderCell({
                    row,
                    value: row[column.field],
                    tabIndex: 0
                  })
                : String(row[column.field] ?? '')}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}));
vi.mock('components/DataGrid/CustomToolbar', () => ({
  default: () => <div data-testid="custom-toolbar" />
}));
/**
Simplified dialog implementation.

ConfirmDialog is tested separately. This mock lets us verify ScansView:
- opens the correct dialog
- sends the appropriate API request after confirmation
- closes dialogs after cancel/confirm actions
**/
vi.mock('@/components/Dialog/ConfirmDialog', () => ({
  default: ({
    isOpen,
    title,
    content,
    onConfirm,
    onCancel
  }: {
    isOpen: boolean;
    title: string;
    content: React.ReactNode;
    onConfirm?: () => void;
    onCancel: () => void;
  }) => {
    if (!isOpen) {
      return null;
    }
    return (
      <section role="dialog" aria-label={title}>
        <h2>{title}</h2>
        <div>{content}</div>
        {onConfirm && (
          <button type="button" onClick={onConfirm}>
            Confirm
          </button>
        )}
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </section>
    );
  }
}));
/**
ScanForm has its own unit tests. Here, the mock provides a form with a
representative valid submission payload and invokes ScansView.onSubmit.
**/
vi.mock('components/ScanForm', () => ({
  ScanForm: ({
    onSubmit
  }: {
    onSubmit: (values: Record<string, unknown>) => Promise<void>;
  }) => (
    <form
      aria-label="create-scan-form"
      onSubmit={(event) => {
        event.preventDefault();
        void onSubmit({
          name: 'new-scan',
          arguments: '{"assetType":"domain"}',
          organizations: [{ label: 'Organization One', value: 'org-1' }],
          frequency: 2,
          frequencyUnit: 'hour',
          is_granular: false,
          is_user_modifiable: false,
          is_single_scan: false,
          tags: [{ label: 'Production', value: 'tag-1' }],
          concurrent_tasks: 3,
          useDateRange: false
        });
      }}
    >
      <button type="submit">Create Scan</button>
    </form>
  )
}));
const scan = {
  id: 'scan-1',
  name: 'test-scan',
  tags: [{ id: 'tag-1', name: 'Production' }],
  frequency: 3600,
  last_run: null,
  concurrent_tasks: 2,
  is_single_scan: false
};
const scanSchema = {
  'test-scan': {
    description: 'A test scan',
    is_passive: false
  }
};
const loadScansResponse = {
  scans: [scan],
  organizations: [{ id: 'org-1', name: 'Organization One' }],
  schema: scanSchema
};
describe('ScansView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet,
      apiPost,
      apiDelete
    } as any);
    apiGet.mockImplementation((endpoint: string) => {
      if (endpoint === ENDPOINTS.SCANS) {
        return Promise.resolve(loadScansResponse);
      }
      if (endpoint === ENDPOINTS.ORGANIZATIONS_TAGS) {
        return Promise.resolve([{ id: 'tag-1', name: 'Production' }]);
      }
      return Promise.resolve([]);
    });
    apiPost.mockResolvedValue({
      id: 'scan-2',
      name: 'new-scan',
      tags: [],
      frequency: 7200,
      last_run: null,
      concurrent_tasks: 3,
      is_single_scan: false
    });
    apiDelete.mockResolvedValue(undefined);
  });
  it('loads scans and displays mapped scan data', async () => {
    render(<ScansView />);
    expect(await screen.findByTestId('custom-data-grid')).toBeInTheDocument();
    expect(apiGet).toHaveBeenCalledWith(ENDPOINTS.SCANS);
    expect(apiGet).toHaveBeenCalledWith(ENDPOINTS.ORGANIZATIONS_TAGS);
    expect(screen.getByLabelText('Scan name: test-scan')).toBeInTheDocument();
    expect(
      screen.getByLabelText('Tags for test-scan scan: Production')
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Mode for test-scan scan: Active')
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Frequency for test-scan scan: 1 hour')
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Last run for test-scan scan: None')
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Concurrent tasks for test-scan scan: 2')
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Description for test-scan scan: A test scan')
    ).toBeInTheDocument();
    expect(screen.getByTestId('has-active-filters').textContent).toBe('false');
  });
  it('shows an empty-state message and allows a user to create a scan when no scans exist', async () => {
    const user = userEvent.setup();

    apiGet.mockImplementation((endpoint: string) => {
      if (endpoint === ENDPOINTS.SCANS) {
        return Promise.resolve({
          scans: [],
          organizations: [],
          schema: {}
        });
      }
      if (endpoint === ENDPOINTS.ORGANIZATIONS_TAGS) {
        return Promise.resolve([]);
      }
      return Promise.resolve([]);
    });
    render(<ScansView />);
    expect(
      await screen.findByText(
        'No scans found. Create a new scan with the "Add New Scan" button.'
      )
    ).toBeInTheDocument();
    expect(screen.getByTestId('custom-data-grid')).toBeInTheDocument();
    const addNewScanButton = screen.getByRole('button', {
      name: 'Add New Scan'
    });
    expect(addNewScanButton).toBeInTheDocument();
    await user.click(addNewScanButton);
    expect(
      screen.getByRole('dialog', { name: 'Add a Scan' })
    ).toBeInTheDocument();
  });
  it('logs an error when loading scans fails', async () => {
    const error = new Error('Unable to load scans');
    apiGet.mockRejectedValueOnce(error);
    render(<ScansView />);
    await waitFor(() => {
      expect(logger.error).toHaveBeenCalledWith(
        'ScansView.fetchScans failed:',
        { error }
      );
    });
  });
  it('opens the run-scan confirmation dialog for the selected scan', async () => {
    const user = userEvent.setup();
    render(<ScansView />);
    const runButton = await screen.findByRole('button', {
      name: 'Run test-scan scan.'
    });
    await user.click(runButton);
    const dialog = screen.getByRole('dialog', { name: 'Run scan?' });
    expect(dialog).toBeInTheDocument();
    expect(
      within(dialog).getByText(/are you sure you would like to run the/i)
    ).toBeInTheDocument();
    expect(within(dialog).getByText('test-scan')).toBeInTheDocument();
  });
  it('runs the selected scan and invokes the scheduler after confirmation', async () => {
    const user = userEvent.setup();
    render(<ScansView />);
    await user.click(
      await screen.findByRole('button', {
        name: 'Run test-scan scan.'
      })
    );
    const dialog = screen.getByRole('dialog', { name: 'Run scan?' });
    await user.click(within(dialog).getByRole('button', { name: 'Confirm' }));
    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(
        ENDPOINTS.SCAN_RUN.replace('{scan_id}', 'scan-1'),
        { body: {} }
      );
    });
    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(ENDPOINTS.SCAN_SCHEDULER, {
        body: {}
      });
    });
    expect(
      screen.queryByRole('dialog', { name: 'Run scan?' })
    ).not.toBeInTheDocument();
  });
  it('does not run a scan when the Run Scan dialog is cancelled', async () => {
    const user = userEvent.setup();
    render(<ScansView />);
    await user.click(
      await screen.findByRole('button', {
        name: 'Run test-scan scan.'
      })
    );
    const dialog = screen.getByRole('dialog', { name: 'Run scan?' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(apiPost).not.toHaveBeenCalled();
    expect(
      screen.queryByRole('dialog', { name: 'Run scan?' })
    ).not.toBeInTheDocument();
  });

  it('logs an error and invokes the scheduler when running a scan fails', async () => {
    const user = userEvent.setup();
    const runError = new Error('Run failed');

    apiPost.mockRejectedValueOnce(runError).mockResolvedValueOnce(undefined);

    render(<ScansView />);

    await user.click(
      await screen.findByRole('button', {
        name: 'Run test-scan scan.'
      })
    );

    await user.click(
      within(screen.getByRole('dialog', { name: 'Run scan?' })).getByRole(
        'button',
        { name: 'Confirm' }
      )
    );

    await waitFor(() => {
      expect(logger.error).toHaveBeenCalledWith('ScansView.runScan failed:', {
        error: runError,
        scanId: 'scan-1'
      });
    });

    expect(apiPost).toHaveBeenCalledWith(
      ENDPOINTS.SCAN_RUN.replace('{scan_id}', 'scan-1'),
      { body: {} }
    );

    expect(apiPost).toHaveBeenCalledWith(ENDPOINTS.SCAN_SCHEDULER, {
      body: {}
    });
  });
  it('opens the delete confirmation dialog for the selected scan', async () => {
    const user = userEvent.setup();
    render(<ScansView />);
    await user.click(
      await screen.findByRole('button', {
        name: 'Delete test-scan scan.'
      })
    );
    const dialog = screen.getByRole('dialog', { name: 'Delete scan?' });
    expect(dialog).toBeInTheDocument();
    expect(
      within(dialog).getByText(/are you sure you would like to delete/i)
    ).toBeInTheDocument();
    expect(within(dialog).getByText('test-scan')).toBeInTheDocument();
  });
  it('deletes the selected scan after confirmation', async () => {
    const user = userEvent.setup();
    render(<ScansView />);
    await user.click(
      await screen.findByRole('button', {
        name: 'Delete test-scan scan.'
      })
    );
    const dialog = screen.getByRole('dialog', { name: 'Delete scan?' });
    await user.click(within(dialog).getByRole('button', { name: 'Confirm' }));
    await waitFor(() => {
      expect(apiDelete).toHaveBeenCalledWith(
        ENDPOINTS.SCAN.replace('{scan_id}', 'scan-1')
      );
    });
    await waitFor(() => {
      expect(
        screen.queryByLabelText('Scan name: test-scan')
      ).not.toBeInTheDocument();
    });
    expect(
      screen.queryByRole('dialog', { name: 'Delete scan?' })
    ).not.toBeInTheDocument();
  });
  it('shows a specific error when deletion returns status 422', async () => {
    const user = userEvent.setup();
    const deleteError = { status: 422 };
    apiDelete.mockRejectedValueOnce(deleteError);
    render(<ScansView />);
    await user.click(
      await screen.findByRole('button', {
        name: 'Delete test-scan scan.'
      })
    );
    await user.click(
      within(screen.getByRole('dialog', { name: 'Delete scan?' })).getByRole(
        'button',
        { name: 'Confirm' }
      )
    );
    expect(
      await screen.findByText('Unable to delete scan')
    ).toBeInTheDocument();
    expect(logger.error).toHaveBeenCalledWith('ScansView.deleteRow failed:', {
      error: deleteError,
      scanId: 'scan-1'
    });
  });
  it('opens and cancels the Add New Scan dialog', async () => {
    const user = userEvent.setup();
    render(<ScansView />);
    await user.click(
      await screen.findByRole('button', { name: 'Add New Scan' })
    );
    const dialog = screen.getByRole('dialog', { name: 'Add a Scan' });
    expect(dialog).toBeInTheDocument();
    expect(
      within(dialog).getByRole('form', { name: 'create-scan-form' })
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(
      screen.queryByRole('dialog', { name: 'Add a Scan' })
    ).not.toBeInTheDocument();
  });
  it('submits a new scan with converted frequency, organization IDs, and tag IDs', async () => {
    const user = userEvent.setup();
    render(<ScansView />);
    await user.click(
      await screen.findByRole('button', { name: 'Add New Scan' })
    );
    const dialog = screen.getByRole('dialog', { name: 'Add a Scan' });
    await user.click(
      within(dialog).getByRole('button', { name: 'Create Scan' })
    );
    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(ENDPOINTS.SCANS, {
        body: expect.objectContaining({
          name: 'new-scan',
          arguments: { assetType: 'domain' },
          organizations: ['org-1'],
          tags: [{ id: 'tag-1' }],
          frequency: 7200,
          frequencyUnit: 'hour',
          concurrent_tasks: 3
        })
      });
    });
    expect(
      await screen.findByText('Scan created successfully!')
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('dialog', { name: 'Add a Scan' })
    ).not.toBeInTheDocument();
  });
  it('keeps the Add New Scan dialog open and shows an error when creation fails', async () => {
    const user = userEvent.setup();
    const createError = new Error('Unable to create scan');
    apiPost.mockRejectedValueOnce(createError);
    render(<ScansView />);
    await user.click(
      await screen.findByRole('button', { name: 'Add New Scan' })
    );
    const dialog = screen.getByRole('dialog', { name: 'Add a Scan' });
    await user.click(
      within(dialog).getByRole('button', { name: 'Create Scan' })
    );
    expect(
      await screen.findByText('Scan creation failed: Unable to create scan')
    ).toBeInTheDocument();
    expect(screen.getByText('Unable to create scan')).toBeInTheDocument();
    expect(
      screen.getByRole('dialog', { name: 'Add a Scan' })
    ).toBeInTheDocument();
    expect(logger.error).toHaveBeenCalledWith('ScansView.createScan failed:', {
      error: createError
    });
  });
  it('invokes the scheduler manually', async () => {
    const user = userEvent.setup();
    render(<ScansView />);
    await user.click(
      screen.getByRole('button', { name: 'Manually run scheduler' })
    );
    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(ENDPOINTS.SCAN_SCHEDULER, {
        body: {}
      });
    });
  });
  it('shows an error when manually invoking the scheduler fails', async () => {
    const user = userEvent.setup();
    const schedulerError = new Error('Scheduler unavailable');
    apiPost.mockRejectedValueOnce(schedulerError);
    render(<ScansView />);
    await user.click(
      screen.getByRole('button', { name: 'Manually run scheduler' })
    );
    expect(await screen.findByText('Invocation failed.')).toBeInTheDocument();
    expect(logger.error).toHaveBeenCalledWith(
      'ScansView.invokeScheduler failed:',
      { error: schedulerError }
    );
  });
});
